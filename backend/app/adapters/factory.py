"""
Gateway Adapter Factory
Returns the appropriate BaseGatewayAdapter implementation for a given provider name.
"""
from typing import Dict, Type
from app.adapters.base import BaseGatewayAdapter
from app.adapters.sandbox import SandboxSimulatorAdapter

_ADAPTER_REGISTRY: Dict[str, Type[BaseGatewayAdapter]] = {
    "sandbox": SandboxSimulatorAdapter,
    # Future providers (e.g. stripe, razorpay) can be registered here safely without breaking API contracts
}


def get_gateway_adapter(provider_name: str = "sandbox") -> BaseGatewayAdapter:
    """
    Factory function to retrieve a gateway adapter instance.
    Defaults to SandboxSimulatorAdapter for safety.
    """
    normalized_name = (provider_name or "sandbox").lower().strip()
    adapter_cls = _ADAPTER_REGISTRY.get(normalized_name, SandboxSimulatorAdapter)
    return adapter_cls()
