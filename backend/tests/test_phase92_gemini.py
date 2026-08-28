import os
import sys
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.schemas import AIDecisionOutput
from app.ai.context_builder import build_ai_context
from app.ai.recovery_strategist import call_ai_strategist


def _build_dummy_context():
    raw_tx = {
        "transaction_id": "tx_gemini_test",
        "merchant_id": "merchant_001",
        "customer_id": "cust_001",
        "amount": 1000.0,
        "currency": "INR",
        "payment_method": "card",
        "transaction_status": "FAILED",
        "failure_code": "INSUFFICIENT_FUNDS",
        "failure_reason": "Insufficient funds in customer account",
        "retry_count": 1,
        "transaction_timestamp": "2026-08-28T00:00:00Z",
        "previous_success_rate": 0.8,
        "customer_lifetime_value": 5000.0,
        "subscription_status": "active",
        "days_since_last_success": 5
    }
    return build_ai_context(raw_tx)


def test_missing_api_key_fallback():
    """Proves that missing API key gracefully returns expert fallback without error."""
    context = _build_dummy_context()
    with patch("app.config.settings.GEMINI_API_KEY", ""):
        res = call_ai_strategist(context)
        assert isinstance(res, AIDecisionOutput)
        assert res.decision in ["RECOVER", "MANUAL_REVIEW", "NO_ACTION"]
        assert res.strategy in ["SMART_RETRY", "PAYMENT_METHOD_UPDATE", "PERSONALIZED_DUNNING", "CHECKOUT_REMINDER", "MANUAL_REVIEW", "NO_ACTION"]


def test_gemini_api_failure_fallback():
    """Proves that Gemini API exception triggers fallback decision safely."""
    context = _build_dummy_context()
    with patch("app.config.settings.GEMINI_API_KEY", "dummy_key"):
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("Network connection lost")
            mock_client_cls.return_value = mock_client

            res = call_ai_strategist(context)
            assert isinstance(res, AIDecisionOutput)
            assert res.decision in ["RECOVER", "MANUAL_REVIEW", "NO_ACTION"]


def test_modern_gemini_client_successful_mock():
    """Proves modern google.genai Client initialization & content generation returning valid schema."""
    context = _build_dummy_context()
    mock_response_data = {
        "decision": "RECOVER",
        "strategy": "SMART_RETRY",
        "confidence": 0.92,
        "recovery_probability": 0.78,
        "expected_recovery_amount": 780.0,
        "reason": "High probability smart retry candidate",
        "risk_factors": ["Observed failure"],
        "recommended_delay_minutes": 30,
        "fallback_strategy": "MANUAL_REVIEW"
    }

    with patch("app.config.settings.GEMINI_API_KEY", "mock_key"):
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = json.dumps(mock_response_data)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            res = call_ai_strategist(context)

            # Verify modern Client was initialized with api_key
            mock_client_cls.assert_called_once_with(api_key="mock_key")

            # Verify generate_content call
            mock_client.models.generate_content.assert_called_once()
            _, kwargs = mock_client.models.generate_content.call_args
            assert "model" in kwargs
            assert "contents" in kwargs
            assert "config" in kwargs

            # Verify response schema parsing
            assert res.decision == "RECOVER"
            assert res.strategy == "SMART_RETRY"
            assert res.confidence == 0.92
            assert res.expected_recovery_amount == 780.0


def run_gemini_migration_tests():
    print("--- RUNNING PHASE 9.2 GEMINI MIGRATION TESTS ---")
    tests = [
        ("1. Modern Gemini client initialization & generation success", test_modern_gemini_client_successful_mock),
        ("2. Missing API key fallback", test_missing_api_key_fallback),
        ("3. Gemini API failure fallback", test_gemini_api_failure_fallback),
    ]

    passed = 0
    for title, tfunc in tests:
        try:
            tfunc()
            print(f"[PASS] {title}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {title}: {str(e)}")

    print(f"\nGEMINI MIGRATION TEST RESULTS: {passed}/{len(tests)} PASSED")
    assert passed == len(tests)


if __name__ == "__main__":
    run_gemini_migration_tests()
