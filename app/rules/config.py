"""Configurable thresholds, weights, rule enablement, and risk bands."""
from dataclasses import dataclass, field
from decimal import Decimal

DEFAULT_RULE_IDS = frozenset({
    "high_amount", "unusual_amount", "velocity",
    "unfamiliar_device", "unusual_geography",
})

@dataclass(frozen=True)
class RuleConfig:
    """Illustrative defaults for synthetic data, not calibrated fraud probabilities."""
    enabled_rules: frozenset[str] = field(default_factory=lambda: DEFAULT_RULE_IDS)
    high_amount_threshold: Decimal = Decimal("1000000.00")
    high_amount_score: int = 35
    unusual_amount_multiplier: Decimal = Decimal("3")
    unusual_amount_min_history: int = 3
    unusual_amount_score: int = 20
    velocity_window_seconds: int = 300
    velocity_max_transactions: int = 3
    velocity_score: int = 30
    unfamiliar_device_score: int = 15
    geography_window_minutes: int = 60
    unusual_geography_score: int = 25
    low_risk_max: int = 29
    medium_risk_max: int = 59

    def __post_init__(self):
        unknown = self.enabled_rules - DEFAULT_RULE_IDS
        if unknown:
            raise ValueError(f"Unknown rule IDs: {', '.join(sorted(unknown))}")
        if self.high_amount_threshold <= 0:
            raise ValueError("high_amount_threshold must be positive")
        if self.unusual_amount_multiplier <= 1:
            raise ValueError("unusual_amount_multiplier must be greater than 1")
        if self.unusual_amount_min_history < 1:
            raise ValueError("unusual_amount_min_history must be at least 1")
        if self.velocity_window_seconds <= 0:
            raise ValueError("velocity_window_seconds must be positive")
        if self.velocity_max_transactions < 1:
            raise ValueError("velocity_max_transactions must be at least 1")
        if self.geography_window_minutes <= 0:
            raise ValueError("geography_window_minutes must be positive")
        if not (0 <= self.low_risk_max < self.medium_risk_max < 100):
            raise ValueError("risk boundaries must satisfy 0 <= low < medium < 100")
        scores = (
            self.high_amount_score, self.unusual_amount_score, self.velocity_score,
            self.unfamiliar_device_score, self.unusual_geography_score,
        )
        if any(isinstance(s, bool) or not isinstance(s, int) or not 0 <= s <= 100 for s in scores):
            raise ValueError("each rule score must be an integer from 0 to 100")
