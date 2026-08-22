from typing import Dict, Any, List
from app.engine.dataset_generator import generate_synthetic_dataset
from app.services.recovery_pipeline import run_recovery_pipeline
from app.ai.schemas import MerchantPolicy

def run_ai_evaluation(sample_size: int = 100) -> Dict[str, Any]:
    """
    Evaluates AI Recovery Strategist on the FROZEN v2.1 test split.
    
    STRICT COMPLIANCE:
    - AI receives NO ground-truth labels.
    - Test split records only (disjoint customers).
    - Measures strategy agreement, policy violation rate, simulation performance.
    """
    dataset = generate_synthetic_dataset(count=10000, seed=42)
    test_df = [r for r in dataset if r.get("dataset_split") == "test" or r.get("split") == "test"]

    # Cap sample size to test dataset length
    if sample_size > len(test_df):
        sample_size = len(test_df)

    eval_records = test_df[:sample_size]
    policy = MerchantPolicy()

    results: List[Dict[str, Any]] = []
    strategy_dist: Dict[str, int] = {}
    decision_dist: Dict[str, int] = {}
    
    agreements = 0
    no_action_count = 0
    inappropriate_recovery_count = 0
    policy_violations = 0
    
    confidences: List[float] = []
    expected_errors: List[float] = []
    
    sim_attempts = 0
    sim_successes = 0
    est_recovered_total = 0.0
    sim_recovered_total = 0.0

    for tx in eval_records:
        # Run AI decision pipeline
        pipe_res = run_recovery_pipeline(tx, merchant_policy=policy)
        ai_dec = pipe_res.ai_decision
        pol_res = pipe_res.policy_result
        sim_res = pipe_res.simulation_result

        # Track distributions
        strat = ai_dec.strategy
        dec = ai_dec.decision
        strategy_dist[strat] = strategy_dist.get(strat, 0) + 1
        decision_dist[dec] = decision_dist.get(dec, 0) + 1

        confidences.append(ai_dec.confidence)
        est_recovered_total += ai_dec.expected_recovery_amount

        # Ground truth comparison (Strictly after prediction!)
        gt_dict = tx.get("ground_truth", {})
        gt_strat = gt_dict.get("recommended_recovery_strategy", tx.get("recommended_recovery_strategy", "NO_ACTION"))
        gt_recoverable_amt = float(gt_dict.get("expected_recovery_amount", tx.get("expected_recovery_amount", 0.0)))
        gt_is_opportunity = bool(gt_dict.get("is_recovery_opportunity", tx.get("is_recovery_opportunity", False)))

        if strat == gt_strat:
            agreements += 1

        if dec == "NO_ACTION":
            no_action_count += 1

        if dec == "RECOVER" and not gt_is_opportunity:
            inappropriate_recovery_count += 1

        if not pipe_res.validation_status == "PASSED":
            policy_violations += 1

        # Calculate error in expected recovery estimation
        expected_errors.append(abs(ai_dec.expected_recovery_amount - gt_recoverable_amt))

        # Simulation metrics
        if sim_res:
            sim_attempts += 1
            if sim_res.success:
                sim_successes += 1
                sim_recovered_total += sim_res.recovered_amount

    total_n = len(eval_records)
    
    return {
        "benchmark_version": "v2.1",
        "evaluation_split": "test",
        "sample_size": total_n,
        "strategy_distribution": strategy_dist,
        "decision_distribution": decision_dist,
        "strategy_agreement_with_gt": round(agreements / total_n, 4),
        "no_action_rate": round(no_action_count / total_n, 4),
        "inappropriate_recovery_rate": round(inappropriate_recovery_count / total_n, 4),
        "policy_violation_rate": round(policy_violations / total_n, 4),
        "mean_ai_confidence": round(sum(confidences) / max(len(confidences), 1), 4),
        "mean_expected_recovery_error": round(sum(expected_errors) / max(len(expected_errors), 1), 2),
        "simulated_attempts": sim_attempts,
        "simulated_successes": sim_successes,
        "simulated_success_rate": round(sim_successes / max(sim_attempts, 1), 4),
        "total_estimated_recovered_revenue": round(est_recovered_total, 2),
        "total_simulated_recovered_revenue": round(sim_recovered_total, 2)
    }
