import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_phase2_engine import (
    test_dataset_generation_structure_and_splits,
    test_reproducible_random_seed,
    test_risk_engine_no_ground_truth_access,
    test_customer_history_influences_probability,
    test_retry_count_influences_probability,
    test_amount_influences_expected_recovery_amount,
    test_probability_bounded_between_zero_and_one,
    test_mathematical_consistency,
    test_ambiguity_test_fixtures,
    test_evaluator_continuous_metrics
)

from tests.test_phase3_safety import run_all_safety_tests
from tests.test_phase7_ingestion import run_all_ingestion_tests

def main():
    print("--- RUNNING PHASE 2.5 DECOUPLED ENGINE AUTOMATED TEST SUITE ---")
    tests = [
        ("1. Dataset Generation Structure & Splits Test", test_dataset_generation_structure_and_splits),
        ("2. Reproducible Random Seed Test", test_reproducible_random_seed),
        ("3. Risk Engine Independence (No GT Access) Test", test_risk_engine_no_ground_truth_access),
        ("4. Customer History Sensitivity Test", test_customer_history_influences_probability),
        ("5. Retry Velocity Sensitivity Test", test_retry_count_influences_probability),
        ("6. Transaction Amount Sensitivity Test", test_amount_influences_expected_recovery_amount),
        ("7. Probability Boundedness [0, 1] Test", test_probability_bounded_between_zero_and_one),
        ("8. Mathematical Consistency Test", test_mathematical_consistency),
        ("9. Ambiguity Test Fixtures (20 cases) Test", test_ambiguity_test_fixtures),
        ("10. Continuous Evaluator Metrics Test", test_evaluator_continuous_metrics)
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

    print(f"\nENGINE TEST RESULTS: {passed} PASSED, {failed} FAILED")

    print("\n--- RUNNING PHASE 3 SAFETY TEST SUITE ---")
    try:
        run_all_safety_tests()
    except Exception as e:
        print(f"[FAIL] Safety tests error: {e}")
        failed += 1

    print("\n--- RUNNING PHASE 7 INGESTION TEST SUITE ---")
    try:
        run_all_ingestion_tests()
    except Exception as e:
        print(f"[FAIL] Ingestion tests error: {e}")
        failed += 1

    if failed > 0:
        sys.exit(1)
    else:
        print("\nALL BACKEND AUTOMATED TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
