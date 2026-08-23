import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.db import get_supabase_admin_client
from app.ai.schemas import (
    MerchantPolicy,
    PipelineResult,
    AIDecisionOutput,
    PolicyResult,
    SimulationResult
)
from app.ai.context_builder import build_ai_context
from app.ai.recovery_strategist import call_ai_strategist
from app.ai.decision_validator import validate_ai_decision
from app.ai.policy_controller import evaluate_policy
from app.recovery.simulator import simulate_recovery_action

logger = logging.getLogger("app.services.recovery_pipeline")


def _persist_pipeline_records(
    pipeline_run_id: str,
    transaction: Dict[str, Any],
    ai_decision: AIDecisionOutput,
    policy_res: PolicyResult,
    sim_res: Optional[SimulationResult]
) -> None:
    """
    Persists AI Decision, Simulation Result, and Audit Log to Supabase.
    Gracefully catches DB exceptions so offline/unseeded DB operation never crashes.
    """
    try:
        supabase = get_supabase_admin_client()
        now_str = datetime.utcnow().isoformat()
        tx_id = str(transaction.get("transaction_id", ""))
        raw_m_id = str(transaction.get("merchant_id", "merchant_001"))
        try:
            merchant_id = str(uuid.UUID(raw_m_id))
        except ValueError:
            merchant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_m_id))

        # 1. Insert into ai_decisions table
        ai_decision_payload = {
            "id": str(uuid.uuid4()),
            "transaction_id": tx_id,
            "merchant_id": merchant_id,
            "decision": ai_decision.decision,
            "strategy": ai_decision.strategy,
            "confidence": float(ai_decision.confidence),
            "recovery_probability": float(ai_decision.recovery_probability),
            "expected_recovery_amount": float(ai_decision.expected_recovery_amount),
            "reasoning": ai_decision.reason,
            "risk_factors": ai_decision.risk_factors,
            "policy_result": policy_res.model_dump(),
            "pipeline_run_id": pipeline_run_id,
            "created_at": now_str
        }
        supabase.table("ai_decisions").insert(ai_decision_payload).execute()

        # 2. Insert recovery action record
        if sim_res:
            try:
                action_id_uuid = str(uuid.UUID(sim_res.action_id))
            except ValueError:
                action_id_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, sim_res.action_id))

            action_payload = {
                "id": action_id_uuid,
                "transaction_id": tx_id,
                "merchant_id": merchant_id,
                "strategy": sim_res.strategy,
                "action_type": sim_res.strategy,
                "status": "SIMULATED",
                "success": sim_res.success,
                "attempted_amount": sim_res.attempted_amount,
                "recovered_amount": sim_res.recovered_amount,
                "pipeline_run_id": pipeline_run_id,
                "created_at": sim_res.execution_timestamp
            }
            supabase.table("recovery_actions").insert(action_payload).execute()

            result_payload = {
                "id": str(uuid.uuid4()),
                "merchant_id": merchant_id,
                "recovery_action_id": action_id_uuid,
                "transaction_id": tx_id,
                "pipeline_run_id": pipeline_run_id,
                "recovered_amount": sim_res.recovered_amount,
                "is_successful": sim_res.success,
                "result_details": {
                    "strategy": sim_res.strategy,
                    "simulated": True,
                    "attempted_amount": sim_res.attempted_amount
                },
                "measured_at": sim_res.execution_timestamp,
                "created_at": sim_res.execution_timestamp
            }
            supabase.table("recovery_results").insert(result_payload).execute()
        elif policy_res.requires_human_approval or ai_decision.decision == "MANUAL_REVIEW":
            action_id_uuid = str(uuid.uuid4())
            action_payload = {
                "id": action_id_uuid,
                "transaction_id": tx_id,
                "merchant_id": merchant_id,
                "strategy": ai_decision.strategy if ai_decision.strategy != "MANUAL_REVIEW" else "RETRY_WITH_SMART_ROUTING",
                "action_type": ai_decision.strategy if ai_decision.strategy != "MANUAL_REVIEW" else "RETRY_WITH_SMART_ROUTING",
                "status": "PENDING_APPROVAL",
                "policy_reason": policy_res.reason,
                "attempted_amount": float(transaction.get("amount", 0.0) or 0.0),
                "pipeline_run_id": pipeline_run_id,
                "created_at": now_str
            }
            supabase.table("recovery_actions").insert(action_payload).execute()
        else:
            action_id_uuid = str(uuid.uuid4())
            action_payload = {
                "id": action_id_uuid,
                "transaction_id": tx_id,
                "merchant_id": merchant_id,
                "strategy": ai_decision.strategy,
                "action_type": ai_decision.strategy,
                "status": "CANCELLED_SAFEGUARD",
                "policy_reason": policy_res.reason,
                "attempted_amount": float(transaction.get("amount", 0.0) or 0.0),
                "pipeline_run_id": pipeline_run_id,
                "created_at": now_str
            }
            supabase.table("recovery_actions").insert(action_payload).execute()

        try:
            entity_id_val = str(uuid.UUID(tx_id))
        except ValueError:
            entity_id_val = str(uuid.uuid5(uuid.NAMESPACE_DNS, tx_id))

        # 3. Create Audit Log Entry
        audit_payload = {
            "id": str(uuid.uuid4()),
            "merchant_id": merchant_id,
            "actor_type": "system",
            "action": "AI_RECOVERY_DECISION",
            "action_type": "AI_RECOVERY_DECISION",
            "entity_type": "transaction",
            "entity_id": entity_id_val,
            "actor": "RecoverAI_Strategist",
            "details": {
                "pipeline_run_id": pipeline_run_id,
                "decision": ai_decision.decision,
                "strategy": ai_decision.strategy,
                "confidence": ai_decision.confidence,
                "policy_allowed": policy_res.allowed,
                "policy_reason": policy_res.reason,
                "simulation_success": sim_res.success if sim_res else False,
                "recovered_amount": sim_res.recovered_amount if sim_res else 0.0
            },
            "created_at": now_str
        }
        supabase.table("audit_logs").insert(audit_payload).execute()

    except Exception as e:
        logger.warning(f"Failed to persist pipeline run '{pipeline_run_id}' to database: {str(e)}")


def run_recovery_pipeline(
    transaction: Dict[str, Any],
    merchant_policy: Optional[MerchantPolicy] = None
) -> PipelineResult:
    """
    Executes the complete, traceable RecoverAI Decision & Execution Pipeline.
    
    1. Load/Build AI Context
    2. Call AI Strategist
    3. Validate AI Output (Decision Validator)
    4. Run Governance Policy Controller
    5. Execute SIMULATED Recovery Action (if allowed)
    6. Audit & Database Persistence
    """
    pipeline_run_id = f"pipe_run_{uuid.uuid4().hex[:12]}"
    now_str = datetime.utcnow().isoformat()
    merchant_id = str(transaction.get("merchant_id", "merchant_001"))
    tx_id = str(transaction.get("transaction_id", ""))

    # Step 1: Build Context (Strictly observable data, no ground truth)
    context = build_ai_context(transaction, merchant_policy)

    # Step 2: Call AI Strategist (Server-side Gemini with expert fallback)
    raw_ai_decision = call_ai_strategist(context)

    # Step 3: Validate AI Output
    validated_decision, is_valid, validation_errors = validate_ai_decision(raw_ai_decision, context)
    validation_status = "PASSED" if is_valid else "FAILED"

    # Step 4: Governance Policy Controller
    policy_res = evaluate_policy(validated_decision, context)

    # Step 5: Simulated Recovery Execution (Only if policy allows)
    sim_res: Optional[SimulationResult] = None
    if policy_res.allowed:
        sim_res = simulate_recovery_action(validated_decision, context)

    # Step 6: Database Persistence & Audit Log
    _persist_pipeline_records(pipeline_run_id, transaction, validated_decision, policy_res, sim_res)

    # Step 7: Return Complete Pipeline Result
    return PipelineResult(
        pipeline_run_id=pipeline_run_id,
        transaction_id=tx_id,
        merchant_id=merchant_id,
        context=context,
        ai_decision=validated_decision,
        validation_status=validation_status,
        validation_errors=validation_errors,
        policy_result=policy_res,
        simulation_result=sim_res,
        created_at=now_str
    )
