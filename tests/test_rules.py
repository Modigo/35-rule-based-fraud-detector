from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from app.models.transaction import Transaction
from app.rules import (
    HighAmountRule, RuleConfig, RuleContext, RuleEngine, RuleStatus, RiskBand,
    UnusualAmountRule, VelocityRule, UnfamiliarDeviceRule, UnusualGeographyRule,
)

def tx(id="current", customer="c1", amount="100.00", minutes=0, device="d1", country="NG", currency="NGN"):
    stamp = datetime(2025, 1, 1, 12, tzinfo=timezone.utc) + timedelta(minutes=minutes)
    return Transaction(transaction_id=id, customer_id=customer, amount=Decimal(amount), currency=currency,
        timestamp=stamp, merchant_category="groceries", channel="card", device_id=device,
        country_code=country, created_at=stamp)

def test_high_amount_threshold_is_inclusive_and_explained():
    result = HighAmountRule(Decimal("1000")).evaluate(RuleContext(tx(amount="1000"), ()))
    assert result.status is RuleStatus.TRIGGERED and result.score == 35
    assert "threshold" in result.explanation

def test_high_amount_below_threshold_does_not_trigger():
    assert HighAmountRule(Decimal("1000")).evaluate(
        RuleContext(tx(amount="999.99"), ())).status is RuleStatus.NOT_TRIGGERED

def test_unusual_amount_reports_insufficient_history():
    history = (tx("old1", amount="10", minutes=-10), tx("old2", amount="12", minutes=-20))
    result = UnusualAmountRule(min_history=3).evaluate(RuleContext(tx(amount="1000"), history))
    assert result.status is RuleStatus.INSUFFICIENT_HISTORY and result.score == 0

def test_unusual_amount_uses_prior_mean_and_same_currency():
    history = tuple(tx(f"old{i}", amount="100", minutes=-i) for i in (1, 2, 3))
    result = UnusualAmountRule().evaluate(RuleContext(tx(amount="300"), history))
    assert result.status is RuleStatus.TRIGGERED
    assert "mean 100.00" in result.explanation

def test_unusual_amount_does_not_mix_currencies():
    history = tuple(tx(f"old{i}", amount="10", minutes=-i, currency="USD") for i in (1, 2, 3))
    result = UnusualAmountRule().evaluate(RuleContext(tx(amount="500"), history))
    assert result.status is RuleStatus.INSUFFICIENT_HISTORY

def test_velocity_triggers_only_above_maximum():
    current = tx()
    two_prior = (tx("a", minutes=-1), tx("b", minutes=-2))
    assert VelocityRule(max_transactions=3).evaluate(
        RuleContext(current, two_prior)).status is RuleStatus.NOT_TRIGGERED
    third = tx("c", minutes=-3)
    result = VelocityRule(max_transactions=3).evaluate(RuleContext(current, two_prior + (third,)))
    assert result.status is RuleStatus.TRIGGERED and "4 transactions" in result.explanation

def test_velocity_ignores_history_outside_window():
    result = VelocityRule(window_seconds=60, max_transactions=1).evaluate(
        RuleContext(tx(), (tx("old", minutes=-10),)))
    assert result.status is RuleStatus.NOT_TRIGGERED

def test_unfamiliar_device_requires_history_and_detects_new_device():
    current = tx(device="new")
    rule = UnfamiliarDeviceRule()
    assert rule.evaluate(RuleContext(current, ())).status is RuleStatus.INSUFFICIENT_HISTORY
    old = tx("old", minutes=-60, device="known")
    result = rule.evaluate(RuleContext(current, (old,)))
    assert result.status is RuleStatus.TRIGGERED and "new" in result.explanation

def test_known_device_does_not_trigger():
    assert UnfamiliarDeviceRule().evaluate(
        RuleContext(tx(device="known"), (tx("old", minutes=-1, device="known"),))
    ).status is RuleStatus.NOT_TRIGGERED

def test_geography_requires_recent_history_and_detects_change():
    rule = UnusualGeographyRule(window_minutes=60)
    current = tx(country="GB")
    assert rule.evaluate(RuleContext(current, ())).status is RuleStatus.INSUFFICIENT_HISTORY
    old = tx("old", minutes=-20, country="NG")
    result = rule.evaluate(RuleContext(current, (old,)))
    assert result.status is RuleStatus.TRIGGERED and "NG to GB" in result.explanation

def test_geography_ignores_old_history():
    result = UnusualGeographyRule().evaluate(RuleContext(tx(country="GB"), (tx("old", minutes=-120),)))
    assert result.status is RuleStatus.INSUFFICIENT_HISTORY

def test_engine_filters_other_customer_and_future_history():
    current = tx()
    wrong_customer = tx("other", customer="c2", amount="2000000", minutes=-1)
    future = tx("future", amount="2000000", minutes=1)
    config = RuleConfig(enabled_rules=frozenset({"velocity"}), velocity_max_transactions=1)
    result = RuleEngine(config).evaluate(current, (wrong_customer, future))
    velocity = next(r for r in result.rule_results if r.rule_id == "velocity")
    assert velocity.status is RuleStatus.NOT_TRIGGERED

def test_disabled_rules_are_reported_but_do_not_score():
    result = RuleEngine(RuleConfig(enabled_rules=frozenset({"velocity"}))).evaluate(tx(amount="2000000"))
    high = next(r for r in result.rule_results if r.rule_id == "high_amount")
    assert high.status is RuleStatus.DISABLED and high.score == 0
    assert result.risk_score == 0

def test_score_is_capped_at_100():
    current = tx(amount="2000000", device="new", country="GB")
    old = tx("old", amount="10", minutes=-10, device="old-device", country="NG")
    config = RuleConfig(enabled_rules=frozenset({"high_amount", "unfamiliar_device", "unusual_geography"}),
        high_amount_score=80, unfamiliar_device_score=40, unusual_geography_score=40)
    assessment = RuleEngine(config).evaluate(current, (old,))
    assert assessment.risk_score == 100 and assessment.risk_band is RiskBand.HIGH

@pytest.mark.parametrize(("score", "band"), [
    (0, RiskBand.LOW), (29, RiskBand.LOW), (30, RiskBand.MEDIUM),
    (59, RiskBand.MEDIUM), (60, RiskBand.HIGH), (100, RiskBand.HIGH),
])
def test_risk_band_boundaries(score, band):
    class FixedRule:
        rule_id = "high_amount"
        name = "Boundary test"
        def evaluate(self, context):
            from app.rules.models import RuleResult
            return RuleResult(self.rule_id, self.name,
                RuleStatus.TRIGGERED if score else RuleStatus.NOT_TRIGGERED, score, "test")
    config = replace(RuleConfig(), enabled_rules=frozenset({"high_amount"}))
    assert RuleEngine(config, (FixedRule(),)).evaluate(tx()).risk_band is band

def test_assessment_exposes_triggered_explanations_only():
    assessment = RuleEngine().evaluate(tx(amount="2000000"))
    assert assessment.triggered_rules
    assert assessment.explanations
    assert all(r.explanation for r in assessment.triggered_rules)

def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError, match="Unknown rule IDs"):
        RuleConfig(enabled_rules=frozenset({"made_up"}))
    with pytest.raises(ValueError, match="positive"):
        RuleConfig(high_amount_threshold=Decimal("0"))
    with pytest.raises(ValueError, match="risk boundaries"):
        RuleConfig(low_risk_max=59, medium_risk_max=59)
    with pytest.raises(ValueError, match="score"):
        RuleConfig(velocity_score=101)

def test_empty_history_is_safe():
    assessment = RuleEngine().evaluate(tx())
    assert 0 <= assessment.risk_score <= 100
    assert any(r.status is RuleStatus.INSUFFICIENT_HISTORY for r in assessment.rule_results)
