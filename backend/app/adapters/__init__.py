"""
Gateway Adapters Module for RecoverAI
Provides abstract BaseGatewayAdapter and concrete implementations (SandboxSimulatorAdapter).
"""
from app.adapters.base import BaseGatewayAdapter, AdapterExecutionResult, ExecutionState, ErrorClassification
from app.adapters.sandbox import SandboxSimulatorAdapter
from app.adapters.factory import get_gateway_adapter
from app.adapters.resilient_executor import ResilientGatewayExecutor

__all__ = [
    "BaseGatewayAdapter",
    "AdapterExecutionResult",
    "ExecutionState",
    "ErrorClassification",
    "SandboxSimulatorAdapter",
    "get_gateway_adapter",
    "ResilientGatewayExecutor",
]
