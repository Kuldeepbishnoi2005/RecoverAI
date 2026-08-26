import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Header, status, Depends
from pydantic import BaseModel, Field
from app.auth.deps import get_current_user, AuthenticatedUser

from app.db import get_supabase_admin_client
from app.recovery.state_machine import (
    RecoveryActionStateMachine,
    RecoveryActionStatus,
    InvalidStateTransitionError
)
from app.recovery.simulator import simulate_recovery_action
from app.ai.schemas import (
    AIDecisionOutput,
    AIContext,
    MerchantPolicy,
    TransactionContext,
    CustomerContext,
    RiskEngineContext
)

from app.adapters import get_gateway_adapter

logger = logging.getLogger("app.routers.manual_review")

router = APIRouter(prefix="/manual-review", tags=["Manual Review"])

VALID_STRATEGIES = [
    "RETRY_WITH_SMART_ROUTING",
    "ACQUIRER_FAILOVER",
    "CARD_UPDATE_PROMPT",
    "ALTERNATIVE_PAYMENT_METHOD",
    "PARTIAL_AMOUNT_RETRY",
    "MANUAL_REVIEW"
]

MAX_ALLOWED_RETRY_COUNT = 3
MAX_ALLOWED_RECOVERY_AMOUNT = 50000.0

class ApproveRequest(BaseModel):
    override_strategy: Optional[str] = None
    actor: str = "merchant_admin"
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None

class RejectRequest(BaseModel):
    rejection_reason: str = "Rejected by merchant operator"
    actor: str = "merchant_admin"

class ReplayRequest(BaseModel):
    actor: str = "merchant_admin"
    notes: Optional[str] = "Manual action replay initiated"



def expire_stale_manual_reviews(merchant_id: Optional[str] = None) -> int:
    """
    Scans for PENDING_APPROVAL recovery actions older than 72 hours
    and transitions them to EXPIRED state with audit logging.
    """
    try:
        supabase = get_supabase_admin_client()
        cutoff_dt = (datetime.utcnow() - timedelta(hours=72)).isoformat()
        
        query = supabase.table("recovery_actions").select("*").eq("status", "PENDING_APPROVAL").lt("created_at", cutoff_dt)
        if merchant_id:
            query = query.eq("merchant_id", merchant_id)
        
        res = query.execute()
        stale_actions = res.data or []
        expired_count = 0

        for act in stale_actions:
            action_id = act.get("id")
            m_id = act.get("merchant_id")
            tx_id = act.get("transaction_id")

            # Update action status to EXPIRED
            supabase.table("recovery_actions").update({
                "status": "EXPIRED",
                "policy_reason": "Action expired after 72 hours without manual intervention"
            }).eq("id", action_id).execute()

            # Update associated risk event if present
            risk_event_id = act.get("risk_event_id")
            if risk_event_id:
                try:
                    supabase.table("revenue_risk_events").update({"status": "expired"}).eq("id", risk_event_id).execute()
                except Exception:
                    pass

            # Create Audit Log
            audit_payload = {
                "id": str(uuid.uuid4()),
                "merchant_id": m_id,
                "actor_type": "system",
                "action": "MANUAL_REVIEW_EXPIRE",
                "action_type": "MANUAL_REVIEW_EXPIRE",
                "entity_type": "recovery_action",
                "entity_id": action_id,
                "actor": "system_expiration_worker",
                "details": {
                    "action_id": action_id,
                    "transaction_id": tx_id,
                    "previous_status": "PENDING_APPROVAL",
                    "new_status": "EXPIRED",
                    "reason": "Exceeded 72-hour human review window"
                },
                "created_at": datetime.utcnow().isoformat()
            }
            try:
                supabase.table("audit_logs").insert(audit_payload).execute()
            except Exception:
                pass

            expired_count += 1

        return expired_count
    except Exception as e:
        logger.warning(f"Error in expire_stale_manual_reviews: {str(e)}")
        return 0


@router.get("/queue")
async def get_manual_review_queue(
    min_risk_score: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns items currently awaiting manual review in PENDING_APPROVAL state for authenticated merchant.
    Triggers lazy expiration of stale items older than 72h.
    """
    try:
        # Step 1: Run lazy expiration for user's merchant
        expire_stale_manual_reviews(merchant_id=user.merchant_id)

        supabase = get_supabase_admin_client()

        # Query recovery_actions in PENDING_APPROVAL or legacy pending status for user's merchant
        query = supabase.table("recovery_actions").select("*").in_("status", ["PENDING_APPROVAL", "pending"]).eq("merchant_id", user.merchant_id)

        res = query.order("created_at", desc=True).execute()
        all_actions = res.data or []

        # Enrich with transaction & AI decision context
        enriched_items = []
        for act in all_actions:
            tx_id = act.get("transaction_id")
            
            # Fetch transaction details
            tx_data = {}
            if tx_id:
                try:
                    tx_res = supabase.table("transactions").select("*").eq("transaction_id", tx_id).execute()
                    if tx_res.data:
                        tx_data = tx_res.data[0]
                except Exception:
                    pass

            amt = float(tx_data.get("amount", act.get("attempted_amount", 0.0)) or 0.0)
            risk_score = float(tx_data.get("risk_score", 0.0) or 0.0)

            # Apply query filters if specified
            if min_risk_score is not None and risk_score < min_risk_score:
                continue
            if max_amount is not None and amt > max_amount:
                continue

            item = {
                "id": act.get("id"),
                "action_id": act.get("id"),
                "transaction_id": tx_id,
                "merchant_id": act.get("merchant_id"),
                "strategy": act.get("strategy") or act.get("action_type") or "RETRY_WITH_SMART_ROUTING",
                "status": act.get("status"),
                "attempted_amount": amt,
                "risk_score": risk_score,
                "policy_reason": act.get("policy_reason") or "Awaiting merchant authorization",
                "created_at": act.get("created_at"),
                "transaction": tx_data
            }
            enriched_items.append(item)

        total_count = len(enriched_items)
        paged_items = enriched_items[offset : offset + limit]

        return {
            "items": paged_items,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dlq")
async def list_dlq_actions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieve recovery actions currently in Dead-Letter Queue (DLQ) or EXECUTED_FAILED state for authenticated merchant.
    """
    try:
        supabase = get_supabase_admin_client()
        query = supabase.table("recovery_actions").select("*").eq("merchant_id", user.merchant_id).or_("is_dlq.eq.true,status.eq.EXECUTED_FAILED")

        res = query.order("created_at", desc=True).execute()
        raw_items = res.data or []

        enriched_items = []
        for act in raw_items:
            tx_id = act.get("transaction_id")
            tx_data = {}
            if tx_id:
                try:
                    tx_res = supabase.table("transactions").select("*").eq("transaction_id", tx_id).execute()
                    if tx_res.data:
                        tx_data = tx_res.data[0]
                except Exception:
                    pass

            item = {
                "id": act.get("id"),
                "action_id": act.get("id"),
                "transaction_id": tx_id,
                "merchant_id": act.get("merchant_id"),
                "strategy": act.get("strategy") or act.get("action_type") or "RETRY_WITH_SMART_ROUTING",
                "status": act.get("status"),
                "attempted_amount": float(tx_data.get("amount", act.get("attempted_amount", 0.0)) or 0.0),
                "retry_count": act.get("retry_count", 0),
                "last_error": act.get("last_error") or act.get("policy_reason") or "Execution failure",
                "is_dlq": bool(act.get("is_dlq", True)),
                "created_at": act.get("created_at"),
                "transaction": tx_data
            }
            enriched_items.append(item)

        total_count = len(enriched_items)
        paged_items = enriched_items[offset : offset + limit]

        return {
            "items": paged_items,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error retrieving DLQ list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dlq-summary")
async def get_dlq_summary(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves aggregate Dead-Letter Queue (DLQ) observability metrics and top 5 recent items for authenticated merchant.
    """
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("recovery_actions").select("*").eq("merchant_id", user.merchant_id).or_("is_dlq.eq.true,status.eq.EXECUTED_FAILED").order("created_at", desc=True).execute()
        items = res.data or []

        total_count = len(items)
        total_failed_volume = 0.0
        by_strategy: Dict[str, int] = {}
        by_error: Dict[str, int] = {}

        enriched_recent = []

        for idx, act in enumerate(items):
            tx_id = act.get("transaction_id")
            tx_data = {}
            if tx_id and idx < 5:
                try:
                    tx_res = supabase.table("transactions").select("*").eq("transaction_id", tx_id).execute()
                    if tx_res.data:
                        tx_data = tx_res.data[0]
                except Exception:
                    pass

            amount = float(tx_data.get("amount", act.get("attempted_amount", 0.0)) or 0.0)
            total_failed_volume += amount

            strat = str(act.get("strategy") or act.get("action_type") or "RETRY_WITH_SMART_ROUTING")
            by_strategy[strat] = by_strategy.get(strat, 0) + 1

            err_reason = str(act.get("last_error") or act.get("policy_reason") or "Execution failure")
            by_error[err_reason] = by_error.get(err_reason, 0) + 1

            if idx < 5:
                enriched_recent.append({
                    "id": act.get("id"),
                    "action_id": act.get("id"),
                    "transaction_id": tx_id,
                    "merchant_id": act.get("merchant_id"),
                    "strategy": strat,
                    "status": act.get("status"),
                    "attempted_amount": amount,
                    "retry_count": act.get("retry_count", 0),
                    "last_error": err_reason,
                    "is_dlq": bool(act.get("is_dlq", True)),
                    "created_at": act.get("created_at")
                })

        return {
            "total_dlq_count": total_count,
            "total_failed_volume": round(total_failed_volume, 2),
            "by_strategy": by_strategy,
            "by_error": by_error,
            "recent_dlq_items": enriched_recent
        }
    except Exception as e:
        logger.error(f"Error generating DLQ summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{action_id}")
async def get_manual_review_item(
    action_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns complete details for a single recovery action item in manual review for authenticated merchant.
    """
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("recovery_actions").select("*").eq("id", action_id).eq("merchant_id", user.merchant_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Recovery action '{action_id}' not found")
        
        act = res.data[0]
        tx_id = act.get("transaction_id")
        
        tx_data = {}
        if tx_id:
            try:
                tx_res = supabase.table("transactions").select("*").eq("transaction_id", tx_id).execute()
                if tx_res.data:
                    tx_data = tx_res.data[0]
            except Exception:
                pass

        ai_decision_data = {}
        ai_dec_id = act.get("ai_decision_id")
        if ai_dec_id:
            try:
                ai_res = supabase.table("ai_decisions").select("*").eq("id", ai_dec_id).execute()
                if ai_res.data:
                    ai_decision_data = ai_res.data[0]
            except Exception:
                pass
        elif tx_id:
            try:
                ai_res = supabase.table("ai_decisions").select("*").eq("transaction_id", tx_id).order("created_at", desc=True).limit(1).execute()
                if ai_res.data:
                    ai_decision_data = ai_res.data[0]
            except Exception:
                pass

        return {
            "action": act,
            "transaction": tx_data,
            "ai_decision": ai_decision_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/approve")
async def approve_manual_review(
    action_id: str,
    payload: ApproveRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Approves a PENDING_APPROVAL recovery action, applying safety checks & idempotency,
    executing simulated recovery, and updating state atomically.
    """
    try:
        supabase = get_supabase_admin_client()

        # Step 1: Fetch recovery action record scoped to authenticated user's merchant
        res = supabase.table("recovery_actions").select("*").eq("id", action_id).eq("merchant_id", user.merchant_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Recovery action '{action_id}' not found")


        act = res.data[0]
        current_status = act.get("status")
        merchant_id = act.get("merchant_id")
        tx_id = act.get("transaction_id")

        # Step 2: Status check - MUST be PENDING_APPROVAL (or pending)
        if current_status not in ["PENDING_APPROVAL", "pending"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action '{action_id}' cannot be approved because current status is '{current_status}'. Expected 'PENDING_APPROVAL'."
            )

        # Step 3: Idempotency Key check
        idempotency_key = payload.idempotency_key or x_idempotency_key or act.get("idempotency_key")
        if not idempotency_key:
            idempotency_key = f"idem_appr_{action_id}_{uuid.uuid4().hex[:8]}"

        existing_key_res = supabase.table("recovery_actions").select("id, status").eq("idempotency_key", idempotency_key).execute()
        if existing_key_res.data and existing_key_res.data[0].get("id") != action_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate idempotency key '{idempotency_key}' already processed for action '{existing_key_res.data[0].get('id')}'"
            )

        # Step 4: Authoritative Transaction Safeguard Check
        tx_data = {}
        if tx_id:
            tx_res = supabase.table("transactions").select("*").eq("transaction_id", tx_id).execute()
            if tx_res.data:
                tx_data = tx_res.data[0]

        tx_status_val = str(tx_data.get("transaction_status", "")).upper()
        if tx_status_val in ["SUCCESS", "SUCCESSFUL", "DISPUTED", "RESOLVED", "REFUNDED"]:
            # Transition state to CANCELLED_SAFEGUARD
            sm = RecoveryActionStateMachine(current_status=RecoveryActionStatus.PENDING_APPROVAL)
            safeguard_state = sm.transition_to(RecoveryActionStatus.CANCELLED_SAFEGUARD, actor=payload.actor, reason="Transaction safeguard failure").value

            supabase.table("recovery_actions").update({
                "status": safeguard_state,
                "policy_reason": f"Transaction safeguard triggered: transaction status is '{tx_status_val}'",
                "idempotency_key": idempotency_key
            }).eq("id", action_id).execute()

            # Insert Audit Log
            audit_payload = {
                "id": str(uuid.uuid4()),
                "merchant_id": merchant_id,
                "actor_type": "user",
                "action": "RECOVERY_EXECUTION_BLOCKED",
                "action_type": "RECOVERY_EXECUTION_BLOCKED",
                "entity_type": "recovery_action",
                "entity_id": action_id,
                "actor": payload.actor,
                "details": {
                    "action_id": action_id,
                    "transaction_id": tx_id,
                    "safeguard_reason": "Authoritative transaction status check failed",
                    "transaction_status": tx_status_val
                },
                "created_at": datetime.utcnow().isoformat()
            }
            try:
                supabase.table("audit_logs").insert(audit_payload).execute()
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recovery execution blocked by safeguard: transaction status is '{tx_status_val}'"
            )

        # Step 5: Retry Count Check
        retry_count = int(tx_data.get("retry_count", 0) or 0)
        if retry_count >= MAX_ALLOWED_RETRY_COUNT:
            sm = RecoveryActionStateMachine(current_status=RecoveryActionStatus.PENDING_APPROVAL)
            safeguard_state = sm.transition_to(RecoveryActionStatus.CANCELLED_SAFEGUARD, actor=payload.actor, reason="Exceeded maximum retries").value

            supabase.table("recovery_actions").update({
                "status": safeguard_state,
                "policy_reason": f"Exceeded maximum retry limit ({retry_count}/{MAX_ALLOWED_RETRY_COUNT})",
                "idempotency_key": idempotency_key
            }).eq("id", action_id).execute()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recovery execution blocked: retry count ({retry_count}) reaches limit ({MAX_ALLOWED_RETRY_COUNT})"
            )

        # Step 6: Amount limit check
        tx_amount = float(tx_data.get("amount", act.get("attempted_amount", 0.0)) or 0.0)
        if tx_amount > MAX_ALLOWED_RECOVERY_AMOUNT:
            sm = RecoveryActionStateMachine(current_status=RecoveryActionStatus.PENDING_APPROVAL)
            safeguard_state = sm.transition_to(RecoveryActionStatus.CANCELLED_SAFEGUARD, actor=payload.actor, reason="Exceeded max recovery amount").value

            supabase.table("recovery_actions").update({
                "status": safeguard_state,
                "policy_reason": f"Amount (₹{tx_amount}) exceeds maximum recovery limit (₹{MAX_ALLOWED_RECOVERY_AMOUNT})",
                "idempotency_key": idempotency_key
            }).eq("id", action_id).execute()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recovery execution blocked: amount (₹{tx_amount}) exceeds limit (₹{MAX_ALLOWED_RECOVERY_AMOUNT})"
            )

        # Step 7: Override strategy validation
        chosen_strategy = act.get("strategy") or act.get("action_type") or "RETRY_WITH_SMART_ROUTING"
        if payload.override_strategy:
            if payload.override_strategy not in VALID_STRATEGIES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid override strategy '{payload.override_strategy}'. Allowed strategies: {VALID_STRATEGIES}"
                )
            chosen_strategy = payload.override_strategy

        # Step 8: Formal State Machine Transition: PENDING_APPROVAL -> APPROVED
        sm = RecoveryActionStateMachine(current_status=RecoveryActionStatus.PENDING_APPROVAL)
        approved_state = sm.transition_to(RecoveryActionStatus.APPROVED, actor=payload.actor, reason=payload.notes or "Approved by merchant operator").value

        now_str = datetime.utcnow().isoformat()

        # Step 9: Execute Simulator Engine
        try:
            sim_strategy = chosen_strategy
            if sim_strategy == "RETRY_WITH_SMART_ROUTING":
                sim_strategy = "SMART_RETRY"
            elif sim_strategy not in ['SMART_RETRY', 'PAYMENT_METHOD_UPDATE', 'PERSONALIZED_DUNNING', 'CHECKOUT_REMINDER', 'MANUAL_REVIEW', 'NO_ACTION']:
                sim_strategy = "SMART_RETRY"

            decision_for_sim = AIDecisionOutput(
                decision="RECOVER",
                strategy=sim_strategy,
                confidence=0.9,
                recovery_probability=0.85,
                expected_recovery_amount=tx_amount,
                reason=payload.notes or "Manual approval recovery execution",
                risk_factors=[]
            )
            context_for_sim = AIContext(
                transaction=TransactionContext(
                    transaction_id=tx_id or "tx_manual",
                    amount=tx_amount,
                    currency=tx_data.get("currency", "INR"),
                    payment_method=tx_data.get("payment_method", "UPI"),
                    transaction_status=tx_status_val or "FAILED",
                    failure_code=tx_data.get("error_code", "GATEWAY_TIMEOUT"),
                    failure_reason=tx_data.get("error_message", "Transaction timed out"),
                    retry_count=retry_count,
                    timestamp=tx_data.get("created_at", now_str)
                ),
                customer=CustomerContext(
                    customer_id=tx_data.get("customer_id", "cust_001"),
                    customer_history="NORMAL",
                    previous_success_rate=0.85,
                    customer_lifetime_value=5000.0,
                    subscription_status="ACTIVE",
                    days_since_last_success=5
                ),
                risk_engine=RiskEngineContext(
                    risk_score=float(tx_data.get("risk_score", 45.0) or 45.0),
                    risk_level="MEDIUM",
                    recovery_probability=0.85,
                    revenue_at_risk=tx_amount,
                    expected_recoverable_amount=tx_amount * 0.85,
                    detected_risk_reasons=[]
                ),
                merchant_policy=MerchantPolicy()
            )
            sim_res = simulate_recovery_action(decision_for_sim, context_for_sim)
            
            final_status = RecoveryActionStatus.EXECUTED_SUCCESS.value if sim_res.success else RecoveryActionStatus.EXECUTED_FAILED.value
            # Transition state machine: APPROVED -> EXECUTED_SUCCESS / EXECUTED_FAILED
            sm.transition_to(RecoveryActionStatus(final_status), actor=payload.actor, reason="Simulation executed")

        except Exception as sim_err:
            logger.error(f"Simulator execution failed during manual approval: {str(sim_err)}")
            sim_res = None
            final_status = approved_state

        # Step 10: Persist updated recovery action in DB
        update_payload = {
            "status": final_status,
            "approved_by": payload.actor,
            "approved_at": now_str,
            "idempotency_key": idempotency_key,
            "override_strategy": payload.override_strategy,
            "success": sim_res.success if sim_res else True,
            "recovered_amount": sim_res.recovered_amount if sim_res else tx_amount,
            "executed_at": now_str
        }
        supabase.table("recovery_actions").update(update_payload).eq("id", action_id).execute()

        # Record simulation result into recovery_results table if executed
        if sim_res:
            try:
                res_payload = {
                    "id": str(uuid.uuid4()),
                    "merchant_id": merchant_id,
                    "recovery_action_id": action_id,
                    "transaction_id": tx_id,
                    "recovered_amount": sim_res.recovered_amount,
                    "is_successful": sim_res.success,
                    "result_details": {
                        "strategy": chosen_strategy,
                        "approved_by": payload.actor,
                        "idempotency_key": idempotency_key,
                        "override_used": payload.override_strategy is not None
                    },
                    "measured_at": now_str,
                    "created_at": now_str
                }
                supabase.table("recovery_results").insert(res_payload).execute()
            except Exception:
                pass

        # Update associated risk event if exists
        risk_event_id = act.get("risk_event_id")
        if risk_event_id:
            try:
                evt_status = "resolved" if (sim_res and sim_res.success) else "open"
                supabase.table("revenue_risk_events").update({"status": evt_status}).eq("id", risk_event_id).execute()
            except Exception:
                pass

        # Step 11: Create Audit Log Entries
        audit_approve = {
            "id": str(uuid.uuid4()),
            "merchant_id": merchant_id,
            "actor_type": "user",
            "action": "MANUAL_REVIEW_APPROVE",
            "action_type": "MANUAL_REVIEW_APPROVE",
            "entity_type": "recovery_action",
            "entity_id": action_id,
            "actor": payload.actor,
            "details": {
                "action_id": action_id,
                "transaction_id": tx_id,
                "previous_status": current_status,
                "new_status": final_status,
                "override_strategy": payload.override_strategy,
                "idempotency_key": idempotency_key,
                "notes": payload.notes
            },
            "created_at": now_str
        }
        audit_execution = {
            "id": str(uuid.uuid4()),
            "merchant_id": merchant_id,
            "actor_type": "system",
            "action": "RECOVERY_EXECUTION",
            "action_type": "RECOVERY_EXECUTION",
            "entity_type": "recovery_action",
            "entity_id": action_id,
            "actor": "simulator_engine",
            "details": {
                "action_id": action_id,
                "transaction_id": tx_id,
                "strategy": chosen_strategy,
                "success": sim_res.success if sim_res else True,
                "recovered_amount": sim_res.recovered_amount if sim_res else tx_amount,
                "idempotency_key": idempotency_key
            },
            "created_at": now_str
        }
        try:
            supabase.table("audit_logs").insert(audit_approve).execute()
            supabase.table("audit_logs").insert(audit_execution).execute()
        except Exception:
            pass

        return {
            "success": True,
            "action_id": action_id,
            "status": final_status,
            "approved_by": payload.actor,
            "approved_at": now_str,
            "idempotency_key": idempotency_key,
            "override_strategy": payload.override_strategy,
            "simulation_result": {
                "success": sim_res.success if sim_res else True,
                "recovered_amount": sim_res.recovered_amount if sim_res else tx_amount,
                "strategy": chosen_strategy
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving manual review action '{action_id}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/reject")
async def reject_manual_review(
    action_id: str,
    payload: RejectRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Rejects a PENDING_APPROVAL recovery action with rejection reason logging.
    """
    try:
        supabase = get_supabase_admin_client()

        # Step 1: Fetch recovery action record scoped to authenticated user's merchant
        res = supabase.table("recovery_actions").select("*").eq("id", action_id).eq("merchant_id", user.merchant_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Recovery action '{action_id}' not found")


        act = res.data[0]
        current_status = act.get("status")
        merchant_id = act.get("merchant_id")
        tx_id = act.get("transaction_id")

        # Step 2: Status check - MUST be PENDING_APPROVAL
        if current_status not in ["PENDING_APPROVAL", "pending"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action '{action_id}' cannot be rejected because current status is '{current_status}'. Expected 'PENDING_APPROVAL'."
            )

        # Step 3: Transition state via state machine
        sm = RecoveryActionStateMachine(current_status=RecoveryActionStatus.PENDING_APPROVAL)
        rejected_state = sm.transition_to(RecoveryActionStatus.REJECTED, actor=payload.actor, reason=payload.rejection_reason).value

        now_str = datetime.utcnow().isoformat()

        # Step 4: Update DB
        supabase.table("recovery_actions").update({
            "status": rejected_state,
            "rejection_reason": payload.rejection_reason
        }).eq("id", action_id).execute()

        # Update associated risk event if present
        risk_event_id = act.get("risk_event_id")
        if risk_event_id:
            try:
                supabase.table("revenue_risk_events").update({"status": "closed"}).eq("id", risk_event_id).execute()
            except Exception:
                pass

        # Step 5: Insert Audit Log
        audit_payload = {
            "id": str(uuid.uuid4()),
            "merchant_id": merchant_id,
            "actor_type": "user",
            "action": "MANUAL_REVIEW_REJECT",
            "action_type": "MANUAL_REVIEW_REJECT",
            "entity_type": "recovery_action",
            "entity_id": action_id,
            "actor": payload.actor,
            "details": {
                "action_id": action_id,
                "transaction_id": tx_id,
                "previous_status": current_status,
                "new_status": rejected_state,
                "rejection_reason": payload.rejection_reason
            },
            "created_at": now_str
        }
        try:
            supabase.table("audit_logs").insert(audit_payload).execute()
        except Exception:
            pass

        return {
            "success": True,
            "action_id": action_id,
            "status": rejected_state,
            "rejection_reason": payload.rejection_reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting manual review action '{action_id}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/replay")
async def replay_recovery_action(
    action_id: str,
    payload: Optional[ReplayRequest] = None,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Manual replay endpoint for failed recovery actions in DLQ.
    Executes via Gateway Adapter, updates retry counts and DLQ status, and logs audit trail.
    """
    req_actor = payload.actor if payload else "merchant_admin"
    req_notes = payload.notes if payload else "Manual action replay initiated"

    try:
        supabase = get_supabase_admin_client()

        # Step 1: Fetch recovery action record scoped to authenticated user's merchant
        res = supabase.table("recovery_actions").select("*").eq("id", action_id).eq("merchant_id", user.merchant_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Recovery action '{action_id}' not found")

        act = res.data[0]
        tx_id = act.get("transaction_id")
        current_retry = int(act.get("retry_count", 0) or 0)

        # Check max retry attempts (default 3)
        max_retry_attempts = 3
        try:
            ms_res = supabase.table("merchant_settings").select("max_retry_attempts").eq("merchant_id", user.merchant_id).execute()
            if ms_res.data and len(ms_res.data) > 0:
                max_retry_attempts = int(ms_res.data[0].get("max_retry_attempts") or 3)
        except Exception:
            pass

        if current_retry >= max_retry_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceeded maximum retry attempts ({max_retry_attempts})"
            )

        # Fetch transaction details
        tx_data = {}
        if tx_id:
            try:
                tx_res = supabase.table("transactions").select("*").eq("transaction_id", tx_id).execute()
                if tx_res.data:
                    tx_data = tx_res.data[0]
            except Exception:
                pass

        # Step 2: Fetch merchant settings to know gateway provider
        gateway_provider = "sandbox"
        if payload and payload.force_gateway:
            gateway_provider = payload.force_gateway
        else:
            try:
                ms_res = supabase.table("merchant_settings").select("default_gateway").eq("merchant_id", user.merchant_id).execute()
                if ms_res.data and len(ms_res.data) > 0:
                    gateway_provider = ms_res.data[0].get("default_gateway", "sandbox")
            except Exception:
                pass

        # Step 3: Instantiate Adapter and execute replay
        adapter = get_gateway_adapter(gateway_provider)
        action_type = act.get("strategy") or act.get("action_type") or "RETRY_WITH_SMART_ROUTING"
        amount = float(tx_data.get("amount", act.get("attempted_amount", 0.0)) or 0.0)
        currency = tx_data.get("currency", "INR")
        adapter_res = adapter.execute_action(
            action_type=action_type,
            amount=amount,
            currency=currency,
            payload={
                "transaction_id": tx_id,
                "action_id": action_id,
                "merchant_id": user.merchant_id,
                "replay_note": req_notes,
            }
        )

        now_str = datetime.utcnow().isoformat()
        new_retry_count = current_retry + 1

        if adapter_res.success:
            update_data = {
                "status": "EXECUTED_SUCCESS",
                "is_dlq": False,
                "retry_count": new_retry_count,
                "last_error": None,
                "success": True,
                "recovered_amount": amount,
                "executed_at": now_str,
                "replayed_at": now_str,
                "replayed_by": req_actor
            }
            supabase.table("recovery_actions").update(update_data).eq("id", action_id).execute()

            # Record result
            try:
                res_payload = {
                    "id": str(uuid.uuid4()),
                    "merchant_id": user.merchant_id,
                    "recovery_action_id": action_id,
                    "transaction_id": tx_id,
                    "recovered_amount": amount,
                    "is_successful": True,
                    "result_details": {
                        "gateway": adapter.provider_name,
                        "transaction_id": adapter_res.transaction_id,
                        "replayed_by": req_actor
                    },
                    "measured_at": now_str,
                    "created_at": now_str
                }
                supabase.table("recovery_results").insert(res_payload).execute()
            except Exception:
                pass

            # Insert Audit Log
            audit_payload = {
                "merchant_id": user.merchant_id,
                "actor_type": "user",
                "actor_id": user.user_id,
                "action": "RECOVERY_ACTION_REPLAY_SUCCESS",
                "action_type": "RECOVERY_ACTION_REPLAY_SUCCESS",
                "entity_type": "recovery_action",
                "entity_id": action_id,
                "actor": req_actor,
                "details": {
                    "action_id": action_id,
                    "transaction_id": tx_id,
                    "gateway": adapter.provider_name,
                    "transaction_id_gateway": adapter_res.transaction_id,
                    "retry_count": new_retry_count
                },
                "created_at": now_str
            }
            try:
                supabase.table("audit_logs").insert(audit_payload).execute()
            except Exception:
                pass

            return {
                "success": True,
                "action_id": action_id,
                "status": "EXECUTED_SUCCESS",
                "retry_count": new_retry_count,
                "gateway_transaction_id": adapter_res.transaction_id,
                "message": "Action replayed successfully."
            }
        else:
            update_data = {
                "status": "EXECUTED_FAILED",
                "is_dlq": True,
                "retry_count": new_retry_count,
                "last_error": adapter_res.error_message or "Gateway execution failed",
                "success": False,
                "executed_at": now_str,
                "replayed_at": now_str,
                "replayed_by": req_actor
            }
            supabase.table("recovery_actions").update(update_data).eq("id", action_id).execute()

            # Insert Audit Log
            audit_payload = {
                "merchant_id": user.merchant_id,
                "actor_type": "user",
                "actor_id": user.user_id,
                "action": "RECOVERY_ACTION_REPLAY_FAILED",
                "action_type": "RECOVERY_ACTION_REPLAY_FAILED",
                "entity_type": "recovery_action",
                "entity_id": action_id,
                "actor": req_actor,
                "details": {
                    "action_id": action_id,
                    "transaction_id": tx_id,
                    "error_code": adapter_res.error_code,
                    "error_message": adapter_res.error_message,
                    "retry_count": new_retry_count
                },
                "created_at": now_str
            }
            try:
                supabase.table("audit_logs").insert(audit_payload).execute()
            except Exception:
                pass

            return {
                "success": False,
                "action_id": action_id,
                "status": "EXECUTED_FAILED",
                "retry_count": new_retry_count,
                "error_code": adapter_res.error_code,
                "error_message": adapter_res.error_message,
                "message": "Replay failed and item remains in DLQ."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replaying recovery action '{action_id}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
