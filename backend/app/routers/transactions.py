from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_supabase_admin_client

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
    merchant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Retrieve database transactions."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("transactions").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        if status:
            query = query.eq("status", status)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
