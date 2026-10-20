"""Deterministic synthetic transaction and scenario generation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.models.transaction import Transaction


@dataclass(frozen=True)
class Scenario:
    """A named synthetic scenario; labels are metadata, not transaction facts."""

    label: str
    description: str
    transactions: tuple[Transaction, ...]
    target_transaction_id: str


class SyntheticTransactionGenerator:
    """Generate synthetic transactions reproducibly from a seed.

    A generator instance owns its random-number stream. Re-create it with the
    same seed to reproduce the same dataset. No external data is used.
    """

    CATEGORIES = ("groceries", "electronics", "travel", "fuel", "utilities", "dining")
    CHANNELS = ("card", "online", "transfer")
    COUNTRIES = ("NG", "GH", "KE", "ZA")
    BASE_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._random = random.Random(seed)
        self._sequence = 0

    def _next_id(self, prefix: str) -> str:
        self._sequence += 1
        return f"{prefix}-{self._sequence:06d}"

    def _transaction(
        self,
        *,
        customer_id: str | None = None,
        amount: Decimal | None = None,
        timestamp: datetime | None = None,
        device_id: str | None = None,
        country_code: str | None = None,
        channel: str | None = None,
        merchant_category: str | None = None,
    ) -> Transaction:
        timestamp = timestamp or (self.BASE_TIME + timedelta(minutes=self._random.randint(0, 60 * 24 * 30)))
        amount = amount if amount is not None else Decimal(self._random.randint(200, 150_000)) / Decimal("100")
        return Transaction(
            transaction_id=self._next_id("txn"),
            customer_id=customer_id or f"cust-{self._random.randint(1, 250):04d}",
            amount=amount,
            currency="NGN",
            timestamp=timestamp,
            merchant_category=merchant_category or self._random.choice(self.CATEGORIES),
            channel=channel or self._random.choice(self.CHANNELS),
            device_id=device_id if device_id is not None else f"device-{self._random.randint(1, 80):03d}",
            country_code=country_code if country_code is not None else self._random.choice(self.COUNTRIES),
            created_at=timestamp + timedelta(seconds=1),
        )

    def generate(self, count: int = 100) -> list[Transaction]:
        """Generate `count` valid transactions; count may be zero but not negative."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("count must be a non-negative integer")
        transactions = [self._transaction() for _ in range(count)]
        return sorted(transactions, key=lambda item: (item.timestamp, item.transaction_id))

    def normal_scenario(self) -> Scenario:
        customer = "cust-normal-001"
        base = self.BASE_TIME
        transactions = (
            self._transaction(customer_id=customer, amount=Decimal("24.50"), timestamp=base,
                              device_id="device-normal-001", country_code="NG", channel="card",
                              merchant_category="groceries"),
            self._transaction(customer_id=customer, amount=Decimal("18.75"), timestamp=base + timedelta(hours=4),
                              device_id="device-normal-001", country_code="NG", channel="online",
                              merchant_category="dining"),
        )
        return Scenario("normal", "Ordinary purchases from a familiar device and country.", transactions, transactions[-1].transaction_id)

    def high_value_scenario(self) -> Scenario:
        transaction = self._transaction(customer_id="cust-high-value-001", amount=Decimal("2500000.00"),
                                        timestamp=self.BASE_TIME, device_id="device-high-001",
                                        country_code="NG", channel="online", merchant_category="electronics")
        return Scenario("high_value", "A single transaction with an unusually high amount.", (transaction,), transaction.transaction_id)

    def rapid_successive_scenario(self) -> Scenario:
        customer = "cust-velocity-001"
        transactions = tuple(
            self._transaction(customer_id=customer, amount=Decimal("45000.00"),
                             timestamp=self.BASE_TIME + timedelta(seconds=30 * index),
                             device_id="device-velocity-001", country_code="NG", channel="online",
                             merchant_category="electronics")
            for index in range(4)
        )
        return Scenario("rapid_successive", "Several transactions for the same customer within 90 seconds.",
                        transactions, transactions[-1].transaction_id)

    def unfamiliar_device_scenario(self) -> Scenario:
        customer = "cust-device-001"
        baseline = self._transaction(customer_id=customer, amount=Decimal("3200.00"),
                                     timestamp=self.BASE_TIME, device_id="device-known-001",
                                     country_code="NG", channel="card", merchant_category="groceries")
        target = self._transaction(customer_id=customer, amount=Decimal("5100.00"),
                                   timestamp=self.BASE_TIME + timedelta(hours=2), device_id="device-new-999",
                                   country_code="NG", channel="online", merchant_category="travel")
        return Scenario("unfamiliar_device", "The customer uses a device not seen in the supplied baseline transaction.",
                        (baseline, target), target.transaction_id)

    def unusual_geography_scenario(self) -> Scenario:
        customer = "cust-geography-001"
        baseline = self._transaction(customer_id=customer, amount=Decimal("2800.00"),
                                     timestamp=self.BASE_TIME, device_id="device-geo-001",
                                     country_code="NG", channel="card", merchant_category="groceries")
        target = self._transaction(customer_id=customer, amount=Decimal("6800.00"),
                                   timestamp=self.BASE_TIME + timedelta(minutes=25), device_id="device-geo-001",
                                   country_code="GB", channel="online", merchant_category="travel")
        return Scenario("unusual_geography", "A short-interval transaction appears in a different country.",
                        (baseline, target), target.transaction_id)

    def all_scenarios(self) -> tuple[Scenario, ...]:
        """Return one example of every supported scenario using this instance's RNG."""
        return (
            self.normal_scenario(),
            self.high_value_scenario(),
            self.rapid_successive_scenario(),
            self.unfamiliar_device_scenario(),
            self.unusual_geography_scenario(),
        )
