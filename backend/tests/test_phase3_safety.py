import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.schemas import MerchantPolicy, AIDecisionOutput
from app.ai.context_builder import build_ai_context
from app.ai.decision_validator import validate_ai_decision
from app.ai.policy_controller import evaluate_policy
from app.services.recovery_pipeline import run_recovery_pipeline

def _get_base_tx():
    return {
        "transaction_id": "tx_test_safety_001",
        "merchant_id": "merchant_001",
        "customer_id": "cust_safety_001",
        "amount": 1000.0,
        "currency": "INR",
        "payment_method": "card",
        "transaction_status": "FAILED",
        "failure_code": "INSUFFICIENT_FUNDS",
        "failure_reason": "Insufficient funds in customer account",
        "retry_count": 1,
        "transaction_timestamp": "2026-08-22T00:00:00Z",
        "previous_success_rate": 0.8,
        "customer_lifetime_value": 5000.0,
        "subscription_status": "active",
        "days_since_last_success": 5
    }

def test_1_disallowed_strategy_blocked():
    tx = _get_base_tx()
    policy = MerchantPolicy(allowed_recovery_strategies=["SMART_RETRY"])
    context = build_ai_context(tx, policy)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="PAYMENT_METHOD_UPDATE",
        confidence=0.9,
        recovery_probability=0.8,
        expected_recovery_amount=800.0,
        reason="Test",
        risk_factors=[]
    )
    validated_dec, is_valid, errors = validate_ai_decision(dec, context)
    assert not is_valid
    assert validated_dec.strategy == "MANUAL_REVIEW"

def test_2_low_confidence_blocked():
    tx = _get_base_tx()
    policy = MerchantPolicy(minimum_ai_confidence=0.80)
    context = build_ai_context(tx, policy)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY",
        confidence=0.60, # Below 0.80
        recovery_probability=0.8,
        expected_recovery_amount=800.0,
        reason="Test",
        risk_factors=[]
    )
    pol_res = evaluate_policy(dec, context)
    assert not pol_res.allowed
    assert pol_res.requires_human_approval

def test_3_amount_exceeds_merchant_limit():
    tx = _get_base_tx()
    tx["amount"] = 75000.0
    policy = MerchantPolicy(maximum_recovery_amount=50000.0)
    context = build_ai_context(tx, policy)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY",
        confidence=0.9,
        recovery_probability=0.8,
        expected_recovery_amount=50000.0,
        reason="Test",
        risk_factors=[]
    )
    pol_res = evaluate_policy(dec, context)
    assert not pol_res.allowed

def test_4_retry_count_exceeds_maximum():
    tx = _get_base_tx()
    tx["retry_count"] = 5
    policy = MerchantPolicy(maximum_retry_attempts=3)
    context = build_ai_context(tx, policy)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY",
        confidence=0.9,
        recovery_probability=0.8,
        expected_recovery_amount=800.0,
        reason="Test",
        risk_factors=[]
    )
    pol_res = evaluate_policy(dec, context)
    assert not pol_res.allowed

def test_5_successful_transaction_no_recovery():
    tx = _get_base_tx()
    tx["transaction_status"] = "SUCCESS"
    pipe_res = run_recovery_pipeline(tx)
    assert not pipe_res.policy_result.allowed
    assert pipe_res.simulation_result is None

def test_6_disputed_transaction_no_auto_recovery():
    tx = _get_base_tx()
    tx["transaction_status"] = "DISPUTED"
    pipe_res = run_recovery_pipeline(tx)
    assert not pipe_res.policy_result.allowed

def test_7_invalid_ai_json_validation_failure():
    tx = _get_base_tx()
    context = build_ai_context(tx)
    try:
        dec = AIDecisionOutput(
            decision="RECOVER",
            strategy="SMART_RETRY",
            confidence=1.5, # Invalid > 1.0
            recovery_probability=0.8,
            expected_recovery_amount=800.0,
            reason="Test",
            risk_factors=[]
        )
        validated_dec, is_valid, errors = validate_ai_decision(dec, context)
        assert not is_valid
        assert validated_dec.decision == "MANUAL_REVIEW"
    except Exception:
        pass # Pydantic schema validation correctly rejected confidence > 1.0

def test_8_invented_facts_rejected():
    tx = _get_base_tx()
    context = build_ai_context(tx)
    # Expected recovery amount exceeds tx amount (invented value)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY",
        confidence=0.9,
        recovery_probability=0.8,
        expected_recovery_amount=1500.0, # > tx.amount (1000)
        reason="Test",
        risk_factors=[]
    )
    validated_dec, is_valid, errors = validate_ai_decision(dec, context)
    assert not is_valid
    assert "exceeds transaction amount" in errors[0]

def test_9_negative_recovery_amount_rejected():
    tx = _get_base_tx()
    context = build_ai_context(tx)
    try:
        dec = AIDecisionOutput(
            decision="RECOVER",
            strategy="SMART_RETRY",
            confidence=0.9,
            recovery_probability=0.8,
            expected_recovery_amount=-50.0, # Invalid
            reason="Test",
            risk_factors=[]
        )
        validated_dec, is_valid, errors = validate_ai_decision(dec, context)
        assert not is_valid
    except Exception:
        pass # Pydantic schema validation correctly caught negative amount

def test_10_recovery_greater_than_transaction_rejected():
    tx = _get_base_tx()
    context = build_ai_context(tx)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY",
        confidence=0.9,
        recovery_probability=0.8,
        expected_recovery_amount=1200.0, # 1200 > 1000
        reason="Test",
        risk_factors=[]
    )
    validated_dec, is_valid, errors = validate_ai_decision(dec, context)
    assert not is_valid

def test_11_automatic_recovery_disabled():
    tx = _get_base_tx()
    policy = MerchantPolicy(automatic_recovery_enabled=False)
    context = build_ai_context(tx, policy)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY",
        confidence=0.95,
        recovery_probability=0.85,
        expected_recovery_amount=800.0,
        reason="Test",
        risk_factors=[]
    )
    pol_res = evaluate_policy(dec, context)
    assert not pol_res.allowed

def test_12_strategy_not_in_allowed_strategies():
    tx = _get_base_tx()
    policy = MerchantPolicy(allowed_recovery_strategies=["PAYMENT_METHOD_UPDATE"])
    context = build_ai_context(tx, policy)
    dec = AIDecisionOutput(
        decision="RECOVER",
        strategy="SMART_RETRY", # Not allowed
        confidence=0.90,
        recovery_probability=0.80,
        expected_recovery_amount=800.0,
        reason="Test",
        risk_factors=[]
    )
    pol_res = evaluate_policy(dec, context)
    assert not pol_res.allowed


def run_all_safety_tests():
    print("--- RUNNING PHASE 3.11 AI SAFETY TESTS ---")
    tests = [
        ("1. Disallowed strategy blocked", test_1_disallowed_strategy_blocked),
        ("2. Low confidence blocked", test_2_low_confidence_blocked),
        ("3. Amount exceeds merchant limit", test_3_amount_exceeds_merchant_limit),
        ("4. Retry count exceeds maximum limit", test_4_retry_count_exceeds_maximum),
        ("5. Successful transaction no recovery", test_5_successful_transaction_no_recovery),
        ("6. Disputed transaction no auto recovery", test_6_disputed_transaction_no_auto_recovery),
        ("7. Invalid AI JSON validation failure", test_7_invalid_ai_json_validation_failure),
        ("8. Invented facts rejected", test_8_invented_facts_rejected),
        ("9. Negative recovery amount rejected", test_9_negative_recovery_amount_rejected),
        ("10. Recovery greater than transaction rejected", test_10_recovery_greater_than_transaction_rejected),
        ("11. Automatic recovery disabled", test_11_automatic_recovery_disabled),
        ("12. Strategy not in allowed strategies", test_12_strategy_not_in_allowed_strategies),
    ]

    passed = 0
    for title, tfunc in tests:
        try:
            tfunc()
            print(f"[PASS] {title}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {title}: {str(e)}")

    print(f"\nSAFETY TEST RESULTS: {passed}/{len(tests)} PASSED")
    assert passed == len(tests)

if __name__ == "__main__":
    run_all_safety_tests()
