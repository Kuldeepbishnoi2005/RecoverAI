"""
Sandbox Simulator Gateway Adapter
Simulates payment gateway recovery executions without real financial transactions.
"""
import hmac
import hashlib
import uuid
import time
from typing import Dict, Any, Optional
from app.adapters.base import BaseGatewayAdapter, AdapterExecutionResult, ExecutionState, ErrorClassification


class SandboxSimulatorAdapter(BaseGatewayAdapter):
    """Sandbox simulator adapter for zero-risk recovery execution testing."""

    @property
    def provider_name(self) -> str:
        return "sandbox"

    def execute_action(
        self,
        action_type: str,
        amount: float,
        currency: str,
        payload: Dict[str, Any],
        merchant_settings: Optional[Dict[str, Any]] = None,
    ) -> AdapterExecutionResult:
        """
        Executes simulated recovery action.
        Allows testing failure & retry scenarios via payload parameters:
        - simulate_failure: bool
        - simulate_retryable: bool
        - simulate_execution_state: str | ExecutionState
        - simulate_error_classification: str | ErrorClassification
        - error_code: str
        - error_message: str
        """
        is_backup = "primary_attempt" in payload
        if is_backup and payload.get("simulate_primary_failure"):
            simulate_failure = payload.get("simulate_backup_failure", False)
        else:
            simulate_failure = payload.get("simulate_failure", False) or payload.get("simulate_primary_failure", False)

        simulate_retryable = payload.get("simulate_retryable", False)

        exec_state_raw = payload.get("simulate_execution_state")
        if isinstance(exec_state_raw, ExecutionState):
            exec_state = exec_state_raw
        elif exec_state_raw:
            try:
                exec_state = ExecutionState(str(exec_state_raw).upper())
            except ValueError:
                exec_state = ExecutionState.UNKNOWN
        else:
            exec_state = ExecutionState.CONFIRMED_NOT_EXECUTED if simulate_failure else ExecutionState.CONFIRMED_EXECUTED

        err_class_raw = payload.get("simulate_error_classification")
        if isinstance(err_class_raw, ErrorClassification):
            err_class = err_class_raw
        elif err_class_raw:
            try:
                err_class = ErrorClassification(str(err_class_raw).upper())
            except ValueError:
                err_class = ErrorClassification.UNKNOWN
        else:
            if not simulate_failure:
                err_class = ErrorClassification.NONE
            else:
                err_class = ErrorClassification.TRANSIENT if simulate_retryable else ErrorClassification.PERMANENT

        if simulate_failure:
            return AdapterExecutionResult(
                success=False,
                transaction_id=None,
                gateway_response={
                    "status": "failed",
                    "mode": "sandbox_simulation",
                    "action_type": action_type,
                    "amount": amount,
                    "currency": currency,
                    "timestamp": time.time(),
                },
                error_code=payload.get("error_code", "SIMULATED_GATEWAY_DECLINE"),
                error_message=payload.get("error_message", "Simulated card decline or gateway error in sandbox."),
                retryable=simulate_retryable,
                execution_state=exec_state,
                error_classification=err_class,
            )

        # Successful execution simulation
        tx_id = f"sb_tx_{uuid.uuid4().hex[:12]}"
        return AdapterExecutionResult(
            success=True,
            transaction_id=tx_id,
            gateway_response={
                "status": "succeeded",
                "mode": "sandbox_simulation",
                "transaction_id": tx_id,
                "action_type": action_type,
                "amount": amount,
                "currency": currency,
                "timestamp": time.time(),
                "details": f"Simulated {action_type} of {amount} {currency} completed successfully.",
            },
            error_code=None,
            error_message=None,
            retryable=False,
            execution_state=ExecutionState.CONFIRMED_EXECUTED,
            error_classification=ErrorClassification.NONE,
        )

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
        webhook_secret: str,
    ) -> bool:
        """
        Verifies HMAC-SHA256 signature for sandbox webhooks.
        Expected signature format:
        Header: t=<timestamp>,v1=<signature> or raw hex digest string.
        """
        if not signature_header or not webhook_secret:
            return False

        try:
            # Parse header format t=...,v1=... if present
            sig_to_compare = signature_header
            if "v1=" in signature_header:
                parts = signature_header.split(",")
                for part in parts:
                    if part.strip().startswith("v1="):
                        sig_to_compare = part.strip()[3:]
                        break

            # Calculate expected HMAC-SHA256
            expected_hmac = hmac.new(
                webhook_secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_hmac.lower(), sig_to_compare.lower())
        except Exception:
            return False
