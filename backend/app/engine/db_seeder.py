from typing import List, Dict, Any
from app.db import get_supabase_admin_client
from app.engine.dataset_generator import BENCHMARK_MERCHANT_ID

BATCH_SIZE = 1000

def seed_benchmark_to_supabase(
    dataset: List[Dict[str, Any]],
    evaluation_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Persists synthetic benchmark dataset and evaluation metrics into Supabase tables
    using the SECURITY DEFINER RPC function `seed_benchmark_data`.
    """
    supabase = get_supabase_admin_client()

    # 1. Merchant Payload
    merchant_payload = {
        "id": BENCHMARK_MERCHANT_ID,
        "name": "Acme Payments Benchmark Merchant",
        "slug": "acme_benchmark_merchant",
        "plan": "enterprise",
        "currency": "INR",
        "settings": {"auto_mode": True, "min_confidence": 85}
    }

    # 2. Extract Customers
    customer_dict = {}
    for item in dataset:
        c_id = item["customer_id"]
        if c_id not in customer_dict:
            customer_dict[c_id] = {
                "id": c_id,
                "merchant_id": BENCHMARK_MERCHANT_ID,
                "external_customer_id": f"cust_{c_id[:8]}",
                "name": f"Customer {c_id[:6]}",
                "email": f"cust_{c_id[:8]}@example.com",
                "risk_score": round(100.0 * (1.0 - item["previous_success_rate"]), 2),
                "metadata": {
                    "history": item["customer_history"],
                    "lifetime_value": item["customer_lifetime_value"],
                    "subscription_status": item["subscription_status"]
                }
            }
    cust_list = list(customer_dict.values())

    # 3. Process items in matched batches so foreign keys are guaranteed
    eval_run_payload = {
        "merchant_id": BENCHMARK_MERCHANT_ID,
        "name": "Phase 2 Deterministic Revenue Risk Engine Benchmark",
        "status": "completed",
        "metrics": evaluation_metrics
    }

    total_tx_inserted = 0
    total_rre_inserted = 0
    total_ra_inserted = 0
    eval_run_id = None

    for i in range(0, len(dataset), BATCH_SIZE):
        chunk_items = dataset[i : i + BATCH_SIZE]

        tx_chunk = []
        att_chunk = []
        rre_chunk = []
        ra_chunk = []

        for item in chunk_items:
            t_id = item["transaction_id"]
            gt = item["ground_truth"]
            pred = item["risk_engine_result"]

            tx_chunk.append({
                "id": t_id,
                "merchant_id": BENCHMARK_MERCHANT_ID,
                "customer_id": item["customer_id"],
                "external_transaction_id": f"tx_{t_id[:8]}",
                "amount": item["amount"],
                "currency": item["currency"],
                "status": item["transaction_status"],
                "payment_method": item["payment_method"],
                "failure_reason": item["failure_reason"],
                "failure_code": item["failure_code"],
                "metadata": {
                    "gateway": item["payment_gateway"],
                    "retry_count": item["retry_count"],
                    "days_since_last_success": item["days_since_last_success"],
                    "previous_success_rate": item["previous_success_rate"],
                    "card_expiry_status": item["card_expiry_status"],
                    "dispute_status": item["dispute_status"],
                    "checkout_completed": item["checkout_completed"],
                    "event_type": item["event_type"],
                    "ground_truth": gt,
                    "risk_engine": pred
                },
                "occurred_at": item["transaction_timestamp"]
            })

            if item["transaction_status"] != "successful":
                att_chunk.append({
                    "transaction_id": t_id,
                    "merchant_id": BENCHMARK_MERCHANT_ID,
                    "gateway": item["payment_gateway"],
                    "attempt_number": max(1, item["retry_count"]),
                    "status": item["transaction_status"],
                    "error_code": item["failure_code"],
                    "error_description": item["failure_reason"]
                })

                rre_id = t_id
                rre_chunk.append({
                    "id": rre_id,
                    "merchant_id": BENCHMARK_MERCHANT_ID,
                    "transaction_id": t_id,
                    "customer_id": item["customer_id"],
                    "risk_type": item["failure_code"] or item["transaction_status"],
                    "severity": pred["risk_level"],
                    "amount_at_risk": pred["revenue_at_risk"],
                    "status": "detected" if pred["is_opportunity"] else "closed",
                    "details": {
                        "risk_score": pred["risk_score"],
                        "recovery_probability": pred["recovery_probability"],
                        "reason": pred["reason"]
                    }
                })

                if pred["is_opportunity"]:
                    ra_chunk.append({
                        "merchant_id": BENCHMARK_MERCHANT_ID,
                        "risk_event_id": rre_id,
                        "action_type": pred["recommended_strategy"],
                        "status": "scheduled",
                        "parameters": {
                            "expected_recovery_amount": pred["expected_recovery_amount"],
                            "confidence": pred["confidence"]
                        }
                    })

        cust_chunk = cust_list if i == 0 else []

        rpc_res = supabase.rpc(
            "seed_benchmark_data",
            {
                "p_merchant": merchant_payload,
                "p_customers": cust_chunk,
                "p_transactions": tx_chunk,
                "p_attempts": att_chunk,
                "p_risk_events": rre_chunk,
                "p_actions": ra_chunk,
                "p_eval_run": eval_run_payload if i == 0 else {"merchant_id": BENCHMARK_MERCHANT_ID, "name": "Chunk", "status": "completed", "metrics": {}}
            }
        ).execute()

        total_tx_inserted += len(tx_chunk)
        total_rre_inserted += len(rre_chunk)
        total_ra_inserted += len(ra_chunk)

        if i == 0 and rpc_res.data:
            eval_run_id = rpc_res.data.get("evaluation_run_id")

    return {
        "status": "success",
        "merchant_id": BENCHMARK_MERCHANT_ID,
        "transactions_inserted": total_tx_inserted,
        "risk_events_inserted": total_rre_inserted,
        "recovery_actions_inserted": total_ra_inserted,
        "evaluation_run_id": eval_run_id
    }
