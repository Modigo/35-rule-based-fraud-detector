"""Shared results from rules and the overall assessment."""
from dataclasses import dataclass
from enum import Enum

class RuleStatus(str, Enum):
    TRIGGERED = "triggered"
    NOT_TRIGGERED = "not_triggered"
    INSUFFICIENT_HISTORY = "insufficient_history"
    DISABLED = "disabled"

class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    name: str
    status: RuleStatus
    score: int
    explanation: str

    @property
    def triggered(self) -> bool:
        return self.status is RuleStatus.TRIGGERED

@dataclass(frozen=True)
class RiskAssessment:
    transaction_id: str
    risk_score: int
    risk_band: RiskBand
    rule_results: tuple[RuleResult, ...]

    @property
    def triggered_rules(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.rule_results if r.triggered)

    @property
    def explanations(self) -> tuple[str, ...]:
        return tuple(r.explanation for r in self.triggered_rules)
