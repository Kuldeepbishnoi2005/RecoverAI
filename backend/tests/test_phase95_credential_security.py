"""
Phase 9.5 Test Suite: Multi-Tenant Gateway Credential Security & Isolation
Validates AES-256-GCM envelope encryption, merchant AAD isolation, zero-exposure SecretString handling,
tamper rejection, key rotation, production fail-closed KMS key validation, and legacy migration safety.
"""
import unittest
import os
import json
import base64
import hmac
import hashlib
from unittest.mock import MagicMock, patch

from app.services.credential_resolver import (
    CredentialResolver,
    SecretString,
    migrate_legacy_merchant_credentials,
)
from app.routers.events import resolve_webhook_merchant, verify_webhook_signature
from app.config import settings, DEFAULT_DEV_KMS_KEY


class TestPhase95CredentialSecurity(unittest.TestCase):

    def setUp(self):
        self.kms_key_1 = "test_kms_master_key_32bytes_v1_recoverai"
        self.kms_key_2 = "test_kms_master_key_32bytes_v2_recoverai"
        self.resolver_v1 = CredentialResolver(kms_key=self.kms_key_1)
        self.resolver_v2 = CredentialResolver(kms_key=self.kms_key_2)
        self.merchant_a = "00000000-0000-4000-a000-000000000001"
        self.merchant_b = "00000000-0000-4000-a000-000000000002"

    def test_1_aes256_gcm_roundtrip(self):
        """Test AES-256-GCM roundtrip encryption and decryption."""
        raw_secret = "sk_test_mock_stripe_key_12345"
        encrypted_payload = self.resolver_v1.encrypt(self.merchant_a, raw_secret)
        self.assertIsInstance(encrypted_payload, str)
        self.assertNotEqual(encrypted_payload, raw_secret)

        decrypted = self.resolver_v1.decrypt(self.merchant_a, encrypted_payload)
        self.assertIsInstance(decrypted, SecretString)
        self.assertEqual(decrypted.get_secret_value(), raw_secret)

    def test_2_tampered_ciphertext_rejection(self):
        """Test that tampered base64 ciphertext fails authentication and raises ValueError."""
        raw_secret = "sk_test_mock_secret"
        encrypted_payload = self.resolver_v1.encrypt(self.merchant_a, raw_secret)

        # Tamper with the middle of the base64 string
        tampered_bytes = bytearray(encrypted_payload.encode("utf-8"))
        tampered_bytes[15] = (tampered_bytes[15] + 1) % 256
        tampered_payload = tampered_bytes.decode("utf-8", errors="ignore")

        with self.assertRaises(ValueError) as ctx:
            self.resolver_v1.decrypt(self.merchant_a, tampered_payload)
        self.assertIn("Decryption failed", str(ctx.exception))

    def test_3_wrong_merchant_aad_rejection(self):
        """Test that decrypting Merchant A's payload with Merchant B's ID fails (AAD validation)."""
        raw_secret = "sk_test_merchant_a_secret"
        encrypted_payload_a = self.resolver_v1.encrypt(self.merchant_a, raw_secret)

        # Attempt to decrypt Merchant A's payload using Merchant B's identity
        with self.assertRaises(ValueError) as ctx:
            self.resolver_v1.decrypt(self.merchant_b, encrypted_payload_a)
        self.assertIn("Decryption failed", str(ctx.exception))

    def test_4_key_versioning_and_rotation(self):
        """Test decrypting payload with a specific KMS key version during key rotation."""
        raw_secret = "rzp_test_secret_key_v1"
        payload_v1 = self.resolver_v1.encrypt(self.merchant_a, raw_secret, kms_key=self.kms_key_1)

        # Decrypting with wrong key fails
        with self.assertRaises(ValueError):
            self.resolver_v2.decrypt(self.merchant_a, payload_v1)

        # Decrypting with explicit old KMS key succeeds
        decrypted_old = self.resolver_v2.decrypt(self.merchant_a, payload_v1, kms_key=self.kms_key_1)
        self.assertEqual(decrypted_old.get_secret_value(), raw_secret)

        # Re-encrypt under new KMS key
        payload_v2 = self.resolver_v2.encrypt(self.merchant_a, raw_secret, kms_key=self.kms_key_2)
        decrypted_new = self.resolver_v2.decrypt(self.merchant_a, payload_v2)
        self.assertEqual(decrypted_new.get_secret_value(), raw_secret)

    def test_5_secret_string_repr_str_redaction(self):
        """Test that SecretString never exposes raw secrets in repr(), str(), or formatting."""
        raw_secret = "super_secret_stripe_live_key_999"
        secret_obj = SecretString(raw_secret)

        self.assertEqual(str(secret_obj), "[REDACTED]")
        self.assertEqual(repr(secret_obj), "SecretString('[REDACTED]')")
        self.assertNotIn(raw_secret, str(secret_obj))
        self.assertNotIn(raw_secret, repr(secret_obj))
        self.assertEqual(secret_obj.get_secret_value(), raw_secret)

    def test_6_secret_comparison_equality(self):
        """Test SecretString equality operator safely compares raw values."""
        sec1 = SecretString("secret_123")
        sec2 = SecretString("secret_123")
        sec3 = SecretString("secret_456")

        self.assertEqual(sec1, sec2)
        self.assertEqual(sec1, "secret_123")
        self.assertNotEqual(sec1, sec3)

    def test_7_missing_credentials_preserve_sandbox_fallback(self):
        """Test that empty or unconfigured credentials default safely to sandbox adapter."""
        from app.adapters.stripe_adapter import StripeAdapter
        from app.adapters.razorpay_adapter import RazorpayAdapter

        stripe_adapter = StripeAdapter()
        res_stripe = stripe_adapter.execute_action(
            action_type="retry_charge",
            amount=50.0,
            currency="USD",
            payload={"action_id": "act_test_01", "mock_client": True},
            merchant_settings={}
        )
        self.assertTrue(res_stripe.success)
        self.assertEqual(res_stripe.gateway_response.get("provider"), "stripe")

        razorpay_adapter = RazorpayAdapter()
        res_razorpay = razorpay_adapter.execute_action(
            action_type="retry_charge",
            amount=1000.0,
            currency="INR",
            payload={"action_id": "act_test_02", "mock_client": True},
            merchant_settings={}
        )
        self.assertTrue(res_razorpay.success)
        self.assertEqual(res_razorpay.gateway_response.get("provider"), "razorpay")

    def test_8_webhook_cryptographic_tenant_resolution_with_resolver(self):
        """Test cryptographic merchant resolution using encrypted webhook secrets."""
        raw_body = b'{"event": "payment.failed", "transaction_id": "tx_999"}'
        webhook_secret = "whsec_encrypted_merchant_a_signing_key_777"

        sig_header = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        enc_payload = self.resolver_v1.encrypt(self.merchant_a, webhook_secret)

        mock_data = [
            {
                "merchant_id": self.merchant_a,
                "encrypted_payload": enc_payload,
            }
        ]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_data

        with patch("app.routers.events.get_supabase_admin_client", return_value=mock_supabase), \
             patch("app.services.credential_resolver.credential_resolver", self.resolver_v1):

            resolved_id = resolve_webhook_merchant(raw_body, sig_header)
            self.assertEqual(resolved_id, self.merchant_a)

    def test_9_cross_tenant_webhook_signature_rejected(self):
        """Test that a webhook signed by Merchant A does not resolve to Merchant B."""
        raw_body = b'{"event": "payment.failed"}'
        secret_a = "whsec_merchant_a_secret"
        secret_b = "whsec_merchant_b_secret"

        sig_a = hmac.new(secret_a.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        enc_payload_b = self.resolver_v1.encrypt(self.merchant_b, secret_b)

        mock_data = [{"merchant_id": self.merchant_b, "encrypted_payload": enc_payload_b}]
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_data

        with patch("app.routers.events.get_supabase_admin_client", return_value=mock_supabase), \
             patch("app.services.credential_resolver.credential_resolver", self.resolver_v1):

            resolved_id = resolve_webhook_merchant(raw_body, sig_a)
            self.assertNotEqual(resolved_id, self.merchant_b)
            self.assertIsNone(resolved_id)

    def test_10_empty_and_invalid_inputs_safety(self):
        """Test empty/invalid secret or payload inputs fail cleanly without unhandled exceptions."""
        with self.assertRaises(ValueError):
            self.resolver_v1.encrypt(self.merchant_a, "")

        with self.assertRaises(ValueError):
            self.resolver_v1.decrypt(self.merchant_a, "")

        with self.assertRaises(TypeError):
            SecretString(12345)

    def test_11_production_kms_fail_closed(self):
        """Test that production environment with missing/default KMS key raises RuntimeError."""
        with patch.object(settings, "ENVIRONMENT", "production"), \
             patch.object(settings, "RECOVERAI_KMS_KEY", DEFAULT_DEV_KMS_KEY):
            with self.assertRaises(RuntimeError) as ctx:
                settings.get_kms_key()
            self.assertIn("Production Fail-Closed Violation", str(ctx.exception))

    def test_12_envelope_encryption_structure(self):
        """Test that encrypted payload contains true envelope encryption structure (ep, wd, pn, wn, v)."""
        raw_secret = "sk_live_stripe_secret_key_prod"
        encrypted_str = self.resolver_v1.encrypt(self.merchant_a, raw_secret)

        decoded_json = base64.b64decode(encrypted_str).decode("utf-8")
        envelope = json.loads(decoded_json)

        self.assertIn("v", envelope)
        self.assertIn("ep", envelope)
        self.assertIn("wd", envelope)
        self.assertIn("pn", envelope)
        self.assertIn("wn", envelope)

        # Encrypt second secret for same merchant to verify per-record DEK randomness
        encrypted_str_2 = self.resolver_v1.encrypt(self.merchant_a, raw_secret)
        envelope_2 = json.loads(base64.b64decode(encrypted_str_2).decode("utf-8"))

        self.assertNotEqual(envelope["wd"], envelope_2["wd"])
        self.assertNotEqual(envelope["ep"], envelope_2["ep"])

    def test_13_multi_key_version_resolution(self):
        """Test multi-key version resolution using CredentialResolver initialized with kms_keys mapping."""
        keys_map = {
            1: "master_kek_version_1_key_32bytes!",
            2: "master_kek_version_2_key_32bytes!",
        }
        multi_resolver = CredentialResolver(kms_keys=keys_map)

        secret_v1 = "secret_encrypted_under_v1"
        secret_v2 = "secret_encrypted_under_v2"

        enc_v1 = multi_resolver.encrypt(self.merchant_a, secret_v1, key_version=1)
        enc_v2 = multi_resolver.encrypt(self.merchant_a, secret_v2, key_version=2)

        dec_v1 = multi_resolver.decrypt(self.merchant_a, enc_v1)
        dec_v2 = multi_resolver.decrypt(self.merchant_a, enc_v2)

        self.assertEqual(dec_v1.get_secret_value(), secret_v1)
        self.assertEqual(dec_v2.get_secret_value(), secret_v2)

    def test_14_database_store_and_fetch_envelope_record(self):
        """Test storing and fetching encrypted credentials using database helper methods."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [
            {"merchant_id": self.merchant_a, "provider": "stripe", "credential_type": "secret_key"}
        ]

        store_res = self.resolver_v1.store_merchant_credential(
            merchant_id=self.merchant_a,
            provider="stripe",
            credential_type="secret_key",
            raw_secret="sk_test_stored_key",
            supabase_client=mock_supabase,
        )
        self.assertIsNotNone(store_res)
        mock_supabase.table.assert_called_with("merchant_credentials")

    def test_15_legacy_migration_utility(self):
        """Test legacy credential migration helper populates merchant_credentials correctly."""
        mock_supabase = MagicMock()
        mock_ms_data = [
            {
                "merchant_id": self.merchant_a,
                "webhook_secret": "whsec_legacy_a",
                "stripe_secret_key": "sk_test_legacy_a",
                "razorpay_key_id": "rzp_test_id_a",
                "razorpay_key_secret": "rzp_test_sec_a",
            }
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = mock_ms_data
        mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [{}]

        res = migrate_legacy_merchant_credentials(supabase_client=mock_supabase)
        self.assertEqual(res["migrated_records"], 4)


if __name__ == "__main__":
    unittest.main()
