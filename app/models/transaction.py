"""Validated transaction model used throughout the application."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class Transaction(BaseModel):
    """A validated synthetic financial transaction.

    Monetary values use Decimal and are limited to two fractional digits.
    Timestamps must include a timezone so comparisons are unambiguous.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    transaction_id: Identifier
    customer_id: Identifier
    amount: Annotated[Decimal, Field(gt=Decimal("0"), max_digits=14, decimal_places=2)]
    currency: CurrencyCode = "NGN"
    timestamp: datetime
    merchant_category: Annotated[str, Field(min_length=1, max_length=80)]
    channel: Annotated[str, Field(pattern=r"^(card|online|transfer)$")]
    device_id: Identifier | None = None
    country_code: CountryCode | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("timestamp", "created_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value

    @field_validator("merchant_category")
    @classmethod
    def trim_category(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("merchant_category must not be blank")
        return value
