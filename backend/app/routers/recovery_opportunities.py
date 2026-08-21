from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
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
