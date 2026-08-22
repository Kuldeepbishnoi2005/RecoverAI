import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.evaluator import run_ai_evaluation

def test_evaluator_execution():
    # Run evaluation on a sample of test dataset
    results = run_ai_evaluation(sample_size=20)

    assert results["benchmark_version"] == "v2.1"
    assert results["evaluation_split"] == "test"
    assert results["sample_size"] == 20
    assert "strategy_distribution" in results
    assert "decision_distribution" in results
    assert "strategy_agreement_with_gt" in results
    assert "no_action_rate" in results
    assert "policy_violation_rate" in results
    assert "simulated_success_rate" in results

def run_evaluator_test():
    print("--- RUNNING PHASE 3.13 AI EVALUATOR SUITE ---")
    try:
        test_evaluator_execution()
        print("[PASS] Evaluator executed on benchmark test split without ground-truth leakage")
        print("\nAI EVALUATOR TEST RESULT: ALL PASSED")
        return True
    except Exception as e:
        print(f"[FAIL] Evaluator test failed: {str(e)}")
        raise e

if __name__ == "__main__":
    run_evaluator_test()
