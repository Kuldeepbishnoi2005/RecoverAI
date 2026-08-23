from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from pydantic import BaseModel
from app.db import get_supabase_admin_client
from app.auth.deps import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/analytics", tags=["Analytics"])

class OverviewMetricsSchema(BaseModel):
    total_recovered: float = 0.0
    total_at_risk: float = 0.0
    recovery_rate: float = 0.0
    active_risk_events: int = 0
    autonomous_actions_count: int = 0

@router.get("/overview", response_model=OverviewMetricsSchema)
async def get_analytics_overview(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Calculate overview analytics dynamically from database records for authenticated merchant."""
    try:
        supabase = get_supabase_admin_client()

        # Query recovery_results
        rr_query = supabase.table("recovery_results").select("recovered_amount, is_successful").eq("merchant_id", user.merchant_id)
        rr_res = rr_query.execute()
        rr_data = rr_res.data or []

        total_recovered = sum(float(r.get("recovered_amount", 0.0) or 0.0) for r in rr_data if r.get("is_successful"))

        # Query revenue_risk_events
        rre_query = supabase.table("revenue_risk_events").select("amount_at_risk, status").eq("merchant_id", user.merchant_id)
        rre_res = rre_query.execute()
        rre_data = rre_res.data or []

        total_at_risk = sum(float(r.get("amount_at_risk", 0.0) or 0.0) for r in rre_data)
        active_risk_events = sum(1 for r in rre_data if r.get("status") in ["detected", "open", "in_recovery"])

        # Query recovery_actions
        ra_query = supabase.table("recovery_actions").select("id").eq("merchant_id", user.merchant_id)
        ra_res = ra_query.execute()
        ra_data = ra_res.data or []

        autonomous_actions_count = len(ra_data)

        # Calculate recovery rate
        denom = total_recovered + total_at_risk
        recovery_rate = (total_recovered / denom * 100.0) if denom > 0 else 0.0

        return OverviewMetricsSchema(
            total_recovered=round(total_recovered, 2),
            total_at_risk=round(total_at_risk, 2),
            recovery_rate=round(recovery_rate, 2),
            active_risk_events=active_risk_events,
            autonomous_actions_count=autonomous_actions_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
