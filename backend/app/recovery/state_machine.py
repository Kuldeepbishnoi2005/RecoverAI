from enum import Enum
from typing import Dict, Set

class RecoveryActionStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    IN_PROGRESS = "IN_PROGRESS"
    SIMULATED = "SIMULATED"
    EXECUTED_SUCCESS = "EXECUTED_SUCCESS"
    EXECUTED_FAILED = "EXECUTED_FAILED"
    CANCELLED_SAFEGUARD = "CANCELLED_SAFEGUARD"
    # Legacy alias support if needed in database reading
    PENDING = "pending"
    SCHEDULED = "scheduled"

# Explicit transition matrix
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    RecoveryActionStatus.PENDING_APPROVAL.value: {
        RecoveryActionStatus.APPROVED.value,
        RecoveryActionStatus.REJECTED.value,
        RecoveryActionStatus.EXPIRED.value,
        RecoveryActionStatus.CANCELLED_SAFEGUARD.value
    },
    RecoveryActionStatus.PENDING.value: {
        RecoveryActionStatus.PENDING_APPROVAL.value,
        RecoveryActionStatus.APPROVED.value,
        RecoveryActionStatus.REJECTED.value,
        RecoveryActionStatus.EXPIRED.value,
        RecoveryActionStatus.CANCELLED_SAFEGUARD.value
    },
    RecoveryActionStatus.SCHEDULED.value: {
        RecoveryActionStatus.PENDING_APPROVAL.value,
        RecoveryActionStatus.APPROVED.value,
        RecoveryActionStatus.REJECTED.value,
        RecoveryActionStatus.SIMULATED.value,
        RecoveryActionStatus.CANCELLED_SAFEGUARD.value
    },
    RecoveryActionStatus.APPROVED.value: {
        RecoveryActionStatus.IN_PROGRESS.value,
        RecoveryActionStatus.SIMULATED.value,
        RecoveryActionStatus.EXECUTED_SUCCESS.value,
        RecoveryActionStatus.EXECUTED_FAILED.value,
        RecoveryActionStatus.CANCELLED_SAFEGUARD.value
    },
    RecoveryActionStatus.IN_PROGRESS.value: {
        RecoveryActionStatus.SIMULATED.value,
        RecoveryActionStatus.EXECUTED_SUCCESS.value,
        RecoveryActionStatus.EXECUTED_FAILED.value,
        RecoveryActionStatus.CANCELLED_SAFEGUARD.value
    },
    RecoveryActionStatus.SIMULATED.value: {
        RecoveryActionStatus.EXECUTED_SUCCESS.value,
        RecoveryActionStatus.EXECUTED_FAILED.value,
        RecoveryActionStatus.CANCELLED_SAFEGUARD.value
    },
    # Terminal states
    RecoveryActionStatus.REJECTED.value: set(),
    RecoveryActionStatus.EXPIRED.value: set(),
    RecoveryActionStatus.EXECUTED_SUCCESS.value: set(),
    RecoveryActionStatus.EXECUTED_FAILED.value: set(),
    RecoveryActionStatus.CANCELLED_SAFEGUARD.value: set(),
}

class InvalidStateTransitionError(Exception):
    pass

def validate_state_transition(current_status: str, new_status: str) -> bool:
    """
    Validates if transitioning from current_status to new_status is allowed.
    Raises InvalidStateTransitionError if illegal.
    """
    current_upper = (current_status or "").upper()
    new_upper = (new_status or "").upper()

    # Normalization for legacy lowercase statuses
    curr_key = current_status if current_status in VALID_TRANSITIONS else current_upper
    new_val = new_status if new_status in [s.value for s in RecoveryActionStatus] else new_upper

    # Special forbidden checks per prompt requirements
    if curr_key == RecoveryActionStatus.APPROVED.value and new_val == RecoveryActionStatus.REJECTED.value:
        raise InvalidStateTransitionError("Cannot transition APPROVED action to REJECTED.")
    if curr_key == RecoveryActionStatus.REJECTED.value and new_val == RecoveryActionStatus.APPROVED.value:
        raise InvalidStateTransitionError("Cannot transition REJECTED action to APPROVED.")
    if curr_key == RecoveryActionStatus.EXPIRED.value and new_val == RecoveryActionStatus.APPROVED.value:
        raise InvalidStateTransitionError("Cannot transition EXPIRED action to APPROVED.")
    if curr_key == RecoveryActionStatus.EXECUTED_SUCCESS.value:
        raise InvalidStateTransitionError("Cannot transition EXECUTED_SUCCESS action to any state.")

    allowed = VALID_TRANSITIONS.get(curr_key, set())
    if new_val not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid state transition from '{current_status}' to '{new_status}'."
        )
    return True


class RecoveryActionStateMachine:
    """
    State machine controller for managing recovery action status transitions.
    """
    def __init__(self, current_status = RecoveryActionStatus.PENDING_APPROVAL):
        if hasattr(current_status, 'value'):
            self.current_status = current_status.value
        else:
            self.current_status = str(current_status)

    def transition_to(self, new_status, actor: str = "system", reason: str = "") -> RecoveryActionStatus:
        target_str = new_status.value if hasattr(new_status, 'value') else str(new_status)
        validate_state_transition(self.current_status, target_str)
        self.current_status = target_str
        for s in RecoveryActionStatus:
            if s.value == target_str:
                return s
        return RecoveryActionStatus.PENDING_APPROVAL

    @staticmethod
    def validate_transition(current_status: str, new_status: str) -> bool:
        return validate_state_transition(current_status, new_status)

    @staticmethod
    def can_transition(current_status: str, new_status: str) -> bool:
        try:
            return validate_state_transition(current_status, new_status)
        except InvalidStateTransitionError:
            return False


