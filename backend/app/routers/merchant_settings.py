"""
Merchant Settings Router
Manages dynamic merchant configuration, autonomous recovery parameters, and secure webhook secret rotation.
"""
import secrets
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user, AuthenticatedUser
from app.db import get_supabase_admin_client

logger = logging.getLogger("app.routers.merchant_settings")

router = APIRouter(prefix="/merchant-settings", tags=["Merchant Settings"])


class MerchantSettingsResponse(BaseModel):
    id: str
    merchant_id: str
    autonomous_mode: bool
    min_ai_confidence_threshold: float
    default_gateway: str
    webhook_secret_masked: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MerchantSettingsUpdateRequest(BaseModel):
    autonomous_mode: Optional[bool] = None
    min_ai_confidence_threshold: Optional[float] = Field(None, ge=0.5, le=1.0)
    default_gateway: Optional[str] = None


class SecretRotationResponse(BaseModel):
    success: bool
    merchant_id: str
    new_webhook_secret: str
    message: str


def _mask_secret(secret: Optional[str]) -> str:
    """Returns a masked representation of a secret string to prevent leakage in GET APIs."""
    if not secret:
        return "whsec_••••••••••••••••"
    if len(secret) <= 8:
        return secret[:3] + "••••••••"
    return secret[:6] + "••••••••" + secret[-4:]


def _get_or_create_merchant_settings(merchant_id: str) -> dict:
    """Fetches merchant settings from database or initializes default settings row."""
    supabase = get_supabase_admin_client()
    res = supabase.table("merchant_settings").select("*").eq("merchant_id", merchant_id).execute()

    if res.data and len(res.data) > 0:
        return res.data[0]

    # Initialize default settings row for this merchant
    initial_secret = f"whsec_{secrets.token_hex(24)}"
    default_row = {
        "merchant_id": merchant_id,
        "autonomous_mode": False,
        "min_ai_confidence_threshold": 0.85,
        "default_gateway": "sandbox",
        "webhook_secret": initial_secret,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    try:
        ins_res = supabase.table("merchant_settings").insert(default_row).execute()
        if ins_res.data and len(ins_res.data) > 0:
            return ins_res.data[0]
    except Exception as e:
        logger.warning(f"Error initializing merchant_settings row: {e}")

    return default_row


@router.get("", response_model=MerchantSettingsResponse)
@router.get("/", response_model=MerchantSettingsResponse)
async def get_merchant_settings(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Retrieve dynamic merchant settings for the authenticated tenant.
    SECURITY REQUIREMENT: Existing webhook secret is ALWAYS returned masked.
    """
    try:
        settings_row = _get_or_create_merchant_settings(user.merchant_id)
        raw_secret = settings_row.get("webhook_secret")

        return MerchantSettingsResponse(
            id=str(settings_row.get("id", f"set_{user.merchant_id}")),
            merchant_id=user.merchant_id,
            autonomous_mode=bool(settings_row.get("autonomous_mode", False)),
            min_ai_confidence_threshold=float(settings_row.get("min_ai_confidence_threshold", 0.85)),
            default_gateway=str(settings_row.get("default_gateway", "sandbox")),
            webhook_secret_masked=_mask_secret(raw_secret),
            created_at=settings_row.get("created_at"),
            updated_at=settings_row.get("updated_at"),
        )
    except Exception as e:
        logger.error(f"Error retrieving merchant settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=MerchantSettingsResponse)
@router.put("/", response_model=MerchantSettingsResponse)
async def update_merchant_settings(
    payload: MerchantSettingsUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update merchant settings (autonomous_mode, min_ai_confidence_threshold, default_gateway).
    Derives merchant_id strictly from user context. Creates an audit log entry.
    """
    try:
        supabase = get_supabase_admin_client()
        existing = _get_or_create_merchant_settings(user.merchant_id)

        update_data = {}
        changes = {}

        if payload.autonomous_mode is not None:
            update_data["autonomous_mode"] = payload.autonomous_mode
            changes["autonomous_mode"] = {
                "old": existing.get("autonomous_mode"),
                "new": payload.autonomous_mode
            }

        if payload.min_ai_confidence_threshold is not None:
            update_data["min_ai_confidence_threshold"] = payload.min_ai_confidence_threshold
            changes["min_ai_confidence_threshold"] = {
                "old": existing.get("min_ai_confidence_threshold"),
                "new": payload.min_ai_confidence_threshold
            }

        if payload.default_gateway is not None:
            update_data["default_gateway"] = payload.default_gateway
            changes["default_gateway"] = {
                "old": existing.get("default_gateway"),
                "new": payload.default_gateway
            }

        if not update_data:
            return await get_merchant_settings(user=user)

        now_str = datetime.utcnow().isoformat()
        update_data["updated_at"] = now_str

        upd_res = supabase.table("merchant_settings").update(update_data).eq("merchant_id", user.merchant_id).execute()
        updated_row = upd_res.data[0] if upd_res.data else existing
        updated_row.update(update_data)

        # Audit log entry
        audit_payload = {
            "merchant_id": user.merchant_id,
            "actor_type": "user",
            "actor_id": user.user_id,
            "action": "MERCHANT_SETTINGS_UPDATE",
            "action_type": "MERCHANT_SETTINGS_UPDATE",
            "entity_type": "merchant_settings",
            "entity_id": str(updated_row.get("id", user.merchant_id)),
            "details": {
                "changes": changes,
                "updated_by": user.email,
            },
            "created_at": now_str
        }
        try:
            supabase.table("audit_logs").insert(audit_payload).execute()
        except Exception as audit_err:
            logger.warning(f"Failed to record audit log for settings update: {audit_err}")

        return MerchantSettingsResponse(
            id=str(updated_row.get("id", f"set_{user.merchant_id}")),
            merchant_id=user.merchant_id,
            autonomous_mode=bool(updated_row.get("autonomous_mode", False)),
            min_ai_confidence_threshold=float(updated_row.get("min_ai_confidence_threshold", 0.85)),
            default_gateway=str(updated_row.get("default_gateway", "sandbox")),
            webhook_secret_masked=_mask_secret(updated_row.get("webhook_secret")),
            created_at=updated_row.get("created_at"),
            updated_at=updated_row.get("updated_at"),
        )
    except Exception as e:
        logger.error(f"Error updating merchant settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotate-webhook-secret", response_model=SecretRotationResponse)
async def rotate_webhook_secret(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Rotates the merchant's webhook signing secret.
    Invalidates previous secret and returns the NEW secret ONCE in the API response.
    Creates an audit log entry.
    """
    try:
        supabase = get_supabase_admin_client()
        existing = _get_or_create_merchant_settings(user.merchant_id)

        new_secret = f"whsec_{secrets.token_hex(24)}"
        now_str = datetime.utcnow().isoformat()

        update_payload = {
            "webhook_secret": new_secret,
            "updated_at": now_str
        }

        supabase.table("merchant_settings").update(update_payload).eq("merchant_id", user.merchant_id).execute()

        # Audit log entry
        audit_payload = {
            "merchant_id": user.merchant_id,
            "actor_type": "user",
            "actor_id": user.user_id,
            "action": "WEBHOOK_SECRET_ROTATE",
            "action_type": "WEBHOOK_SECRET_ROTATE",
            "entity_type": "merchant_settings",
            "entity_id": str(existing.get("id", user.merchant_id)),
            "details": {
                "rotated_by": user.email,
                "reason": "Merchant initiated secret rotation",
            },
            "created_at": now_str
        }
        try:
            supabase.table("audit_logs").insert(audit_payload).execute()
        except Exception as audit_err:
            logger.warning(f"Failed to record audit log for secret rotation: {audit_err}")

        return SecretRotationResponse(
            success=True,
            merchant_id=user.merchant_id,
            new_webhook_secret=new_secret,
            message="Webhook secret successfully rotated. Store this new secret securely; it will not be displayed again."
        )
    except Exception as e:
        logger.error(f"Error rotating webhook secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook-logs")
async def list_webhook_logs(
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves recent webhook delivery attempt logs for the authenticated merchant.
    """
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("webhook_deliveries") \
            .select("*") \
            .eq("merchant_id", user.merchant_id) \
            .order("delivered_at", desc=True) \
            .limit(limit) \
            .execute()

        logs = res.data or []
        return {
            "items": logs,
            "total": len(logs)
        }
    except Exception as e:
        logger.error(f"Error retrieving webhook logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
