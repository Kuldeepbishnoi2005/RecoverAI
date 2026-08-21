from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.db import get_supabase_admin_client

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

class AuditLogSchema(BaseModel):
    id: str
    merchant_id: str
    actor_type: str
    actor_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    changes: Optional[dict] = {}
    created_at: Optional[str] = None

@router.get("/", response_model=List[AuditLogSchema])
async def list_audit_logs(
    merchant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Retrieve database audit log records."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("audit_logs").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
