from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import List, Optional, Dict, Any
from app.db import get_supabase_admin_client
from app.engine.dataset_generator import generate_synthetic_dataset
from app.ai.schemas import MerchantPolicy, PipelineResult
from app.services.recovery_pipeline import run_recovery_pipeline
from app.auth.deps import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/ai", tags=["AI Strategist"])

# Memory cache for benchmark transactions
_benchmark_tx_map: Optional[Dict[str, Dict[str, Any]]] = None

def _get_transaction_by_id(transaction_id: str, merchant_id: Optional[str] = None) -> Dict[str, Any]:
    global _benchmark_tx_map
    
    # 1. Try Supabase first
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("transactions").select("*").eq("transaction_id", transaction_id)
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception:
        pass

    # 2. Fallback to benchmark dataset
    if _benchmark_tx_map is None:
        df, _ = generate_synthetic_dataset(n_samples=10000, seed=42)
        _benchmark_tx_map = {str(row["transaction_id"]): row for row in df.to_dict(orient="records")}

    if transaction_id in _benchmark_tx_map:
        tx = _benchmark_tx_map[transaction_id]
        if merchant_id and tx.get("merchant_id") and tx.get("merchant_id") != merchant_id:
            raise HTTPException(status_code=403, detail="Access to transaction forbidden for current merchant context.")
        return tx

    raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")


@router.post("/analyze/{transaction_id}", response_model=PipelineResult)
async def analyze_transaction(
    transaction_id: str,
    merchant_policy: Optional[MerchantPolicy] = Body(None),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Analyzes a transaction context using the AI Recovery Strategist and Governance Controller.
    Returns structured AI Decision, validation status, and policy result.
    Does NOT execute simulation unless explicitly requested.
    """
    tx_data = _get_transaction_by_id(transaction_id, merchant_id=user.merchant_id)
    policy = merchant_policy or MerchantPolicy()
    
    # Run pipeline with auto-execution blocked in policy if needed or standard policy
    result = run_recovery_pipeline(tx_data, merchant_policy=policy)
    return result


@router.get("/decisions/{transaction_id}")
async def get_ai_decisions_for_transaction(
    transaction_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves historical AI decisions stored for a specific transaction ID.
    """
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("ai_decisions").select("*").eq("transaction_id", transaction_id).eq("merchant_id", user.merchant_id).order("created_at", desc=True).execute()
        if res.data:
            return res.data
    except Exception:
        pass

    # If no DB records found, run fresh analysis on transaction
    tx_data = _get_transaction_by_id(transaction_id, merchant_id=user.merchant_id)
    pipeline_res = run_recovery_pipeline(tx_data)
    return [pipeline_res.ai_decision.model_dump()]


@router.post("/evaluate")
async def evaluate_ai_strategist(
    sample_size: int = Query(100, ge=10, le=1000),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Evaluates AI Recovery Strategist on a controlled sample of the frozen v2.1 test split.
    Does NOT give ground-truth labels to the AI.
    """
    from app.ai.evaluator import run_ai_evaluation
    eval_summary = run_ai_evaluation(sample_size=sample_size)
    return eval_summary
