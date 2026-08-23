from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Optional, List, Dict, Any
from app.db import get_supabase_admin_client
from app.ai.schemas import MerchantPolicy, PipelineResult
from app.routers.ai import _get_transaction_by_id
from app.services.recovery_pipeline import run_recovery_pipeline
from app.auth.deps import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/recovery", tags=["Recovery Simulation"])

@router.post("/simulate/{transaction_id}", response_model=PipelineResult)
async def simulate_recovery(
    transaction_id: str,
    merchant_policy: Optional[MerchantPolicy] = Body(None),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Runs the complete RecoverAI Decision & Recovery Simulation Pipeline.
    Clearly labeled execution_status = 'SIMULATED'. NO REAL PAYMENTS are executed.
    """
    tx_data = _get_transaction_by_id(transaction_id, merchant_id=user.merchant_id)
    policy = merchant_policy or MerchantPolicy()
    result = run_recovery_pipeline(tx_data, merchant_policy=policy)
    return result


@router.get("/results/{transaction_id}")
async def get_recovery_results(
    transaction_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns recovery simulation results for a transaction.
    """
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("recovery_actions").select("*").eq("transaction_id", transaction_id).eq("merchant_id", user.merchant_id).order("created_at", desc=True).execute()
        if res.data:
            return res.data
    except Exception:
        pass

    # Fallback simulation
    tx_data = _get_transaction_by_id(transaction_id, merchant_id=user.merchant_id)
    pipeline_res = run_recovery_pipeline(tx_data)
    if pipeline_res.simulation_result:
        return [pipeline_res.simulation_result.model_dump()]
    return []
