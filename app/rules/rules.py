"""Pure, independently testable rules; no API or persistence dependencies."""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Protocol
from app.models.transaction import Transaction
from app.rules.config import RuleConfig
from app.rules.models import RuleResult, RuleStatus

@dataclass(frozen=True)
class RuleContext:
    transaction: Transaction
    history: tuple[Transaction, ...]

class FraudRule(Protocol):
    rule_id: str
    name: str
    def evaluate(self, context: RuleContext) -> RuleResult: ...

def result(rule_id, name, status, score, explanation):
    return RuleResult(rule_id, name, status, score if status is RuleStatus.TRIGGERED else 0, explanation)

class HighAmountRule:
    rule_id = "high_amount"
    name = "High transaction amount"
    def __init__(self, threshold=Decimal("1000000.00"), score=35):
        if threshold <= 0: raise ValueError("threshold must be positive")
        if not 0 <= score <= 100: raise ValueError("score must be between 0 and 100")
        self.threshold, self.score = threshold, score
    def evaluate(self, context):
        t = context.transaction
        if t.amount >= self.threshold:
            return result(self.rule_id, self.name, RuleStatus.TRIGGERED, self.score,
                f"Amount {t.amount:.2f} {t.currency} meets or exceeds configured threshold "
                f"{self.threshold:.2f} {t.currency}.")
        return result(self.rule_id, self.name, RuleStatus.NOT_TRIGGERED, 0,
            f"Amount {t.amount:.2f} {t.currency} is below the configured threshold.")

class UnusualAmountRule:
    rule_id = "unusual_amount"
    name = "Amount unusual for customer"
    def __init__(self, multiplier=Decimal("3"), min_history=3, score=20):
        if multiplier <= 1: raise ValueError("multiplier must be greater than 1")
        if min_history < 1: raise ValueError("min_history must be at least 1")
        if not 0 <= score <= 100: raise ValueError("score must be between 0 and 100")
        self.multiplier, self.min_history, self.score = multiplier, min_history, score
    def evaluate(self, context):
        t = context.transaction
        history = [x for x in context.history if x.currency == t.currency]
        if len(history) < self.min_history:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                f"Not evaluated: need at least {self.min_history} prior transaction(s) in "
                f"{t.currency}; found {len(history)}.")
        baseline = sum((x.amount for x in history), Decimal("0")) / Decimal(len(history))
        threshold = baseline * self.multiplier
        if t.amount >= threshold:
            return result(self.rule_id, self.name, RuleStatus.TRIGGERED, self.score,
                f"Amount {t.amount:.2f} {t.currency} is at least {self.multiplier}x the "
                f"customer mean {baseline:.2f} {t.currency} (threshold {threshold:.2f}).")
        return result(self.rule_id, self.name, RuleStatus.NOT_TRIGGERED, 0,
            f"Amount {t.amount:.2f} {t.currency} is below {self.multiplier}x customer mean "
            f"{baseline:.2f} {t.currency}.")

class VelocityRule:
    rule_id = "velocity"
    name = "Rapid successive transactions"
    def __init__(self, window_seconds=300, max_transactions=3, score=30):
        if window_seconds <= 0: raise ValueError("window_seconds must be positive")
        if max_transactions < 1: raise ValueError("max_transactions must be at least 1")
        if not 0 <= score <= 100: raise ValueError("score must be between 0 and 100")
        self.window_seconds, self.max_transactions, self.score = window_seconds, max_transactions, score
    def evaluate(self, context):
        t = context.transaction
        cutoff = t.timestamp - timedelta(seconds=self.window_seconds)
        recent = [x for x in context.history if cutoff <= x.timestamp < t.timestamp]
        total = len(recent) + 1
        if total > self.max_transactions:
            return result(self.rule_id, self.name, RuleStatus.TRIGGERED, self.score,
                f"{total} transactions for this customer fall within {self.window_seconds} seconds; "
                f"configured maximum is {self.max_transactions}.")
        return result(self.rule_id, self.name, RuleStatus.NOT_TRIGGERED, 0,
            f"{total} transaction(s) fall within {self.window_seconds} seconds; "
            f"configured maximum is {self.max_transactions}.")

class UnfamiliarDeviceRule:
    rule_id = "unfamiliar_device"
    name = "Unfamiliar device"
    def __init__(self, score=15):
        if not 0 <= score <= 100: raise ValueError("score must be between 0 and 100")
        self.score = score
    def evaluate(self, context):
        t = context.transaction
        if not context.history:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                "Not evaluated: no prior customer transactions establish known devices.")
        if not t.device_id:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                "Not evaluated: current transaction has no device identifier.")
        known = {x.device_id for x in context.history if x.device_id}
        if not known:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                "Not evaluated: prior transactions contain no device identifiers.")
        if t.device_id not in known:
            return result(self.rule_id, self.name, RuleStatus.TRIGGERED, self.score,
                f"Device '{t.device_id}' has not appeared in supplied prior transactions "
                f"for customer '{t.customer_id}'.")
        return result(self.rule_id, self.name, RuleStatus.NOT_TRIGGERED, 0,
            f"Device '{t.device_id}' appears in the customer's prior transactions.")

class UnusualGeographyRule:
    rule_id = "unusual_geography"
    name = "Unusual geographic change"
    def __init__(self, window_minutes=60, score=25):
        if window_minutes <= 0: raise ValueError("window_minutes must be positive")
        if not 0 <= score <= 100: raise ValueError("score must be between 0 and 100")
        self.window_minutes, self.score = window_minutes, score
    def evaluate(self, context):
        t = context.transaction
        if not context.history:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                "Not evaluated: no prior transactions are available for geographic comparison.")
        if not t.country_code:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                "Not evaluated: current transaction has no country code.")
        cutoff = t.timestamp - timedelta(minutes=self.window_minutes)
        recent = [x for x in context.history if cutoff <= x.timestamp < t.timestamp and x.country_code]
        if not recent:
            return result(self.rule_id, self.name, RuleStatus.INSUFFICIENT_HISTORY, 0,
                f"Not evaluated: no prior transaction with country data in {self.window_minutes} minutes.")
        different = next((x for x in reversed(recent) if x.country_code != t.country_code), None)
        if different:
            return result(self.rule_id, self.name, RuleStatus.TRIGGERED, self.score,
                f"Country changed from {different.country_code} to {t.country_code} within "
                f"{self.window_minutes} minutes for this customer.")
        return result(self.rule_id, self.name, RuleStatus.NOT_TRIGGERED, 0,
            f"Country {t.country_code} matches available recent geographic history.")

def build_default_rules(config: RuleConfig | None = None):
    config = config or RuleConfig()
    return (
        HighAmountRule(config.high_amount_threshold, config.high_amount_score),
        UnusualAmountRule(config.unusual_amount_multiplier, config.unusual_amount_min_history,
                          config.unusual_amount_score),
        VelocityRule(config.velocity_window_seconds, config.velocity_max_transactions, config.velocity_score),
        UnfamiliarDeviceRule(config.unfamiliar_device_score),
        UnusualGeographyRule(config.geography_window_minutes, config.unusual_geography_score),
    )
