from sdc_mcp_gateway.safety.policy_engine import ReadOnlyPolicyEngine


def test_read_only_policy_denies_all_tools() -> None:
    decision = ReadOnlyPolicyEngine().check_tool_allowed("set_fio2")
    assert decision.allowed is False
    assert "read-only" in decision.reason
