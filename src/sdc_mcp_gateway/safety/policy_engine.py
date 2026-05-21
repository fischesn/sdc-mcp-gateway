from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class ReadOnlyPolicyEngine:
    """Read-only policy engine: all write/tool operations are denied."""

    def check_tool_allowed(self, tool_name: str) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{tool_name}' is denied: this prototype is read-only and exports no MCP tools.",
        )
