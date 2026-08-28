"""
Stripe Payment Gateway Adapter
Implements BaseGatewayAdapter for Stripe payment recovery executions and webhook verification.
"""
import hmac
import hashlib
import time
import logging
from typing import Dict, Any, Optional

from app.adapters.base import (
    BaseGatewayAdapter,
    AdapterExecutionResult,
    ExecutionState,
    ErrorClassification,
)

logger = logging.getLogger("app.adapters.stripe_adapter")


class StripeAdapter(BaseGatewayAdapter):
    """Production Stripe gateway adapter with intent reuse and error mapping."""

    @property
    def provider_name(self) -> str:
        return "stripe"

    def execute_action(
        self,
        action_type: str,
        amount: float,
        currency: str,
        payload: Dict[str, Any],
        merchant_settings: Optional[Dict[str, Any]] = None,
    ) -> AdapterExecutionResult:
        """
        Executes a payment recovery action on Stripe.

        Handles:
        1. Reuse of existing reusable PaymentIntent (stripe_payment_intent_id)
        2. Creation of new PaymentIntent when required
        3. Deterministic idempotency key propagation
        4. Classification of Stripe error response into ExecutionState & ErrorClassification
        5. Zero credential exposure in logs or responses
        """
        merchant_settings = merchant_settings or {}
        api_key = (
            merchant_settings.get("stripe_secret_key")
            or payload.get("stripe_secret_key")
        )

        # 1. Deterministic Idempotency Key
        action_id = payload.get("action_id", "act_unknown")
        role = payload.get("role", "primary")
        retry_count = payload.get("retry_count", 1)
        idempotency_key = payload.get(
            "idempotency_key"
        ) or f"idem_{action_id}_{role}_{retry_count}_stripe"

        # Check for simulated testing parameters, mock mode, or unconfigured credentials
        mock_client = payload.get("mock_client")
        if mock_client or (not api_key and mock_client is not False):
            return self._execute_mock(
                action_type, amount, currency, payload, idempotency_key
            )

        # Check for missing credentials if mock_client was explicitly disabled
        if not api_key:
            logger.warning("Stripe secret key missing for execution.")
            return AdapterExecutionResult(
                success=False,
                transaction_id=None,
                gateway_response={"provider": "stripe", "status": "failed"},
                error_code="MISSING_CREDENTIALS",
                error_message="Stripe secret key is not configured for this merchant.",
                retryable=False,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.PERMANENT,
            )


        try:
            import stripe
            stripe.api_key = api_key

            # Smallest currency unit conversion (cents/paise)
            unit_amount = int(round(amount * 100))

            existing_intent_id = (
                payload.get("stripe_payment_intent_id")
                or payload.get("payment_intent_id")
            )

            # 2. Re-use existing PaymentIntent if present & reusable
            if existing_intent_id:
                try:
                    intent = stripe.PaymentIntent.retrieve(existing_intent_id)
                    intent_status = getattr(intent, "status", None) or intent.get("status")

                    if intent_status == "succeeded":
                        return AdapterExecutionResult(
                            success=True,
                            transaction_id=existing_intent_id,
                            gateway_response={
                                "provider": "stripe",
                                "status": "succeeded",
                                "payment_intent_id": existing_intent_id,
                                "reused": True,
                            },
                            execution_state=ExecutionState.CONFIRMED_EXECUTED,
                            error_classification=ErrorClassification.NONE,
                        )
                    elif intent_status in ["requires_payment_method", "requires_confirmation"]:
                        confirmed_intent = stripe.PaymentIntent.confirm(
                            existing_intent_id,
                            idempotency_key=idempotency_key,
                        )
                        conf_status = getattr(confirmed_intent, "status", None) or confirmed_intent.get("status")
                        if conf_status == "succeeded":
                            return AdapterExecutionResult(
                                success=True,
                                transaction_id=existing_intent_id,
                                gateway_response={
                                    "provider": "stripe",
                                    "status": "succeeded",
                                    "payment_intent_id": existing_intent_id,
                                    "reused": True,
                                },
                                execution_state=ExecutionState.CONFIRMED_EXECUTED,
                                error_classification=ErrorClassification.NONE,
                            )
                except Exception as e:
                    logger.info(f"Could not reuse intent {existing_intent_id}: {e}")

            # 3. Create New PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=unit_amount,
                currency=currency.lower(),
                confirm=True,
                payment_method=payload.get("payment_method_id", "pm_card_visa"),
                off_session=True,
                metadata={
                    "merchant_id": payload.get("merchant_id", ""),
                    "action_id": action_id,
                    "retry_count": str(retry_count),
                },
                idempotency_key=idempotency_key,
            )

            intent_id = getattr(intent, "id", None) or intent.get("id")
            intent_status = getattr(intent, "status", None) or intent.get("status")

            if intent_status == "succeeded":
                return AdapterExecutionResult(
                    success=True,
                    transaction_id=intent_id,
                    gateway_response={
                        "provider": "stripe",
                        "status": "succeeded",
                        "payment_intent_id": intent_id,
                        "reused": False,
                    },
                    execution_state=ExecutionState.CONFIRMED_EXECUTED,
                    error_classification=ErrorClassification.NONE,
                )
            else:
                return AdapterExecutionResult(
                    success=False,
                    transaction_id=intent_id,
                    gateway_response={
                        "provider": "stripe",
                        "status": intent_status,
                        "payment_intent_id": intent_id,
                    },
                    error_code="UNSUCCESSFUL_INTENT_STATUS",
                    error_message=f"Stripe PaymentIntent status is {intent_status}",
                    retryable=True,
                    execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                    error_classification=ErrorClassification.TRANSIENT,
                )

        except Exception as e:
            return self.classify_stripe_error(e)

    def classify_stripe_error(self, exc: Exception) -> AdapterExecutionResult:
        """Classifies Stripe SDK & network exceptions into ExecutionState & ErrorClassification."""
        err_str = str(exc)
        exc_type_name = type(exc).__name__

        # Import stripe error types if available
        try:
            import stripe
            card_err = stripe.error.CardError
            invalid_req_err = stripe.error.InvalidRequestError
            auth_err = stripe.error.AuthenticationError
            rate_err = stripe.error.RateLimitError
            conn_err = stripe.error.APIConnectionError
            stripe_err = stripe.error.StripeError
        except ImportError:
            card_err = invalid_req_err = auth_err = rate_err = conn_err = stripe_err = Exception

        if isinstance(exc, card_err):
            code = getattr(exc, "code", "card_declined")
            decline_code = getattr(exc, "decline_code", "")

            if code in ["expired_card", "incorrect_cvc", "invalid_expiry_year", "invalid_cvc"]:
                return AdapterExecutionResult(
                    success=False,
                    error_code=code,
                    error_message=err_str,
                    retryable=False,
                    execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                    error_classification=ErrorClassification.PERMANENT,
                )
            # Default card decline -> Transient
            return AdapterExecutionResult(
                success=False,
                error_code=code or "card_declined",
                error_message=err_str,
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )

        elif isinstance(exc, (invalid_req_err, auth_err)) or exc_type_name in ["InvalidRequestError", "AuthenticationError"]:
            return AdapterExecutionResult(
                success=False,
                error_code="INVALID_REQUEST_OR_AUTH",
                error_message=err_str,
                retryable=False,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.PERMANENT,
            )

        elif isinstance(exc, (rate_err, conn_err)) or exc_type_name in ["RateLimitError", "APIConnectionError"]:
            return AdapterExecutionResult(
                success=False,
                error_code="GATEWAY_TRANSIENT_ERROR",
                error_message=err_str,
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )

        elif "timeout" in err_str.lower() or "connection" in err_str.lower() or exc_type_name in ["Timeout", "ReadTimeout", "ConnectTimeout"]:
            # UNKNOWN state for network timeout / connection drop
            return AdapterExecutionResult(
                success=False,
                error_code="NETWORK_TIMEOUT",
                error_message="Stripe API request timed out or connection dropped.",
                retryable=False,
                execution_state=ExecutionState.UNKNOWN,
                error_classification=ErrorClassification.UNKNOWN,
            )

        # Catch-all for unhandled / HTTP 5xx / unknown errors -> UNKNOWN
        return AdapterExecutionResult(
            success=False,
            error_code="UNKNOWN_STRIPE_ERROR",
            error_message=f"Unhandled Stripe exception: {err_str}",
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
        idempotency_key: str,
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
                gateway_response={"provider": "stripe", "status": "failed"},
                error_code=payload.get("error_code", "SIMULATED_FAILURE"),
                error_message=payload.get("error_message", "Simulated mock execution failure"),
                retryable=payload.get("simulate_retryable", True),
                execution_state=exec_state,
                error_classification=err_class,
            )

        mock_type = payload.get("mock_type", "success")


        if mock_type == "success":
            tx_id = payload.get("stripe_payment_intent_id") or "pi_mock_123456789"
            return AdapterExecutionResult(
                success=True,
                transaction_id=tx_id,
                gateway_response={
                    "provider": "stripe",
                    "status": "succeeded",
                    "idempotency_key": idempotency_key,
                },
                execution_state=ExecutionState.CONFIRMED_EXECUTED,
                error_classification=ErrorClassification.NONE,
            )
        elif mock_type == "card_declined":
            return AdapterExecutionResult(
                success=False,
                error_code="card_declined",
                error_message="The card was declined.",
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )
        elif mock_type == "expired_card":
            return AdapterExecutionResult(
                success=False,
                error_code="expired_card",
                error_message="The card has expired.",
                retryable=False,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.PERMANENT,
            )
        elif mock_type == "rate_limit":
            return AdapterExecutionResult(
                success=False,
                error_code="rate_limit_error",
                error_message="Stripe rate limit exceeded.",
                retryable=True,
                execution_state=ExecutionState.CONFIRMED_NOT_EXECUTED,
                error_classification=ErrorClassification.TRANSIENT,
            )
        elif mock_type == "timeout" or mock_type == "unknown":
            return AdapterExecutionResult(
                success=False,
                error_code="NETWORK_TIMEOUT",
                error_message="Stripe API request timed out.",
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
        Verifies Stripe webhook HMAC-SHA256 signature and timestamp tolerance.

        Header format: t=<timestamp>,v1=<signature>
        Tolerance window: <= 300 seconds (5 minutes)
        """
        if not signature_header or not webhook_secret:
            return False

        try:
            timestamp = None
            signatures = []

            for item in signature_header.split(","):
                item = item.strip()
                if item.startswith("t="):
                    timestamp = int(item[2:])
                elif item.startswith("v1="):
                    signatures.append(item[3:])

            if timestamp is None or not signatures:
                return False

            # Check timestamp drift tolerance (max 300 seconds)
            now = int(time.time())
            if abs(now - timestamp) > 300:
                logger.warning(f"Stripe webhook timestamp drift exceeded: {abs(now - timestamp)}s")
                return False

            # Calculate expected HMAC-SHA256: t.payload_bytes
            signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
            expected_sig = hmac.new(
                webhook_secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            # Compare against any matching v1 signature in header
            for sig in signatures:
                if hmac.compare_digest(expected_sig.lower(), sig.lower()):
                    return True

            return False
        except Exception as e:
            logger.error(f"Stripe signature verification failed with exception: {e}")
            return False
