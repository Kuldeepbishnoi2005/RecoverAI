from typing import Dict, Any, List

def calculate_risk_score(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Revenue Risk Engine scoring formula.
    Returns calculated risk_score, risk_level, revenue_at_risk,
    recovery_probability, and recommended_strategy.
    """
    status = event.get("transaction_status", "failed")
    code = event.get("failure_code")
    amount = float(event.get("amount", 0.0))
    retry_count = int(event.get("retry_count", 0))
    prev_success = float(event.get("previous_success_rate", 1.0))
    sub_status = event.get("subscription_status", "none")
    card_expiry = event.get("card_expiry_status", "valid")
    days_since_success = int(event.get("days_since_last_success", 0))
    checkout_completed = event.get("checkout_completed", True)

    # 1. Successful payments have 0 risk score and 0 revenue at risk
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

    score = 0.0

    # Component A: Base status & Failure code weight (Max 40 pts)
    if status == "abandoned" or not checkout_completed:
        score += 30.0
    elif status == "disputed":
        score += 35.0
    elif status == "failed":
        if code in ["network_timeout", "gateway_error"]:
            score += 20.0
        elif code in ["insufficient_funds", "authentication_failed"]:
            score += 25.0
        elif code == "expired_card":
            score += 30.0
        elif code == "do_not_honor":
            score += 35.0
        elif code in ["stolen_card", "invalid_card"]:
            score += 40.0
        else:
            score += 25.0

    # Component B: Retry Count Penalty (Max 20 pts)
    if retry_count == 1:
        score += 5.0
    elif retry_count == 2:
        score += 10.0
    elif retry_count == 3:
        score += 15.0
    elif retry_count >= 4:
        score += 20.0

    # Component C: Customer History & Success Rate Penalty (Max 20 pts)
    if prev_success >= 0.90:
        score += 0.0
    elif prev_success >= 0.70:
        score += 5.0
    elif prev_success >= 0.40:
        score += 10.0
    else:
        score += 20.0

    # Component D: Subscription & Card Expiry Penalty (Max 10 pts)
    if card_expiry == "expired" or sub_status == "past_due":
        score += 10.0
    elif card_expiry == "expiring_soon" or sub_status == "canceled":
        score += 5.0

    # Component E: Days Since Last Success Penalty (Max 10 pts)
    if days_since_success > 30:
        score += 10.0
    elif days_since_success > 7:
        score += 5.0

    risk_score = round(min(100.0, max(0.0, score)), 2)

    # Risk Level mapping
    if risk_score == 0.0:
        risk_level = "none"
    elif risk_score < 25.0:
        risk_level = "low"
    elif risk_score < 50.0:
        risk_level = "medium"
    elif risk_score < 75.0:
        risk_level = "high"
    else:
        risk_level = "critical"

    revenue_at_risk = amount

    # Determine recommended strategy and recovery probability
    if code in ["stolen_card", "invalid_card"]:
        strategy = "no_action"
        prob = 0.0
        is_opp = False
        reason = "Hard decline (stolen or invalid card); transaction is unrecoverable"
        confidence = 0.95
    elif status == "abandoned" or not checkout_completed:
        strategy = "checkout_abandonment_reminder"
        prob = 0.45
        is_opp = True
        reason = "Customer abandoned checkout prior to payment authorization"
        confidence = 0.85
    elif status == "disputed":
        strategy = "manual_review"
        prob = 0.20
        is_opp = True
        reason = "Chargeback dispute initiated; requires risk analyst manual review"
        confidence = 0.80
    elif code in ["network_timeout", "gateway_error"]:
        strategy = "smart_retry"
        prob = 0.85
        is_opp = True
        reason = "Transient gateway network error; high probability smart retry"
        confidence = 0.90
    elif code in ["insufficient_funds", "authentication_failed"]:
        if prev_success >= 0.70:
            strategy = "smart_retry"
            prob = 0.75
            is_opp = True
            reason = "Temporary balance issue for high-value loyal customer"
            confidence = 0.85
        else:
            strategy = "personalized_dunning"
            prob = 0.50
            is_opp = True
            reason = "Repeated balance failure; trigger automated personalized dunning"
            confidence = 0.80
    elif code == "expired_card" or card_expiry == "expired":
        strategy = "payment_method_update"
        prob = 0.70 if sub_status == "active" else 0.40
        is_opp = True
        reason = "Card instrument expired; request customer payment method update"
        confidence = 0.88
    elif code == "do_not_honor":
        strategy = "personalized_dunning"
        prob = 0.30
        is_opp = True
        reason = "Issuer generic decline; send cardholder dunning notice"
        confidence = 0.75
    else:
        strategy = "smart_retry"
        prob = 0.50
        is_opp = True
        reason = "Failed payment candidate for automated recovery protocol"
        confidence = 0.70

    expected_recovery = round(revenue_at_risk * prob, 2)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "revenue_at_risk": revenue_at_risk,
        "recovery_probability": round(prob, 2),
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
