from typing import List, Dict, Any, Tuple

def _compute_brier_score(y_true: List[int], y_prob: List[float]) -> float:
    """Calculates Mean Squared Error of predicted probabilities against binary ground truth."""
    if not y_true:
        return 0.0
    total = sum((p - y) ** 2 for y, p in zip(y_true, y_prob))
    return round(total / len(y_true), 4)

def _compute_ece(y_true: List[int], y_prob: List[float], num_bins: int = 10) -> float:
    """Calculates Expected Calibration Error (ECE) across 10 probability bins."""
    if not y_true:
        return 0.0
    bins = [[] for _ in range(num_bins)]
    for y, p in zip(y_true, y_prob):
        bin_idx = min(int(p * num_bins), num_bins - 1)
        bins[bin_idx].append((y, p))
    
    ece = 0.0
    n = len(y_true)
    for b in bins:
        if not b:
            continue
        bin_size = len(b)
        avg_acc = sum(item[0] for item in b) / bin_size
        avg_conf = sum(item[1] for item in b) / bin_size
        ece += (bin_size / n) * abs(avg_acc - avg_conf)
    return round(ece, 4)

def _compute_roc_auc(y_true: List[int], y_prob: List[float]) -> float:
    """Calculates Area Under ROC Curve via trapezoidal integration."""
    if not y_true or sum(y_true) == 0 or sum(y_true) == len(y_true):
        return 0.5
    pairs = sorted(zip(y_prob, y_true), key=lambda x: x[0], reverse=True)
    pos_count = sum(y_true)
    neg_count = len(y_true) - pos_count
    
    auc = 0.0
    tp = 0
    fp = 0
    prev_tp = 0
    prev_fp = 0
    
    for prob, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        auc += (fp - prev_fp) * (tp + prev_tp) / 2.0
        prev_tp = tp
        prev_fp = fp
        
    return round(auc / (pos_count * neg_count), 4)

def _compute_pr_auc(y_true: List[int], y_prob: List[float]) -> float:
    """Calculates Area Under Precision-Recall Curve via trapezoidal integration."""
    if not y_true or sum(y_true) == 0:
        return 0.0
    pairs = sorted(zip(y_prob, y_true), key=lambda x: x[0], reverse=True)
    total_positives = sum(y_true)
    
    tp = 0
    fp = 0
    precisions = [1.0]
    recalls = [0.0]
    
    for prob, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        precisions.append(tp / (tp + fp))
        recalls.append(tp / total_positives)
        
    auc = 0.0
    for i in range(1, len(recalls)):
        dr = recalls[i] - recalls[i-1]
        avg_p = (precisions[i] + precisions[i-1]) / 2.0
        auc += dr * avg_p
    return round(auc, 4)

def run_evaluation(dataset_with_predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Comprehensive evaluation pipeline comparing Risk Engine predictions against Ground-Truth.
    Calculates Binary (Precision, Recall, F1, FPR, FNR), Continuous (ROC-AUC, PR-AUC, Brier Score, ECE),
    and Financial Metrics.
    """
    total_records = len(dataset_with_predictions)

    tp, fp, tn, fn = 0, 0, 0, 0
    total_revenue_processed = 0.0
    total_revenue_at_risk = 0.0
    predicted_recoverable_revenue = 0.0
    ground_truth_recoverable_revenue = 0.0
    estimated_recovery_value = 0.0

    y_true = []
    y_prob = []

    risk_categories = {
        "low": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "medium": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "high": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "critical": {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    }

    for item in dataset_with_predictions:
        gt = item["ground_truth"]
        pred = item["risk_engine_result"]

        amt = float(item["amount"])
        total_revenue_processed += amt

        gt_is_opp = bool(gt["is_recovery_opportunity"])
        pred_is_opp = bool(pred["is_opportunity"])
        pred_prob = float(pred["recovery_probability"])

        y_true.append(1 if gt_is_opp else 0)
        y_prob.append(pred_prob)

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

    # Continuous Metric calculations
    brier_score = _compute_brier_score(y_true, y_prob)
    calibration_error = _compute_ece(y_true, y_prob)
    roc_auc = _compute_roc_auc(y_true, y_prob)
    pr_auc = _compute_pr_auc(y_true, y_prob)

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
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "brier_score": brier_score,
        "calibration_error": calibration_error,
        "total_revenue_processed": round(total_revenue_processed, 2),
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "predicted_recoverable_revenue": round(predicted_recoverable_revenue, 2),
        "ground_truth_recoverable_revenue": round(ground_truth_recoverable_revenue, 2),
        "estimated_recovery_value": round(estimated_recovery_value, 2),
        "category_metrics": category_metrics
    }
