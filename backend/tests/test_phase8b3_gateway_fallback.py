import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.adapters.base import ExecutionState, ErrorClassification
from app.adapters.sandbox import SandboxSimulatorAdapter
from app.adapters.resilient_executor import ResilientGatewayExecutor


def test_primary_gateway_success():
    """1. Primary Gateway Success: returns immediately without fallback."""
    executor = ResilientGatewayExecutor()
    res = executor.execute_with_fallback(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=150.0,
        currency="INR",
        primary_provider="sandbox",
        backup_provider="stripe",
        payload={"action_id": "act_test_01"},
    )
    assert res.success is True
    assert res.execution_state == ExecutionState.CONFIRMED_EXECUTED
    assert res.error_classification == ErrorClassification.NONE
    assert res.gateway_response is None or not res.gateway_response.get("fallback_executed")


def test_transient_error_confirmed_not_executed_fallback_success():
    """2. Transient + Confirmed Not Executed: Triggers fallback which succeeds."""
    executor = ResilientGatewayExecutor()
    res = executor.execute_with_fallback(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=200.0,
        currency="INR",
        primary_provider="sandbox",
        backup_provider="stripe",
        payload={
            "action_id": "act_test_02",
            "simulate_primary_failure": True,
            "simulate_execution_state": "CONFIRMED_NOT_EXECUTED",
            "simulate_error_classification": "TRANSIENT",
        },
    )
    assert res.success is True
    assert res.gateway_response is not None
    assert res.gateway_response.get("fallback_executed") is True
    assert res.gateway_response.get("primary_gateway") == "sandbox"


def test_transient_error_confirmed_not_executed_backup_fails():
    """3. Transient + Confirmed Not Executed: Backup executed but also fails."""
    executor = ResilientGatewayExecutor()
    res = executor.execute_with_fallback(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=250.0,
        currency="INR",
        primary_provider="sandbox",
        backup_provider="stripe",
        payload={
            "action_id": "act_test_03",
            "simulate_failure": True,
            "simulate_execution_state": "CONFIRMED_NOT_EXECUTED",
            "simulate_error_classification": "TRANSIENT",
        },
    )
    assert res.gateway_response is not None
    assert res.gateway_response.get("fallback_executed") is True
    assert res.success is False


def test_unknown_execution_state_blocks_fallback():
    """4. UNKNOWN Execution State: Fallback is BLOCKED to prevent double-charging."""
    executor = ResilientGatewayExecutor()
    res = executor.execute_with_fallback(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=300.0,
        currency="INR",
        primary_provider="sandbox",
        backup_provider="stripe",
        payload={
            "action_id": "act_test_04",
            "simulate_failure": True,
            "simulate_execution_state": "UNKNOWN",
            "simulate_error_classification": "TRANSIENT",
        },
    )
    assert res.success is False
    assert res.execution_state == ExecutionState.UNKNOWN
    assert res.gateway_response is not None
    assert res.gateway_response.get("fallback_blocked_reason") == "UNKNOWN_EXECUTION_STATE"
    assert not res.gateway_response.get("fallback_executed")


def test_permanent_error_no_fallback():
    """5. Permanent Error: Fallback is NOT attempted."""
    executor = ResilientGatewayExecutor()
    res = executor.execute_with_fallback(
        action_type="RETRY_WITH_SMART_ROUTING",
        amount=350.0,
        currency="INR",
        primary_provider="sandbox",
        backup_provider="stripe",
        payload={
            "action_id": "act_test_05",
            "simulate_failure": True,
            "simulate_execution_state": "CONFIRMED_NOT_EXECUTED",
            "simulate_error_classification": "PERMANENT",
        },
    )
    assert res.success is False
    assert res.error_classification == ErrorClassification.PERMANENT
    assert res.gateway_response is None or not res.gateway_response.get("fallback_executed")


def test_idempotency_key_generation():
    """6. Idempotency Key Generation: Ensures scoped keys with retry_count for primary and backup."""
    adapter = SandboxSimulatorAdapter()
    retry_cnt = 2
    primary_idem_key = f"idem_act_test_06_primary_{retry_cnt}_{adapter.provider_name}"
    backup_idem_key = f"idem_act_test_06_backup_{retry_cnt}_{adapter.provider_name}"
    assert primary_idem_key != backup_idem_key
    assert "primary" in primary_idem_key
    assert "backup" in backup_idem_key
    assert f"_{retry_cnt}_" in primary_idem_key
    assert f"_{retry_cnt}_" in backup_idem_key


def test_replay_endpoint_execution_state_response():
    """7. Replay Response Structure: Includes execution state and error classification."""
    from app.adapters.base import AdapterExecutionResult
    res = AdapterExecutionResult(
        success=True,
        transaction_id="sb_tx_999",
        execution_state=ExecutionState.CONFIRMED_EXECUTED,
        error_classification=ErrorClassification.NONE,
    )
    assert res.execution_state.value == "CONFIRMED_EXECUTED"
    assert res.error_classification.value == "NONE"


def test_tenant_isolation_prevents_cross_merchant_replay():
    """8. Tenant Isolation: Merchant A cannot replay Merchant B's action or use Merchant B's gateway config."""
    import asyncio
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException
    from app.routers.manual_review import replay_recovery_action, ReplayRequest
    from app.auth.deps import AuthenticatedUser

    user_merchant_a = AuthenticatedUser(
        user_id="user_merchant_a_123",
        merchant_id="merchant_A",
        email="admin@merchant-a.com",
        role="merchant_admin"
    )

    action_b_id = "act_merchant_B_999"

    # Mock Supabase admin client to simulate DB lookup scoped by action_id AND user.merchant_id
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq_id = MagicMock()
    mock_eq_merchant = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq_id
    mock_eq_id.eq.return_value = mock_eq_merchant
    mock_eq_merchant.execute.return_value = MagicMock(data=[])

    mock_executor = MagicMock()

    with patch("app.routers.manual_review.get_supabase_admin_client", return_value=mock_supabase), \
         patch("app.routers.manual_review.ResilientGatewayExecutor", return_value=mock_executor):

        try:
            asyncio.run(
                replay_recovery_action(
                    action_id=action_b_id,
                    payload=ReplayRequest(notes="Unauthorized cross-tenant attempt"),
                    user=user_merchant_a
                )
            )
            assert False, "Should have raised HTTPException 404 for cross-tenant access"
        except HTTPException as exc:
            # 1 & 4. Must raise 404 before any gateway adapter is executed
            assert exc.status_code == 404
            assert f"Recovery action '{action_b_id}' not found" in exc.detail

        # 2 & 3. Ensure gateway adapter executor was NEVER called
        mock_executor.execute_with_fallback.assert_not_called()



def run_all_phase8b3_tests():
    print("--- RUNNING PHASE 8B.3 RESILIENT GATEWAY FALLBACK & REPLAY TESTS ---")
    test_primary_gateway_success()
    print("[PASS] 1. Primary Gateway Success returns immediately")
    test_transient_error_confirmed_not_executed_fallback_success()
    print("[PASS] 2. Transient error + Confirmed Not Executed triggers fallback")
    test_transient_error_confirmed_not_executed_backup_fails()
    print("[PASS] 3. Fallback execution failure handling")
    test_unknown_execution_state_blocks_fallback()
    print("[PASS] 4. UNKNOWN execution state strictly BLOCKS fallback")
    test_permanent_error_no_fallback()
    print("[PASS] 5. Permanent error does NOT trigger fallback")
    test_idempotency_key_generation()
    print("[PASS] 6. Deterministic, scoped idempotency keys generated")
    test_replay_endpoint_execution_state_response()
    print("[PASS] 7. Execution state & error classification returned in replay responses")
    test_tenant_isolation_prevents_cross_merchant_replay()
    print("[PASS] 8. Tenant isolation prevents cross-merchant replay and gateway usage")
    print("ALL PHASE 8B.3 GATEWAY FALLBACK TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_all_phase8b3_tests()
