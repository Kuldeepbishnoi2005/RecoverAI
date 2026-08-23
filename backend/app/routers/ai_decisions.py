from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_supabase_admin_client
from app.auth.deps import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/ai-decisions", tags=["AI Decisions"])

class AIDecisionSchema(BaseModel):
    id: str
    merchant_id: str
    risk_event_id: Optional[str] = None
    model_name: Optional[str] = None
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    root_cause_analysis: Optional[str] = None
    recommended_strategy: Optional[str] = None
    confidence_score: Optional[float] = 0.0
    reasoning_raw: Optional[dict] = {}
    created_at: Optional[str] = None

@router.get("/", response_model=List[AIDecisionSchema])
async def list_ai_decisions(
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve database AI decision records for authenticated merchant."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("ai_decisions").select("*").eq("merchant_id", user.merchant_id)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
