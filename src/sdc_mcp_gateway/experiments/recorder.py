from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field

from sdc_mcp_gateway.models import AuditRecord


REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "proxy_authorization",
    "secret",
    "set_cookie",
    "token",
}


class AuditProvenance(BaseModel):
    """Immutable identifiers needed to reproduce an audited decision."""

    provider_identity: str
    resource_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_id: str


class AuditChainVerification(BaseModel):
    valid: bool
    record_count: int
    head_sha256: str | None = None
    error_line: int | None = None
    reason: str | None = None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def redact_secrets(value: Any) -> Any:
    """Recursively remove credentials while retaining an auditable field shape."""

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            sensitive = normalized in _SENSITIVE_KEYS or normalized.endswith(
                ("_api_key", "_password", "_secret", "_token")
            )
            redacted[str(key)] = REDACTED if sensitive else redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value


def verify_hash_chain(path: str | Path) -> AuditChainVerification:
    """Verify every JSONL record and link; report the first changed or missing record."""

    audit_path = Path(path)
    if not audit_path.exists():
        return AuditChainVerification(valid=True, record_count=0)
    previous_hash: str | None = None
    record_count = 0
    with audit_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                return AuditChainVerification(
                    valid=False,
                    record_count=record_count,
                    head_sha256=previous_hash,
                    error_line=line_number,
                    reason="invalid_json",
                )
            claimed_hash = payload.pop("record_sha256", None)
            if payload.get("chain_index") != record_count:
                reason = "invalid_chain_index"
            elif payload.get("previous_record_sha256") != previous_hash:
                reason = "previous_hash_mismatch"
            elif not isinstance(claimed_hash, str):
                reason = "missing_record_hash"
            elif sha256_canonical(payload) != claimed_hash:
                reason = "record_hash_mismatch"
            else:
                reason = None
            if reason is not None:
                return AuditChainVerification(
                    valid=False,
                    record_count=record_count,
                    head_sha256=previous_hash,
                    error_line=line_number,
                    reason=reason,
                )
            previous_hash = claimed_hash
            record_count += 1
    return AuditChainVerification(
        valid=True,
        record_count=record_count,
        head_sha256=previous_hash,
    )


class JsonlRecorder:
    """JSONL recorder with optional provenance, redaction, and a SHA-256 hash chain."""

    def __init__(
        self,
        path: str | Path,
        *,
        provenance: AuditProvenance | None = None,
        hash_chain: bool = False,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.provenance = provenance
        self.hash_chain = hash_chain
        self._lock = Lock()
        self._chain_index = 0
        self._previous_hash: str | None = None
        if hash_chain and self.path.exists() and self.path.stat().st_size:
            verification = verify_hash_chain(self.path)
            if not verification.valid:
                raise ValueError(
                    "Refusing to append to an invalid audit chain: "
                    f"line={verification.error_line}, reason={verification.reason}"
                )
            self._chain_index = verification.record_count
            self._previous_hash = verification.head_sha256

    def write(self, record: AuditRecord) -> None:
        with self._lock:
            payload = record.model_dump()
            if self.provenance is not None:
                payload["provenance"] = self.provenance.model_dump()
            result = payload.get("details", {}).get("result", {})
            payload["decision_reason"] = result.get("reason") if isinstance(result, dict) else None
            payload = redact_secrets(payload)
            if self.hash_chain:
                payload["chain_index"] = self._chain_index
                payload["previous_record_sha256"] = self._previous_hash
                record_hash = sha256_canonical(payload)
                payload["record_sha256"] = record_hash
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(payload) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            if self.hash_chain:
                self._previous_hash = record_hash
                self._chain_index += 1
