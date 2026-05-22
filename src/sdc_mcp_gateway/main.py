from __future__ import annotations

import json
from pathlib import Path

import typer

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.benchmark import BenchmarkConfig, run_benchmark
from sdc_mcp_gateway.experiments.summarize import BenchmarkSummaryConfig, summarize_benchmarks
from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, run_agent_evaluation
from sdc_mcp_gateway.agent_eval.summarize import AgentEvalSummaryConfig, summarize_agent_evaluations
from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.client_smoke import (
    McpClientSmokeTestConfig,
    MissingMcpClientDependency,
    run_mcp_client_smoke_test,
)
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.mcp.server import MissingMcpDependency, create_mcp_server
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies
from sdc_mcp_gateway.sdc.consumer import (
    DummySdcConsumer,
    MissingSdc11073Dependency,
    Sdc11073Consumer,
    SdcConsumer,
    SimulatedSdcConsumer,
)

app = typer.Typer(help="SDC-to-MCP Gateway research prototype")


def _make_recorder(config: GatewayConfig) -> JsonlRecorder:
    return JsonlRecorder(config.gateway.log_file)


def _make_consumer(config: GatewayConfig, recorder: JsonlRecorder | None = None) -> SdcConsumer:
    if config.sdc.adapter == "dummy":
        return DummySdcConsumer()
    if config.sdc.adapter == "simulated":
        if not config.sdc.simulation_config:
            raise typer.BadParameter("sdc.simulation_config must be set when adapter is simulated")
        return SimulatedSdcConsumer(
            scenario_path=config.sdc.simulation_config,
            elapsed_s=config.sdc.simulation_elapsed_s,
            recorder=recorder,
        )
    if config.sdc.adapter == "sdc11073":
        return Sdc11073Consumer(
            discovery_timeout_s=config.sdc.discovery_timeout_s,
            provider_whitelist=config.sdc.provider_whitelist,
            local_ip=config.sdc.local_ip,
            max_devices=config.sdc.max_devices,
            recorder=recorder,
        )
    raise typer.BadParameter(f"Unsupported SDC adapter: {config.sdc.adapter}")


def _make_registry(config_path: Path, mie_path: Path) -> ResourceRegistry:
    config = GatewayConfig.from_file(config_path)
    mapping = load_mapping(mie_path)
    recorder = _make_recorder(config)
    consumer = _make_consumer(config, recorder=recorder)
    devices = consumer.get_snapshots()
    return ResourceRegistry(
        devices=devices,
        mapping=mapping,
        recorder=recorder,
        tools_exported=config.gateway.allow_tools,
        tool_mode="dry-run" if config.gateway.allow_tools else None,
        write_operations_allowed=config.gateway.allow_write_operations,
        gateway_mode=config.gateway.mode,
    )


def _make_tool_registry(config_path: Path, mie_path: Path, tool_policy: Path) -> DryRunToolRegistry:
    config = GatewayConfig.from_file(config_path)
    recorder = _make_recorder(config)
    registry = _make_registry(config_path, mie_path)
    policies = load_tool_policies(tool_policy)
    return DryRunToolRegistry(
        resource_registry=registry,
        policies=policies,
        recorder=recorder,
        tools_enabled=config.gateway.allow_tools,
        write_operations_allowed=config.gateway.allow_write_operations,
    )


@app.command()
def discover(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
) -> None:
    """Discover SDC providers with the configured adapter and print provider identifiers."""

    gateway_config = GatewayConfig.from_file(config)
    recorder = _make_recorder(gateway_config)
    consumer = _make_consumer(gateway_config, recorder=recorder)
    try:
        providers = consumer.discover()
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    typer.echo(json.dumps({"providers": providers}, ensure_ascii=False, indent=2, sort_keys=True))


@app.command()
def snapshot(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Print all read-only resource payloads as JSON. Useful without an MCP client."""

    try:
        registry = _make_registry(config, mie)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    payloads = {uri: registry.read(uri).model_dump() for uri in registry.list_resource_uris()}
    typer.echo(json.dumps(payloads, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("simulate-snapshot")
def simulate_snapshot(
    scenario: Path = typer.Option(Path("config/sim.patient-monitor.yaml"), help="Simulation scenario YAML file."),
    elapsed_s: float = typer.Option(0.0, help="Scenario time in seconds."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Generate a mapped snapshot from a simulation scenario without SDC networking."""

    from sdc_mcp_gateway.simulation.scenarios import SimulationEngine, SimulationScenario

    mapping = load_mapping(mie)
    scenario_doc = SimulationScenario.from_file(scenario)
    devices = SimulationEngine(scenario_doc).snapshot(elapsed_s=elapsed_s)
    registry = ResourceRegistry(devices=devices, mapping=mapping, recorder=None)
    payloads = {uri: registry.read(uri).model_dump() for uri in registry.list_resource_uris()}
    typer.echo(json.dumps(payloads, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("list-resources")
def list_resources(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """List the read-only MCP resources exposed by the gateway."""

    try:
        registry = _make_registry(config, mie)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    descriptors = [descriptor.model_dump() for descriptor in registry.list_resource_descriptors()]
    typer.echo(json.dumps({"resources": descriptors}, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("read-resource")
def read_resource(
    uri: str = typer.Argument(..., help="Resource URI, for example sdc://health."),
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Read one gateway resource without starting an external MCP client."""

    try:
        registry = _make_registry(config, mie)
        payload = registry.read(uri)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(payload.model_dump(), ensure_ascii=False, indent=2, sort_keys=True))


@app.command("mcp-smoke-test")
def mcp_smoke_test(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    require_mcp_sdk: bool = typer.Option(
        False,
        "--require-mcp-sdk/--no-require-mcp-sdk",
        help="Fail if the optional MCP Python SDK is not installed.",
    ),
) -> None:
    """Run a local smoke test of the read-only MCP resource surface.

    The command does not start a long-running stdio MCP server. It builds the same
    registry used by `serve`, verifies that all advertised resources can be read,
    checks the read-only safety boundary, and attempts to construct the FastMCP
    server when the optional MCP SDK is installed.
    """

    checks: list[dict[str, object]] = []
    failures: list[str] = []

    def add_check(name: str, ok: bool, details: dict[str, object] | None = None) -> None:
        checks.append({"name": name, "ok": ok, "details": details or {}})
        if not ok:
            failures.append(name)

    try:
        gateway_config = GatewayConfig.from_file(config)
        registry = _make_registry(config, mie)
        add_check("registry_created", True)
    except MissingSdc11073Dependency as exc:
        add_check("registry_created", False, {"error": str(exc)})
        typer.echo(json.dumps({"status": "failed", "checks": checks}, ensure_ascii=False, indent=2, sort_keys=True))
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        add_check("registry_created", False, {"error": str(exc)})
        typer.echo(json.dumps({"status": "failed", "checks": checks}, ensure_ascii=False, indent=2, sort_keys=True))
        raise typer.Exit(code=1) from exc

    descriptors = registry.list_resource_descriptors()
    resource_uris = [descriptor.uri for descriptor in descriptors]
    add_check("resources_listed", len(resource_uris) > 0, {"resource_count": len(resource_uris)})

    read_errors: list[dict[str, str]] = []
    for uri in resource_uris:
        try:
            registry.read(uri)
        except Exception as exc:  # pragma: no cover - defensive user-facing command
            read_errors.append({"uri": uri, "error": str(exc)})
    add_check(
        "all_advertised_resources_readable",
        len(read_errors) == 0,
        {"read_resource_count": len(resource_uris), "errors": read_errors},
    )

    health = registry.read("sdc://health").model_dump()
    health_data = health.get("data", {})
    add_check(
        "read_only_safety_boundary",
        bool(
            health_data.get("mode") == "read-only"
            and health_data.get("tools_exported") is False
            and health_data.get("write_operations_allowed") is False
        ),
        {
            "mode": health_data.get("mode"),
            "tools_exported": health_data.get("tools_exported"),
            "write_operations_allowed": health_data.get("write_operations_allowed"),
        },
    )
    add_check(
        "health_resource_count_matches_catalogue",
        health_data.get("resource_count") == len(resource_uris),
        {"health_resource_count": health_data.get("resource_count"), "catalogue_resource_count": len(resource_uris)},
    )

    resources_payload = registry.read("sdc://resources").model_dump()
    resources_data = resources_payload.get("data", [])
    add_check(
        "resource_catalogue_readable",
        isinstance(resources_data, list) and len(resources_data) == len(resource_uris),
        {"catalogue_entries": len(resources_data) if isinstance(resources_data, list) else None},
    )

    mcp_sdk_available = True
    server_constructed = False
    mcp_error: str | None = None
    try:
        create_mcp_server(registry, server_name=gateway_config.mcp.server_name)
        server_constructed = True
    except MissingMcpDependency as exc:
        mcp_sdk_available = False
        mcp_error = str(exc)
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        mcp_error = str(exc)

    add_check(
        "fastmcp_server_constructed",
        server_constructed or (not require_mcp_sdk and not mcp_sdk_available),
        {
            "mcp_sdk_available": mcp_sdk_available,
            "server_constructed": server_constructed,
            "error": mcp_error,
            "required": require_mcp_sdk,
        },
    )

    status = "ok" if not failures else "failed"
    report = {
        "status": status,
        "config": str(config),
        "mie": str(mie),
        "adapter": gateway_config.sdc.adapter,
        "resource_count": len(resource_uris),
        "sample_resources": resource_uris[:5],
        "checks": checks,
    }
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if failures:
        raise typer.Exit(code=1)


@app.command("mcp-client-smoke-test")
def mcp_client_smoke_test(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    timeout_s: float = typer.Option(15.0, help="Read timeout for MCP client requests in seconds."),
) -> None:
    """Start the stdio MCP server as a subprocess and test it with an MCP client.

    Unlike `mcp-smoke-test`, this command exercises the actual MCP protocol path:
    it starts `sdc-mcp-gateway serve`, initializes an MCP ClientSession, lists
    resources, reads selected resources, and verifies that no tools are exposed.
    """

    try:
        report = run_mcp_client_smoke_test(
            McpClientSmokeTestConfig(
                config_path=config,
                mie_path=mie,
                cwd=Path.cwd(),
                timeout_s=timeout_s,
            )
        )
    except MissingMcpClientDependency as exc:
        raise typer.Exit(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        typer.echo(
            json.dumps(
                {"status": "failed", "error": str(exc), "config": str(config), "mie": str(mie)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report.get("status") != "ok":
        raise typer.Exit(code=1)


@app.command("list-tools")
def list_tools(
    config: Path = typer.Option(Path("config/gateway.simulated.dryrun.example.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    tool_policy: Path = typer.Option(Path("config/tool_policies.yaml"), help="Dry-run tool policy YAML file."),
) -> None:
    """List policy-checked dry-run MCP tools for the configured gateway."""

    tool_registry = _make_tool_registry(config, mie, tool_policy)
    descriptors = [descriptor.model_dump() for descriptor in tool_registry.list_tool_descriptors()]
    gateway_config = GatewayConfig.from_file(config)
    typer.echo(
        json.dumps(
            {
                "tools": descriptors,
                "tool_count": len(descriptors),
                "tool_mode": "dry-run" if gateway_config.gateway.allow_tools else None,
                "tools_enabled": gateway_config.gateway.allow_tools,
                "write_operations_allowed": gateway_config.gateway.allow_write_operations,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command("call-tool")
def call_tool(
    tool_name: str = typer.Argument(..., help="Dry-run tool name, e.g., prepare_set_fio2."),
    args_json: str | None = typer.Option(None, "--args-json", help="Tool arguments as JSON object."),
    args_file: Path | None = typer.Option(None, "--args-file", help="Path to a JSON file containing tool arguments."),
    config: Path = typer.Option(Path("config/gateway.simulated.dryrun.example.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    tool_policy: Path = typer.Option(Path("config/tool_policies.yaml"), help="Dry-run tool policy YAML file."),
) -> None:
    """Call one dry-run MCP tool without executing any SDC operation.

    Prefer --args-file on Windows/PowerShell to avoid JSON quoting issues.
    If neither --args-json nor --args-file is provided, an empty JSON object is used.
    """

    if args_json is not None and args_file is not None:
        raise typer.BadParameter("Use either --args-json or --args-file, not both")

    if args_file is not None:
        try:
            raw_args = args_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise typer.BadParameter(f"--args-file could not be read: {exc}") from exc
        source_label = f"--args-file {args_file}"
    else:
        raw_args = args_json if args_json is not None else "{}"
        source_label = "--args-json"

    try:
        arguments = json.loads(raw_args)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{source_label} must contain valid JSON: {exc}") from exc
    if not isinstance(arguments, dict):
        raise typer.BadParameter(f"{source_label} must decode to a JSON object")
    tool_registry = _make_tool_registry(config, mie, tool_policy)
    result = tool_registry.call_tool(tool_name, arguments)
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2, sort_keys=True))
    if result.status == "rejected":
        # Rejection is a valid policy outcome, not a CLI failure.
        return


@app.command("tool-smoke-test")
def tool_smoke_test(
    config: Path = typer.Option(Path("config/gateway.simulated.dryrun.example.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    tool_policy: Path = typer.Option(Path("config/tool_policies.yaml"), help="Dry-run tool policy YAML file."),
) -> None:
    """Run a deterministic dry-run tool validation smoke test."""

    tool_registry = _make_tool_registry(config, mie, tool_policy)
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, details: dict[str, object] | None = None) -> None:
        checks.append({"name": name, "ok": ok, "details": details or {}})

    descriptors = tool_registry.list_tool_descriptors()
    tool_names = {descriptor.name for descriptor in descriptors}
    check("tools_listed", {"prepare_set_fio2", "prepare_set_peep", "prepare_acknowledge_alarm"}.issubset(tool_names), {"tool_names": sorted(tool_names)})

    accepted = tool_registry.call_tool("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 45.0})
    check(
        "valid_fio2_accepted_dry_run",
        accepted.status == "accepted_dry_run" and accepted.executed is False and accepted.requires_human_approval is True,
        accepted.model_dump(),
    )

    rejected_range = tool_registry.call_tool("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 150.0})
    check("out_of_range_fio2_rejected", rejected_range.status == "rejected" and rejected_range.reason == "value_out_of_range", rejected_range.model_dump())

    rejected_device = tool_registry.call_tool("prepare_set_peep", {"device_id": "sim-monitor-1", "value": 8.0})
    check("wrong_device_type_rejected", rejected_device.status == "rejected" and rejected_device.reason == "wrong_device_type", rejected_device.model_dump())

    health = tool_registry.resource_registry.read("sdc://health").model_dump()["data"]
    check(
        "dry_run_safety_boundary",
        health.get("tools_exported") is True and health.get("tool_mode") == "dry-run" and health.get("write_operations_allowed") is False,
        health,
    )

    status = "ok" if all(item["ok"] for item in checks) else "failed"
    report = {"status": status, "checks": checks, "tool_count": len(descriptors)}
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if status != "ok":
        raise typer.Exit(code=1)


@app.command("benchmark")
def benchmark(
    config: Path = typer.Option(Path("config/gateway.simulated.example.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    iterations: int = typer.Option(10, help="Number of measured iterations."),
    warmup: int = typer.Option(1, help="Number of warm-up iterations that are excluded from summaries."),
    output_dir: Path = typer.Option(Path("data/experiment_runs"), help="Directory for JSONL, CSV, and summary output."),
    label: str = typer.Option("benchmark", help="Prefix for generated result files."),
    elapsed_start_s: float = typer.Option(0.0, help="Initial simulated scenario time in seconds."),
    elapsed_step_s: float = typer.Option(1.0, help="Scenario-time increment per iteration for simulated adapters."),
) -> None:
    """Run a repeatable read-only benchmark and write experiment artifacts.

    The command repeatedly builds the configured gateway resource registry, lists
    resources, reads all advertised resources, checks the read-only safety
    boundary, and writes JSONL/CSV/summary files that can be used for paper
    figures and tables. For the simulated adapter, elapsed_s is advanced between
    iterations so metric values change reproducibly.
    """

    try:
        report = run_benchmark(
            BenchmarkConfig(
                config_path=config,
                mie_path=mie,
                output_dir=output_dir,
                run_label=label,
                iterations=iterations,
                warmup=warmup,
                elapsed_start_s=elapsed_start_s,
                elapsed_step_s=elapsed_step_s,
            )
        )
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        typer.echo(
            json.dumps(
                {"status": "failed", "error": str(exc), "config": str(config), "mie": str(mie)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report.get("status") != "ok":
        raise typer.Exit(code=1)


@app.command("evaluate-agent-tasks")
def evaluate_agent_tasks(
    config: Path = typer.Option(Path("config/gateway.simulated.example.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    tasks: Path = typer.Option(Path("config/agent_eval.tasks.yaml"), help="Agent task YAML file."),
    scenario: str = typer.Option("baseline", help="Scenario key used for ground-truth expectations."),
    agent: str = typer.Option("oracle", help="Agent backend: oracle, llm-mock, llm-ollama, llm-openai-compatible, or llm-gemini."),
    output_dir: Path = typer.Option(Path("data/agent_eval"), help="Directory for JSON, CSV, and Markdown outputs."),
    label: str = typer.Option("agent-eval", help="Prefix for generated output files."),
    elapsed_s: float | None = typer.Option(100.0, help="Simulated scenario time in seconds, if using the simulated adapter."),
    llm_provider: str = typer.Option("mock", help="LLM provider when agent='llm': mock, ollama, openai-compatible, or gemini."),
    llm_model: str = typer.Option("mock-medical-agent", help="LLM model name for llm-* agents."),
    llm_endpoint: str | None = typer.Option(None, help="Optional LLM HTTP endpoint override."),
    llm_api_key_env: str | None = typer.Option(None, help="Environment variable holding API key for openai-compatible provider."),
    llm_timeout_s: float = typer.Option(60.0, help="LLM backend timeout in seconds."),
    llm_temperature: float = typer.Option(0.0, help="LLM sampling temperature."),
) -> None:
    """Evaluate agent-facing read-only tasks against scenario ground truth.

    v0.9 supports the deterministic oracle agent and optional LLM-backed agents.
    LLM backends are read-only and receive only MCP resource context; no tools or
    write operations are exposed by the gateway.
    """

    try:
        report = run_agent_evaluation(
            AgentEvalConfig(
                config_path=config,
                mie_path=mie,
                tasks_path=tasks,
                scenario=scenario,
                output_dir=output_dir,
                run_label=label,
                agent=agent,
                elapsed_s=elapsed_s,
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_endpoint=llm_endpoint,
                llm_api_key_env=llm_api_key_env,
                llm_timeout_s=llm_timeout_s,
                llm_temperature=llm_temperature,
            )
        )
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        typer.echo(
            json.dumps(
                {
                    "status": "failed",
                    "error": str(exc),
                    "config": str(config),
                    "mie": str(mie),
                    "tasks": str(tasks),
                    "scenario": scenario,
                    "agent": agent,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report.get("status") != "ok":
        raise typer.Exit(code=1)


@app.command("summarize-agent-evaluations")
def summarize_agent_evaluation_results(
    input_dir: Path = typer.Option(Path("data/agent_eval"), help="Directory containing agent evaluation JSON files."),
    output_dir: Path | None = typer.Option(None, help="Directory for aggregate JSON/CSV output. Defaults to input-dir."),
    label: str = typer.Option("agent-eval-summary", help="Prefix for generated aggregate result files."),
    pattern: str = typer.Option("agent-eval-*.json", help="Glob pattern for agent evaluation JSON files."),
) -> None:
    """Aggregate multiple agent-evaluation JSON files into JSON and CSV outputs."""

    try:
        report = summarize_agent_evaluations(
            AgentEvalSummaryConfig(input_dir=input_dir, output_dir=output_dir, label=label, pattern=pattern)
        )
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        typer.echo(
            json.dumps(
                {"status": "failed", "error": str(exc), "input_dir": str(input_dir), "pattern": pattern},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report.get("status") not in {"ok", "warning"}:
        raise typer.Exit(code=1)


@app.command("summarize-benchmarks")
def summarize_benchmark_results(
    input_dir: Path = typer.Option(Path("data/experiment_runs"), help="Directory containing *.summary.json benchmark files."),
    output_dir: Path | None = typer.Option(None, help="Directory for aggregate JSON/CSV output. Defaults to input-dir."),
    label: str = typer.Option("benchmark-summary", help="Prefix for generated aggregate result files."),
    pattern: str = typer.Option("*.summary.json", help="Glob pattern for benchmark summary files."),
) -> None:
    """Aggregate multiple benchmark summary JSON files into JSON and CSV outputs."""

    try:
        report = summarize_benchmarks(
            BenchmarkSummaryConfig(input_dir=input_dir, output_dir=output_dir, label=label, pattern=pattern)
        )
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        typer.echo(
            json.dumps(
                {"status": "failed", "error": str(exc), "input_dir": str(input_dir), "pattern": pattern},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report.get("status") not in {"ok", "warning"}:
        raise typer.Exit(code=1)


@app.command()
def serve(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    tool_policy: Path = typer.Option(Path("config/tool_policies.yaml"), help="Dry-run tool policy YAML file."),
) -> None:
    """Run the MCP server with the configured SDC adapter."""

    gateway_config = GatewayConfig.from_file(config)
    try:
        registry = _make_registry(config, mie)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    try:
        tool_registry = None
        if gateway_config.gateway.allow_tools:
            tool_registry = _make_tool_registry(config, mie, tool_policy)
        mcp = create_mcp_server(registry, server_name=gateway_config.mcp.server_name, tool_registry=tool_registry)
    except MissingMcpDependency as exc:
        raise typer.Exit(str(exc)) from exc
    mcp.run()


if __name__ == "__main__":
    app()
