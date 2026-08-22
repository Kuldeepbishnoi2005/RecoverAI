import json
import os
import sys
import math
from typing import Dict, Any, List
from datetime import datetime

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.dataset_generator import generate_synthetic_dataset
from app.services.recovery_pipeline import run_recovery_pipeline
from app.ai.schemas import MerchantPolicy
from app.ai.context_builder import build_ai_context, sanitize_untrusted_text
from app.ai.policy_controller import evaluate_policy
from app.db import get_supabase_admin_client

def run_evaluation(sample_size: int = 500):
    print(f"--- STARTING PHASE 3 EVALUATION (Sample Size: {sample_size}) ---")
    dataset = generate_synthetic_dataset(count=10000, seed=42)
    test_df = [r for r in dataset if r.get("dataset_split") == "test" or r.get("split") == "test"]
    
    if sample_size > len(test_df):
        sample_size = len(test_df)
    
    eval_records = test_df[:sample_size]
    policy = MerchantPolicy()
    
    # Distributions
    strategy_dist = {}
    decision_dist = {}
    
    # Agreement & Confusion Matrix
    all_strategies = ["SMART_RETRY", "PAYMENT_METHOD_UPDATE", "PERSONALIZED_DUNNING", "CHECKOUT_REMINDER", "MANUAL_REVIEW", "NO_ACTION"]
    confusion_matrix = {ai_s: {gt_s: 0 for gt_s in all_strategies} for ai_s in all_strategies}
    exact_agreements = 0
    
    # Decision Quality (RECOVER vs Opp)
    tp, fp, tn, fn = 0, 0, 0, 0
    
    # Confidence
    confidences = []
    conf_buckets = {"0.00-0.20": 0, "0.20-0.40": 0, "0.40-0.60": 0, "0.60-0.80": 0, "0.80-1.00": 0}
    
    # Amount Estimation
    est_amounts = []
    gt_amounts = []
    abs_errors = []
    percentage_errors = []
    overestimations = []
    underestimations = []
    
    # Policy
    policy_allowed = 0
    policy_blocked = 0
    policy_manual = 0
    policy_violations = 0
    
    # Simulation
    sim_attempts = 0
    sim_successes = 0
    sim_failures = 0
    sim_attempted_amt_total = 0.0
    sim_recovered_amt_total = 0.0
    
    correct_samples = []
    incorrect_samples = []
    
    for idx, tx in enumerate(eval_records, 1):
        if idx == 1 or idx % 25 == 0 or idx == sample_size:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Evaluating record {idx}/{sample_size}...")
        pipe_res = run_recovery_pipeline(tx, merchant_policy=policy)
        ai_dec = pipe_res.ai_decision
        pol_res = pipe_res.policy_result
        sim_res = pipe_res.simulation_result
        
        # GT values (strictly for evaluation after AI prediction)
        gt_dict = tx.get("ground_truth", {})
        gt_strat = gt_dict.get("recommended_recovery_strategy", "NO_ACTION")
        gt_recoverable_amt = float(gt_dict.get("expected_recovery_amount", 0.0))
        gt_is_opportunity = bool(gt_dict.get("is_recovery_opportunity", False))
        
        strat = ai_dec.strategy
        dec = ai_dec.decision
        conf = ai_dec.confidence
        est_amt = ai_dec.expected_recovery_amount
        
        # Strategy Distribution
        strategy_dist[strat] = strategy_dist.get(strat, 0) + 1
        decision_dist[dec] = decision_dist.get(dec, 0) + 1
        
        # Agreement & Confusion Matrix
        if strat in confusion_matrix and gt_strat in confusion_matrix[strat]:
            confusion_matrix[strat][gt_strat] += 1
        if strat == gt_strat:
            exact_agreements += 1
            
        # Decision Quality
        if dec == "RECOVER":
            if gt_is_opportunity:
                tp += 1
            else:
                fp += 1
        else:
            if gt_is_opportunity:
                fn += 1
            else:
                tn += 1
                
        # Confidence
        confidences.append(conf)
        if conf <= 0.20: conf_buckets["0.00-0.20"] += 1
        elif conf <= 0.40: conf_buckets["0.20-0.40"] += 1
        elif conf <= 0.60: conf_buckets["0.40-0.60"] += 1
        elif conf <= 0.80: conf_buckets["0.60-0.80"] += 1
        else: conf_buckets["0.80-1.00"] += 1
        
        # Amount Estimation
        est_amounts.append(est_amt)
        gt_amounts.append(gt_recoverable_amt)
        err = abs(est_amt - gt_recoverable_amt)
        abs_errors.append(err)
        if gt_recoverable_amt > 0:
            percentage_errors.append(err / gt_recoverable_amt)
        if est_amt > gt_recoverable_amt:
            overestimations.append(est_amt - gt_recoverable_amt)
        elif est_amt < gt_recoverable_amt:
            underestimations.append(gt_recoverable_amt - est_amt)
            
        # Policy
        if pol_res.allowed:
            policy_allowed += 1
        else:
            policy_blocked += 1
        if pol_res.requires_human_approval or ai_dec.decision == "MANUAL_REVIEW":
            policy_manual += 1
        if pipe_res.validation_status != "PASSED":
            policy_violations += 1
            
        # Simulation
        if sim_res:
            sim_attempts += 1
            sim_attempted_amt_total += sim_res.attempted_amount
            if sim_res.success:
                sim_successes += 1
                sim_recovered_amt_total += sim_res.recovered_amount
            else:
                sim_failures += 1
                
        # Case Studies
        case_info = {
            "transaction_id": tx.get("transaction_id"),
            "amount": tx.get("amount"),
            "failure_code": tx.get("failure_code"),
            "risk_level": pipe_res.context.risk_engine.risk_level,
            "ai_strategy": strat,
            "ai_confidence": conf,
            "gt_strategy": gt_strat,
            "gt_opportunity": gt_is_opportunity,
            "policy_result": "ALLOWED" if pol_res.allowed else f"BLOCKED ({pol_res.reason})",
            "simulated_result": f"SUCCESS (₹{sim_res.recovered_amount})" if sim_res and sim_res.success else ("FAILED" if sim_res else "N/A")
        }
        
        if (dec == "RECOVER" and gt_is_opportunity and strat == gt_strat) or (dec == "NO_ACTION" and not gt_is_opportunity):
            if len(correct_samples) < 10:
                correct_samples.append(case_info)
        else:
            if len(incorrect_samples) < 10:
                incorrect_samples.append(case_info)

    # Compute aggregate stats
    total_n = len(eval_records)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    confidences.sort()
    mean_conf = sum(confidences) / total_n
    median_conf = confidences[total_n // 2]
    min_conf = confidences[0]
    max_conf = confidences[-1]
    
    mae = sum(abs_errors) / total_n
    mape = (sum(percentage_errors) / len(percentage_errors)) * 100 if percentage_errors else 0.0
    mean_over = sum(overestimations) / len(overestimations) if overestimations else 0.0
    mean_under = sum(underestimations) / len(underestimations) if underestimations else 0.0
    
    # Per-strategy P/R
    per_strategy_stats = {}
    for s in all_strategies:
        s_tp = confusion_matrix[s][s]
        s_pred = sum(confusion_matrix[s][gt] for gt in all_strategies)
        s_gt = sum(confusion_matrix[ai][s] for ai in all_strategies)
        s_prec = s_tp / s_pred if s_pred > 0 else 0.0
        s_rec = s_tp / s_gt if s_gt > 0 else 0.0
        per_strategy_stats[s] = {"count": s_pred, "precision": round(s_prec, 4), "recall": round(s_rec, 4)}

    output = {
        "evaluation_summary": {
            "sample_size": total_n,
            "exact_strategy_agreement": round(exact_agreements / total_n, 4),
            "decision_precision": round(precision, 4),
            "decision_recall": round(recall, 4),
            "decision_f1": round(f1, 4),
            "false_recovery_rate": round(fpr, 4),
            "missed_recovery_rate": round(fnr, 4),
        },
        "strategy_distribution": {k: {"count": v, "percentage": round(v / total_n * 100, 2)} for k, v in strategy_dist.items()},
        "decision_distribution": {k: {"count": v, "percentage": round(v / total_n * 100, 2)} for k, v in decision_dist.items()},
        "confusion_matrix": confusion_matrix,
        "per_strategy_stats": per_strategy_stats,
        "confidence_stats": {
            "mean": round(mean_conf, 4),
            "median": round(median_conf, 4),
            "min": round(min_conf, 4),
            "max": round(max_conf, 4),
            "distribution": conf_buckets
        },
        "expected_recovery_stats": {
            "mae": round(mae, 2),
            "mape_percent": round(mape, 2),
            "mean_overestimation": round(mean_over, 2),
            "mean_underestimation": round(mean_under, 2),
            "total_ai_expected": round(sum(est_amounts), 2),
            "total_gt_recoverable": round(sum(gt_amounts), 2)
        },
        "policy_stats": {
            "allowed_count": policy_allowed,
            "allowed_percent": round(policy_allowed / total_n * 100, 2),
            "blocked_count": policy_blocked,
            "blocked_percent": round(policy_blocked / total_n * 100, 2),
            "manual_review_count": policy_manual,
            "policy_violation_attempts": policy_violations
        },
        "simulated_recovery_stats": {
            "total_simulated_actions": sim_attempts,
            "successful_actions": sim_successes,
            "failed_actions": sim_failures,
            "simulated_success_rate": round(sim_successes / max(sim_attempts, 1), 4),
            "total_attempted_revenue": round(sim_attempted_amt_total, 2),
            "total_simulated_recovered_revenue": round(sim_recovered_amt_total, 2),
            "avg_recovered_amount": round(sim_recovered_amt_total / max(sim_successes, 1), 2),
            "avg_attempted_amount": round(sim_attempted_amt_total / max(sim_attempts, 1), 2)
        },
        "correct_samples": correct_samples,
        "incorrect_samples": incorrect_samples
    }
    
    return output

if __name__ == "__main__":
    res = run_evaluation(500)
    report_path = os.path.join(os.path.dirname(__file__), "phase3_gemini_eval_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[SUCCESS] Saved full Phase 3 evaluation report to {report_path}")
    print(json.dumps(res, indent=2))
