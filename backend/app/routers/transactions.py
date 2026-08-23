from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_supabase_admin_client
from app.auth.deps import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/transactions", tags=["Transactions"])

class TransactionSchema(BaseModel):
    id: str
    merchant_id: str
    customer_id: Optional[str] = None
    external_transaction_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str
    payment_method: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    metadata: Optional[dict] = {}
    occurred_at: Optional[str] = None
    created_at: Optional[str] = None

@router.get("/", response_model=List[TransactionSchema])
async def list_transactions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve database transactions for authenticated merchant."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("transactions").select("*").eq("merchant_id", user.merchant_id)
        if status:
            query = query.eq("status", status)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
