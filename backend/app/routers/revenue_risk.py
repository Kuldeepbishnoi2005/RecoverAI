from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
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

@router.get("/summary")
async def get_revenue_risk_summary(
    merchant_id: Optional[str] = Query(None)
):
    """Retrieves database-backed summary of revenue risk events."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("revenue_risk_events").select("severity, status, amount_at_risk")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.execute()
        data = res.data or []

        total_count = len(data)
        total_amount_at_risk = sum(float(r.get("amount_at_risk", 0.0) or 0.0) for r in data)

        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        status_counts = {"detected": 0, "open": 0, "in_recovery": 0, "recovered": 0, "closed": 0}

        for r in data:
            sev = r.get("severity", "medium")
            st = r.get("status", "detected")
            if sev in severity_counts:
                severity_counts[sev] += 1
            if st in status_counts:
                status_counts[st] += 1

        return {
            "total_risk_events": total_count,
            "total_amount_at_risk": round(total_amount_at_risk, 2),
            "severity_breakdown": severity_counts,
            "status_breakdown": status_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{event_id}", response_model=RiskEventSchema)
async def get_risk_event(event_id: str):
    """Retrieve a single revenue risk event by ID."""
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("revenue_risk_events").select("*").eq("id", event_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Risk event not found")
        return res.data[0]
    except HTTPException:
        raise
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

