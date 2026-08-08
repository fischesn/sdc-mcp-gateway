from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BoundaryState(str, Enum):
    IDLE = "idle"
    READ_RETURNED = "read_returned"
    PROPOSED = "proposed"
    VALIDATED = "validated"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RETURNED = "returned"


class BoundaryEvent(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    VALIDATE = "validate"
    REQUIRE_APPROVAL = "require_approval"
    APPROVE = "approve"
    REJECT = "reject"
    EXPIRE = "expire"
    RETURN = "return"


@dataclass(frozen=True)
class BoundaryTransition:
    source: BoundaryState
    event: BoundaryEvent
    target: BoundaryState
    device_effect: bool = False


TRANSITIONS = (
    BoundaryTransition(BoundaryState.IDLE, BoundaryEvent.READ, BoundaryState.READ_RETURNED),
    BoundaryTransition(BoundaryState.READ_RETURNED, BoundaryEvent.RETURN, BoundaryState.RETURNED),
    BoundaryTransition(BoundaryState.IDLE, BoundaryEvent.PROPOSE, BoundaryState.PROPOSED),
    BoundaryTransition(BoundaryState.PROPOSED, BoundaryEvent.VALIDATE, BoundaryState.VALIDATED),
    BoundaryTransition(BoundaryState.PROPOSED, BoundaryEvent.REJECT, BoundaryState.REJECTED),
    BoundaryTransition(
        BoundaryState.VALIDATED,
        BoundaryEvent.REQUIRE_APPROVAL,
        BoundaryState.PENDING_APPROVAL,
    ),
    BoundaryTransition(BoundaryState.VALIDATED, BoundaryEvent.REJECT, BoundaryState.REJECTED),
    BoundaryTransition(BoundaryState.VALIDATED, BoundaryEvent.RETURN, BoundaryState.RETURNED),
    BoundaryTransition(BoundaryState.PENDING_APPROVAL, BoundaryEvent.APPROVE, BoundaryState.APPROVED),
    BoundaryTransition(BoundaryState.PENDING_APPROVAL, BoundaryEvent.REJECT, BoundaryState.REJECTED),
    BoundaryTransition(BoundaryState.PENDING_APPROVAL, BoundaryEvent.EXPIRE, BoundaryState.EXPIRED),
    BoundaryTransition(BoundaryState.APPROVED, BoundaryEvent.RETURN, BoundaryState.RETURNED),
    BoundaryTransition(BoundaryState.REJECTED, BoundaryEvent.RETURN, BoundaryState.RETURNED),
    BoundaryTransition(BoundaryState.EXPIRED, BoundaryEvent.RETURN, BoundaryState.RETURNED),
)


class NoExecutionTransitionSystem:
    """Finite abstract workflow whose transition relation has no execution edge."""

    def __init__(self) -> None:
        self._by_key = {(item.source, item.event): item for item in TRANSITIONS}

    def transition(self, state: BoundaryState, event: BoundaryEvent) -> BoundaryTransition | None:
        return self._by_key.get((state, event))

    def reachable_states(self) -> set[BoundaryState]:
        reachable = {BoundaryState.IDLE}
        changed = True
        while changed:
            changed = False
            for transition in TRANSITIONS:
                if transition.source in reachable and transition.target not in reachable:
                    reachable.add(transition.target)
                    changed = True
        return reachable

    def verify(self) -> dict[str, object]:
        reachable = self.reachable_states()
        device_effect_edges = [item for item in TRANSITIONS if item.device_effect]
        execution_names = {
            item.value
            for item in (*BoundaryState, *BoundaryEvent)
            if "execut" in item.value.lower()
        }
        all_states_reachable = reachable == set(BoundaryState)
        ok = not device_effect_edges and not execution_names and all_states_reachable
        return {
            "status": "ok" if ok else "failed",
            "states": len(BoundaryState),
            "reachable_states": sorted(state.value for state in reachable),
            "transitions": len(TRANSITIONS),
            "device_effect_edges": len(device_effect_edges),
            "execution_named_states_or_events": sorted(execution_names),
        }
