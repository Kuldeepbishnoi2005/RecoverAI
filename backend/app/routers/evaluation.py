from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional, List
from app.engine.dataset_generator import generate_synthetic_dataset, DEFAULT_SEED, BENCHMARK_MERCHANT_ID, BENCHMARK_VERSION
from app.engine.risk_engine import evaluate_risk_events
from app.engine.evaluator import run_evaluation
from app.engine.db_seeder import seed_benchmark_to_supabase
from app.db import get_supabase_admin_client

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.post("/generate-dataset")
async def generate_dataset_endpoint(
    count: int = Query(10000, ge=100, le=50000),
    seed: int = Query(DEFAULT_SEED),
    benchmark_version: str = Query(BENCHMARK_VERSION),
    persist: bool = Query(True)
):
    """
    Generates deterministic synthetic payment dataset and computes Ground Truth & Risk Engine scores.
    Includes train (60%), validation (20%), and test (20%) splits.
    Optionally persists the dataset into Supabase schema.
    """
    try:
        raw_dataset = generate_synthetic_dataset(
            count=count, 
            seed=seed, 
            merchant_id=BENCHMARK_MERCHANT_ID,
            benchmark_version=benchmark_version
        )
        evaluated_dataset = evaluate_risk_events(raw_dataset)
        eval_metrics = run_evaluation(evaluated_dataset)

        persist_res = None
        if persist:
            persist_res = seed_benchmark_to_supabase(evaluated_dataset, eval_metrics, benchmark_version=benchmark_version)

        return {
            "status": "success",
            "count": count,
            "seed": seed,
            "benchmark_version": benchmark_version,
            "metrics": eval_metrics,
            "db_persistence": persist_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def run_evaluation_endpoint(
    merchant_id: Optional[str] = Query(BENCHMARK_MERCHANT_ID),
    split: Optional[str] = Query(None, description="Filter dataset by split: 'train', 'validation', or 'test'")
):
    """
    Runs the evaluation pipeline against database transactions for a given merchant and optional dataset split.
    Calculates Precision, Recall, F1, ROC-AUC, PR-AUC, Brier Score, Calibration Error, and financial metrics.
    """
    try:
        supabase = get_supabase_admin_client()

        query = supabase.table("transactions").select("*")
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        res = query.limit(50000).execute()
        tx_list = res.data or []

        if not tx_list:
            raise HTTPException(status_code=404, detail="No transactions found in database to evaluate.")

        evaluated_dataset = []
        for tx in tx_list:
            meta = tx.get("metadata", {})
            
            # Filter by split if requested
            if split and meta.get("dataset_split") != split:
                continue

            gt = meta.get("ground_truth")
            risk_pred = meta.get("risk_engine")

            if not gt or not risk_pred:
                record = {
                    "transaction_status": tx["status"],
                    "failure_code": tx.get("failure_code"),
                    "amount": tx["amount"],
                    "card_expiry_status": meta.get("card_expiry_status", "valid"),
                    "checkout_completed": meta.get("checkout_completed", True),
                    "previous_success_rate": meta.get("previous_success_rate", 0.80),
                    "customer_lifetime_value": meta.get("customer_lifetime_value", 5000.0),
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

        if not evaluated_dataset:
            raise HTTPException(status_code=404, detail=f"No transactions found matching split '{split}'.")

        metrics = run_evaluation(evaluated_dataset)

        eval_run_payload = {
            "merchant_id": merchant_id,
            "name": f"Evaluation Run ({split or 'all_splits'}) - {len(evaluated_dataset)} records",
            "status": "completed",
            "metrics": metrics
        }
        supabase.table("evaluation_runs").insert(eval_run_payload).execute()

        return {
            "status": "success",
            "split": split or "all",
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
