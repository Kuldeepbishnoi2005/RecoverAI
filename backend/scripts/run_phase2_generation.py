import sys
import os
import json

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.dataset_generator import generate_synthetic_dataset, DEFAULT_SEED, BENCHMARK_MERCHANT_ID, BENCHMARK_VERSION
from app.engine.risk_engine import evaluate_risk_events
from app.engine.evaluator import run_evaluation
from app.engine.db_seeder import seed_benchmark_to_supabase

def main():
    print("==================================================")
    print("RECOVERAI PHASE 2.5 DECOUPLED BENCHMARK EXECUTION")
    print("==================================================")

    print(f"\n1. Generating 10,000 synthetic payment events (seed={DEFAULT_SEED}, version={BENCHMARK_VERSION})...")
    dataset = generate_synthetic_dataset(count=10000, seed=DEFAULT_SEED, benchmark_version=BENCHMARK_VERSION)
    print(f"-> Generated {len(dataset)} records.")

    print("\n2. Evaluating dataset with decoupled Revenue Risk Engine...")
    evaluated_dataset = evaluate_risk_events(dataset)

    print("\n3. Calculating binary & continuous evaluation metrics...")
    overall_metrics = run_evaluation(evaluated_dataset)

    # Calculate split metrics (train/validation/test)
    splits = ["train", "validation", "test"]
    split_metrics = {}
    for s in splits:
        split_ds = [x for x in evaluated_dataset if x.get("dataset_split") == s]
        split_metrics[s] = run_evaluation(split_ds)

    print("\n4. Seeding benchmark records to Supabase...")
    db_res = seed_benchmark_to_supabase(evaluated_dataset, overall_metrics, benchmark_version=BENCHMARK_VERSION)
    print(f"-> Supabase Seed Result: {db_res.get('status')}, Transactions: {db_res.get('transactions_inserted')}, Run ID: {db_res.get('evaluation_run_id')}")

    print("\n==================================================")
    print("PHASE 2.5 BENCHMARK EVALUATION RESULTS (v2.1)")
    print("==================================================")
    print(f"Dataset Size: {overall_metrics['dataset_size']} records (Seed: {DEFAULT_SEED})")
    print(f"Confusion Matrix: TP={overall_metrics['confusion_matrix']['tp']}, FP={overall_metrics['confusion_matrix']['fp']}, TN={overall_metrics['confusion_matrix']['tn']}, FN={overall_metrics['confusion_matrix']['fn']}")
    print(f"\n--- BINARY METRICS ---")
    print(f"Precision : {overall_metrics['precision']:.4f}")
    print(f"Recall    : {overall_metrics['recall']:.4f}")
    print(f"F1-Score  : {overall_metrics['f1_score']:.4f}")
    print(f"FPR       : {overall_metrics['false_positive_rate'] * 100:.2f}%")
    print(f"FNR       : {overall_metrics['false_negative_rate'] * 100:.2f}%")

    print(f"\n--- CONTINUOUS & CALIBRATION METRICS ---")
    print(f"ROC-AUC           : {overall_metrics['roc_auc']:.4f}")
    print(f"PR-AUC            : {overall_metrics['pr_auc']:.4f}")
    print(f"Brier Score       : {overall_metrics['brier_score']:.4f}")
    print(f"Calibration Error : {overall_metrics['calibration_error']:.4f}")

    print(f"\n--- FINANCIAL METRICS ---")
    print(f"Total Revenue Processed          : INR {overall_metrics['total_revenue_processed']:,.2f}")
    print(f"Total Revenue at Risk            : INR {overall_metrics['total_revenue_at_risk']:,.2f}")
    print(f"Predicted Recoverable Revenue    : INR {overall_metrics['predicted_recoverable_revenue']:,.2f}")
    print(f"Ground-Truth Recoverable Revenue: INR {overall_metrics['ground_truth_recoverable_revenue']:,.2f}")
    print(f"Estimated Recovery Value         : INR {overall_metrics['estimated_recovery_value']:,.2f}")

    print(f"\n--- SPLIT EVALUATION COMPARISON ---")
    for s in splits:
        m = split_metrics[s]
        print(f"Split [{s.upper()} ({m['dataset_size']} recs)]: F1={m['f1_score']:.4f}, Precision={m['precision']:.4f}, Recall={m['recall']:.4f}, ROC-AUC={m['roc_auc']:.4f}, Brier={m['brier_score']:.4f}")

    # Top 10 False Positives & False Negatives Analysis
    fps = [x for x in evaluated_dataset if x['risk_engine_result']['is_opportunity'] and not x['ground_truth']['is_recovery_opportunity']]
    fns = [x for x in evaluated_dataset if not x['risk_engine_result']['is_opportunity'] and x['ground_truth']['is_recovery_opportunity']]

    print(f"\n--- TOP 5 FALSE POSITIVES (Model predicted opportunity, Ground Truth said NO) ---")
    for idx, item in enumerate(fps[:5], 1):
        gt = item['ground_truth']
        pred = item['risk_engine_result']
        print(f"{idx}. TX ID: {item['transaction_id'][:8]} | Amt: INR {item['amount']} | Code: {item['failure_code']} | Retry: {item['retry_count']} | PrevSucc: {item['previous_success_rate']} | GT Prob: {gt['ground_truth_probability']} | Pred Prob: {pred['recovery_probability']}")

    print(f"\n--- TOP 5 FALSE NEGATIVES (Ground Truth said YES, Model predicted NO) ---")
    for idx, item in enumerate(fns[:5], 1):
        gt = item['ground_truth']
        pred = item['risk_engine_result']
        print(f"{idx}. TX ID: {item['transaction_id'][:8]} | Amt: INR {item['amount']} | Code: {item['failure_code']} | Retry: {item['retry_count']} | PrevSucc: {item['previous_success_rate']} | GT Prob: {gt['ground_truth_probability']} | Pred Prob: {pred['recovery_probability']}")

    print("\n==================================================")
    print("PHASE 2.5 BENCHMARK COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
