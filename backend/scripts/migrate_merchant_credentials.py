"""
One-Time Legacy Merchant Credential Migration Script
Migrates plaintext webhook secrets and API keys from merchant_settings / merchants tables
into the encrypted merchant_credentials store using AES-256-GCM envelope encryption.

Usage:
  python backend/scripts/migrate_merchant_credentials.py
"""
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.credential_resolver import migrate_legacy_merchant_credentials
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting explicit one-time legacy merchant credential migration...")
    logger.info(f"Target Environment: {settings.ENVIRONMENT}")

    # Ensure KMS Key check passes if running in production mode
    kms_key = settings.get_kms_key()
    if not kms_key:
        logger.error("KMS key resolution failed. Aborting migration.")
        sys.exit(1)

    result = migrate_legacy_merchant_credentials()
    migrated = result.get("migrated_records", 0)
    logger.info(f"Migration finished successfully. Total records migrated: {migrated}")


if __name__ == "__main__":
    main()
