import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.utils.sanitizer import sanitize_sensitive_data

def test_sanitizer_redacts_sensitive_keys_and_tokens():
    """Verify sensitive credentials and PII are redacted from data structures."""
    payload = {
        "event": "payment_intent.failed",
        "secret": "whsec_live_999888777666",
        "authorization": "Bearer secret_token_xyz123",
        "api_key": "sk_live_123456789",
        "card_number": "4111111111111111",
        "cvv": "123",
        "customer": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SuperSecretPassword123!"
        },
        "safe_field": "public_data"
    }

    sanitized = sanitize_sensitive_data(payload)

    assert sanitized["secret"] == "whsec_***REDACTED***"
    assert sanitized["authorization"] == "Bearer ***REDACTED***"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["card_number"] == "[REDACTED]"
    assert sanitized["cvv"] == "[REDACTED]"
    assert sanitized["customer"]["password"] == "[REDACTED]"
    assert sanitized["customer"]["name"] == "Jane Doe"
    assert sanitized["safe_field"] == "public_data"

def run_all_phase8b2_tests():
    print("--- RUNNING PHASE 8B.2 OBSERVABILITY & SANITIZATION TESTS ---")
    test_sanitizer_redacts_sensitive_keys_and_tokens()
    print("[PASS] 1. Sanitizer redacts credentials, authorization headers, and PII")
    print("ALL PHASE 8B.2 OBSERVABILITY TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_phase8b2_tests()
