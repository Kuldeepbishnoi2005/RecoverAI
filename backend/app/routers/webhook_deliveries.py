"""
Webhook Deliveries Observability Router
Provides tenant-isolated, sanitized visibility into webhook ingestion delivery attempts and payloads.
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user, AuthenticatedUser
from app.db import get_supabase_admin_client
from app.utils.sanitizer import sanitize_sensitive_data

logger = logging.getLogger("app.routers.webhook_deliveries")

router = APIRouter(prefix="/webhook-deliveries", tags=["Webhook Deliveries"])


class WebhookDeliveryItem(BaseModel):
    id: str
    merchant_id: str
    event_id: str
    event_type: str
    signature_verified: bool
    status_code: int
    payload: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class WebhookDeliveriesListResponse(BaseModel):
    items: List[WebhookDeliveryItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=WebhookDeliveriesListResponse)
@router.get("/", response_model=WebhookDeliveriesListResponse)
async def list_webhook_deliveries(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
    status_code: Optional[int] = Query(None),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Lists and paginates webhook delivery logs for the authenticated merchant.
    Applies strict data sanitization to redact credentials, headers, and secret keys.
    """
    try:
        supabase = get_supabase_admin_client()

        # Build query for tenant's webhook deliveries
        query = supabase.table("webhook_deliveries").select("*").eq("merchant_id", user.merchant_id)

        if event_type:
            query = query.eq("event_type", event_type)
        if status_code is not None:
            query = query.eq("status_code", status_code)

        # Order by created_at descending
        res = query.order("created_at", desc=True).execute()
        raw_deliveries = res.data or []

        total_count = len(raw_deliveries)
        paged_deliveries = raw_deliveries[offset : offset + limit]

        sanitized_items = []
        for d in paged_deliveries:
            raw_payload = d.get("payload") or {}
            clean_payload = sanitize_sensitive_data(raw_payload)
            clean_error = sanitize_sensitive_data(d.get("error_message")) if d.get("error_message") else None

            sanitized_items.append(WebhookDeliveryItem(
                id=str(d.get("id", f"del_{d.get('event_id')}")),
                merchant_id=str(d.get("merchant_id", user.merchant_id)),
                event_id=str(d.get("event_id", "")),
                event_type=str(d.get("event_type", "unknown")),
                signature_verified=bool(d.get("signature_verified", False)),
                status_code=int(d.get("status_code", 200)),
                payload=clean_payload if isinstance(clean_payload, dict) else {"data": clean_payload},
                error_message=str(clean_error) if clean_error else None,
                created_at=d.get("created_at") or d.get("delivered_at")
            ))

        return WebhookDeliveriesListResponse(
            items=sanitized_items,
            total=total_count,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error listing webhook deliveries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch webhook deliveries: {str(e)}"
        )
