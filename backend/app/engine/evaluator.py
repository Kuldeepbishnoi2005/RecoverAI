from typing import List, Dict, Any

def run_evaluation(dataset_with_predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluation pipeline comparing Risk Engine predictions against Ground-Truth labels.
    Calculates Precision, Recall, F1, FPR, FNR, and financial metrics.
    """
    total_records = len(dataset_with_predictions)

    tp, fp, tn, fn = 0, 0, 0, 0
    total_revenue_processed = 0.0
    total_revenue_at_risk = 0.0
    predicted_recoverable_revenue = 0.0
    ground_truth_recoverable_revenue = 0.0
    estimated_recovery_value = 0.0

    # Risk level breakdown accumulators
    risk_categories = {"low": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
                       "medium": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
                       "high": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
                       "critical": {"tp": 0, "fp": 0, "fn": 0, "tn": 0}}

    for item in dataset_with_predictions:
        gt = item["ground_truth"]
        pred = item["risk_engine_result"]

        amt = float(item["amount"])
        total_revenue_processed += amt

        gt_is_opp = bool(gt["is_recovery_opportunity"])
        pred_is_opp = bool(pred["is_opportunity"])

        if item["transaction_status"] != "successful":
            total_revenue_at_risk += amt

        predicted_recoverable_revenue += float(pred["expected_recovery_amount"])
        ground_truth_recoverable_revenue += float(gt["expected_recovery_amount"])

        cat = pred["risk_level"]
        if cat not in risk_categories:
            cat = "medium"

        if pred_is_opp and gt_is_opp:
            tp += 1
            risk_categories[cat]["tp"] += 1
            estimated_recovery_value += float(gt["expected_recovery_amount"])
        elif pred_is_opp and not gt_is_opp:
            fp += 1
            risk_categories[cat]["fp"] += 1
        elif not pred_is_opp and not gt_is_opp:
            tn += 1
            risk_categories[cat]["tn"] += 1
        elif not pred_is_opp and gt_is_opp:
            fn += 1
            risk_categories[cat]["fn"] += 1

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
    fnr = round(fn / (fn + tp), 4) if (fn + tp) > 0 else 0.0

    # Calculate per-category metrics
    category_metrics = {}
    for c_name, c_counts in risk_categories.items():
        c_tp, c_fp, c_fn = c_counts["tp"], c_counts["fp"], c_counts["fn"]
        c_prec = round(c_tp / (c_tp + c_fp), 4) if (c_tp + c_fp) > 0 else 0.0
        c_rec = round(c_tp / (c_tp + c_fn), 4) if (c_tp + c_fn) > 0 else 0.0
        c_f1 = round(2 * (c_prec * c_rec) / (c_prec + c_rec), 4) if (c_prec + c_rec) > 0 else 0.0
        category_metrics[c_name] = {
            "tp": c_tp, "fp": c_fp, "fn": c_fn, "tn": c_counts["tn"],
            "precision": c_prec, "recall": c_rec, "f1_score": c_f1
        }

    return {
        "dataset_size": total_records,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "total_revenue_processed": round(total_revenue_processed, 2),
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "predicted_recoverable_revenue": round(predicted_recoverable_revenue, 2),
        "ground_truth_recoverable_revenue": round(ground_truth_recoverable_revenue, 2),
        "estimated_recovery_value": round(estimated_recovery_value, 2),
        "category_metrics": category_metrics
    }
