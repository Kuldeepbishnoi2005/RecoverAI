from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# ----------------------------------------------------
# Merchant Policy & Controls
# ----------------------------------------------------
class MerchantPolicy(BaseModel):
    merchant_id: str = "merchant_001"
    minimum_ai_confidence: float = Field(default=0.70, ge=0.0, le=1.0)
    maximum_retry_attempts: int = Field(default=3, ge=1)
    maximum_recovery_amount: float = Field(default=50000.0, ge=0.0)
    allowed_recovery_strategies: List[str] = Field(
        default_factory=lambda: [
            "SMART_RETRY",
            "PAYMENT_METHOD_UPDATE",
            "PERSONALIZED_DUNNING",
            "CHECKOUT_REMINDER",
            "MANUAL_REVIEW",
            "NO_ACTION"
        ]
    )
    automatic_recovery_enabled: bool = True

# ----------------------------------------------------
# Structured Context Object for AI (Phase 3.1)
# ----------------------------------------------------
class TransactionContext(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "INR"
    payment_method: str
    transaction_status: str
    failure_code: str
    failure_reason: str
    retry_count: int
    timestamp: str

class CustomerContext(BaseModel):
    customer_id: str
    customer_history: str
    previous_success_rate: float
    customer_lifetime_value: float
    subscription_status: str
    days_since_last_success: int

class RiskEngineContext(BaseModel):
    risk_score: float
    risk_level: str
    recovery_probability: float
    revenue_at_risk: float
    expected_recoverable_amount: float
    detected_risk_reasons: List[str]

class AIContext(BaseModel):
    transaction: TransactionContext
    customer: CustomerContext
    risk_engine: RiskEngineContext
    merchant_policy: MerchantPolicy

# ----------------------------------------------------
# Structured AI Decision Output Schema (Phase 3.2)
# ----------------------------------------------------
AllowedDecision = Literal["RECOVER", "MANUAL_REVIEW", "NO_ACTION"]
AllowedStrategy = Literal[
    "SMART_RETRY",
    "PAYMENT_METHOD_UPDATE",
    "PERSONALIZED_DUNNING",
    "CHECKOUT_REMINDER",
    "MANUAL_REVIEW",
    "NO_ACTION"
]

class AIDecisionOutput(BaseModel):
    decision: AllowedDecision
    strategy: AllowedStrategy
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    recovery_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_recovery_amount: float = Field(default=0.0, ge=0.0)
    reason: str = ""
    risk_factors: List[str] = Field(default_factory=list)
    recommended_delay_minutes: int = Field(default=0, ge=0)
    fallback_strategy: AllowedStrategy = "MANUAL_REVIEW"

# ----------------------------------------------------
# Policy / Governance Result Schema (Phase 3.5)
# ----------------------------------------------------
class PolicyResult(BaseModel):
    allowed: bool
    reason: str
    requires_human_approval: bool

# ----------------------------------------------------
# Simulation Result Schema (Phase 3.6)
# ----------------------------------------------------
class SimulationResult(BaseModel):
    action_id: str
    transaction_id: str
    strategy: str
    execution_status: str = "SIMULATED"
    success: bool
    recovered_amount: float
    attempted_amount: float
    execution_timestamp: str
    failure_reason: Optional[str] = None

# ----------------------------------------------------
# Complete End-to-End Pipeline Result (Phase 3.8 & 3.15)
# ----------------------------------------------------
class PipelineResult(BaseModel):
    pipeline_run_id: str
    transaction_id: str
    merchant_id: str
    context: AIContext
    ai_decision: AIDecisionOutput
    validation_status: str  # "PASSED" or "FAILED"
    validation_errors: List[str] = Field(default_factory=list)
    policy_result: PolicyResult
    simulation_result: Optional[SimulationResult] = None
    created_at: str
