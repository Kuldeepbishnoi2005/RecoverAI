"""
Data Sanitizer Utility
Sanitizes and redacts sensitive parameters, credentials, API keys, tokens,
and payment card details in payloads, headers, and logs before API response/storage.
"""
import re
from typing import Any, Dict, List, Union

SENSITIVE_KEY_PATTERNS = {
    "authorization", "authorization_header", "bearer", "bearer_token",
    "token", "access_token", "api_key", "apikey", "secret", "secret_key",
    "webhook_secret", "signing_secret", "password", "private_key",
    "cvv", "cvc", "pan", "card_number", "account_number", "ssn",
    "x-webhook-signature", "x-signature", "stripe-signature"
}


def sanitize_value(key: str, value: Any) -> Any:
    """Sanitizes a single key-value pair based on sensitive key patterns."""
    key_lower = str(key).lower().replace("-", "_")

    # Direct sensitive key match or substring match
    is_sensitive_key = any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS)

    if is_sensitive_key:
        if isinstance(value, str):
            if len(value) <= 6:
                return "[REDACTED]"
            # Preserve prefix if present (e.g., whsec_1234 -> whsec_***)
            if value.startswith("whsec_"):
                return "whsec_***REDACTED***"
            if value.startswith("Bearer "):
                return "Bearer ***REDACTED***"
            return "[REDACTED]"
        return "[REDACTED]"

    return sanitize_sensitive_data(value)


def sanitize_sensitive_data(data: Any) -> Any:
    """
    Recursively walks dictionaries, lists, and primitives to redact sensitive fields.
    Returns a clean, sanitized deep copy of the data structure.
    """
    if isinstance(data, dict):
        sanitized_dict = {}
        for k, v in data.items():
            sanitized_dict[k] = sanitize_value(k, v)
        return sanitized_dict

    if isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]

    if isinstance(data, str):
        # Sanitize Bearer tokens in plain text strings
        if data.startswith("Bearer "):
            return "Bearer ***REDACTED***"
        # Sanitize hex signatures or raw keys in plain text
        if len(data) == 64 and re.match(r"^[0-9a-fA-F]{64}$", data):
            return "[REDACTED_HASH]"

    return data
