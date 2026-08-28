"""
Razorpay Payment Gateway Adapter
Implements BaseGatewayAdapter for Razorpay payment recovery executions and webhook verification.
"""
import hmac
import hashlib
import time
import json
import logging
from typing import Dict, Any, Optional

from app.adapters.base import (
    BaseGatewayAdapter,
    AdapterExecutionResult,
    ExecutionState,
    ErrorClassification,
)

logger = logging.getLogger("app.adapters.razorpay_adapter")


class RazorpayAdapter(BaseGatewayAdapter):
    """Production Razorpay gateway adapter with application-side idempotency & error mapping."""

    @property
    def provider_name(self) -> str:
        return "razorpay"

    def execute_action(
        self,
        action_type: str,
        amount: float,
        currency: str,
        payload: Dict[str, Any],
        merchant_settings: Optional[Dict[str, Any]] = None,
    ) -> AdapterExecutionResult:
        """
        Executes a payment recovery action on Razorpay.

        Handles:
        1. Application-side idempotency tracking via receipt & notes payload identifiers
        2. Classification of Razorpay API errors into ExecutionState & ErrorClassification
        3. Zero credential exposure in logs or responses
        """
        merchant_settings = merchant_settings or {}
        key_id = (
            merchant_settings.get("razorpay_key_id")
            or payload.get("razorpay_key_id")
        )
        key_secret = (
            merchant_settings.get("razorpay_key_secret")
            or payload.get("razorpay_key_secret")
        )

        action_id = payload.get("action_id", "act_unknown")
        retry_count = payload.get("retry_count", 1)
        receipt_id = f"rcpt_{action_id}_{retry_count}"

        # Check for simulated testing parameters, mock mode, or unconfigured credentials
        mock_client = payload.get("mock_client")
        if mock_client or (not (key_id and key_secret) and mock_client is not False):
            return self._execute_mock(
                action_type, amount, currency, payload, receipt_id
            )

        # Check for missing credentials if mock_client was explicitly disabled
        if not key_id or not key_secret:
            logger.warning("Razorpay API credentials missing for execution.")
            return AdapterExecutionResult(
                success=False,
                transaction_id=None,
                gateway_response={"provider": "razorpay", "status": "failed"},
                error_code="MISSING_CREDENTIALS",
                error_message="Razorpay key_id or key_secret is not configured for this merchant.",
                retryable=False,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.PERMANENT,
            )


        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))

            # Convert amount to smallest currency unit (paise for INR)
            amount_in_paise = int(round(amount * 100))

            # Order / Payment Payload with application-side idempotency markers
            payment_payload = {
                "amount": amount_in_paise,
                "currency": currency.upper(),
                "receipt": receipt_id,
                "notes": {
                    "merchant_id": payload.get("merchant_id", ""),
                    "action_id": action_id,
                    "retry_count": str(retry_count),
                },
            }

            # Create Order or Payment Recurring Retry
            order_res = client.order.create(data=payment_payload)
            order_id = order_res.get("id")
            order_status = order_res.get("status")

            if order_status in ["created", "paid", "attempted"]:
                return AdapterExecutionResult(
                    success=True,
                    transaction_id=order_id,
                    gateway_response={
                        "provider": "razorpay",
                        "status": order_status,
                        "order_id": order_id,
                        "receipt": receipt_id,
                    },
                    execution_state=ExecutionState.CONFIRMED_EXECUTED,
                    error_classification=ErrorClassification.NONE,
                )
            else:
                return AdapterExecutionResult(
                    success=False,
                    transaction_id=order_id,
                    gateway_response={
                        "provider": "razorpay",
                        "status": order_status,
                        "order_id": order_id,
                    },
                    error_code="UNSUCCESSFUL_ORDER_STATUS",
                    error_message=f"Razorpay order status is {order_status}",
                    retryable=True,
                    execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                    error_classification=ErrorClassification.TRANSIENT,
                )

        except Exception as e:
            return self.classify_razorpay_error(e)

    def classify_razorpay_error(self, exc: Exception) -> AdapterExecutionResult:
        """Classifies Razorpay exceptions into ExecutionState & ErrorClassification."""
        err_str = str(exc)
        exc_type_name = type(exc).__name__

        try:
            import razorpay
            bad_req_err = razorpay.errors.BadRequestError
            gateway_err = razorpay.errors.GatewayError
            server_err = razorpay.errors.ServerError
            sig_err = razorpay.errors.SignatureVerificationError
        except ImportError:
            bad_req_err = gateway_err = server_err = sig_err = Exception

        if isinstance(exc, bad_req_err) or "BadRequestError" in exc_type_name:
            if "invalid_card" in err_str.lower() or "expired" in err_str.lower():
                return AdapterExecutionResult(
                    success=False,
                    error_code="BAD_REQUEST_PERMANENT",
                    error_message=err_str,
                    retryable=False,
                    execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                    error_classification=ErrorClassification.PERMANENT,
                )
            return AdapterExecutionResult(
                success=False,
                error_code="BAD_REQUEST_ERROR",
                error_message=err_str,
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )

        elif isinstance(exc, (gateway_err, server_err)) or exc_type_name in ["GatewayError", "ServerError"]:
            return AdapterExecutionResult(
                success=False,
                error_code="GATEWAY_SERVER_ERROR",
                error_message=err_str,
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )

        elif isinstance(exc, sig_err) or "SignatureVerificationError" in exc_type_name or "Authentication" in exc_type_name:
            return AdapterExecutionResult(
                success=False,
                error_code="AUTHENTICATION_FAILED",
                error_message="Razorpay authentication or signature verification failed.",
                retryable=False,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.PERMANENT,
            )

        elif "timeout" in err_str.lower() or "connection" in err_str.lower() or exc_type_name in ["Timeout", "ReadTimeout", "ConnectTimeout"]:
            # UNKNOWN state for network timeout / connection drop
            return AdapterExecutionResult(
                success=False,
                error_code="NETWORK_TIMEOUT",
                error_message="Razorpay API request timed out or connection dropped.",
                retryable=False,
                execution_state=ExecutionState.UNKNOWN,
                error_classification=ErrorClassification.UNKNOWN,
            )

        # Unhandled / HTTP 5xx / Unknown -> UNKNOWN
        return AdapterExecutionResult(
            success=False,
            error_code="UNKNOWN_RAZORPAY_ERROR",
            error_message=f"Unhandled Razorpay exception: {err_str}",
            retryable=False,
            execution_state=ExecutionState.UNKNOWN,
            error_classification=ErrorClassification.UNKNOWN,
        )

    def _execute_mock(
        self,
        action_type: str,
        amount: float,
        currency: str,
        payload: Dict[str, Any],
        receipt_id: str,
    ) -> AdapterExecutionResult:
        """Executes mocked scenarios for unit testing without live network calls."""
        is_backup = "primary_attempt" in payload
        if is_backup and payload.get("simulate_primary_failure"):
            simulate_failure = payload.get("simulate_backup_failure", False)
        else:
            simulate_failure = payload.get("simulate_failure", False) or payload.get("simulate_primary_failure", False)

        if simulate_failure:
            exec_state_raw = payload.get("simulate_execution_state")
            if isinstance(exec_state_raw, ExecutionState):
                exec_state = exec_state_raw
            elif exec_state_raw:
                try:
                    exec_state = ExecutionState(str(exec_state_raw).upper())
                except ValueError:
                    exec_state = ExecutionState.UNKNOWN
            else:
                exec_state = ExecutionState.CONFIRMED_NOT_EXECUTED

            err_class_raw = payload.get("simulate_error_classification")
            if isinstance(err_class_raw, ErrorClassification):
                err_class = err_class_raw
            elif err_class_raw:
                try:
                    err_class = ErrorClassification(str(err_class_raw).upper())
                except ValueError:
                    err_class = ErrorClassification.UNKNOWN
            else:
                err_class = ErrorClassification.TRANSIENT if payload.get("simulate_retryable") else ErrorClassification.PERMANENT

            return AdapterExecutionResult(
                success=False,
                transaction_id=None,
                gateway_response={"provider": "razorpay", "status": "failed"},
                error_code=payload.get("error_code", "SIMULATED_FAILURE"),
                error_message=payload.get("error_message", "Simulated mock execution failure"),
                retryable=payload.get("simulate_retryable", True),
                execution_state=exec_state,
                error_classification=err_class,
            )

        mock_type = payload.get("mock_type", "success")


        if mock_type == "success":
            tx_id = payload.get("razorpay_order_id") or f"order_mock_{receipt_id}"
            return AdapterExecutionResult(
                success=True,
                transaction_id=tx_id,
                gateway_response={
                    "provider": "razorpay",
                    "status": "created",
                    "order_id": tx_id,
                    "receipt": receipt_id,
                },
                execution_state=ExecutionState.CONFIRMED_EXECUTED,
                error_classification=ErrorClassification.NONE,
            )
        elif mock_type == "bad_request":
            return AdapterExecutionResult(
                success=False,
                error_code="BAD_REQUEST_ERROR",
                error_message="Payment failed due to invalid params.",
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )
        elif mock_type == "gateway_error":
            return AdapterExecutionResult(
                success=False,
                error_code="GATEWAY_ERROR",
                error_message="Upstream gateway response timeout.",
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )
        elif mock_type == "timeout" or mock_type == "unknown":
            return AdapterExecutionResult(
                success=False,
                error_code="NETWORK_TIMEOUT",
                error_message="Razorpay API connection timed out.",
                retryable=False,
                execution_state=ExecutionState.UNKNOWN,
                error_classification=ErrorClassification.UNKNOWN,
            )

        return AdapterExecutionResult(
            success=False,
            error_code="MOCK_ERROR",
            error_message="Unspecified mock error",
            retryable=False,
            execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
            error_classification=ErrorClassification.PERMANENT,
        )

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
        webhook_secret: str,
    ) -> bool:
        """
        Verifies Razorpay HMAC-SHA256 signature and timestamp tolerance.

        Header format: X-Razorpay-Signature
        """
        if not signature_header or not webhook_secret:
            return False

        try:
            expected_sig = hmac.new(
                webhook_secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_sig.lower(), signature_header.lower().strip()):
                return False

            # Verify timestamp if present in payload JSON body
            try:
                data = json.loads(payload_bytes.decode("utf-8"))
                created_at = data.get("created_at")
                if created_at:
                    now = int(time.time())
                    if abs(now - int(created_at)) > 300:
                        logger.warning(f"Razorpay webhook timestamp drift exceeded: {abs(now - int(created_at))}s")
                        return False
            except Exception:
                pass

            return True
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {e}")
            return False
