from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.db import get_supabase_admin_client

router = APIRouter(prefix="/recovery-opportunities", tags=["Recovery Opportunities"])

class RecoveryActionSchema(BaseModel):
    id: str
    merchant_id: str
    risk_event_id: Optional[str] = None
    ai_decision_id: Optional[str] = None
    action_type: str
    status: str = "pending"
    parameters: Optional[dict] = {}
    scheduled_at: Optional[str] = None
    executed_at: Optional[str] = None
    created_at: Optional[str] = None

@router.get("/", response_model=List[RecoveryActionSchema])
async def list_recovery_opportunities(
    merchant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Retrieve database recovery opportunities / actions."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("recovery_actions").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        if status:
            query = query.eq("status", status)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_recovery_opportunities_summary(
    merchant_id: Optional[str] = Query(None)
):
    """Retrieves database-backed summary of recovery opportunities / actions."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("recovery_actions").select("action_type, status, parameters")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.execute()
        data = res.data or []

        total_opportunities = len(data)
        total_expected_recovery = 0.0

        action_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}

        for r in data:
            a_type = r.get("action_type", "unknown")
            st = r.get("status", "pending")
            params = r.get("parameters", {}) or {}

            exp_amt = float(params.get("expected_recovery_amount", 0.0) or 0.0)
            total_expected_recovery += exp_amt

            action_counts[a_type] = action_counts.get(a_type, 0) + 1
            status_counts[st] = status_counts.get(st, 0) + 1

        return {
            "total_opportunities": total_opportunities,
            "total_expected_recovery_amount": round(total_expected_recovery, 2),
            "strategy_breakdown": action_counts,
            "status_breakdown": status_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
