from typing import Dict, Any, List

def calculate_risk_score(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Independent Revenue Risk Engine Multi-Factor Scoring Model.
    
    This model independently estimates recovery probability and risk severity 
    using normalized observable transaction features. It does NOT read ground-truth 
    labels or duplicate compute_ground_truth() rules.

    Scoring Architecture:
    1. Risk Score (0-100): Measures structural transaction risk & failure severity.
    2. Recovery Probability (0.0-1.0): Multi-factor estimate of recovery success.
    3. Opportunity Thresholding: is_opportunity = True if recovery_probability >= 0.40.
    """
    status = event.get("transaction_status", "failed")
    code = event.get("failure_code")
    amount = float(event.get("amount", 0.0))
    retry_count = int(event.get("retry_count", 0))
    prev_success = float(event.get("previous_success_rate", 0.80))
    ltv = float(event.get("customer_lifetime_value", 0.0))
    sub_status = event.get("subscription_status", "none")
    card_expiry = event.get("card_expiry_status", "valid")
    days_since_success = int(event.get("days_since_last_success", 0))
    checkout_completed = event.get("checkout_completed", True)

    # 1. Successful transactions have 0 risk and 0 revenue at risk
    if status == "successful":
        return {
            "risk_score": 0.0,
            "risk_level": "none",
            "revenue_at_risk": 0.0,
            "recovery_probability": 0.0,
            "recommended_strategy": "no_action",
            "expected_recovery_amount": 0.0,
            "is_opportunity": False,
            "reason": "Transaction completed successfully",
            "confidence": 1.0
        }

    # -------------------------------------------------------------
    # PART A: RISK SCORE CALCULATION (0 - 100 PTS)
    # -------------------------------------------------------------
    risk_pts = 0.0

    # Component A1: Failure Severity (Max 35 pts)
    if code in ["stolen_card", "invalid_card"]:
        risk_pts += 35.0
    elif code == "do_not_honor":
        risk_pts += 30.0
    elif status == "disputed":
        risk_pts += 25.0
    elif code == "expired_card" or card_expiry == "expired":
        risk_pts += 22.0
    elif code in ["insufficient_funds", "authentication_failed"]:
        risk_pts += 18.0
    elif status == "abandoned" or not checkout_completed:
        risk_pts += 15.0
    elif code in ["network_timeout", "gateway_error"]:
        risk_pts += 10.0
    else:
        risk_pts += 15.0

    # Component A2: Retry Velocity Penalty (Max 20 pts)
    if retry_count == 1:
        risk_pts += 5.0
    elif retry_count == 2:
        risk_pts += 10.0
    elif retry_count == 3:
        risk_pts += 15.0
    elif retry_count >= 4:
        risk_pts += 20.0

    # Component A3: Customer Historical Success Penalty (Max 20 pts)
    if prev_success >= 0.90:
        risk_pts += 0.0
    elif prev_success >= 0.70:
        risk_pts += 5.0
    elif prev_success >= 0.40:
        risk_pts += 12.0
    else:
        risk_pts += 20.0

    # Component A4: Instrument & Subscription Risk (Max 15 pts)
    if card_expiry == "expired" or sub_status == "past_due":
        risk_pts += 15.0
    elif card_expiry == "expiring_soon" or sub_status == "canceled":
        risk_pts += 8.0

    # Component A5: Inactivity / Recency Penalty (Max 10 pts)
    if days_since_success > 45:
        risk_pts += 10.0
    elif days_since_success > 14:
        risk_pts += 5.0

    risk_score = round(min(100.0, max(0.0, risk_pts)), 2)

    # Risk Level mapping
    if risk_score < 25.0:
        risk_level = "low"
    elif risk_score < 50.0:
        risk_level = "medium"
    elif risk_score < 75.0:
        risk_level = "high"
    else:
        risk_level = "critical"

    # -------------------------------------------------------------
    # PART B: INDEPENDENT RECOVERY PROBABILITY CALCULATION (0.0 - 1.0)
    # -------------------------------------------------------------
    
    # Hard declines have zero recovery probability
    if code in ["stolen_card", "invalid_card"]:
        prob = 0.0
        strategy = "no_action"
        reason = "Hard decline (stolen/invalid card); transaction unrecoverable"
        confidence = 0.95
    else:
        # Base recovery probability by failure type
        if code in ["network_timeout", "gateway_error"]:
            p_base = 0.80
        elif code in ["insufficient_funds", "authentication_failed"]:
            p_base = 0.65
        elif code == "expired_card" or card_expiry == "expired":
            p_base = 0.60
        elif status == "abandoned" or not checkout_completed:
            p_base = 0.50
        elif code == "do_not_honor":
            p_base = 0.35
        elif status == "disputed":
            p_base = 0.20
        else:
            p_base = 0.45

        # Customer Loyalty & LTV Adjustments
        adj_cust = 0.0
        if prev_success >= 0.85:
            adj_cust += 0.10
        elif prev_success < 0.50:
            adj_cust -= 0.12

        if ltv >= 15000.0:
            adj_cust += 0.06
        elif ltv < 1000.0:
            adj_cust -= 0.04

        if sub_status == "active":
            adj_cust += 0.06
        elif sub_status == "canceled":
            adj_cust -= 0.10

        # Friction & Recency Adjustments
        adj_frict = 0.0
        if retry_count >= 3:
            adj_frict -= 0.10
        if days_since_success > 30:
            adj_frict -= 0.06
        if amount > 20000.0:
            adj_frict -= 0.04

        prob = round(min(1.0, max(0.0, p_base + adj_cust + adj_frict)), 4)

        # Strategy Determination based on top observable signals
        if status == "abandoned" or not checkout_completed:
            strategy = "checkout_abandonment_reminder"
            reason = "Checkout session abandoned prior to authorization"
            confidence = 0.85
        elif status == "disputed":
            strategy = "manual_review"
            reason = "Chargeback dispute initiated; requires manual review"
            confidence = 0.80
        elif code in ["network_timeout", "gateway_error"]:
            strategy = "smart_retry"
            reason = "Transient network error; high probability smart retry candidate"
            confidence = 0.90
        elif code == "expired_card" or card_expiry == "expired":
            strategy = "payment_method_update"
            reason = "Expired payment instrument; update request advised"
            confidence = 0.85
        elif prev_success >= 0.70 and retry_count <= 2:
            strategy = "smart_retry"
            reason = "Temporary decline for high-reputation customer; smart retry recommended"
            confidence = 0.82
        else:
            strategy = "personalized_dunning"
            reason = "Repeated or persistent decline; trigger dunning sequence"
            confidence = 0.78

    # Opportunity Decision: Threshold at 0.40 probability
    is_opp = bool(prob >= 0.40 and code not in ["stolen_card", "invalid_card"])

    revenue_at_risk = amount
    expected_recovery = round(revenue_at_risk * prob, 2)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "revenue_at_risk": revenue_at_risk,
        "recovery_probability": prob,
        "recommended_strategy": strategy,
        "expected_recovery_amount": expected_recovery,
        "is_opportunity": is_opp,
        "reason": reason,
        "confidence": confidence
    }

def evaluate_risk_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates a batch of payment transaction events using the Risk Engine.
    """
    results = []
    for event in events:
        eval_res = calculate_risk_score(event)
        combined = {**event, "risk_engine_result": eval_res}
        results.append(combined)
    return results
