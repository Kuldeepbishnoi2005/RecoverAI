"""
Resilient Gateway Executor
Orchestrates primary and fallback gateway executions with strict safety matrix and idempotency protection.
"""
import logging
from typing import Dict, Any, Optional
from app.adapters.base import (
    BaseGatewayAdapter,
    AdapterExecutionResult,
    ExecutionState,
    ErrorClassification,
)
from app.adapters.factory import get_gateway_adapter

logger = logging.getLogger(__name__)


class ResilientGatewayExecutor:
    """
    Executes payment actions across primary and backup gateways.
    Enforces safe fallback rules:
    - Fallback ONLY allowed when primary fails with TRANSIENT error AND CONFIRMED_NOT_EXECUTED state.
    - UNKNOWN state strictly BLOCKS fallback to prevent double-charging.
    - Deterministic, scoped idempotency keys for both attempts.
    """

    def execute_with_fallback(
        self,
        action_type: str,
        amount: float,
        currency: str,
        primary_provider: str = "sandbox",
        backup_provider: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        action_id: Optional[str] = None,
        retry_count: int = 1,
    ) -> AdapterExecutionResult:
        payload_data = dict(payload or {})
        act_id_str = action_id or payload_data.get("action_id") or "anon"
        retry_cnt = retry_count or payload_data.get("retry_count") or 1

        # 1. Primary Gateway Attempt
        primary_adapter = get_gateway_adapter(primary_provider)
        primary_idem_key = f"idem_{act_id_str}_primary_{retry_cnt}_{primary_adapter.provider_name}"
        primary_payload = dict(payload_data)
        primary_payload["idempotency_key"] = primary_idem_key

        logger.info(
            f"Executing primary gateway attempt ({primary_adapter.provider_name}) "
            f"for action '{act_id_str}' (retry {retry_cnt}) with key '{primary_idem_key}'"
        )
        primary_res = primary_adapter.execute_action(
            action_type=action_type,
            amount=amount,
            currency=currency,
            payload=primary_payload,
        )

        if primary_res.success:
            logger.info(f"Primary gateway attempt succeeded for action '{act_id_str}'")
            return primary_res

        # Primary failed. Evaluate safety conditions for fallback.
        logger.warning(
            f"Primary gateway ({primary_adapter.provider_name}) failed for action '{act_id_str}'. "
            f"ExecutionState: {primary_res.execution_state.value}, "
            f"ErrorClassification: {primary_res.error_classification.value}"
        )

        # Mandatory Safety Rule 1: Block fallback if execution state is UNKNOWN
        if primary_res.execution_state == ExecutionState.UNKNOWN:
            logger.error(
                f"Fallback BLOCKED for action '{act_id_str}': Primary execution state is UNKNOWN. "
                f"Automatic failover prevented to avoid potential double charging."
            )
            if primary_res.gateway_response is None:
                primary_res.gateway_response = {}
            primary_res.gateway_response["fallback_blocked_reason"] = "UNKNOWN_EXECUTION_STATE"
            return primary_res

        # Mandatory Safety Rule 2: Fallback permitted ONLY if TRANSIENT error and CONFIRMED_NOT_EXECUTED
        can_fallback = (
            primary_res.error_classification == ErrorClassification.TRANSIENT
            and primary_res.execution_state == ExecutionState.CONFIRMED_NOT_EXECUTED
        )

        if not can_fallback:
            logger.info(
                f"Fallback NOT attempted for action '{act_id_str}': Conditions not met "
                f"(requires TRANSIENT + CONFIRMED_NOT_EXECUTED). Skipping backup gateway."
            )
            return primary_res

        # Check if backup provider is configured and distinct
        if not backup_provider or backup_provider.lower().strip() == primary_adapter.provider_name.lower().strip():
            logger.info(
                f"Fallback conditions met for action '{act_id_str}', but no distinct backup provider specified. "
                f"Returning primary failure result."
            )
            return primary_res

        # 2. Backup Gateway Attempt
        backup_adapter = get_gateway_adapter(backup_provider)
        backup_idem_key = f"idem_{act_id_str}_backup_{retry_cnt}_{backup_adapter.provider_name}"
        backup_payload = dict(payload_data)
        backup_payload["idempotency_key"] = backup_idem_key
        backup_payload["primary_attempt"] = {
            "gateway": primary_adapter.provider_name,
            "error_code": primary_res.error_code,
            "error_message": primary_res.error_message,
            "execution_state": primary_res.execution_state.value,
            "error_classification": primary_res.error_classification.value,
        }

        logger.info(
            f"Executing backup gateway attempt ({backup_adapter.provider_name}) "
            f"for action '{act_id_str}' (retry {retry_cnt}) with key '{backup_idem_key}'"
        )
        backup_res = backup_adapter.execute_action(
            action_type=action_type,
            amount=amount,
            currency=currency,
            payload=backup_payload,
        )

        if backup_res.gateway_response is None:
            backup_res.gateway_response = {}
        backup_res.gateway_response["fallback_executed"] = True
        backup_res.gateway_response["primary_gateway"] = primary_adapter.provider_name

        if backup_res.success:
            logger.info(f"Backup gateway attempt ({backup_adapter.provider_name}) succeeded for action '{act_id_str}'")
        else:
            logger.warning(f"Backup gateway attempt ({backup_adapter.provider_name}) also failed for action '{act_id_str}'")

        return backup_res
