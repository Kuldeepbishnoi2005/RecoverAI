from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional
from app.engine.dataset_generator import generate_synthetic_dataset, DEFAULT_SEED, BENCHMARK_MERCHANT_ID
from app.engine.risk_engine import evaluate_risk_events
from app.engine.evaluator import run_evaluation
from app.engine.db_seeder import seed_benchmark_to_supabase
from app.db import get_supabase_admin_client

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.post("/generate-dataset")
async def generate_dataset_endpoint(
    count: int = Query(10000, ge=100, le=50000),
    seed: int = Query(DEFAULT_SEED),
    persist: bool = Query(True)
):
    """
    Generates deterministic synthetic payment dataset and computes Ground Truth & Risk Engine scores.
    Optionally persists the dataset into Supabase schema.
    """
    try:
        raw_dataset = generate_synthetic_dataset(count=count, seed=seed, merchant_id=BENCHMARK_MERCHANT_ID)
        evaluated_dataset = evaluate_risk_events(raw_dataset)
        eval_metrics = run_evaluation(evaluated_dataset)

        persist_res = None
        if persist:
            persist_res = seed_benchmark_to_supabase(evaluated_dataset, eval_metrics)

        return {
            "status": "success",
            "count": count,
            "seed": seed,
            "metrics": eval_metrics,
            "db_persistence": persist_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def run_evaluation_endpoint(
    merchant_id: Optional[str] = Query(BENCHMARK_MERCHANT_ID)
):
    """
    Runs the evaluation pipeline against database transactions for a given merchant.
    Calculates Precision, Recall, F1, FPR, FNR, and revenue metrics.
    """
    try:
        supabase = get_supabase_admin_client()

        # Query transactions from Supabase
        query = supabase.table("transactions").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.limit(50000).execute()
        tx_list = res.data or []

        if not tx_list:
            raise HTTPException(status_code=404, detail="No transactions found in database to evaluate.")

        # Re-construct dataset records with predictions and ground truth
        evaluated_dataset = []
        for tx in tx_list:
            meta = tx.get("metadata", {})
            gt = meta.get("ground_truth")
            risk_pred = meta.get("risk_engine")

            # Fallback if metadata missing
            if not gt or not risk_pred:
                record = {
                    "transaction_status": tx["status"],
                    "failure_code": tx.get("failure_code"),
                    "amount": tx["amount"],
                    "card_expiry_status": meta.get("card_expiry_status", "valid"),
                    "checkout_completed": meta.get("checkout_completed", True),
                    "previous_success_rate": meta.get("previous_success_rate", 0.80),
                    "subscription_status": meta.get("subscription_status", "active"),
                    "retry_count": meta.get("retry_count", 0),
                    "days_since_last_success": meta.get("days_since_last_success", 0)
                }
                from app.engine.dataset_generator import compute_ground_truth
                from app.engine.risk_engine import calculate_risk_score
                gt = compute_ground_truth(record)
                risk_pred = calculate_risk_score(record)

            evaluated_dataset.append({
                "amount": tx["amount"],
                "transaction_status": tx["status"],
                "ground_truth": gt,
                "risk_engine_result": risk_pred
            })

        metrics = run_evaluation(evaluated_dataset)

        # Record evaluation run in database
        eval_run_payload = {
            "merchant_id": merchant_id,
            "name": f"Evaluation Run - {len(evaluated_dataset)} records",
            "status": "completed",
            "metrics": metrics
        }
        supabase.table("evaluation_runs").insert(eval_run_payload).execute()

        return {
            "status": "success",
            "evaluated_records": len(evaluated_dataset),
            "metrics": metrics
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
async def get_latest_evaluation_run(
    merchant_id: Optional[str] = Query(BENCHMARK_MERCHANT_ID)
):
    """Retrieves the most recent evaluation run from Supabase."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("evaluation_runs").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.order("created_at", desc=True).limit(1).execute()

        if not res.data:
            return {"status": "empty", "message": "No evaluation runs found in database."}

        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_evaluation_metrics(
    merchant_id: Optional[str] = Query(BENCHMARK_MERCHANT_ID)
):
    """Retrieves evaluation metrics from the latest evaluation run."""
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("evaluation_runs").select("metrics, created_at").eq("status", "completed")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.order("created_at", desc=True).limit(1).execute()

        if not res.data:
            return {"status": "empty", "metrics": None}

        return {
            "status": "success",
            "created_at": res.data[0].get("created_at"),
            "metrics": res.data[0].get("metrics")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
