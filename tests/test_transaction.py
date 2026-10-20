from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.transaction import Transaction


def valid_payload() -> dict:
    return {
        "transaction_id": "txn-001",
        "customer_id": "cust-001",
        "amount": Decimal("125.50"),
        "currency": "NGN",
        "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "merchant_category": " groceries ",
        "channel": "card",
        "device_id": "device-001",
        "country_code": "NG",
    }


def test_valid_transaction_and_category_trimmed():
    transaction = Transaction(**valid_payload())
    assert transaction.amount == Decimal("125.50")
    assert transaction.merchant_category == "groceries"
    assert transaction.created_at.tzinfo is not None


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1.00")])
def test_non_positive_amount_rejected(amount):
    payload = valid_payload()
    payload["amount"] = amount
    with pytest.raises(ValidationError):
        Transaction(**payload)


def test_too_many_decimal_places_rejected():
    payload = valid_payload()
    payload["amount"] = Decimal("1.239")
    with pytest.raises(ValidationError):
        Transaction(**payload)


@pytest.mark.parametrize("currency", ["ngn", "US", "USDD", "1NG"])
def test_invalid_currency_rejected(currency):
    payload = valid_payload()
    payload["currency"] = currency
    with pytest.raises(ValidationError):
        Transaction(**payload)


@pytest.mark.parametrize("country", ["ng", "NGA", "1G", ""])
def test_invalid_country_rejected(country):
    payload = valid_payload()
    payload["country_code"] = country
    with pytest.raises(ValidationError):
        Transaction(**payload)


def test_naive_timestamp_rejected():
    payload = valid_payload()
    payload["timestamp"] = datetime(2025, 1, 1)
    with pytest.raises(ValidationError, match="timezone"):
        Transaction(**payload)


def test_missing_required_field_rejected():
    payload = valid_payload()
    del payload["customer_id"]
    with pytest.raises(ValidationError):
        Transaction(**payload)


def test_blank_category_rejected():
    payload = valid_payload()
    payload["merchant_category"] = "   "
    with pytest.raises(ValidationError):
        Transaction(**payload)


def test_json_serialization_is_supported():
    transaction = Transaction(**valid_payload())
    encoded = transaction.model_dump_json()
    assert '"amount":"125.50"' in encoded
    assert "2025-01-01T00:00:00Z" in encoded or "+00:00" in encoded
