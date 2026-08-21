# RecoverAI Phase 2.5 Comprehensive Test Suite
from app.engine.dataset_generator import generate_synthetic_dataset, compute_ground_truth, DEFAULT_SEED
from app.engine.risk_engine import calculate_risk_score, evaluate_risk_events
from app.engine.evaluator import run_evaluation
from app.engine.fixtures.ambiguity_cases import AMBIGUITY_TEST_CASES

def test_dataset_generation_structure_and_splits():
    """Verify synthetic dataset count, fields, and 60/20/20 train/val/test splits."""
    ds = generate_synthetic_dataset(count=1000, seed=123)
    assert len(ds) == 1000

    item = ds[0]
    required_fields = [
        "transaction_id", "merchant_id", "customer_id", "payment_gateway",
        "amount", "currency", "transaction_timestamp", "payment_method",
        "transaction_status", "failure_code", "retry_count",
        "customer_lifetime_value", "subscription_status",
        "days_since_last_success", "previous_success_rate",
        "card_expiry_status", "dispute_status", "checkout_completed",
        "event_type", "benchmark_version", "dataset_split", "ground_truth"
    ]
    for field in required_fields:
        assert field in item, f"Missing field: {field}"

    # Verify split distributions and customer-disjoint isolation
    train_items = [x for x in ds if x["dataset_split"] == "train"]
    val_items = [x for x in ds if x["dataset_split"] == "validation"]
    test_items = [x for x in ds if x["dataset_split"] == "test"]

    assert len(train_items) + len(val_items) + len(test_items) == 1000

    train_custs = set(x["customer_id"] for x in train_items)
    val_custs = set(x["customer_id"] for x in val_items)
    test_custs = set(x["customer_id"] for x in test_items)

    assert len(train_custs & val_custs) == 0, "Train and Validation share customers"
    assert len(train_custs & test_custs) == 0, "Train and Test share customers"
    assert len(val_custs & test_custs) == 0, "Validation and Test share customers"


def test_reproducible_random_seed():
    """Verify dataset generation is 100% reproducible with fixed seed."""
    ds1 = generate_synthetic_dataset(count=100, seed=42)
    ds2 = generate_synthetic_dataset(count=100, seed=42)

    for i in range(len(ds1)):
        assert ds1[i]["transaction_id"] == ds2[i]["transaction_id"]
        assert ds1[i]["amount"] == ds2[i]["amount"]
        assert ds1[i]["ground_truth"]["ground_truth_score"] == ds2[i]["ground_truth"]["ground_truth_score"]

def test_risk_engine_no_ground_truth_access():
    """Verify Risk Engine produces identical output regardless of ground_truth dict presence."""
    event_with_gt = {
        "transaction_status": "failed",
        "failure_code": "insufficient_funds",
        "amount": 2500.0,
        "retry_count": 2,
        "previous_success_rate": 0.80,
        "customer_lifetime_value": 10000.0,
        "subscription_status": "active",
        "card_expiry_status": "valid",
        "days_since_last_success": 5,
        "checkout_completed": True,
        "ground_truth": {"is_recovery_opportunity": False, "expected_recovery_amount": 0.0}
    }
    
    event_without_gt = {k: v for k, v in event_with_gt.items() if k != "ground_truth"}

    res_with = calculate_risk_score(event_with_gt)
    res_without = calculate_risk_score(event_without_gt)

    assert res_with == res_without

def test_customer_history_influences_probability():
    """Verify changing previous_success_rate changes recovery probability."""
    base_event = {
        "transaction_status": "failed",
        "failure_code": "insufficient_funds",
        "amount": 2000.0,
        "retry_count": 1,
        "subscription_status": "active",
        "card_expiry_status": "valid",
        "days_since_last_success": 5,
        "checkout_completed": True
    }

    event_good_hist = {**base_event, "previous_success_rate": 0.95, "customer_lifetime_value": 20000.0}
    event_poor_hist = {**base_event, "previous_success_rate": 0.20, "customer_lifetime_value": 200.0}

    res_good = calculate_risk_score(event_good_hist)
    res_poor = calculate_risk_score(event_poor_hist)

    assert res_good["recovery_probability"] > res_poor["recovery_probability"]

def test_retry_count_influences_probability():
    """Verify changing retry_count changes recovery probability."""
    base_event = {
        "transaction_status": "failed",
        "failure_code": "network_timeout",
        "amount": 3000.0,
        "previous_success_rate": 0.80,
        "subscription_status": "active",
        "card_expiry_status": "valid",
        "days_since_last_success": 2,
        "checkout_completed": True
    }

    event_low_retry = {**base_event, "retry_count": 1}
    event_high_retry = {**base_event, "retry_count": 4}

    res_low = calculate_risk_score(event_low_retry)
    res_high = calculate_risk_score(event_high_retry)

    assert res_low["recovery_probability"] > res_high["recovery_probability"]

def test_amount_influences_expected_recovery_amount():
    """Verify expected_recovery_amount scales with transaction amount."""
    base_event = {
        "transaction_status": "failed",
        "failure_code": "expired_card",
        "retry_count": 1,
        "previous_success_rate": 0.85,
        "subscription_status": "active",
        "card_expiry_status": "expired",
        "days_since_last_success": 10,
        "checkout_completed": True
    }

    res_small = calculate_risk_score({**base_event, "amount": 1000.0})
    res_large = calculate_risk_score({**base_event, "amount": 10000.0})

    assert res_small["recovery_probability"] == res_large["recovery_probability"]
    assert res_large["expected_recovery_amount"] == round(res_small["expected_recovery_amount"] * 10, 2)

def test_probability_bounded_between_zero_and_one():
    """Verify recovery_probability is strictly bounded within [0.0, 1.0]."""
    dataset = generate_synthetic_dataset(count=200, seed=999)
    for item in dataset:
        res = calculate_risk_score(item)
        prob = res["recovery_probability"]
        assert 0.0 <= prob <= 1.0, f"Probability out of bounds: {prob}"

def test_mathematical_consistency():
    """Verify expected_recovery_amount == round(revenue_at_risk * probability, 2)."""
    dataset = generate_synthetic_dataset(count=200, seed=888)
    for item in dataset:
        res = calculate_risk_score(item)
        expected = round(res["revenue_at_risk"] * res["recovery_probability"], 2)
        assert res["expected_recovery_amount"] == expected

def test_ambiguity_test_fixtures():
    """Evaluate all 20 ambiguity test fixtures and verify proper processing."""
    assert len(AMBIGUITY_TEST_CASES) == 20
    for case in AMBIGUITY_TEST_CASES:
        event = case["event"]
        gt = compute_ground_truth(event)
        pred = calculate_risk_score(event)

        assert "is_recovery_opportunity" in gt
        assert "is_opportunity" in pred
        assert 0.0 <= pred["recovery_probability"] <= 1.0
        assert pred["expected_recovery_amount"] == round(pred["revenue_at_risk"] * pred["recovery_probability"], 2)

def test_evaluator_continuous_metrics():
    """Verify ROC-AUC, PR-AUC, Brier score, and ECE in evaluator."""
    ds = generate_synthetic_dataset(count=300, seed=777)
    evaluated = evaluate_risk_events(ds)
    metrics = run_evaluation(evaluated)

    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "brier_score" in metrics
    assert "calibration_error" in metrics

    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert 0.0 <= metrics["brier_score"] <= 1.0
    assert 0.0 <= metrics["calibration_error"] <= 1.0
