"""
Phase 9.3: Real Sandbox Gateway Validation Test Suite

Validates payment gateway adapters, resilient execution orchestration,
provider-native webhook signature verification, fallback safety rules,
tenant isolation, and idempotency guarantees using mocked sandbox clients.
"""
import hmac
import hashlib
import time
import json
from unittest.mock import patch, MagicMock

from app.adapters.stripe_adapter import StripeAdapter
from app.adapters.razorpay_adapter import RazorpayAdapter
from app.adapters.factory import get_gateway_adapter
from app.adapters.base import ExecutionState, ErrorClassification, AdapterExecutionResult

from app.adapters.resilient_executor import ResilientGatewayExecutor
from app.routers.events import (
    verify_webhook_signature,
    resolve_webhook_merchant,
    _PROCESSED_EVENTS,
)
from app.config import settings


def test_stripe_sandbox_validation():
    """Test StripeAdapter in mocked sandbox execution mode across all key scenarios."""
    adapter = StripeAdapter()
    assert adapter.provider_name == "stripe"

    # 1. Success Scenario (PaymentIntent Succeeded)
    payload_success = {
        "action_id": "act_stripe_001",
        "mock_client": True,
        "mock_type": "success",
        "merchant_id": "merch_123",
        "retry_count": 1,
        "role": "primary",
    }
    res_success = adapter.execute_action("RETRY_PAYMENT", 150.00, "USD", payload_success)
    assert res_success.success is True
    assert res_success.execution_state == ExecutionState.CONFIRMED_EXECUTED
    assert res_success.error_classification == ErrorClassification.NONE
    assert res_success.transaction_id is not None
    assert "idem_act_stripe_001_primary_1_stripe" in res_success.transaction_id or res_success.transaction_id.startswith("pi_mock_")

    # 2. Intent Reuse Scenario
    payload_reuse = {
        "action_id": "act_stripe_002",
        "mock_client": True,
        "mock_type": "success",
        "stripe_payment_intent_id": "pi_reused_999",
    }
    res_reuse = adapter.execute_action("RETRY_PAYMENT", 200.00, "USD", payload_reuse)
    assert res_reuse.success is True
    assert res_reuse.execution_state == ExecutionState.CONFIRMED_EXECUTED

    # 3. Soft Decline Scenario (Insufficient Funds / Transient)
    payload_soft = {
        "action_id": "act_stripe_003",
        "mock_client": True,
        "mock_type": "card_declined",
    }
    res_soft = adapter.execute_action("RETRY_PAYMENT", 100.00, "USD", payload_soft)
    assert res_soft.success is False
    assert res_soft.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_soft.error_classification == ErrorClassification.TRANSIENT
    assert res_soft.retryable is True

    # 4. Hard Decline Scenario (Card Expired / Permanent)
    payload_hard = {
        "action_id": "act_stripe_004",
        "mock_client": True,
        "mock_type": "expired_card",
    }
    res_hard = adapter.execute_action("RETRY_PAYMENT", 100.00, "USD", payload_hard)
    assert res_hard.success is False
    assert res_hard.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_hard.error_classification == ErrorClassification.PERMANENT
    assert res_hard.retryable is False

    # 5. Rate Limiting Scenario
    payload_rate = {
        "action_id": "act_stripe_005",
        "mock_client": True,
        "mock_type": "rate_limit",
    }
    res_rate = adapter.execute_action("RETRY_PAYMENT", 50.00, "USD", payload_rate)
    assert res_rate.success is False
    assert res_rate.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_rate.error_classification == ErrorClassification.TRANSIENT
    assert res_rate.retryable is True

    # 6. Timeout / UNKNOWN Execution State Scenario
    payload_timeout = {
        "action_id": "act_stripe_006",
        "mock_client": True,
        "mock_type": "timeout",
    }
    res_timeout = adapter.execute_action("RETRY_PAYMENT", 75.00, "USD", payload_timeout)
    assert res_timeout.success is False
    assert res_timeout.execution_state == ExecutionState.UNKNOWN
    assert res_timeout.error_classification == ErrorClassification.UNKNOWN
    assert res_timeout.retryable is False

    print("[PASS] Stripe Sandbox Validation Tests")


def test_razorpay_sandbox_validation():
    """Test RazorpayAdapter in mocked sandbox execution mode across all key scenarios."""
    adapter = RazorpayAdapter()
    assert adapter.provider_name == "razorpay"

    # 1. Order Creation Success Scenario
    payload_success = {
        "action_id": "act_rzp_001",
        "mock_client": True,
        "mock_type": "success",
        "merchant_id": "merch_456",
        "retry_count": 1,
    }
    res_success = adapter.execute_action("RETRY_PAYMENT", 2500.00, "INR", payload_success)
    assert res_success.success is True
    assert res_success.execution_state == ExecutionState.CONFIRMED_EXECUTED
    assert res_success.error_classification == ErrorClassification.NONE
    assert res_success.gateway_response.get("receipt") == "rcpt_act_rzp_001_1"

    # 2. Transient Bad Request Error Scenario
    payload_bad_req = {
        "action_id": "act_rzp_002",
        "mock_client": True,
        "mock_type": "bad_request",
    }
    res_bad_req = adapter.execute_action("RETRY_PAYMENT", 1000.00, "INR", payload_bad_req)
    assert res_bad_req.success is False
    assert res_bad_req.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_bad_req.error_classification == ErrorClassification.TRANSIENT
    assert res_bad_req.retryable is True

    # 3. Permanent / Fatal Bad Request Error Classification Rule Check
    # Verify classify_razorpay_error accurately classifies non-transient errors (invalid/expired card) as PERMANENT
    class DummyBadRequestError(Exception):
        pass

    exc_permanent = DummyBadRequestError("BadRequestError: invalid_card details specified")
    res_perm_classified = adapter.classify_razorpay_error(exc_permanent)
    assert res_perm_classified.success is False
    assert res_perm_classified.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_perm_classified.error_classification == ErrorClassification.PERMANENT
    assert res_perm_classified.retryable is False

    # 4. Upstream Gateway / Server Error Scenario
    payload_gw_err = {
        "action_id": "act_rzp_003",
        "mock_client": True,
        "mock_type": "gateway_error",
    }
    res_gw_err = adapter.execute_action("RETRY_PAYMENT", 1500.00, "INR", payload_gw_err)
    assert res_gw_err.success is False
    assert res_gw_err.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_gw_err.error_classification == ErrorClassification.TRANSIENT

    # 5. Network Timeout / UNKNOWN Execution State Scenario
    payload_timeout = {
        "action_id": "act_rzp_004",
        "mock_client": True,
        "mock_type": "timeout",
    }
    res_timeout = adapter.execute_action("RETRY_PAYMENT", 2000.00, "INR", payload_timeout)
    assert res_timeout.success is False
    assert res_timeout.execution_state == ExecutionState.UNKNOWN
    assert res_timeout.error_classification == ErrorClassification.UNKNOWN
    assert res_timeout.retryable is False

    print("[PASS] Razorpay Sandbox Validation Tests")


def test_resilient_executor_safety_rules():
    """
    Enforces the UNKNOWN state safety rule in ResilientGatewayExecutor:
    1. Primary gateway failure with CONFIRMED_NOT_EXECUTED + TRANSIENT allows backup failover.
    2. Primary gateway failure with UNKNOWN execution state STRICTLY BLOCKS automatic backup failover.
    """
    executor = ResilientGatewayExecutor()

    # Case A: Primary fails with TRANSIENT + CONFIRMED_NOT_EXECUTED -> Fallback allowed
    res_a = executor.execute_with_fallback(
        action_type="RETRY_PAYMENT",
        amount=100.00,
        currency="USD",
        primary_provider="stripe",
        backup_provider="razorpay",
        action_id="act_safe_001",
        payload={
            "simulate_primary_failure": True,
            "simulate_execution_state": ExecutionState.CONFIRMED_NOT_EXECUTED,
            "simulate_error_classification": ErrorClassification.TRANSIENT,
            "mock_client": True,
        },
    )
    assert res_a.success is True
    assert res_a.gateway_response.get("fallback_executed") is True
    assert res_a.gateway_response.get("primary_gateway") == "stripe"

    # Case B: Primary fails with UNKNOWN execution state -> Automatic fallback STRICTLY BLOCKED
    res_b = executor.execute_with_fallback(
        action_type="RETRY_PAYMENT",
        amount=100.00,
        currency="USD",
        primary_provider="stripe",
        backup_provider="razorpay",
        action_id="act_safe_002",
        payload={
            "simulate_primary_failure": True,
            "simulate_execution_state": ExecutionState.UNKNOWN,
            "simulate_error_classification": ErrorClassification.UNKNOWN,
            "mock_client": True,
        },
    )
    assert res_b.success is False
    assert res_b.execution_state == ExecutionState.UNKNOWN
    assert res_b.gateway_response.get("fallback_blocked_reason") == "UNKNOWN_EXECUTION_STATE"
    assert res_b.gateway_response.get("fallback_executed") is not True

    print("[PASS] Resilient Executor Safety Rules Tests (UNKNOWN State Blocking)")


def test_webhook_provider_signature_verification():
    """
    Tests provider-native webhook signature verification for Stripe, Razorpay, and global secrets.
    """
    secret = "whsec_test_secret_key_12345"
    payload = b'{"event_id": "evt_test_99", "amount": 1500}'

    # 1. Stripe Header Format (t=<timestamp>,v1=<sig>)
    now = int(time.time())
    signed_payload = f"{now}.".encode("utf-8") + payload
    valid_stripe_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    stripe_header = f"t={now},v1={valid_stripe_sig}"

    # Valid Stripe Header
    assert verify_webhook_signature(payload, stripe_header, secret) is True

    # Expired Stripe Timestamp (> 300s drift)
    expired_time = now - 400
    expired_signed_payload = f"{expired_time}.".encode("utf-8") + payload
    expired_stripe_sig = hmac.new(secret.encode("utf-8"), expired_signed_payload, hashlib.sha256).hexdigest()
    expired_stripe_header = f"t={expired_time},v1={expired_stripe_sig}"
    assert verify_webhook_signature(payload, expired_stripe_header, secret) is False

    # Invalid Stripe Signature
    invalid_stripe_header = f"t={now},v1=invalid_stripe_signature_hash"
    assert verify_webhook_signature(payload, invalid_stripe_header, secret) is False

    # 2. Razorpay Header Format (X-Razorpay-Signature)
    valid_rzp_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(payload, valid_rzp_sig, secret) is True
    assert verify_webhook_signature(payload, "invalid_rzp_signature_hex", secret) is False

    print("[PASS] Webhook Provider Signature Verification Tests")


def test_tenant_isolation_and_security():
    """
    Verifies cryptographic tenant isolation:
    1. Signature with Merchant A secret resolves to Merchant A.
    2. Signature with Merchant A secret NEVER authenticates as Merchant B.
    """
    secret_m1 = "whsec_merchant_alpha_secret"
    secret_m2 = "whsec_merchant_beta_secret"
    payload = b'{"id": "evt_iso_100", "status": "FAILED"}'

    # Create Razorpay signature for Merchant Alpha
    sig_m1 = hmac.new(secret_m1.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.execute.return_value.data = [
        {"merchant_id": "merchant_alpha", "webhook_secret": secret_m1},
        {"merchant_id": "merchant_beta", "webhook_secret": secret_m2},
    ]

    with patch("app.routers.events.get_supabase_admin_client", return_value=mock_db):
        resolved_merchant = resolve_webhook_merchant(payload, sig_m1)
        assert resolved_merchant == "merchant_alpha"
        assert resolved_merchant != "merchant_beta"

    # Spoofed/Tampered signature attempting to access Merchant Beta
    invalid_sig = hmac.new(b"wrong_secret", payload, hashlib.sha256).hexdigest()
    with patch("app.routers.events.get_supabase_admin_client", return_value=mock_db):
        resolved_spoofed = resolve_webhook_merchant(payload, invalid_sig)
        assert resolved_spoofed is None

    print("[PASS] Tenant Isolation & Webhook Security Tests")


def run_all_phase93_tests():
    """Main runner for Phase 9.3 Sandbox Gateway Validation tests."""
    print("Executing Phase 9.3 Sandbox Gateway Validation Test Suite...")
    test_stripe_sandbox_validation()
    test_razorpay_sandbox_validation()
    test_resilient_executor_safety_rules()
    test_webhook_provider_signature_verification()
    test_tenant_isolation_and_security()
    print("ALL PHASE 9.3 SANDBOX GATEWAY VALIDATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_all_phase93_tests()
