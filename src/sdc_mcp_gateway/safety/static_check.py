from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path


FORBIDDEN_DEVICE_CALLS = frozenset(
    {
        "activate",
        "activate_operation",
        "execute_operation",
        "set_alert_state",
        "set_component_state",
        "set_context_state",
        "set_metric_state",
        "set_numeric_value",
        "set_service",
        "set_string_value",
        "set_value",
    }
)
FORBIDDEN_IMPORT_PREFIXES = ("sdc11073",)


@dataclass(frozen=True)
class StaticBoundaryViolation:
    file: str
    line: int
    category: str
    symbol: str


def scan_agent_facing_boundary(package_root: Path) -> dict[str, object]:
    """AST-scan agent-facing code for device-write APIs and direct SDC imports."""

    targets = [
        package_root / "main.py",
        package_root / "mcp",
        package_root / "tools",
        package_root / "agent_eval",
        package_root / "safety",
    ]
    files: list[Path] = []
    for target in targets:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.rglob("*.py")))

    violations: list[StaticBoundaryViolation] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        relative = path.relative_to(package_root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                symbol = _call_symbol(node.func)
                if symbol in FORBIDDEN_DEVICE_CALLS:
                    violations.append(
                        StaticBoundaryViolation(relative, node.lineno, "forbidden_call", symbol)
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        violations.append(
                            StaticBoundaryViolation(
                                relative,
                                node.lineno,
                                "forbidden_import",
                                alias.name,
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(
                        StaticBoundaryViolation(
                            relative,
                            node.lineno,
                            "forbidden_import",
                            module,
                        )
                    )

    return {
        "status": "ok" if not violations else "failed",
        "files_scanned": len(files),
        "forbidden_symbols": sorted(FORBIDDEN_DEVICE_CALLS),
        "violations": [asdict(violation) for violation in violations],
    }


def _call_symbol(function: ast.expr) -> str:
    if isinstance(function, ast.Attribute):
        return function.attr.lower()
    if isinstance(function, ast.Name):
        return function.id.lower()
    return ""
