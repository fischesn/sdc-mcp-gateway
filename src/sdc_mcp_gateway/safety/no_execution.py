from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ForbiddenDeviceOperation(RuntimeError):
    """Raised after the write spy observes a forbidden device operation attempt."""


@dataclass(frozen=True)
class DeviceOperationAttempt:
    operation: str
    target: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceWriteSpy:
    """Independent counter for attempted SDC Set/Activate operations."""

    attempts: list[DeviceOperationAttempt] = field(default_factory=list)

    @property
    def device_write_count(self) -> int:
        return len(self.attempts)

    def record_attempt(
        self,
        operation: str,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        attempt = DeviceOperationAttempt(operation=operation, target=target, details=details or {})
        self.attempts.append(attempt)
        raise ForbiddenDeviceOperation(
            f"Fail-closed no-execution boundary blocked {operation} for {target}"
        )

    def assert_no_writes(self) -> None:
        if self.attempts:
            operations = ", ".join(attempt.operation for attempt in self.attempts)
            raise AssertionError(
                f"Expected zero device operations, observed {self.device_write_count}: {operations}"
            )
