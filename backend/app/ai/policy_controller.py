from app.ai.schemas import AIContext, AIDecisionOutput, PolicyResult

def evaluate_policy(
    decision: AIDecisionOutput,
    context: AIContext
) -> PolicyResult:
    """
    Deterministic Policy & Governance Controller.
    The LLM cannot override this controller.
    
    Returns structured PolicyResult (allowed: bool, reason: str, requires_human_approval: bool).
    """
    tx = context.transaction
    policy = context.merchant_policy

    # 1. Non-RECOVER decisions (NO_ACTION / MANUAL_REVIEW)
    if decision.decision == "NO_ACTION":
        return PolicyResult(
            allowed=False,
            reason="AI recommended NO_ACTION. Governance controller blocked automatic execution.",
            requires_human_approval=False
        )

    if decision.decision == "MANUAL_REVIEW" or decision.strategy == "MANUAL_REVIEW":
        return PolicyResult(
            allowed=False,
            reason="Action flagged for MANUAL_REVIEW. Requires merchant human approval.",
            requires_human_approval=True
        )

    # 2. Transaction status checks
    if tx.transaction_status == "SUCCESS":
        return PolicyResult(
            allowed=False,
            reason="Transaction is already SUCCESS. Recovery is blocked to prevent double-charging.",
            requires_human_approval=False
        )

    if tx.transaction_status in ["DISPUTED", "RESOLVED", "REFUNDED"]:
        return PolicyResult(
            allowed=False,
            reason=f"Transaction status is '{tx.transaction_status}'. Automatic recovery is blocked.",
            requires_human_approval=True
        )

    # 3. Merchant automatic recovery setting
    if not policy.automatic_recovery_enabled:
        return PolicyResult(
            allowed=False,
            reason="Merchant automatic recovery is disabled in merchant controls.",
            requires_human_approval=True
        )

    # 4. Confidence threshold check
    if decision.confidence < policy.minimum_ai_confidence:
        return PolicyResult(
            allowed=False,
            reason=f"AI confidence ({decision.confidence:.2f}) is below merchant minimum threshold ({policy.minimum_ai_confidence:.2f}).",
            requires_human_approval=True
        )

    # 5. Amount limit check
    if tx.amount > policy.maximum_recovery_amount:
        return PolicyResult(
            allowed=False,
            reason=f"Transaction amount (₹{tx.amount:,.2f}) exceeds merchant maximum recovery limit (₹{policy.maximum_recovery_amount:,.2f}).",
            requires_human_approval=True
        )

    # 6. Retry attempt limit check
    if tx.retry_count >= policy.maximum_retry_attempts:
        return PolicyResult(
            allowed=False,
            reason=f"Transaction retry count ({tx.retry_count}) reached merchant maximum limit ({policy.maximum_retry_attempts}).",
            requires_human_approval=True
        )

    # 7. Allowed strategy check
    if decision.strategy not in policy.allowed_recovery_strategies:
        return PolicyResult(
            allowed=False,
            reason=f"Strategy '{decision.strategy}' is not enabled in merchant allowed strategies.",
            requires_human_approval=True
        )

    # All policy checks passed!
    return PolicyResult(
        allowed=True,
        reason="All merchant governance rules passed. Automatic simulated recovery allowed.",
        requires_human_approval=False
    )
