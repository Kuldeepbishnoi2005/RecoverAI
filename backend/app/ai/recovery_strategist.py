import json
import logging
import os
import time
from typing import Dict, Any
from app.config import settings
from app.ai.schemas import AIContext, AIDecisionOutput

logger = logging.getLogger("app.ai.recovery_strategist")

SYSTEM_PROMPT = """You are the RecoverAI Recovery Strategist.

Your job is to select the safest and most effective recovery strategy for a revenue recovery opportunity.

You do not decide whether the transaction is financially risky.
The deterministic Revenue Risk Engine already provides that assessment.

You must use the provided transaction, customer, risk and merchant-policy context.

You must respect all merchant controls.

You must never invent transaction facts.

You must never recommend an action outside the allowed strategies.

If the available evidence is insufficient, choose MANUAL_REVIEW or NO_ACTION.

Prioritize decisions in this exact order:
1. Customer safety & friction minimization
2. Merchant policy compliance
3. Probability of successful recovery
4. Expected recovery value
5. Minimal unnecessary payment attempts

Allowed Decision values: ["RECOVER", "MANUAL_REVIEW", "NO_ACTION"]
Allowed Strategy values: ["SMART_RETRY", "PAYMENT_METHOD_UPDATE", "PERSONALIZED_DUNNING", "CHECKOUT_REMINDER", "MANUAL_REVIEW", "NO_ACTION"]

Respond strictly in valid JSON matching this schema:
{
  "decision": "RECOVER" | "MANUAL_REVIEW" | "NO_ACTION",
  "strategy": "SMART_RETRY" | "PAYMENT_METHOD_UPDATE" | "PERSONALIZED_DUNNING" | "CHECKOUT_REMINDER" | "MANUAL_REVIEW" | "NO_ACTION",
  "confidence": 0.92,
  "recovery_probability": 0.78,
  "expected_recovery_amount": 1949.00,
  "reason": "Clear explanation grounded strictly in context",
  "risk_factors": ["Factor 1", "Factor 2"],
  "recommended_delay_minutes": 30,
  "fallback_strategy": "PAYMENT_METHOD_UPDATE"
}
"""


def _generate_fallback_decision(context: AIContext) -> AIDecisionOutput:
    """
    Deterministic expert fallback AI strategist when Gemini API is unavailable or unconfigured.
    Conforms strictly to schema and merchant policy rules.
    """
    tx = context.transaction
    cust = context.customer
    risk = context.risk_engine
    policy = context.merchant_policy

    # 1. Non-recoverable conditions -> NO_ACTION
    if tx.transaction_status in ["SUCCESS", "REFUNDED", "DISPUTED"]:
        return AIDecisionOutput(
            decision="NO_ACTION",
            strategy="NO_ACTION",
            confidence=0.98,
            recovery_probability=0.0,
            expected_recovery_amount=0.0,
            reason=f"Transaction is already {tx.transaction_status}; recovery is neither safe nor appropriate.",
            risk_factors=[f"Transaction status is {tx.transaction_status}"],
            recommended_delay_minutes=0,
            fallback_strategy="NO_ACTION"
        )

    # 2. Exceeded retry attempts or low CLV -> MANUAL_REVIEW or NO_ACTION
    if tx.retry_count >= policy.maximum_retry_attempts:
        return AIDecisionOutput(
            decision="MANUAL_REVIEW",
            strategy="MANUAL_REVIEW",
            confidence=0.85,
            recovery_probability=min(risk.recovery_probability, 0.3),
            expected_recovery_amount=round(tx.amount * 0.2, 2),
            reason=f"Retry limit ({policy.maximum_retry_attempts}) reached. Requires human intervention.",
            risk_factors=["Maximum retry count reached", "Repeated failure"],
            recommended_delay_minutes=0,
            fallback_strategy="NO_ACTION"
        )

    # 3. Strategy mapping based on failure code & customer state
    if tx.failure_code in ["EXPIRED_CARD", "INVALID_CARD"]:
        strat = "PAYMENT_METHOD_UPDATE" if "PAYMENT_METHOD_UPDATE" in policy.allowed_recovery_strategies else "MANUAL_REVIEW"
        dec = "RECOVER" if strat == "PAYMENT_METHOD_UPDATE" else "MANUAL_REVIEW"
        conf = 0.90
        prob = 0.82
        exp_amt = round(tx.amount * prob, 2)
        delay = 0
    elif tx.failure_code == "INSUFFICIENT_FUNDS":
        strat = "SMART_RETRY" if "SMART_RETRY" in policy.allowed_recovery_strategies else "CHECKOUT_REMINDER"
        dec = "RECOVER"
        conf = 0.88
        prob = 0.75
        exp_amt = round(tx.amount * prob, 2)
        delay = 30 if tx.retry_count == 0 else 120
    elif tx.failure_code == "AUTHENTICATION_FAILED":
        strat = "CHECKOUT_REMINDER" if "CHECKOUT_REMINDER" in policy.allowed_recovery_strategies else "SMART_RETRY"
        dec = "RECOVER"
        conf = 0.82
        prob = 0.65
        exp_amt = round(tx.amount * prob, 2)
        delay = 15
    elif cust.subscription_status in ["active", "past_due"] and cust.previous_success_rate > 0.7:
        strat = "PERSONALIZED_DUNNING" if "PERSONALIZED_DUNNING" in policy.allowed_recovery_strategies else "SMART_RETRY"
        dec = "RECOVER"
        conf = 0.85
        prob = 0.70
        exp_amt = round(tx.amount * prob, 2)
        delay = 60
    else:
        strat = "MANUAL_REVIEW"
        dec = "MANUAL_REVIEW"
        conf = 0.75
        prob = 0.40
        exp_amt = round(tx.amount * prob, 2)
        delay = 0

    return AIDecisionOutput(
        decision=dec,
        strategy=strat,
        confidence=conf,
        recovery_probability=prob,
        expected_recovery_amount=exp_amt,
        reason=f"Recommended {strat} based on failure code '{tx.failure_code}' and customer history.",
        risk_factors=risk.detected_risk_reasons or ["Observed transaction failure"],
        recommended_delay_minutes=delay,
        fallback_strategy="MANUAL_REVIEW"
    )


def call_ai_strategist(context: AIContext) -> AIDecisionOutput:
    """
    Executes the AI Recovery Strategist using Gemini API (server-side only).
    If GEMINI_API_KEY is not configured or network call fails, gracefully uses expert fallback model.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        if os.getenv("STRICT_GEMINI_EVAL", "0") == "1":
            raise RuntimeError("GEMINI_API_KEY is missing while STRICT_GEMINI_EVAL=1")
        logger.info("GEMINI_API_KEY not configured. Using expert fallback AI Strategist.")
        return _generate_fallback_decision(context)

    try:
        import time
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        model_name = getattr(settings, "GEMINI_MODEL", None) or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        user_content = f"CONTEXT DATA:\n{context.model_dump_json(indent=2)}"
        
        max_retries = 20
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=f"{SYSTEM_PROMPT}\n\n{user_content}",
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                raw_json = response.text
                data = json.loads(raw_json)
                if isinstance(data, dict):
                    if "expected_recovery_amount" not in data or data["expected_recovery_amount"] is None:
                        data["expected_recovery_amount"] = 0.0
                    if "recovery_probability" not in data or data["recovery_probability"] is None:
                        data["recovery_probability"] = 0.0
                    if "confidence" not in data or data["confidence"] is None:
                        data["confidence"] = 0.5
                    if "risk_factors" not in data or not isinstance(data["risk_factors"], list):
                        data["risk_factors"] = []
                    if "recommended_delay_minutes" not in data or data["recommended_delay_minutes"] is None:
                        data["recommended_delay_minutes"] = 0
                    if "fallback_strategy" not in data or data["fallback_strategy"] is None:
                        data["fallback_strategy"] = "MANUAL_REVIEW"
                return AIDecisionOutput(**data)
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "Quota exceeded" in err_str or "ResourceExhausted" in err_str) and attempt < max_retries - 1:
                    import re
                    match = re.search(r'retry in (\d+\.?\d*)s', err_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r'seconds:\s*(\d+)', err_str, re.IGNORECASE)
                    if match:
                        sleep_time = float(match.group(1)) + 2.0
                    else:
                        sleep_time = max((2 ** min(attempt, 5)) * 5, 20)
                    msg = f"Rate limited (429)... Retrying in {sleep_time:.1f}s... (Attempt {attempt + 1}/{max_retries})"
                    logger.warning(msg)
                    time.sleep(sleep_time)
                else:
                    if os.getenv("STRICT_GEMINI_EVAL", "0") == "1":
                        raise RuntimeError("Gemini API call failed during STRICT_GEMINI_EVAL") from e
                    logger.warning("Falling back to expert AI Strategist.")
                    return _generate_fallback_decision(context)
    except Exception as e:
        logger.error("Gemini API call failed.")
        if os.getenv("STRICT_GEMINI_EVAL", "0") == "1":
            raise RuntimeError("Gemini API call failed during STRICT_GEMINI_EVAL") from e
        logger.warning("Falling back to expert AI Strategist.")
        return _generate_fallback_decision(context)
