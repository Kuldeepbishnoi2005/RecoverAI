from fastapi.testclient import TestClient
from app.main import app
from app.adapters.factory import get_gateway_adapter
from app.adapters.sandbox import SandboxSimulatorAdapter
from app.adapters.base import BaseGatewayAdapter

client = TestClient(app)

def test_gateway_adapter_factory():
    """Verifies get_gateway_adapter returns SandboxSimulatorAdapter without external calls."""
    adapter = get_gateway_adapter("sandbox")
    assert isinstance(adapter, SandboxSimulatorAdapter)
    assert isinstance(adapter, BaseGatewayAdapter)

def test_sandbox_adapter_execution():
    """Verifies SandboxSimulatorAdapter simulates successful and failed actions."""
    adapter = SandboxSimulatorAdapter()

    # Successful simulation
    res_success = adapter.execute_action(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=100.0,
        currency="INR",
        payload={}
    )
    assert res_success.success is True
    assert res_success.transaction_id is not None
    assert res_success.transaction_id.startswith("sb_tx_")

    # Failed simulation
    res_fail = adapter.execute_action(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=100.0,
        currency="INR",
        payload={"simulate_failure": True, "error_code": "TEST_DECLINE"}
    )
    assert res_fail.success is False
    assert res_fail.error_code == "TEST_DECLINE"

def run_all_phase8_tests():
    print("--- RUNNING PHASE 8 RESILIENCE & GATEWAY ADAPTER TESTS ---")
    test_gateway_adapter_factory()
    print("[PASS] 1. Gateway Adapter Factory returns Sandbox Simulator")
    test_sandbox_adapter_execution()
    print("[PASS] 2. Sandbox Adapter execution simulation success/failure")
    print("ALL PHASE 8 RESILIENCE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_phase8_tests()
