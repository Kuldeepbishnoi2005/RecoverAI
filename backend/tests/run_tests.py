import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_phase2_engine import (
    test_dataset_generation,
    test_deterministic_seed,
    test_ground_truth_labeling,
    test_risk_scoring,
    test_recovery_opportunity_detection,
    test_revenue_at_risk_calculation,
    test_evaluation_metrics
)

def main():
    print("--- RUNNING PHASE 2 ENGINE AUTOMATED TEST SUITE ---")
    tests = [
        ("1. Dataset Generation Test", test_dataset_generation),
        ("2. Deterministic Seed Test", test_deterministic_seed),
        ("3. Ground-Truth Labeling Test", test_ground_truth_labeling),
        ("4. Risk Scoring Test", test_risk_scoring),
        ("5. Recovery Opportunity Detection Test", test_recovery_opportunity_detection),
        ("6. Revenue-At-Risk Calculation Test", test_revenue_at_risk_calculation),
        ("7. Evaluation Metrics Test", test_evaluation_metrics)
    ]

    passed = 0
    failed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name} -> Error: {e}")
            failed += 1

    print(f"\nRESULTS: {passed} PASSED, {failed} FAILED")
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL AUTOMATED TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
