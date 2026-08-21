# Phase 2 Engine Test Suite
from app.engine.dataset_generator import generate_synthetic_dataset, compute_ground_truth, DEFAULT_SEED
from app.engine.risk_engine import calculate_risk_score, evaluate_risk_events
from app.engine.evaluator import run_evaluation

def test_dataset_generation():
    """Verify synthetic dataset contains required length and fields."""
    ds = generate_synthetic_dataset(count=500, seed=123)
    assert len(ds) == 500

    item = ds[0]
    required_fields = [
        "transaction_id", "merchant_id", "customer_id", "payment_gateway",
        "amount", "currency", "transaction_timestamp", "payment_method",
        "transaction_status", "failure_code", "retry_count",
        "customer_lifetime_value", "subscription_status",
        "days_since_last_success", "previous_success_rate",
        "card_expiry_status", "dispute_status", "checkout_completed",
        "event_type", "ground_truth"
    ]
    for field in required_fields:
        assert field in item, f"Missing field: {field}"

def test_deterministic_seed():
    """Verify dataset generation is 100% reproducible with fixed seed."""
    ds1 = generate_synthetic_dataset(count=100, seed=42)
    ds2 = generate_synthetic_dataset(count=100, seed=42)

    assert ds1[0]["transaction_id"] == ds2[0]["transaction_id"]
    assert ds1[0]["amount"] == ds2[0]["amount"]
    assert ds1[50]["failure_code"] == ds2[50]["failure_code"]

def test_ground_truth_labeling():
    """Verify ground-truth rules logic."""
    # Successful transaction
    gt_succ = compute_ground_truth({"transaction_status": "successful", "amount": 1000, "card_expiry_status": "valid", "checkout_completed": True, "previous_success_rate": 0.9, "subscription_status": "active"})
    assert gt_succ["is_recovery_opportunity"] is False
    assert gt_succ["expected_recovery_amount"] == 0.0

    # Transient network failure
    gt_net = compute_ground_truth({"transaction_status": "failed", "failure_code": "network_timeout", "amount": 2000, "card_expiry_status": "valid", "checkout_completed": True, "previous_success_rate": 0.9, "subscription_status": "active"})
    assert gt_net["is_recovery_opportunity"] is True
    assert gt_net["recommended_recovery_strategy"] == "smart_retry"

    # Stolen card
    gt_stolen = compute_ground_truth({"transaction_status": "failed", "failure_code": "stolen_card", "amount": 5000, "card_expiry_status": "valid", "checkout_completed": True, "previous_success_rate": 0.2, "subscription_status": "none"})
    assert gt_stolen["is_recovery_opportunity"] is False
    assert gt_stolen["recoverability"] == "unrecoverable"

def test_risk_scoring():
    """Verify explainable risk scoring formula."""
    res_succ = calculate_risk_score({"transaction_status": "successful", "amount": 1000})
    assert res_succ["risk_score"] == 0.0
    assert res_succ["risk_level"] == "none"

    res_fail = calculate_risk_score({
        "transaction_status": "failed",
        "failure_code": "expired_card",
        "amount": 3000,
        "retry_count": 3,
        "previous_success_rate": 0.5,
        "card_expiry_status": "expired",
        "subscription_status": "past_due",
        "days_since_last_success": 40
    })
    assert res_fail["risk_score"] > 50.0
    assert res_fail["risk_level"] in ["high", "critical"]

def test_recovery_opportunity_detection():
    """Verify recovery opportunity detection in risk engine."""
    res = calculate_risk_score({
        "transaction_status": "failed",
        "failure_code": "network_timeout",
        "amount": 1500
    })
    assert res["is_opportunity"] is True
    assert res["recommended_strategy"] == "smart_retry"

def test_revenue_at_risk_calculation():
    """Verify revenue at risk calculation."""
    res_succ = calculate_risk_score({"transaction_status": "successful", "amount": 1000})
    assert res_succ["revenue_at_risk"] == 0.0

    res_fail = calculate_risk_score({"transaction_status": "failed", "failure_code": "insufficient_funds", "amount": 2500})
    assert res_fail["revenue_at_risk"] == 2500.0

def test_evaluation_metrics():
    """Verify evaluation metric calculations."""
    dataset = generate_synthetic_dataset(count=200, seed=42)
    evaluated = evaluate_risk_events(dataset)
    metrics = run_evaluation(evaluated)

    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "total_revenue_processed" in metrics
    assert "total_revenue_at_risk" in metrics
    assert metrics["dataset_size"] == 200
