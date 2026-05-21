from __future__ import annotations

from sdc_mcp_gateway.sdc.extractor import MdibSnapshotExtractor


class CodedValue:
    def __init__(self, code: str) -> None:
        self.Code = code


class UnitValue:
    def __init__(self, code: str) -> None:
        self.Code = code


class NumericMetricDescriptor:
    def __init__(self) -> None:
        self.Handle = "metric.hr"
        self.Type = CodedValue("150456")
        self.Unit = UnitValue("beats/min")


class NumericMetricValue:
    def __init__(self) -> None:
        self.Value = 75
        self.Validity = "Valid"
        self.DeterminationTime = "2026-05-21T10:00:00Z"


class NumericMetricState:
    def __init__(self) -> None:
        self.DescriptorHandle = "metric.hr"
        self.MetricValue = NumericMetricValue()


class AlertConditionDescriptor:
    def __init__(self) -> None:
        self.Handle = "alarm.hr.high"
        self.Type = CodedValue("alarm.hr.high")
        self.Kind = "physiological"


class AlertConditionState:
    def __init__(self) -> None:
        self.DescriptorHandle = "alarm.hr.high"
        self.Presence = True
        self.Priority = "high"


class PatientContextState:
    def __init__(self) -> None:
        self.DescriptorHandle = "ctx.patient"
        self.ContextAssociation = "Assoc"


class Container:
    def __init__(self, *items: object) -> None:
        self.objects = {str(index): item for index, item in enumerate(items)}


class FakeMdib:
    def __init__(self) -> None:
        self.descriptions = Container(NumericMetricDescriptor(), AlertConditionDescriptor())
        self.states = Container(NumericMetricState(), AlertConditionState(), PatientContextState())


def test_extracts_metric_alarm_and_context_from_fake_mdib() -> None:
    snapshot = MdibSnapshotExtractor().extract(FakeMdib(), provider_epr="urn:uuid:test-provider")

    assert snapshot.device_id == "test-provider"
    assert len(snapshot.metrics) == 1
    assert snapshot.metrics[0].code == "150456"
    assert snapshot.metrics[0].value == 75
    assert snapshot.metrics[0].unit == "beats/min"
    assert len(snapshot.alarms) == 1
    assert snapshot.alarms[0].presence is True
    assert snapshot.context.patient_ref == "ctx.patient"
    assert snapshot.raw_mdib["descriptor_count"] == 2
    assert snapshot.raw_mdib["state_count"] == 3
