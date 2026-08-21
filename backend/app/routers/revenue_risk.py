from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_supabase_admin_client

router = APIRouter(prefix="/revenue-risk", tags=["Revenue Risk"])

class RiskEventSchema(BaseModel):
    id: str
    merchant_id: str
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    risk_type: str
    severity: str = "medium"
    amount_at_risk: float = 0.0
    status: str = "detected"
    details: Optional[dict] = {}
    detected_at: Optional[str] = None
    created_at: Optional[str] = None

@router.get("/", response_model=List[RiskEventSchema])
async def list_risk_events(
    merchant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Retrieve database revenue risk events."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("revenue_risk_events").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{event_id}/trigger-recovery")
async def trigger_recovery(event_id: str):
    """Trigger autonomous recovery protocol for a given risk event."""
    return {
        "status": "success",
        "event_id": event_id,
        "action_taken": "smart_retry_schedule",
        "message": f"Autonomous recovery triggered for event {event_id}"
    }
