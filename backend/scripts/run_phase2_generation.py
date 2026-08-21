import sys
import os
import json

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.dataset_generator import generate_synthetic_dataset, DEFAULT_SEED, BENCHMARK_MERCHANT_ID
from app.engine.risk_engine import evaluate_risk_events
from app.engine.evaluator import run_evaluation
from app.engine.db_seeder import seed_benchmark_to_supabase

def main():
    print("==========================================================")
    print("RECOVERAI PHASE 2: BENCHMARK DATASET GENERATION & EVALUATION")
    print("==========================================================")
    print(f"Generating 10,000 synthetic payment events (seed={DEFAULT_SEED})...")

    raw_dataset = generate_synthetic_dataset(count=10000, seed=DEFAULT_SEED, merchant_id=BENCHMARK_MERCHANT_ID)
    print(f"Generated {len(raw_dataset)} records successfully.")

    print("\nRunning Revenue Risk Engine evaluation on dataset...")
    evaluated_dataset = evaluate_risk_events(raw_dataset)

    print("\nRunning Evaluation Pipeline against Ground-Truth labels...")
    metrics = run_evaluation(evaluated_dataset)

    print("\n==========================================================")
    print("EVALUATION METRICS RESULTS:")
    print("==========================================================")
    print(json.dumps(metrics, indent=2))

    print("\nPersisting benchmark dataset & evaluation run into Supabase...")
    db_res = seed_benchmark_to_supabase(evaluated_dataset, metrics)
    print("DB Persistence Summary:")
    print(json.dumps(db_res, indent=2))
    print("\nPhase 2 Dataset Generation & Evaluation complete!")

if __name__ == "__main__":
    main()
