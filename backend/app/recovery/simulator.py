import uuid
import random
from datetime import datetime
from app.ai.schemas import AIContext, AIDecisionOutput, SimulationResult

def simulate_recovery_action(
    decision: AIDecisionOutput,
    context: AIContext
) -> SimulationResult:
    """
    Simulates recovery action execution deterministically based on context & strategy.
    
    IMPORTANT:
    This is a SIMULATED recovery action engine.
    NO REAL PAYMENTS are executed.
    Results are strictly labeled execution_status = 'SIMULATED'.
    Does NOT guarantee 100% success (has realistic failures).
    """
    tx = context.transaction
    cust = context.customer
    strategy = decision.strategy
    amount = tx.amount
    action_id = f"sim_act_{uuid.uuid4().hex[:12]}"
    now_str = datetime.utcnow().isoformat()

    # Manual Review / No Action -> No attempt executed
    if strategy in ["MANUAL_REVIEW", "NO_ACTION"]:
        return SimulationResult(
            action_id=action_id,
            transaction_id=tx.transaction_id,
            strategy=strategy,
            execution_status="SIMULATED",
            success=False,
            recovered_amount=0.0,
            attempted_amount=0.0,
            execution_timestamp=now_str,
            failure_reason=f"Execution skipped for {strategy} strategy."
        )

    # Use a deterministic seed per transaction + strategy to ensure consistent reproducible simulation
    seed_val = hash(f"{tx.transaction_id}_{strategy}_{tx.retry_count}") % (2**31 - 1)
    rng = random.Random(seed_val)

    # Strategy-specific realistic success probabilities
    base_probability = context.risk_engine.recovery_probability

    if strategy == "SMART_RETRY":
        if tx.failure_code == "INSUFFICIENT_FUNDS":
            # Smart retry after delay works well for temporary liquidity
            sim_success_prob = min(0.85, base_probability + 0.10)
        elif tx.failure_code in ["EXPIRED_CARD", "INVALID_CARD"]:
            # Smart retry without updated card fails frequently
            sim_success_prob = 0.15
        else:
            sim_success_prob = base_probability
    elif strategy == "PAYMENT_METHOD_UPDATE":
        if tx.failure_code in ["EXPIRED_CARD", "INVALID_CARD"]:
            sim_success_prob = 0.88
        else:
            sim_success_prob = 0.70
    elif strategy == "PERSONALIZED_DUNNING":
        if cust.subscription_status in ["active", "past_due"]:
            sim_success_prob = 0.80
        else:
            sim_success_prob = 0.50
    elif strategy == "CHECKOUT_REMINDER":
        if tx.failure_code in ["AUTHENTICATION_FAILED", "USER_ABANDONED"]:
            sim_success_prob = 0.75
        else:
            sim_success_prob = 0.45
    else:
        sim_success_prob = 0.50

    # Penalize based on retry count
    if tx.retry_count > 1:
        sim_success_prob *= (0.85 ** tx.retry_count)

    # Roll simulation result deterministically
    roll = rng.random()
    is_success = roll < sim_success_prob

    if is_success:
        recovered = amount
        fail_reason = None
    else:
        recovered = 0.0
        fail_reason = f"Simulated bank response: Declined during {strategy} (rule roll {roll:.2f} >= {sim_success_prob:.2f})."

    return SimulationResult(
        action_id=action_id,
        transaction_id=tx.transaction_id,
        strategy=strategy,
        execution_status="SIMULATED",
        success=is_success,
        recovered_amount=recovered,
        attempted_amount=amount,
        execution_timestamp=now_str,
        failure_reason=fail_reason
    )
