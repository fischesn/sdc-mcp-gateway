from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sdc_mcp_gateway.models import AlarmState, ContextState, DeviceSnapshot, MetricState, utc_now_iso


class MdibSnapshotExtractor:
    """Best-effort extraction of read-only information from an sdc11073 ConsumerMdib.

    The sdc11073 object model exposes BICEPS containers rather than a flat Python dict.
    This extractor intentionally uses defensive introspection and conservative fallbacks so
    that a snapshot can still be captured when device-specific descriptors differ.
    """

    def extract(self, mdib: Any, provider_epr: str | None = None, display_name: str | None = None) -> DeviceSnapshot:
        descriptors = list(_iter_container_items(_safe_getattr(mdib, "descriptions")))
        states = list(_iter_container_items(_safe_getattr(mdib, "states")))
        descriptors_by_handle = _descriptors_by_handle(descriptors)

        metrics = self._extract_metrics(states, descriptors_by_handle)
        alarms = self._extract_alarms(states, descriptors_by_handle)
        context = self._extract_context(states)
        device_id = _safe_identifier(provider_epr or _first_non_empty(_safe_getattr(mdib, "sequence_id"), display_name) or "sdc-provider")

        return DeviceSnapshot(
            device_id=device_id,
            display_name=display_name or self._extract_display_name(descriptors) or device_id,
            manufacturer=self._extract_manufacturer(descriptors),
            model=self._extract_model(descriptors),
            metrics=metrics,
            alarms=alarms,
            context=context,
            raw_mdib=self._summarize_raw_mdib(provider_epr, descriptors, states),
            observed_at=utc_now_iso(),
        )

    def _extract_metrics(self, states: list[Any], descriptors_by_handle: dict[str, Any]) -> list[MetricState]:
        metrics: list[MetricState] = []
        for state in states:
            type_name = _type_name(state)
            if "MetricState" not in type_name and "RealTimeSampleArray" not in type_name:
                continue
            descriptor_handle = _as_str(_first_non_empty(
                _safe_getattr(state, "DescriptorHandle"),
                _safe_getattr(state, "descriptor_handle"),
                _safe_getattr(state, "Handle"),
            )) or f"metric-{len(metrics)}"
            descriptor = descriptors_by_handle.get(descriptor_handle)
            metric_value = _safe_getattr(state, "MetricValue")
            value = _simple_value(_first_non_empty(
                _safe_getattr(metric_value, "Value"),
                _safe_getattr(metric_value, "Samples"),
                _safe_getattr(state, "Value"),
            ))
            timestamp = _as_str(_first_non_empty(
                _safe_getattr(metric_value, "DeterminationTime"),
                _safe_getattr(metric_value, "StartTime"),
                _safe_getattr(state, "DeterminationTime"),
            )) or utc_now_iso()
            metrics.append(
                MetricState(
                    handle=descriptor_handle,
                    code=_extract_code(descriptor),
                    value=value,
                    unit=_extract_unit(descriptor),
                    timestamp=timestamp,
                    validity=_as_str(_first_non_empty(
                        _safe_getattr(metric_value, "Validity"),
                        _safe_getattr(state, "Validity"),
                    )),
                    raw={
                        "state_type": type_name,
                        "descriptor_type": _type_name(descriptor) if descriptor is not None else None,
                    },
                )
            )
        return metrics

    def _extract_alarms(self, states: list[Any], descriptors_by_handle: dict[str, Any]) -> list[AlarmState]:
        alarms: list[AlarmState] = []
        for state in states:
            type_name = _type_name(state)
            if "Alert" not in type_name:
                continue
            descriptor_handle = _as_str(_first_non_empty(
                _safe_getattr(state, "DescriptorHandle"),
                _safe_getattr(state, "descriptor_handle"),
                _safe_getattr(state, "Handle"),
            )) or f"alarm-{len(alarms)}"
            descriptor = descriptors_by_handle.get(descriptor_handle)
            alarms.append(
                AlarmState(
                    handle=descriptor_handle,
                    code=_extract_code(descriptor),
                    presence=_to_bool(_safe_getattr(state, "Presence")),
                    priority=_as_str(_first_non_empty(
                        _safe_getattr(state, "Priority"),
                        _safe_getattr(descriptor, "Priority"),
                    )),
                    kind=_as_str(_first_non_empty(
                        _safe_getattr(state, "Kind"),
                        _safe_getattr(descriptor, "Kind"),
                    )),
                    timestamp=utc_now_iso(),
                    raw={
                        "state_type": type_name,
                        "descriptor_type": _type_name(descriptor) if descriptor is not None else None,
                    },
                )
            )
        return alarms

    def _extract_context(self, states: list[Any]) -> ContextState:
        raw_context: list[dict[str, Any]] = []
        patient_ref = None
        location_ref = None
        operator_ref = None
        workflow_ref = None
        for state in states:
            type_name = _type_name(state)
            if "ContextState" not in type_name:
                continue
            handle = _as_str(_first_non_empty(
                _safe_getattr(state, "DescriptorHandle"),
                _safe_getattr(state, "Handle"),
            ))
            association = _as_str(_safe_getattr(state, "ContextAssociation"))
            raw_context.append({"handle": handle, "type": type_name, "association": association})
            lower = type_name.lower()
            if "patient" in lower:
                patient_ref = handle or patient_ref
            elif "location" in lower:
                location_ref = handle or location_ref
            elif "operator" in lower:
                operator_ref = handle or operator_ref
            elif "workflow" in lower:
                workflow_ref = handle or workflow_ref
        return ContextState(
            patient_ref=patient_ref,
            location_ref=location_ref,
            operator_ref=operator_ref,
            workflow_ref=workflow_ref,
            raw={"context_states": raw_context},
        )

    def _extract_display_name(self, descriptors: list[Any]) -> str | None:
        for descriptor in descriptors:
            if "MdsDescriptor" in _type_name(descriptor):
                value = _first_non_empty(
                    _safe_getattr(descriptor, "FriendlyName"),
                    _safe_getattr(descriptor, "Type"),
                    _safe_getattr(descriptor, "Handle"),
                )
                return _as_str(value)
        return None

    def _extract_manufacturer(self, descriptors: list[Any]) -> str | None:
        for descriptor in descriptors:
            value = _first_non_empty(
                _safe_getattr(descriptor, "Manufacturer"),
                _safe_getattr(descriptor, "manufacturer"),
            )
            if value is not None:
                return _as_str(value)
        return None

    def _extract_model(self, descriptors: list[Any]) -> str | None:
        for descriptor in descriptors:
            value = _first_non_empty(_safe_getattr(descriptor, "ModelName"), _safe_getattr(descriptor, "model"))
            if value is not None:
                return _as_str(value)
        return None

    def _summarize_raw_mdib(self, provider_epr: str | None, descriptors: list[Any], states: list[Any]) -> dict[str, Any]:
        descriptor_types: dict[str, int] = {}
        state_types: dict[str, int] = {}
        for descriptor in descriptors:
            descriptor_types[_type_name(descriptor)] = descriptor_types.get(_type_name(descriptor), 0) + 1
        for state in states:
            state_types[_type_name(state)] = state_types.get(_type_name(state), 0) + 1
        return {
            "kind": "sdc11073-mdib-summary",
            "provider_epr": provider_epr,
            "descriptor_count": len(descriptors),
            "state_count": len(states),
            "descriptor_types": descriptor_types,
            "state_types": state_types,
            "note": "Raw device objects are summarized to avoid non-serializable sdc11073 internals.",
        }


def _iter_container_items(container: Any) -> Iterable[Any]:
    """Iterate over container-like sdc11073 MultiKeyLookup structures defensively."""
    if container is None:
        return []

    # Most useful case for sdc11073 MultiKeyLookup-like objects.
    for attr in ("objects", "_objects", "_data"):
        value = _safe_getattr(container, attr)
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, list | tuple | set):
            return list(value)

    if isinstance(container, dict):
        return list(container.values())
    if isinstance(container, list | tuple | set):
        return list(container)

    # Last-resort fallback: try common collection views.
    values = getattr(container, "values", None)
    if callable(values):
        try:
            return list(values())
        except Exception:
            pass
    return []


def _descriptors_by_handle(descriptors: list[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for descriptor in descriptors:
        handle = _as_str(_first_non_empty(_safe_getattr(descriptor, "Handle"), _safe_getattr(descriptor, "handle")))
        if handle:
            result[handle] = descriptor
    return result


def _extract_code(descriptor: Any) -> str | None:
    if descriptor is None:
        return None
    for obj in (_safe_getattr(descriptor, "Type"), _safe_getattr(descriptor, "CodedValue"), descriptor):
        code = _first_non_empty(
            _safe_getattr(obj, "Code"),
            _safe_getattr(obj, "code"),
            _safe_getattr(obj, "CodingSystem"),
        )
        if code is not None:
            return _as_str(code)
    return None


def _extract_unit(descriptor: Any) -> str | None:
    if descriptor is None:
        return None
    unit = _safe_getattr(descriptor, "Unit")
    if unit is None:
        return None
    return _as_str(_first_non_empty(_safe_getattr(unit, "Code"), _safe_getattr(unit, "code"), unit))


def _safe_getattr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    try:
        return getattr(obj, name)
    except Exception:
        return None


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _type_name(obj: Any) -> str:
    if obj is None:
        return "None"
    return type(obj).__name__


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _simple_value(value: Any) -> float | int | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int | float | str):
        return value
    if isinstance(value, list | tuple):
        return ",".join(str(item) for item in value[:8])
    return str(value)


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).lower()
    if text in {"true", "1", "on", "present", "yes"}:
        return True
    if text in {"false", "0", "off", "not_present", "no"}:
        return False
    return None


def _safe_identifier(value: str) -> str:
    sanitized = value.replace("urn:uuid:", "").replace(":", "-").replace("/", "-")
    return sanitized or "sdc-provider"
