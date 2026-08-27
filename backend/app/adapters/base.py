"""
Base Gateway Adapter Interface
Defines the contract for payment gateway integrations (Sandbox, Stripe, Razorpay, etc.)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


from enum import Enum


class ExecutionState(str, Enum):
    CONFIRMED_EXECUTED = "CONFIRMED_EXECUTED"
    CONFIRMED_NOT_EXECUTED = "CONFIRMED_NOT_EXECUTED"
    UNKNOWN = "UNKNOWN"


class ErrorClassification(str, Enum):
    NONE = "NONE"
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    UNKNOWN = "UNKNOWN"


class AdapterExecutionResult(BaseModel):
    """Result returned by any Gateway Adapter execution."""
    success: bool
    transaction_id: Optional[str] = None
    gateway_response: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = False
    execution_state: ExecutionState = ExecutionState.UNKNOWN
    error_classification: ErrorClassification = ErrorClassification.NONE


class BaseGatewayAdapter(ABC):
    """Abstract Base Class for Gateway Adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the gateway provider identifier (e.g. 'sandbox', 'stripe', 'razorpay')."""
        pass

    @abstractmethod
    def execute_action(
        self,
        action_type: str,
        amount: float,
        currency: str,
        payload: Dict[str, Any],
        merchant_settings: Optional[Dict[str, Any]] = None,
    ) -> AdapterExecutionResult:
        """
        Executes a recovery action against the payment gateway.

        Args:
            action_type: RETRY_CHARGE, UPDATE_PAYMENT_METHOD, OFFER_DISCOUNT, EXTEND_TRIAL, etc.
            amount: Transaction amount
            currency: 3-letter currency code (e.g. USD, EUR, INR)
            payload: Gateway payload parameters (e.g. customer_id, card_token, discount_pct)
            merchant_settings: Optional dictionary containing merchant configuration/credentials

        Returns:
            AdapterExecutionResult
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
        webhook_secret: str,
    ) -> bool:
        """
        Verifies the cryptographic signature of an incoming gateway webhook payload.

        Args:
            payload_bytes: Raw HTTP body bytes
            signature_header: HTTP header string containing signature/timestamp
            webhook_secret: Secret string used to verify signature

        Returns:
            bool: True if signature is valid, False otherwise
        """
        pass
