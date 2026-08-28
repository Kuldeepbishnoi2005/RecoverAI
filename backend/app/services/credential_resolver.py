"""
Multi-Tenant Gateway Credential Resolver & Envelope Encryption Service
Implements true AES-256-GCM envelope encryption (KEK wrapping per-record random DEK),
tenant isolation (merchant_id as AAD binding), multi-version key management,
production fail-closed KMS key validation, zero-exposure SecretString handling,
and legacy credential migration.
"""
import os
import json
import base64
import hashlib
import logging
from typing import Dict, Any, Optional, Union
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings

logger = logging.getLogger("app.services.credential_resolver")


class SecretString:
    """
    Secure wrapper for sensitive strings preventing accidental exposure in logs,
    repr(), str(), format strings, and stack traces.
    """

    def __init__(self, secret: str):
        if not isinstance(secret, str):
            raise TypeError("SecretString requires a string value")
        self._secret = secret

    def get_secret_value(self) -> str:
        return self._secret

    def __repr__(self) -> str:
        return "SecretString('[REDACTED]')"

    def __str__(self) -> str:
        return "[REDACTED]"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SecretString):
            return self._secret == other._secret
        if isinstance(other, str):
            return self._secret == other
        return False


class CredentialResolver:
    """
    Service for encrypting, decrypting, and resolving multi-tenant gateway credentials
    using true envelope encryption:
    - KEK (Key Encryption Key): Derived from versioned KMS master key.
    - DEK (Data Encryption Key): Cryptographically random 256-bit key generated per record.
    - AAD (Additional Authenticated Data): Bound strictly to merchant_id for tenant isolation.
    """

    def __init__(
        self,
        kms_key: Optional[str] = None,
        kms_keys: Optional[Dict[int, str]] = None,
    ):
        self._kms_keys: Dict[int, bytes] = {}

        if kms_keys:
            for ver, key_str in kms_keys.items():
                if key_str:
                    self._kms_keys[int(ver)] = hashlib.sha256(key_str.encode("utf-8")).digest()

        # Primary / active KMS key
        if kms_key:
            primary_bytes = hashlib.sha256(kms_key.encode("utf-8")).digest()
            self._kms_keys[1] = primary_bytes
        elif not self._kms_keys:
            raw_key = settings.get_kms_key()
            primary_bytes = hashlib.sha256(raw_key.encode("utf-8")).digest()
            self._kms_keys[1] = primary_bytes

    def _normalize_merchant_id(self, merchant_id: Union[str, UUID]) -> str:
        return str(merchant_id).strip()

    def _get_aad(self, merchant_id: Union[str, UUID]) -> bytes:
        return self._normalize_merchant_id(merchant_id).encode("utf-8")

    def _get_kek_bytes(self, key_version: int = 1, kms_key_override: Optional[str] = None) -> bytes:
        if kms_key_override:
            return hashlib.sha256(kms_key_override.encode("utf-8")).digest()

        if key_version in self._kms_keys:
            return self._kms_keys[key_version]

        if 1 in self._kms_keys:
            return self._kms_keys[1]

        raw_key = settings.get_kms_key()
        return hashlib.sha256(raw_key.encode("utf-8")).digest()

    def encrypt(
        self,
        merchant_id: Union[str, UUID],
        raw_secret: str,
        kms_key: Optional[str] = None,
        key_version: int = 1,
    ) -> str:
        """
        Encrypts a raw secret string using true envelope encryption (KEK wrapping a random DEK).
        Returns a base64-encoded JSON envelope string containing:
        - v: key_version
        - ep: encrypted_payload (secret encrypted under random DEK)
        - wd: wrapped_dek (DEK encrypted under KEK)
        - pn: payload_nonce (12-byte nonce for payload encryption)
        - wn: wrapped_dek_nonce (12-byte nonce for DEK wrapping)
        """
        if not raw_secret:
            raise ValueError("Cannot encrypt an empty secret.")

        m_id = self._normalize_merchant_id(merchant_id)
        aad = self._get_aad(m_id)

        # 1. Generate random 256-bit DEK & nonces
        dek = os.urandom(32)
        payload_nonce = os.urandom(12)
        wrapped_dek_nonce = os.urandom(12)

        # 2. Encrypt payload with DEK (bound to merchant AAD)
        aesgcm_dek = AESGCM(dek)
        encrypted_payload_bytes = aesgcm_dek.encrypt(payload_nonce, raw_secret.encode("utf-8"), aad)

        # 3. Wrap DEK with KEK (bound to merchant AAD)
        kek_bytes = self._get_kek_bytes(key_version=key_version, kms_key_override=kms_key)
        aesgcm_kek = AESGCM(kek_bytes)
        wrapped_dek_bytes = aesgcm_kek.encrypt(wrapped_dek_nonce, dek, aad)

        # 4. Construct JSON envelope structure
        envelope = {
            "v": key_version,
            "ep": base64.b64encode(encrypted_payload_bytes).decode("ascii"),
            "wd": base64.b64encode(wrapped_dek_bytes).decode("ascii"),
            "pn": base64.b64encode(payload_nonce).decode("ascii"),
            "wn": base64.b64encode(wrapped_dek_nonce).decode("ascii"),
        }

        envelope_json = json.dumps(envelope)
        return base64.b64encode(envelope_json.encode("utf-8")).decode("ascii")

    def decrypt(
        self,
        merchant_id: Union[str, UUID],
        encrypted_payload: Union[str, Dict[str, Any]],
        kms_key: Optional[str] = None,
    ) -> SecretString:
        """
        Decrypts an envelope-encrypted payload using KEK unwrapping of DEK and merchant AAD validation.
        Fails if payload is tampered with, decrypted under wrong merchant_id (tenant mismatch), or wrong KMS key.
        Supports both base64 envelope strings and DB record dictionaries.
        """
        if not encrypted_payload:
            raise ValueError("Cannot decrypt an empty payload.")

        m_id = self._normalize_merchant_id(merchant_id)
        aad = self._get_aad(m_id)

        try:
            key_ver = 1
            ep_bytes = b""
            wd_bytes = b""
            pn_bytes = b""
            wn_bytes = b""

            if isinstance(encrypted_payload, dict):
                if "wrapped_dek" in encrypted_payload and encrypted_payload["wrapped_dek"]:
                    key_ver = int(encrypted_payload.get("key_version", 1))
                    ep_bytes = base64.b64decode(encrypted_payload["encrypted_payload"])
                    wd_bytes = base64.b64decode(encrypted_payload["wrapped_dek"])
                    pn_bytes = base64.b64decode(encrypted_payload["payload_nonce"])
                    wn_bytes = base64.b64decode(encrypted_payload["wrapped_dek_nonce"])
                elif "encrypted_payload" in encrypted_payload and isinstance(encrypted_payload["encrypted_payload"], str):
                    return self.decrypt(merchant_id, encrypted_payload["encrypted_payload"], kms_key=kms_key)
                else:
                    raise ValueError("Invalid dictionary payload format")
            elif isinstance(encrypted_payload, str):
                decoded_str = base64.b64decode(encrypted_payload).decode("utf-8", errors="ignore")
                try:
                    envelope = json.loads(decoded_str)
                    if isinstance(envelope, dict) and "ep" in envelope and "wd" in envelope:
                        key_ver = int(envelope.get("v", 1))
                        ep_bytes = base64.b64decode(envelope["ep"])
                        wd_bytes = base64.b64decode(envelope["wd"])
                        pn_bytes = base64.b64decode(envelope["pn"])
                        wn_bytes = base64.b64decode(envelope["wn"])
                    else:
                        raise ValueError("Not JSON envelope format")
                except Exception:
                    # Backward compatibility for direct AESGCM non-envelope byte payloads
                    raw_bytes = base64.b64decode(encrypted_payload)
                    if len(raw_bytes) < 28:
                        raise ValueError("Payload too short")
                    pn_bytes = raw_bytes[:12]
                    ep_bytes = raw_bytes[12:]
                    kek_bytes = self._get_kek_bytes(key_version=1, kms_key_override=kms_key)
                    aesgcm_direct = AESGCM(kek_bytes)
                    decrypted_direct = aesgcm_direct.decrypt(pn_bytes, ep_bytes, aad)
                    return SecretString(decrypted_direct.decode("utf-8"))
            else:
                raise ValueError("Unsupported payload type")

            # Envelope decryption pipeline:
            # Step 1: Unwrap DEK using KEK + wrapped_dek_nonce + AAD
            kek_bytes = self._get_kek_bytes(key_version=key_ver, kms_key_override=kms_key)
            aesgcm_kek = AESGCM(kek_bytes)
            dek = aesgcm_kek.decrypt(wn_bytes, wd_bytes, aad)

            # Step 2: Decrypt payload using unwrapped DEK + payload_nonce + AAD
            aesgcm_dek = AESGCM(dek)
            decrypted_bytes = aesgcm_dek.decrypt(pn_bytes, ep_bytes, aad)

            return SecretString(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Credential decryption failed for tenant '{m_id}': {e}")
            raise ValueError(
                "Decryption failed: invalid ciphertext, wrong KMS key, or merchant tenant mismatch."
            ) from e

    def get_merchant_credential(
        self,
        merchant_id: Union[str, UUID],
        provider: str,
        credential_type: str,
        supabase_client: Optional[Any] = None,
    ) -> Optional[SecretString]:
        """
        Retrieves and decrypts a specific credential for a merchant from database.
        """
        m_id = self._normalize_merchant_id(merchant_id)
        try:
            from app.db import get_supabase_admin_client
            client = supabase_client or get_supabase_admin_client()
            res = (
                client.table("merchant_credentials")
                .select("encrypted_payload, wrapped_dek, payload_nonce, wrapped_dek_nonce, key_version")
                .eq("merchant_id", m_id)
                .eq("provider", provider)
                .eq("credential_type", credential_type)
                .execute()
            )

            if res and res.data and len(res.data) > 0:
                record = res.data[0]
                if record.get("encrypted_payload") and record.get("wrapped_dek"):
                    return self.decrypt(m_id, record)
        except Exception as e:
            logger.warning(f"Failed to fetch encrypted credential from database for merchant '{m_id}': {e}")

        return None

    def store_merchant_credential(
        self,
        merchant_id: Union[str, UUID],
        provider: str,
        credential_type: str,
        raw_secret: str,
        key_version: int = 1,
        supabase_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Encrypts and upserts a merchant credential record in the database using envelope encryption.
        """
        m_id = self._normalize_merchant_id(merchant_id)
        envelope_str = self.encrypt(m_id, raw_secret, key_version=key_version)

        # Decode envelope JSON to populate DB columns
        decoded_json = base64.b64decode(envelope_str).decode("utf-8")
        envelope = json.loads(decoded_json)

        from app.db import get_supabase_admin_client
        client = supabase_client or get_supabase_admin_client()

        record = {
            "merchant_id": m_id,
            "provider": provider,
            "credential_type": credential_type,
            "encrypted_payload": envelope["ep"],
            "wrapped_dek": envelope["wd"],
            "payload_nonce": envelope["pn"],
            "wrapped_dek_nonce": envelope["wn"],
            "key_version": key_version,
        }
        res = client.table("merchant_credentials").upsert(record, on_conflict="merchant_id,provider,credential_type").execute()
        return res.data[0] if res and res.data else record

    def get_provider_credentials(
        self,
        merchant_id: Union[str, UUID],
        provider: str,
        supabase_client: Optional[Any] = None,
    ) -> Dict[str, SecretString]:
        """
        Retrieves all decrypted credentials for a merchant provider (e.g. key_id, key_secret for razorpay).
        """
        m_id = self._normalize_merchant_id(merchant_id)
        credentials: Dict[str, SecretString] = {}
        try:
            from app.db import get_supabase_admin_client
            client = supabase_client or get_supabase_admin_client()
            res = (
                client.table("merchant_credentials")
                .select("credential_type, encrypted_payload, wrapped_dek, payload_nonce, wrapped_dek_nonce, key_version")
                .eq("merchant_id", m_id)
                .eq("provider", provider)
                .execute()
            )

            if res and res.data:
                for row in res.data:
                    c_type = row.get("credential_type")
                    if c_type and row.get("encrypted_payload") and row.get("wrapped_dek"):
                        credentials[c_type] = self.decrypt(m_id, row)
        except Exception as e:
            logger.warning(f"Failed to fetch credentials for merchant '{m_id}' provider '{provider}': {e}")

        return credentials


def migrate_legacy_merchant_credentials(supabase_client: Optional[Any] = None) -> Dict[str, int]:
    """
    Utility function to safely migrate legacy plaintext webhook secrets and API keys
    from merchant_settings / merchants tables into the encrypted merchant_credentials store.
    """
    from app.db import get_supabase_admin_client
    client = supabase_client or get_supabase_admin_client()
    migrated_count = 0

    try:
        # Migrate merchant_settings webhook secrets
        ms_res = client.table("merchant_settings").select("merchant_id, webhook_secret, stripe_secret_key, razorpay_key_id, razorpay_key_secret").execute()
        if ms_res and ms_res.data:
            for row in ms_res.data:
                m_id = row.get("merchant_id")
                if not m_id:
                    continue

                if row.get("webhook_secret"):
                    credential_resolver.store_merchant_credential(
                        m_id, "webhook", "webhook_secret", row["webhook_secret"], supabase_client=client
                    )
                    migrated_count += 1

                if row.get("stripe_secret_key"):
                    credential_resolver.store_merchant_credential(
                        m_id, "stripe", "secret_key", row["stripe_secret_key"], supabase_client=client
                    )
                    migrated_count += 1

                if row.get("razorpay_key_id"):
                    credential_resolver.store_merchant_credential(
                        m_id, "razorpay", "key_id", row["razorpay_key_id"], supabase_client=client
                    )
                    migrated_count += 1

                if row.get("razorpay_key_secret"):
                    credential_resolver.store_merchant_credential(
                        m_id, "razorpay", "key_secret", row["razorpay_key_secret"], supabase_client=client
                    )
                    migrated_count += 1
    except Exception as e:
        logger.warning(f"Legacy merchant_settings migration failed or table absent: {e}")

    return {"migrated_records": migrated_count}


# Singleton instance for standard app usage
credential_resolver = CredentialResolver()
