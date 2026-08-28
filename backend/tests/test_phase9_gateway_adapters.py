"""
Phase 9.1 Automated Test Suite: Production Gateway Adapters
Tests StripeAdapter, RazorpayAdapter, error classification mapping, idempotency propagation,
UNKNOWN state protection, webhook signature verification, factory registration, and sandbox default.
ALL TESTS MOCK NETWORK CALLS - ZERO REAL MONEY OR NETWORK REQUESTS.
"""
import sys
import os
import time
import hmac
import hashlib
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters.base import ExecutionState, ErrorClassification
from app.adapters.sandbox import SandboxSimulatorAdapter
from app.adapters.stripe_adapter import StripeAdapter
from app.adapters.razorpay_adapter import RazorpayAdapter
from app.adapters.factory import get_gateway_adapter


# --- 1. STRIPE ADAPTER TESTS ---

def test_stripe_adapter_success():
    """Stripe Adapter: Successful execution returns CONFIRMED_EXECUTED and NONE."""
    adapter = StripeAdapter()
    res = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=50.0,
        currency="USD",
        payload={
            "action_id": "act_stripe_01",
            "mock_client": True,
            "mock_type": "success",
            "stripe_payment_intent_id": "pi_123456789",
        },
    )
    assert res.success is True
    assert res.transaction_id == "pi_123456789"
    assert res.execution_state == ExecutionState.CONFIRMED_EXECUTED
    assert res.error_classification == ErrorClassification.NONE
    assert res.gateway_response.get("provider") == "stripe"


def test_stripe_adapter_idempotency_propagation():
    """Stripe Adapter: Deterministic idempotency key is propagated in request payload/options."""
    adapter = StripeAdapter()
    res = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=100.0,
        currency="USD",
        payload={
            "action_id": "act_idem_test",
            "role": "primary",
            "retry_count": 2,
            "mock_client": True,
            "mock_type": "success",
        },
    )
    assert res.success is True
    expected_idem_key = "idem_act_idem_test_primary_2_stripe"
    assert res.gateway_response.get("idempotency_key") == expected_idem_key


def test_stripe_adapter_error_classification():
    """Stripe Adapter: Maps card decline to TRANSIENT and expired card to PERMANENT."""
    adapter = StripeAdapter()

    # 1. Card Declined -> Transient
    res_decline = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=75.0,
        currency="USD",
        payload={
            "action_id": "act_stripe_dec",
            "mock_client": True,
            "mock_type": "card_declined",
        },
    )
    assert res_decline.success is False
    assert res_decline.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_decline.error_classification == ErrorClassification.TRANSIENT
    assert res_decline.retryable is True

    # 2. Expired Card -> Permanent
    res_expired = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=75.0,
        currency="USD",
        payload={
            "action_id": "act_stripe_exp",
            "mock_client": True,
            "mock_type": "expired_card",
        },
    )
    assert res_expired.success is False
    assert res_expired.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_expired.error_classification == ErrorClassification.PERMANENT
    assert res_expired.retryable is False


def test_stripe_adapter_unknown_state_handling():
    """Stripe Adapter: Network timeout/connection failure returns ExecutionState.UNKNOWN."""
    adapter = StripeAdapter()
    res = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=200.0,
        currency="USD",
        payload={
            "action_id": "act_stripe_timeout",
            "mock_client": True,
            "mock_type": "timeout",
        },
    )
    assert res.success is False
    assert res.execution_state == ExecutionState.UNKNOWN
    assert res.error_classification == ErrorClassification.UNKNOWN
    assert res.retryable is False


def test_stripe_adapter_webhook_signature_verification():
    """Stripe Adapter: Validates HMAC-SHA256 signature and timestamp tolerance window."""
    adapter = StripeAdapter()
    secret = "whsec_test_secret_key_12345"
    payload_bytes = b'{"id": "evt_test_01", "type": "payment_intent.succeeded"}'
    now = int(time.time())

    # 1. Valid Signature
    signed_payload = f"{now}.".encode("utf-8") + payload_bytes
    valid_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    valid_header = f"t={now},v1={valid_sig}"

    assert adapter.verify_webhook_signature(payload_bytes, valid_header, secret) is True

    # 2. Invalid Signature Header
    invalid_header = f"t={now},v1=invalid_signature_hex"
    assert adapter.verify_webhook_signature(payload_bytes, invalid_header, secret) is False

    # 3. Expired Timestamp Drift (> 300 seconds)
    old_time = now - 305
    old_signed_payload = f"{old_time}.".encode("utf-8") + payload_bytes
    old_sig = hmac.new(secret.encode("utf-8"), old_signed_payload, hashlib.sha256).hexdigest()
    old_header = f"t={old_time},v1={old_sig}"

    assert adapter.verify_webhook_signature(payload_bytes, old_header, secret) is False


# --- 2. RAZORPAY ADAPTER TESTS ---

def test_razorpay_adapter_success():
    """Razorpay Adapter: Successful execution returns CONFIRMED_EXECUTED and NONE."""
    adapter = RazorpayAdapter()
    res = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=1500.0,
        currency="INR",
        payload={
            "action_id": "act_rzp_01",
            "retry_count": 1,
            "mock_client": True,
            "mock_type": "success",
        },
    )
    assert res.success is True
    assert res.execution_state == ExecutionState.CONFIRMED_EXECUTED
    assert res.error_classification == ErrorClassification.NONE
    assert res.gateway_response.get("provider") == "razorpay"
    assert "order_mock_rcpt_act_rzp_01_1" in res.transaction_id


def test_razorpay_adapter_application_side_idempotency():
    """Razorpay Adapter: Passes receipt identifier to support application-side idempotency."""
    adapter = RazorpayAdapter()
    res = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=2500.0,
        currency="INR",
        payload={
            "action_id": "act_rzp_idem",
            "retry_count": 3,
            "mock_client": True,
            "mock_type": "success",
        },
    )
    assert res.success is True
    assert res.gateway_response.get("receipt") == "rcpt_act_rzp_idem_3"


def test_razorpay_adapter_error_classification():
    """Razorpay Adapter: Maps BAD_REQUEST_ERROR and GATEWAY_ERROR to correct states."""
    adapter = RazorpayAdapter()

    # 1. Bad Request -> Transient
    res_bad = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=999.0,
        currency="INR",
        payload={
            "action_id": "act_rzp_bad",
            "mock_client": True,
            "mock_type": "bad_request",
        },
    )
    assert res_bad.success is False
    assert res_bad.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_bad.error_classification == ErrorClassification.TRANSIENT
    assert res_bad.retryable is True

    # 2. Gateway Error -> Transient
    res_gw = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=999.0,
        currency="INR",
        payload={
            "action_id": "act_rzp_gw",
            "mock_client": True,
            "mock_type": "gateway_error",
        },
    )
    assert res_gw.success is False
    assert res_gw.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
    assert res_gw.error_classification == ErrorClassification.TRANSIENT
    assert res_gw.retryable is True


def test_razorpay_adapter_unknown_state_handling():
    """Razorpay Adapter: Timeout/Connection failure returns ExecutionState.UNKNOWN."""
    adapter = RazorpayAdapter()
    res = adapter.execute_action(
        action_type="RETRY_CHARGE",
        amount=5000.0,
        currency="INR",
        payload={
            "action_id": "act_rzp_timeout",
            "mock_client": True,
            "mock_type": "timeout",
        },
    )
    assert res.success is False
    assert res.execution_state == ExecutionState.UNKNOWN
    assert res.error_classification == ErrorClassification.UNKNOWN
    assert res.retryable is False


def test_razorpay_adapter_webhook_signature_verification():
    """Razorpay Adapter: Validates HMAC-SHA256 signature against raw payload bytes."""
    adapter = RazorpayAdapter()
    secret = "rzp_secret_key_8888"
    payload_bytes = b'{"event": "payment.captured", "entity": "event"}'

    # 1. Valid Signature
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    assert adapter.verify_webhook_signature(payload_bytes, valid_sig, secret) is True

    # 2. Invalid Signature
    invalid_sig = "invalid_razorpay_signature_hex"
    assert adapter.verify_webhook_signature(payload_bytes, invalid_sig, secret) is False


# --- 3. FACTORY & REGISTRATION TESTS ---

def test_adapter_factory_registration_and_sandbox_default():
    """Factory correctly instantiates registered adapters and defaults safely to Sandbox."""
    # 1. Registered Stripe
    stripe_adapter = get_gateway_adapter("stripe")
    assert isinstance(stripe_adapter, StripeAdapter)
    assert stripe_adapter.provider_name == "stripe"

    # 2. Registered Razorpay
    razorpay_adapter = get_gateway_adapter("razorpay")
    assert isinstance(razorpay_adapter, RazorpayAdapter)
    assert razorpay_adapter.provider_name == "razorpay"

    # 3. Explicit Sandbox
    sandbox_adapter = get_gateway_adapter("sandbox")
    assert isinstance(sandbox_adapter, SandboxSimulatorAdapter)
    assert sandbox_adapter.provider_name == "sandbox"

    # 4. Unknown provider -> Defaults safely to SandboxSimulatorAdapter
    unknown_adapter = get_gateway_adapter("unknown_provider_xyz")
    assert isinstance(unknown_adapter, SandboxSimulatorAdapter)
    assert unknown_adapter.provider_name == "sandbox"

    # 5. Empty / None provider -> Defaults safely to SandboxSimulatorAdapter
    empty_adapter = get_gateway_adapter("")
    assert isinstance(empty_adapter, SandboxSimulatorAdapter)
    assert empty_adapter.provider_name == "sandbox"


def run_all_phase9_tests():
    """Helper runner for Phase 9.1 test suite."""
    print("\n--- RUNNING PHASE 9.1 PRODUCTION GATEWAY ADAPTER TEST SUITE ---")
    tests = [
        ("1. Stripe Adapter Success", test_stripe_adapter_success),
        ("2. Stripe Idempotency Propagation", test_stripe_adapter_idempotency_propagation),
        ("3. Stripe Error Classification", test_stripe_adapter_error_classification),
        ("4. Stripe UNKNOWN State Handling", test_stripe_adapter_unknown_state_handling),
        ("5. Stripe Webhook Signature Verification", test_stripe_adapter_webhook_signature_verification),
        ("6. Razorpay Adapter Success", test_razorpay_adapter_success),
        ("7. Razorpay Application-Side Idempotency", test_razorpay_adapter_application_side_idempotency),
        ("8. Razorpay Error Classification", test_razorpay_adapter_error_classification),
        ("9. Razorpay UNKNOWN State Handling", test_razorpay_adapter_unknown_state_handling),
        ("10. Razorpay Webhook Signature Verification", test_razorpay_adapter_webhook_signature_verification),
        ("11. Adapter Factory Registration & Sandbox Default", test_adapter_factory_registration_and_sandbox_default),
    ]

    passed = 0
    failed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name} -> Error: {e}")
            failed += 1

    print(f"PHASE 9.1 TEST RESULTS: {passed} PASSED, {failed} FAILED")
    if failed > 0:
        raise RuntimeError(f"{failed} Phase 9.1 tests failed.")


if __name__ == "__main__":
    run_all_phase9_tests()
