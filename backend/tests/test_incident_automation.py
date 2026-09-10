from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.events.models import EventRule, EventSeverity, OperationalEvent
from app.incidents.automation import IncidentAutomationService
from app.incidents.models import Incident, IncidentPriority
from app.rca.engine import RCAEngine
from app.telemetry.models import TelemetrySample
from app.telemetry.schemas import TelemetryIngestRequest
from app.telemetry.service import TelemetryIngestionService


def build_rule(
    metric_id,
    *,
    severity: EventSeverity,
) -> EventRule:
    """Build an event rule for incident-automation tests."""

    return EventRule(
        code=f"automation_{severity.value}",
        name=f"Automation {severity.value}",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=metric_id,
        operator=">",
        threshold=30,
        duration_seconds=180,
        severity=severity,
        active=True,
        description="Incident automation test rule.",
    )


def build_event(
    db_session,
    asset,
    metric,
    *,
    severity: EventSeverity,
) -> OperationalEvent:
    """Create a persisted operational event for automation tests."""

    rule = build_rule(
        metric.id,
        severity=severity,
    )

    db_session.add(rule)
    db_session.flush()

    event = OperationalEvent(
        asset_id=asset.id,
        rule_id=rule.id,
        event_type=rule.event_type,
        severity=rule.severity,
        status="open",
        occurred_at=datetime.now(timezone.utc),
        summary=f"{severity.value} automation test event",
        details={
            "rule_code": rule.code,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "duration_seconds": rule.duration_seconds,
        },
    )

    db_session.add(event)
    db_session.flush()

    return event


def build_ingest_request(
    *,
    observed_at: datetime,
    value: float,
    source_sequence: int,
) -> TelemetryIngestRequest:
    """Build a telemetry request for the end-to-end workflow test."""

    return TelemetryIngestRequest(
        asset_identifier="SW-07",
        metric="packet_loss",
        value=value,
        unit="percent",
        observed_at=observed_at,
        received_at=observed_at + timedelta(seconds=1),
        source="edge_gateway",
        source_sequence=source_sequence,
        quality="good",
        idempotency_key=f"incident-e2e-{source_sequence}",
        extra_data=None,
    )


def test_high_event_creates_incident(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = build_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
        severity=EventSeverity.HIGH,
    )

    automation = IncidentAutomationService(db_session)

    incident = automation.handle_event(event)

    assert incident is not None
    assert incident.event_id == event.id
    assert incident.asset_id == event.asset_id
    assert incident.priority == IncidentPriority.HIGH


def test_critical_event_creates_critical_incident(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = build_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
        severity=EventSeverity.CRITICAL,
    )

    automation = IncidentAutomationService(db_session)

    incident = automation.handle_event(event)

    assert incident is not None
    assert incident.priority == IncidentPriority.CRITICAL


@pytest.mark.parametrize(
    "severity",
    [
        EventSeverity.INFO,
        EventSeverity.LOW,
        EventSeverity.MEDIUM,
    ],
)
def test_lower_severity_event_does_not_create_incident(
    db_session,
    seeded_topology,
    packet_loss_metric,
    severity,
):
    event = build_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
        severity=severity,
    )

    automation = IncidentAutomationService(db_session)

    incident = automation.handle_event(event)

    assert incident is None

    stored_incident = db_session.scalar(
        select(Incident).where(
            Incident.event_id == event.id,
        )
    )

    assert stored_incident is None


def test_high_event_attempts_root_cause_from_rca(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = build_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
        severity=EventSeverity.HIGH,
    )

    expected_rca = RCAEngine(db_session).analyze(
        event.id,
    )

    automation = IncidentAutomationService(db_session)

    incident = automation.handle_event(event)

    assert incident is not None

    if expected_rca.root_cause_asset_id is not None:
        assert (
            incident.root_cause_asset_id
            == expected_rca.root_cause_asset_id
        )


def test_existing_incident_is_not_duplicated(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = build_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
        severity=EventSeverity.HIGH,
    )

    automation = IncidentAutomationService(db_session)

    first = automation.handle_event(event)
    second = automation.handle_event(event)

    assert first is not None
    assert second is not None
    assert second.id == first.id

    incidents = db_session.scalars(
        select(Incident).where(
            Incident.event_id == event.id,
        )
    ).all()

    assert len(incidents) == 1


def test_rca_failure_does_not_prevent_incident_creation(
    db_session,
    seeded_topology,
    packet_loss_metric,
    monkeypatch,
):
    event = build_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
        severity=EventSeverity.HIGH,
    )

    def failing_analyze(event_id):
        raise RuntimeError("Simulated RCA failure.")

    monkeypatch.setattr(
        RCAEngine,
        "analyze",
        failing_analyze,
    )

    automation = IncidentAutomationService(db_session)

    incident = automation.handle_event(event)

    assert incident is not None
    assert incident.event_id == event.id
    assert incident.root_cause_asset_id is None


def test_telemetry_to_event_to_incident_end_to_end(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    """
    Verify the real operational path:

    telemetry ingestion
        -> sustained event detection
        -> automatic incident creation
        -> RCA execution
    """

    rule = build_rule(
        packet_loss_metric.id,
        severity=EventSeverity.HIGH,
    )

    db_session.add(rule)
    db_session.flush()

    start = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    telemetry_service = TelemetryIngestionService(
        db_session,
    )

    requests = [
        build_ingest_request(
            observed_at=start,
            value=38,
            source_sequence=1,
        ),
        build_ingest_request(
            observed_at=start + timedelta(minutes=1),
            value=41,
            source_sequence=2,
        ),
        build_ingest_request(
            observed_at=start + timedelta(minutes=3),
            value=37,
            source_sequence=3,
        ),
    ]

    results = [
        telemetry_service.ingest(request)
        for request in requests
    ]

    assert all(
        result.status == "accepted"
        for result in results
    )

    events = db_session.scalars(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    ).all()

    assert len(events) == 1

    event = events[0]

    assert event.severity == EventSeverity.HIGH
    assert event.asset_id == seeded_topology["switch"].id

    incident = db_session.scalar(
        select(Incident).where(
            Incident.event_id == event.id,
        )
    )

    assert incident is not None
    assert incident.event_id == event.id
    assert incident.asset_id == event.asset_id
    assert incident.priority == IncidentPriority.HIGH