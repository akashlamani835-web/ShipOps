from uuid import uuid4

import pytest

from app.events.models import (
    EventRule,
    EventSeverity,
    EventStatus,
    OperationalEvent,
)
from app.incidents.models import (
    IncidentPriority,
    IncidentStatus,
)
from app.incidents.service import IncidentService


def create_operational_event(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    """Create an operational event for incident tests."""

    rule = EventRule(
        code=f"incident-test-rule-{uuid4().hex[:8]}",
        name="Incident Test Rule",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=packet_loss_metric.id,
        operator=">",
        threshold=30,
        duration_seconds=180,
        severity=EventSeverity.HIGH,
        active=True,
        description="Incident service test rule.",
    )

    db_session.add(rule)
    db_session.flush()

    event = OperationalEvent(
        asset_id=seeded_topology["switch"].id,
        rule_id=rule.id,
        event_type="NETWORK_DEGRADATION",
        severity=EventSeverity.HIGH,
        status=EventStatus.OPEN,
        occurred_at=__import__("datetime").datetime(
            2026,
            9,
            10,
            10,
            0,
            0,
            tzinfo=__import__("datetime").timezone.utc,
        ),
        summary="Switch degradation detected.",
        details={
            "rule_code": rule.code,
            "threshold": 30,
        },
    )

    db_session.add(event)
    db_session.flush()

    return event


def test_create_incident_from_operational_event(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Switch degradation",
        description="Investigate packet loss on SW-07.",
        priority=IncidentPriority.HIGH,
    )

    assert incident.incident_number == "INC-000001"
    assert incident.title == "Switch degradation"
    assert incident.description == (
        "Investigate packet loss on SW-07."
    )
    assert incident.priority == IncidentPriority.HIGH
    assert incident.status == IncidentStatus.OPEN
    assert incident.event_id == event.id
    assert incident.asset_id == event.asset_id
    assert incident.root_cause_asset_id is None
    assert incident.assigned_to is None


def test_same_event_cannot_create_two_incidents(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    service.create_incident(
        event_id=event.id,
        title="First incident",
        description=None,
        priority=IncidentPriority.MEDIUM,
    )

    with pytest.raises(
        ValueError,
        match="Incident already exists",
    ):
        service.create_incident(
            event_id=event.id,
            title="Second incident",
            description=None,
            priority=IncidentPriority.HIGH,
        )


def test_incident_numbers_increment(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event_one = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    event_two = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident_one = service.create_incident(
        event_id=event_one.id,
        title="Incident one",
        description=None,
        priority=IncidentPriority.LOW,
    )

    incident_two = service.create_incident(
        event_id=event_two.id,
        title="Incident two",
        description=None,
        priority=IncidentPriority.MEDIUM,
    )

    assert incident_one.incident_number == "INC-000001"
    assert incident_two.incident_number == "INC-000002"


def test_assign_incident_moves_it_to_in_progress(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Assignment test",
        description=None,
        priority=IncidentPriority.HIGH,
    )

    updated = service.assign_incident(
        incident.id,
        "network-operator",
    )

    assert updated.assigned_to == "network-operator"
    assert updated.status == IncidentStatus.IN_PROGRESS


def test_acknowledge_incident(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Acknowledgement test",
        description=None,
        priority=IncidentPriority.HIGH,
    )

    updated = service.acknowledge_incident(
        incident.id,
    )

    assert updated.status == IncidentStatus.IN_PROGRESS
    assert updated.acknowledged_at is not None


def test_resolve_incident(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Resolution test",
        description=None,
        priority=IncidentPriority.HIGH,
    )

    updated = service.resolve_incident(
        incident.id,
        resolution_summary="Replaced faulty switch uplink.",
    )

    assert updated.status == IncidentStatus.RESOLVED
    assert updated.resolved_at is not None
    assert updated.resolution_summary == (
        "Replaced faulty switch uplink."
    )


def test_resolved_incident_can_be_closed(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Close test",
        description=None,
        priority=IncidentPriority.MEDIUM,
    )

    service.resolve_incident(
        incident.id,
        resolution_summary="Issue resolved.",
    )

    updated = service.close_incident(
        incident.id,
    )

    assert updated.status == IncidentStatus.CLOSED


def test_unresolved_incident_cannot_be_closed(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Invalid close test",
        description=None,
        priority=IncidentPriority.LOW,
    )

    with pytest.raises(
        ValueError,
        match="Only resolved incidents can be closed",
    ):
        service.close_incident(
            incident.id,
        )


def test_resolved_incident_cannot_be_assigned(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="Resolved assignment test",
        description=None,
        priority=IncidentPriority.HIGH,
    )

    service.resolve_incident(
        incident.id,
        resolution_summary="Already resolved.",
    )

    with pytest.raises(
        ValueError,
        match="cannot be assigned",
    ):
        service.assign_incident(
            incident.id,
            "operator",
        )


def test_root_cause_can_be_attached_to_incident(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_operational_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    service = IncidentService(db_session)

    incident = service.create_incident(
        event_id=event.id,
        title="RCA attachment test",
        description=None,
        priority=IncidentPriority.HIGH,
    )

    updated = service.set_root_cause(
        incident.id,
        root_cause_asset_id=seeded_topology["switch"].id,
    )

    assert updated.root_cause_asset_id == (
        seeded_topology["switch"].id
    )


def test_missing_event_cannot_create_incident(
    db_session,
):
    service = IncidentService(db_session)

    with pytest.raises(
        ValueError,
        match="Operational event",
    ):
        service.create_incident(
            event_id=uuid4(),
            title="Invalid incident",
            description=None,
            priority=IncidentPriority.HIGH,
        )


def test_missing_incident_is_rejected(
    db_session,
):
    service = IncidentService(db_session)

    with pytest.raises(
        ValueError,
        match="Incident",
    ):
        service.acknowledge_incident(
            uuid4(),
        )