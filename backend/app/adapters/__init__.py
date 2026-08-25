"""
Gateway Adapters Module for RecoverAI
Provides abstract BaseGatewayAdapter and concrete implementations (SandboxSimulatorAdapter).
"""
from app.adapters.base import BaseGatewayAdapter, AdapterExecutionResult
from app.adapters.sandbox import SandboxSimulatorAdapter
from app.adapters.factory import get_gateway_adapter

__all__ = [
    "BaseGatewayAdapter",
    "AdapterExecutionResult",
    "SandboxSimulatorAdapter",
    "get_gateway_adapter",
]
