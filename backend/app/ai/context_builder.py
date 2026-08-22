import re
from typing import Dict, Any, Optional
from datetime import datetime
from app.engine.risk_engine import calculate_risk_score
from app.ai.schemas import (
    AIContext,
    TransactionContext,
    CustomerContext,
    RiskEngineContext,
    MerchantPolicy
)

def sanitize_untrusted_text(text: str) -> str:
    """
    Sanitizes free-text fields (customer names, descriptions, failure reasons)
    to protect against prompt injection attacks (Phase 3.12).
    Framed strictly as untrusted data strings.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Strip potential prompt injection directives
    injection_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"override\s+(all\s+)?policies",
        r"system\s*:",
        r"user\s*:",
        r"assistant\s*:",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
        r"approve\s+a?\s*₹?\d+",
        r"set\s+confidence\s+to\s+1"
    ]
    
    sanitized = text
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[CLEANED_UNTRUSTED_INPUT]", sanitized, flags=re.IGNORECASE)
    
    # Remove control characters and cap max length
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', sanitized)
    return sanitized.strip()[:500]


def build_ai_context(
    transaction: Dict[str, Any],
    merchant_policy: Optional[MerchantPolicy] = None
) -> AIContext:
    """
    Constructs a structured context object for the AI Recovery Strategist.
    
    STRICTLY EXCLUDES ground-truth labels:
    - is_recovery_opportunity
    - true_risk_level
    - recoverability
    - expected_recovery_amount (ground-truth)
    - recommended_recovery_strategy (ground-truth)
    - split (train/validation/test)
    """
    if merchant_policy is None:
        merchant_policy = MerchantPolicy()

    # 1. Compute observable risk engine outputs (NO ground truth access)
    risk_output = calculate_risk_score(transaction)

    # 2. Build Transaction Context (sanitized)
    tx_context = TransactionContext(
        transaction_id=str(transaction.get("transaction_id", "")),
        amount=float(transaction.get("amount", 0.0)),
        currency=str(transaction.get("currency", "INR")),
        payment_method=str(transaction.get("payment_method", "card")),
        transaction_status=str(transaction.get("transaction_status", "FAILED")),
        failure_code=str(transaction.get("failure_code", "UNKNOWN")),
        failure_reason=sanitize_untrusted_text(str(transaction.get("failure_reason", "Payment failed"))),
        retry_count=int(transaction.get("retry_count", 0)),
        timestamp=str(transaction.get("transaction_timestamp", datetime.utcnow().isoformat()))
    )

    # 3. Build Customer Context (sanitized)
    prev_success = float(transaction.get("previous_success_rate", 0.8))
    cust_context = CustomerContext(
        customer_id=str(transaction.get("customer_id", "")),
        customer_history=sanitize_untrusted_text(
            f"Customer with {prev_success:.0%} historical success rate, "
            f"subscription: {transaction.get('subscription_status', 'active')}."
        ),
        previous_success_rate=prev_success,
        customer_lifetime_value=float(transaction.get("customer_lifetime_value", 0.0)),
        subscription_status=str(transaction.get("subscription_status", "active")),
        days_since_last_success=int(transaction.get("days_since_last_success", 0))
    )

    # 4. Build Risk Engine Context (Observable estimation only)
    risk_context = RiskEngineContext(
        risk_score=float(risk_output["risk_score"]),
        risk_level=str(risk_output["risk_level"]),
        recovery_probability=float(risk_output["recovery_probability"]),
        revenue_at_risk=float(risk_output["revenue_at_risk"]),
        expected_recoverable_amount=float(risk_output.get("expected_recovery_amount", 0.0)),
        detected_risk_reasons=[sanitize_untrusted_text(risk_output.get("reason", "Structural transaction risk"))]
    )

    # 5. Assemble AI Context
    return AIContext(
        transaction=tx_context,
        customer=cust_context,
        risk_engine=risk_context,
        merchant_policy=merchant_policy
    )
