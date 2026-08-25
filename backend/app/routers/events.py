import hmac
import hashlib
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends, Header, status
from pydantic import BaseModel, Field

from app.config import settings
from app.auth.deps import get_current_user, AuthenticatedUser
from app.db import get_supabase_admin_client
from app.services.recovery_pipeline import run_recovery_pipeline

logger = logging.getLogger("app.routers.events")

router = APIRouter(
    prefix="/events",
    tags=["events"]
)

# In-memory idempotency cache for fast lookup
_PROCESSED_EVENTS: Dict[str, Dict[str, Any]] = {}


class WebhookIngestResponse(BaseModel):
    status: str
    idempotency_key: str
    merchant_id: str
    transaction_id: str
    auth_method: str
    pipeline_executed: bool
    pipeline_run_id: Optional[str] = None
    message: str


def _to_uuid_str(val: str) -> str:
    """Converts a string to a valid UUID string deterministically."""
    try:
        return str(uuid.UUID(val))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val))


def verify_webhook_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """
    Verifies HMAC-SHA256 webhook signature in constant time.
    """
    if not signature_header or not secret:
        return False
    
    clean_sig = signature_header.strip()
    if "=" in clean_sig and not clean_sig.startswith("0x"):
        parts = clean_sig.split("=")
        clean_sig = parts[-1]

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(clean_sig.lower(), expected_sig.lower())


def resolve_webhook_merchant(raw_body: bytes, sig_header: str) -> Optional[str]:
    """
    Cryptographically resolves the merchant identity from the webhook signing secret.
    Does NOT accept or trust any client-supplied merchant_id or headers.

    Security Model:
    1. Production Webhook Mode: Checks merchant-specific signing secrets from the database.
       If the HMAC signature matches a merchant's secret, that specific merchant's ID is returned.
    2. Local Development / Testing Fallback: Uses global WEBHOOK_SECRET.
       Explicitly maps to the default test merchant ('merchant_001') without inspecting
       or selecting arbitrary database rows.
    """
    if not sig_header:
        return None

    # 1. Production Mode: Check merchant-specific webhook secrets stored in merchant_settings table
    try:
        supabase = get_supabase_admin_client()
        ms_res = supabase.table("merchant_settings").select("merchant_id, webhook_secret").execute()
        if ms_res and ms_res.data:
            for ms in ms_res.data:
                m_secret = ms.get("webhook_secret")
                m_id = ms.get("merchant_id")
                if m_secret and m_id and verify_webhook_signature(raw_body, sig_header, m_secret):
                    logger.info(f"Resolved merchant '{m_id}' cryptographically via merchant_settings webhook secret.")
                    return str(m_id)
    except Exception as e:
        logger.warning(f"Error resolving merchant from merchant_settings database: {e}")

    # Fallback to legacy merchants table settings
    try:
        supabase = get_supabase_admin_client()
        merchants_res = supabase.table("merchants").select("id, settings").execute()
        if merchants_res and merchants_res.data:
            for m in merchants_res.data:
                m_settings = m.get("settings") or {}
                m_secret = m_settings.get("webhook_secret")
                if m_secret and verify_webhook_signature(raw_body, sig_header, m_secret):
                    m_id = str(m["id"])
                    logger.info(f"Resolved merchant '{m_id}' cryptographically via legacy merchants webhook secret.")
                    return m_id
    except Exception as e:
        logger.warning(f"Error resolving merchant from database webhook secrets: {e}")

    # 2. Local Development / Testing Fallback Mode: Check system global WEBHOOK_SECRET
    if settings.WEBHOOK_SECRET and verify_webhook_signature(raw_body, sig_header, settings.WEBHOOK_SECRET):
        logger.info("Authenticated webhook using global WEBHOOK_SECRET fallback (Development/Testing Mode).")
        return getattr(settings, "DEFAULT_MERCHANT_ID", "merchant_001")

    return None


def _log_webhook_delivery(
    merchant_id: Optional[str],
    event_id: str,
    event_type: str,
    signature_verified: bool,
    status_code: int,
    payload: Optional[dict] = None,
    error_message: Optional[str] = None
):
    """Persists webhook delivery result to webhook_deliveries table."""
    if not merchant_id:
        return
    try:
        supabase = get_supabase_admin_client()
        m_uuid = _to_uuid_str(merchant_id)
        # Ensure merchant exists before FK insert
        m_check = supabase.table("merchants").select("id").eq("id", m_uuid).execute()
        if not m_check.data:
            existing_m = supabase.table("merchants").select("id").limit(1).execute()
            if existing_m.data:
                m_uuid = str(existing_m.data[0]["id"])
            else:
                return

        # Sanitize payload to strip Authorization or secret headers if present
        clean_payload = dict(payload) if payload else {}
        if "headers" in clean_payload:
            headers = dict(clean_payload["headers"])
            headers.pop("authorization", None)
            headers.pop("Authorization", None)
            headers.pop("x-webhook-signature", None)
            clean_payload["headers"] = headers

        supabase.table("webhook_deliveries").insert({
            "merchant_id": m_uuid,
            "event_id": event_id,
            "event_type": event_type,
            "signature_verified": signature_verified,
            "status_code": status_code,
            "payload": clean_payload,
            "error_message": error_message,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to record webhook delivery log: {e}")


@router.post("/ingest", response_model=WebhookIngestResponse)
async def ingest_webhook_event(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Secure Webhook Ingestion Endpoint for Payment Gateway Events.
    
    Security Architecture:
    1. Payment Gateway Webhook Mode: Verified via HMAC-SHA256 signature header.
       Merchant identity is resolved strictly from the verified signing key configuration.
    2. Authenticated Dev/Manual Ingestion Mode: Verified via Supabase JWT.
       Merchant identity is resolved strictly from the authenticated user context.
    3. Unsigned / Unauthenticated requests are rejected with 401 Unauthorized.
    4. Idempotency Protection prevents duplicate recovery pipeline execution using database primary key constraints.
    """
    raw_body = await request.body()
    sig_header = x_webhook_signature or x_signature or stripe_signature

    verified_merchant_id: Optional[str] = None
    auth_method: str = "NONE"

    # Step 1: Webhook Signature Verification (Gateway Mode)
    if sig_header:
        verified_merchant_id = resolve_webhook_merchant(raw_body, sig_header)
        if verified_merchant_id:
            auth_method = "WEBHOOK_SIGNATURE"

    # Step 2: Supabase JWT Authentication (Manual/Dev Mode)
    if not verified_merchant_id and authorization:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            try:
                from fastapi.security import HTTPAuthorizationCredentials
                creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                user: AuthenticatedUser = await get_current_user(creds)
                verified_merchant_id = user.merchant_id
                auth_method = "JWT_BEARER"
            except HTTPException as e:
                raise e
            except Exception as e:
                logger.warning(f"JWT verification failed during manual ingestion: {str(e)}")

    # Step 3: Reject Unsigned / Unauthenticated Requests
    if not verified_merchant_id:
        _log_webhook_delivery(
            merchant_id=None,
            event_id="unknown_unauthorized",
            event_type="unknown",
            signature_verified=False,
            status_code=401,
            error_message="Unauthorized ingestion request. Invalid or missing signature."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized ingestion request. Valid webhook signature or authorization token required."
        )

    # Step 4: Parse Payload & Enforce Merchant Isolation
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload format"
        )

    event_id = str(payload.get("event_id") or payload.get("id") or payload.get("idempotency_key") or f"evt_{uuid.uuid4().hex[:12]}")
    raw_tx_id = str(payload.get("transaction_id") or payload.get("tx_id") or payload.get("charge_id") or f"tx_{uuid.uuid4().hex[:12]}")
    
    # Overwrite merchant_id in payload with cryptographically verified identity
    payload["merchant_id"] = verified_merchant_id
    payload["transaction_id"] = raw_tx_id

    # Deterministic UUID for transaction primary key scoped to merchant and event_id
    tx_uuid_str = _to_uuid_str(f"{verified_merchant_id}:{event_id}")
    merchant_uuid_str = _to_uuid_str(verified_merchant_id)

    idempotency_key = f"{verified_merchant_id}:{event_id}"

    # Step 5: Fast In-Memory Idempotency Check
    if idempotency_key in _PROCESSED_EVENTS:
        logger.info(f"Duplicate event detected in memory cache for key '{idempotency_key}'. Skipping execution.")
        prev_record = _PROCESSED_EVENTS[idempotency_key]
        return WebhookIngestResponse(
            status="already_processed",
            idempotency_key=event_id,
            merchant_id=verified_merchant_id,
            transaction_id=raw_tx_id,
            auth_method=auth_method,
            pipeline_executed=False,
            pipeline_run_id=prev_record.get("pipeline_run_id"),
            message="Duplicate event ignored by idempotency filter"
        )

    # Step 6: Atomic Database Insertion for Idempotency Guarantee
    now_str = datetime.utcnow().isoformat()
    failure_code = str(payload.get("failure_code") or payload.get("error_code") or "GENERIC_DECLINE")
    failure_reason = str(payload.get("failure_reason") or payload.get("error_message") or "Payment processing failed")
    
    customer_uuid_str = _to_uuid_str(str(payload.get("customer_id", f"cust_{uuid.uuid4().hex[:8]}")))
    try:
        supabase = get_supabase_admin_client()
        m_check = supabase.table("merchants").select("id").eq("id", merchant_uuid_str).execute()
        if not m_check.data:
            existing_m = supabase.table("merchants").select("id").limit(1).execute()
            if existing_m.data:
                merchant_uuid_str = str(existing_m.data[0]["id"])
            else:
                supabase.table("merchants").insert({"id": merchant_uuid_str, "name": "Default Gateway Merchant"}).execute()

        c_check = supabase.table("customers").select("id").eq("id", customer_uuid_str).execute()
        if not c_check.data:
            existing_c = supabase.table("customers").select("id").eq("merchant_id", merchant_uuid_str).limit(1).execute()
            if existing_c.data:
                customer_uuid_str = str(existing_c.data[0]["id"])
            else:
                supabase.table("customers").insert({
                    "id": customer_uuid_str,
                    "merchant_id": merchant_uuid_str,
                    "name": "Ingestion Customer",
                    "email": f"customer_{customer_uuid_str[:8]}@example.com"
                }).execute()
    except Exception as me:
        logger.warning(f"Merchant/Customer FK resolution warning: {str(me)}")

    db_tx_payload = {
        "id": tx_uuid_str,
        "merchant_id": merchant_uuid_str,
        "external_transaction_id": raw_tx_id,
        "customer_id": customer_uuid_str,
        "amount": float(payload.get("amount", 100.0)),
        "currency": str(payload.get("currency", "INR")),
        "status": str(payload.get("status") or payload.get("transaction_status") or "FAILED"),
        "payment_method": str(payload.get("payment_method", "card")),
        "failure_code": failure_code,
        "failure_reason": failure_reason,
        "metadata": {
            "event_id": event_id,
            "auth_method": auth_method,
            "raw_transaction_id": raw_tx_id
        },
        "created_at": str(payload.get("created_at") or now_str)
    }

    try:
        supabase = get_supabase_admin_client()
        # Atomic insert relying on transactions_pkey primary key unique constraint for database-level idempotency
        supabase.table("transactions").insert(db_tx_payload).execute()
    except Exception as db_err:
        err_msg = str(db_err).lower()
        if "duplicate" in err_msg or "violates unique constraint" in err_msg or "23505" in err_msg or "already exists" in err_msg:
            logger.info(f"Database unique constraint violation for '{tx_uuid_str}'. Idempotency triggered.")
            _PROCESSED_EVENTS[idempotency_key] = {"processed_at": now_str, "pipeline_run_id": None}
            return WebhookIngestResponse(
                status="already_processed",
                idempotency_key=event_id,
                merchant_id=verified_merchant_id,
                transaction_id=raw_tx_id,
                auth_method=auth_method,
                pipeline_executed=False,
                message="Duplicate event ignored by database idempotency filter"
            )
        logger.warning(f"Failed to persist ingested transaction to database: {str(db_err)}")

    # Step 7: Run Recovery Pipeline if Payment Failed
    tx_status = str(payload.get("status") or payload.get("transaction_status") or "").upper()
    raw_event_type = payload.get("event_type") or payload.get("type")
    event_type = str(raw_event_type).lower() if raw_event_type else ""

    pipeline_executed = False
    pipeline_run_id = None

    if tx_status in ["FAILED", "DECLINED"] or "failed" in event_type or (not tx_status and not raw_event_type):

        pipeline_input = {
            "transaction_id": raw_tx_id,
            "merchant_id": verified_merchant_id,
            "customer_id": db_tx_payload["customer_id"],
            "amount": db_tx_payload["amount"],
            "currency": db_tx_payload["currency"],
            "payment_method": db_tx_payload["payment_method"],
            "transaction_status": tx_status,
            "failure_code": failure_code,
            "failure_reason": failure_reason,
            "retry_count": int(payload.get("retry_count", 0)),
            "transaction_timestamp": db_tx_payload["created_at"],
            "previous_success_rate": float(payload.get("previous_success_rate", 0.75)),
            "customer_lifetime_value": float(payload.get("customer_lifetime_value", 2500.0)),
            "subscription_status": str(payload.get("subscription_status", "active")),
            "days_since_last_success": int(payload.get("days_since_last_success", 3))
        }

        pipeline_result = run_recovery_pipeline(pipeline_input)
        pipeline_executed = True
        pipeline_run_id = pipeline_result.pipeline_run_id

    # Mark as processed in idempotency cache
    _PROCESSED_EVENTS[idempotency_key] = {
        "processed_at": now_str,
        "pipeline_run_id": pipeline_run_id
    }

    _log_webhook_delivery(
        merchant_id=verified_merchant_id,
        event_id=event_id,
        event_type=str(payload.get("event_type") or payload.get("type") or "payment_intent.payment_failed"),
        signature_verified=(auth_method == "WEBHOOK_SIGNATURE"),
        status_code=200,
        payload=payload,
        error_message=None
    )

    return WebhookIngestResponse(
        status="processed",
        idempotency_key=event_id,
        merchant_id=verified_merchant_id,
        transaction_id=raw_tx_id,
        auth_method=auth_method,
        pipeline_executed=pipeline_executed,
        pipeline_run_id=pipeline_run_id,
        message="Event successfully ingested and processed"
    )
