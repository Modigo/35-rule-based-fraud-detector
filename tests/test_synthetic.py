import pytest

from app.generators.synthetic import SyntheticTransactionGenerator
from app.models.transaction import Transaction


def test_requested_count_and_valid_models():
    transactions = SyntheticTransactionGenerator(seed=10).generate(25)
    assert len(transactions) == 25
    assert all(isinstance(item, Transaction) for item in transactions)
    assert all(item.amount > 0 for item in transactions)
    assert all(item.timestamp.tzinfo is not None for item in transactions)


def test_zero_count_returns_empty_list():
    assert SyntheticTransactionGenerator(seed=10).generate(0) == []


@pytest.mark.parametrize("count", [-1, 1.5, True, "3"])
def test_invalid_count_rejected(count):
    with pytest.raises(ValueError):
        SyntheticTransactionGenerator(seed=10).generate(count)


def test_same_seed_produces_same_dataset():
    first = [item.model_dump(mode="json") for item in SyntheticTransactionGenerator(seed=99).generate(15)]
    second = [item.model_dump(mode="json") for item in SyntheticTransactionGenerator(seed=99).generate(15)]
    assert first == second


def test_different_seeds_can_produce_different_datasets():
    first = SyntheticTransactionGenerator(seed=1).generate(10)
    second = SyntheticTransactionGenerator(seed=2).generate(10)
    assert [item.model_dump(mode="json") for item in first] != [item.model_dump(mode="json") for item in second]


def test_scenario_labels_are_separate_from_transaction_model():
    scenario = SyntheticTransactionGenerator(seed=1).high_value_scenario()
    assert scenario.label == "high_value"
    assert scenario.target_transaction_id == scenario.transactions[0].transaction_id
    assert "is_fraud" not in Transaction.model_fields


def test_high_value_scenario_has_high_amount():
    scenario = SyntheticTransactionGenerator(seed=1).high_value_scenario()
    assert scenario.transactions[0].amount >= 1_000_000


def test_rapid_successive_transactions_share_customer_and_are_close_in_time():
    scenario = SyntheticTransactionGenerator(seed=1).rapid_successive_scenario()
    transactions = scenario.transactions
    assert len(transactions) >= 3
    assert len({item.customer_id for item in transactions}) == 1
    assert (transactions[-1].timestamp - transactions[0].timestamp).total_seconds() <= 120


def test_unfamiliar_device_scenario_changes_device_for_same_customer():
    scenario = SyntheticTransactionGenerator(seed=1).unfamiliar_device_scenario()
    baseline, target = scenario.transactions
    assert baseline.customer_id == target.customer_id
    assert baseline.device_id != target.device_id
    assert target.transaction_id == scenario.target_transaction_id


def test_geography_scenario_changes_country_for_same_customer():
    scenario = SyntheticTransactionGenerator(seed=1).unusual_geography_scenario()
    baseline, target = scenario.transactions
    assert baseline.customer_id == target.customer_id
    assert baseline.country_code != target.country_code
    assert (target.timestamp - baseline.timestamp).total_seconds() < 3600


def test_normal_scenario_has_familiar_device_and_country():
    scenario = SyntheticTransactionGenerator(seed=1).normal_scenario()
    assert len({item.device_id for item in scenario.transactions}) == 1
    assert len({item.country_code for item in scenario.transactions}) == 1


def test_generated_transactions_can_be_json_serialized():
    transaction = SyntheticTransactionGenerator(seed=7).generate(1)[0]
    payload = transaction.model_dump_json()
    assert '"transaction_id"' in payload
    assert transaction.timestamp.utcoffset() is not None
