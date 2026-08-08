from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from sdc_mcp_gateway.models import MappingDocument


SUPPORTED_SCHEMA_VERSIONS = {"1.0": "sdc-mie-1.0.schema.json"}


class MappingValidationError(ValueError):
    """Raised when an SDC-MIE document is invalid or ambiguous."""


def mapping_schema_path(schema_version: str = "1.0") -> Path:
    try:
        filename = SUPPORTED_SCHEMA_VERSIONS[schema_version]
    except KeyError as exc:
        raise MappingValidationError(
            f"Unsupported SDC-MIE schema_version {schema_version!r}; "
            f"supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        ) from exc
    return Path(__file__).resolve().parent / "schemas" / filename


def _format_jsonschema_error(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path) or "<document>"
    return f"{path}: {error.message}"


def load_mapping(path: str | Path) -> MappingDocument:
    """Load and fail-closed validate an SDC-MIE YAML mapping document."""

    source_path = Path(path)
    source_bytes = source_path.read_bytes()
    data: Any = yaml.safe_load(source_bytes.decode("utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping document at {path}")

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str):
        raise MappingValidationError("SDC-MIE document requires string field 'schema_version'")
    schema_path = mapping_schema_path(schema_version)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
    if errors:
        messages = "; ".join(_format_jsonschema_error(error) for error in errors)
        raise MappingValidationError(f"SDC-MIE JSON Schema validation failed: {messages}")

    try:
        document = MappingDocument.model_validate(data)
    except ValidationError as exc:
        raise MappingValidationError(f"SDC-MIE semantic validation failed: {exc}") from exc
    return document.model_copy(
        update={
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "schema_id": str(schema["$id"]),
        }
    )
