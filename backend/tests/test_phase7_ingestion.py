import os
import sys
import hmac
import hashlib
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import settings

client = TestClient(app)

import uuid

def test_1_unsigned_unauthenticated_request_rejected():
    """Unsigned/unauthenticated requests must be rejected with 401 Unauthorized."""
    payload = {
        "event_id": f"evt_unauth_{uuid.uuid4().hex[:8]}",
        "transaction_id": "tx_unauth_001",
        "merchant_id": "spoofed_merchant_999",
        "amount": 500.0,
        "status": "FAILED"
    }
    response = client.post("/api/v1/events/ingest", json=payload)
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

def test_2_webhook_signature_verification_success_and_merchant_override():
    """Valid HMAC signature request succeeds and enforces verified merchant ID."""
    payload = {
        "event_id": f"evt_sig_{uuid.uuid4().hex[:8]}",
        "transaction_id": "tx_sig_001",
        "merchant_id": "attacker_spoofed_merchant",  # Should be overridden by verified merchant
        "customer_id": "cust_sig_001",
        "amount": 1200.0,
        "currency": "INR",
        "payment_method": "card",
        "status": "SUCCESS",
        "error_code": "NONE",
        "error_message": "None"
    }
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Webhook-Signature": signature,
        "Content-Type": "application/json"
    }

    response = client.post("/api/v1/events/ingest", content=raw_body, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "processed"
    assert res_data["auth_method"] == "WEBHOOK_SIGNATURE"
    # Crucial security assertion: client spoofed merchant ID is ignored and overridden
    assert res_data["merchant_id"] == "merchant_001"

def test_3_invalid_signature_rejected():
    """Invalid HMAC signature must be rejected with 401 Unauthorized."""
    payload = {"event_id": "evt_fake_001", "transaction_id": "tx_fake_001"}
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-Webhook-Signature": "invalid_signature_hash_12345",
        "Content-Type": "application/json"
    }
    response = client.post("/api/v1/events/ingest", content=raw_body, headers=headers)
    assert response.status_code == 401

def test_4_idempotency_duplicate_event_skipped():
    """Duplicate events with same event_id must be skipped without duplicate execution."""
    unique_evt = f"evt_idempotent_{uuid.uuid4().hex[:8]}"
    payload = {
        "event_id": unique_evt,
        "transaction_id": "tx_idempotent_001",
        "amount": 800.0,
        "status": "SUCCESS"
    }

    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Webhook-Signature": signature,
        "Content-Type": "application/json"
    }

    # First ingestion
    res1 = client.post("/api/v1/events/ingest", content=raw_body, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "processed"

    # Second duplicate ingestion
    res2 = client.post("/api/v1/events/ingest", content=raw_body, headers=headers)
    assert res2.status_code == 200
    res2_data = res2.json()
    assert res2_data["status"] == "already_processed"
    assert res2_data["pipeline_executed"] is False
    assert "Duplicate event ignored" in res2_data["message"]

def run_all_ingestion_tests():
    print("--- RUNNING PHASE 7 WEBHOOK INGESTION SECURITY TESTS ---")
    try:
        from app.routers.events import _PROCESSED_EVENTS, _to_uuid_str
        _PROCESSED_EVENTS.clear()
        
        from app.db import get_supabase_admin_client
        supabase = get_supabase_admin_client()
        
        test_ids = [
            _to_uuid_str("merchant_001:evt_sig_001"),
            _to_uuid_str("merchant_001:evt_idempotent_001")
        ]
        for tid in test_ids:
            supabase.table("transactions").delete().eq("id", tid).execute()
        supabase.table("transactions").delete().ilike("external_transaction_id", "%001%").execute()
    except Exception as e:
        print(f"Cleanup warning: {e}")


    test_1_unsigned_unauthenticated_request_rejected()
    print("[PASS] 1. Unsigned/unauthenticated request rejected (401)")
    test_2_webhook_signature_verification_success_and_merchant_override()
    print("[PASS] 2. Webhook signature verification & merchant ID override success")
    test_3_invalid_signature_rejected()
    print("[PASS] 3. Invalid signature rejected (401)")
    test_4_idempotency_duplicate_event_skipped()
    print("[PASS] 4. Idempotency duplicate event skipped (200 already_processed)")
    print("ALL PHASE 7 INGESTION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_ingestion_tests()
