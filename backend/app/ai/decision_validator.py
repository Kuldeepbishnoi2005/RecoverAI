from typing import Tuple, List
from app.ai.schemas import AIContext, AIDecisionOutput

def validate_ai_decision(
    decision: AIDecisionOutput,
    context: AIContext
) -> Tuple[AIDecisionOutput, bool, List[str]]:
    """
    Validates LLM output against strict business logic and security rules.
    Returns: (validated_decision, isValid: bool, validation_errors: List[str])
    
    If validation fails:
    DO NOT execute action -> fallback to MANUAL_REVIEW.
    """
    errors: List[str] = []
    tx = context.transaction
    policy = context.merchant_policy

    # 1. Strategy check
    if decision.strategy not in policy.allowed_recovery_strategies:
        errors.append(f"Strategy '{decision.strategy}' is not in merchant allowed strategies.")

    # 2. Boundedness checks
    if not (0.0 <= decision.confidence <= 1.0):
        errors.append(f"Confidence {decision.confidence} out of range [0, 1].")

    if not (0.0 <= decision.recovery_probability <= 1.0):
        errors.append(f"Recovery probability {decision.recovery_probability} out of range [0, 1].")

    # 3. Financial bounds
    if decision.expected_recovery_amount < 0:
        errors.append(f"Expected recovery amount ({decision.expected_recovery_amount}) cannot be negative.")

    if decision.expected_recovery_amount > tx.amount:
        errors.append(
            f"Expected recovery amount ({decision.expected_recovery_amount}) exceeds transaction amount ({tx.amount})."
        )

    if tx.amount > policy.maximum_recovery_amount:
        errors.append(
            f"Transaction amount ({tx.amount}) exceeds merchant maximum recovery limit ({policy.maximum_recovery_amount})."
        )

    # 4. Retry limit check
    if tx.retry_count > policy.maximum_retry_attempts:
        errors.append(
            f"Transaction retry count ({tx.retry_count}) exceeds merchant limit ({policy.maximum_retry_attempts})."
        )

    # 5. State compatibility check
    if tx.transaction_status in ["SUCCESS", "REFUNDED", "DISPUTED"] and decision.decision == "RECOVER":
        errors.append(f"Cannot perform RECOVER on transaction with status '{tx.transaction_status}'.")

    # If any error exists, override decision to MANUAL_REVIEW safely
    if errors:
        safe_fallback = AIDecisionOutput(
            decision="MANUAL_REVIEW",
            strategy="MANUAL_REVIEW",
            confidence=0.0,
            recovery_probability=0.0,
            expected_recovery_amount=0.0,
            reason=f"Validation failed: {'; '.join(errors)}",
            risk_factors=decision.risk_factors + ["Validation Failure"],
            recommended_delay_minutes=0,
            fallback_strategy="NO_ACTION"
        )
        return safe_fallback, False, errors

    return decision, True, []
