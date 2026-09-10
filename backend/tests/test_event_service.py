from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import (
    EventEvidence,
    EventRule,
    EventSeverity,
    EventStatus,
    OperationalEvent,
)
from app.events.service import EventService
from app.telemetry.models import MetricDefinition, TelemetrySample


def build_rule(
    metric_id,
    *,
    duration_seconds: int = 180,
    threshold: float = 30,
    active: bool = True,
) -> EventRule:
    """Build a deterministic high packet-loss event rule."""

    return EventRule(
        code="packet_loss_high",
        name="High Packet Loss",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=metric_id,
        operator=">",
        threshold=threshold,
        duration_seconds=duration_seconds,
        severity=EventSeverity.HIGH,
        active=active,
        description="Detect sustained packet loss.",
    )


def build_sample(
    *,
    asset_id,
    metric_id,
    value: float,
    observed_at: datetime,
    source_sequence: int,
) -> TelemetrySample:
    """Build a telemetry sample for event-service tests."""

    return TelemetrySample(
        asset_id=asset_id,
        metric_definition_id=metric_id,
        value=value,
        observed_at=observed_at,
        received_at=observed_at + timedelta(seconds=1),
        source="edge_gateway",
        source_sequence=source_sequence,
        quality="good",
        idempotency_key=(
            f"event-test-{source_sequence}-{value}"
        ),
    )


def create_sustained_event(
    db_session: Session,
    asset,
    metric,
) -> tuple[EventService, EventRule, list[TelemetrySample]]:
    """Create the event state used by lifecycle tests."""

    rule = build_rule(
        metric.id,
        duration_seconds=180,
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

    samples = [
        build_sample(
            asset_id=asset.id,
            metric_id=metric.id,
            value=38,
            observed_at=start,
            source_sequence=1,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=metric.id,
            value=41,
            observed_at=start + timedelta(minutes=1),
            source_sequence=2,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=metric.id,
            value=37,
            observed_at=start + timedelta(minutes=3),
            source_sequence=3,
        ),
    ]

    db_session.add_all(samples)
    db_session.flush()

    service = EventService(db_session)

    created_events: list[OperationalEvent] = []

    for sample in samples:
        created_events.extend(
            service.process_sample(sample)
        )

    assert len(created_events) == 1

    return service, rule, samples


def test_no_event_when_condition_is_below_threshold(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    asset = seeded_topology["switch"]

    rule = build_rule(packet_loss_metric.id)

    db_session.add(rule)
    db_session.flush()

    observed_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    sample = build_sample(
        asset_id=asset.id,
        metric_id=packet_loss_metric.id,
        value=10,
        observed_at=observed_at,
        source_sequence=1,
    )

    db_session.add(sample)
    db_session.flush()

    service = EventService(db_session)

    assert service.process_sample(sample) == []


def test_no_event_when_condition_is_not_sustained(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    asset = seeded_topology["switch"]

    rule = build_rule(
        packet_loss_metric.id,
        duration_seconds=180,
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

    samples = [
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=38,
            observed_at=start,
            source_sequence=1,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=41,
            observed_at=start + timedelta(minutes=1),
            source_sequence=2,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=37,
            observed_at=start + timedelta(minutes=2),
            source_sequence=3,
        ),
    ]

    db_session.add_all(samples)
    db_session.flush()

    service = EventService(db_session)

    for sample in samples:
        assert service.process_sample(sample) == []


def test_event_created_after_sustained_breach(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    events = service._repository._db.scalars(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    ).all()

    assert len(events) == 1
    assert events[0].status == EventStatus.OPEN
    assert events[0].occurred_at == samples[-1].observed_at


def test_event_evidence_is_created(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None

    evidence = list(
        db_session.scalars(
            select(EventEvidence).where(
                EventEvidence.event_id == event.id,
            )
        )
    )

    assert len(evidence) == 3
    assert {
        item.telemetry_sample_id
        for item in evidence
    } == {
        sample.id
        for sample in samples
    }


def test_repeated_matching_samples_do_not_create_duplicate_open_events(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    later_sample = build_sample(
        asset_id=seeded_topology["switch"].id,
        metric_id=packet_loss_metric.id,
        value=39,
        observed_at=(
            samples[-1].observed_at
            + timedelta(minutes=1)
        ),
        source_sequence=4,
    )

    db_session.add(later_sample)
    db_session.flush()

    assert service.process_sample(later_sample) == []

    event_count = db_session.scalar(
        select(func.count())
        .select_from(OperationalEvent)
        .where(
            OperationalEvent.asset_id
            == seeded_topology["switch"].id,
            OperationalEvent.rule_id == rule.id,
            OperationalEvent.status.in_(
                [
                    EventStatus.OPEN,
                    EventStatus.ACKNOWLEDGED,
                ]
            ),
        )
    )

    assert event_count == 1


def test_inactive_rule_creates_no_event(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    asset = seeded_topology["switch"]

    rule = build_rule(
        packet_loss_metric.id,
        active=False,
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

    samples = [
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=50,
            observed_at=start,
            source_sequence=1,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=50,
            observed_at=start + timedelta(minutes=3),
            source_sequence=2,
        ),
    ]

    db_session.add_all(samples)
    db_session.flush()

    service = EventService(db_session)

    for sample in samples:
        assert service.process_sample(sample) == []


def test_event_rule_is_specific_to_its_metric(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    asset = seeded_topology["switch"]

    other_metric = MetricDefinition(
        code="latency",
        name="Latency",
        unit="milliseconds",
        minimum_value=0,
        maximum_value=5000,
        description="Network latency.",
        active=True,
    )

    db_session.add(other_metric)
    db_session.flush()

    rule = build_rule(
        packet_loss_metric.id,
        duration_seconds=180,
    )

    db_session.add(rule)
    db_session.flush()

    sample = build_sample(
        asset_id=asset.id,
        metric_id=other_metric.id,
        value=500,
        observed_at=datetime(
            2026,
            9,
            9,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        source_sequence=1,
    )

    db_session.add(sample)
    db_session.flush()

    service = EventService(db_session)

    assert service.process_sample(sample) == []


def test_open_event_can_be_acknowledged(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, _ = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None
    assert event.status == EventStatus.OPEN

    updated = service.acknowledge_event(event.id)

    assert updated.status == EventStatus.ACKNOWLEDGED
    assert updated.resolved_at is None


def test_acknowledged_event_can_be_resolved(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, _ = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None

    service.acknowledge_event(event.id)

    resolved_at = datetime(
        2026,
        9,
        9,
        13,
        0,
        0,
        tzinfo=timezone.utc,
    )

    updated = service.resolve_event(
        event.id,
        resolved_at=resolved_at,
    )

    assert updated.status == EventStatus.RESOLVED
    assert updated.resolved_at == resolved_at


def test_open_event_can_be_resolved_directly(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None

    resolved_at = samples[-1].observed_at + timedelta(
        minutes=5
    )

    updated = service.resolve_event(
        event.id,
        resolved_at=resolved_at,
    )

    assert updated.status == EventStatus.RESOLVED
    assert updated.resolved_at == resolved_at


def test_resolved_event_cannot_be_acknowledged_again(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None

    service.resolve_event(
        event.id,
        resolved_at=samples[-1].observed_at + timedelta(
            minutes=5
        ),
    )

    with pytest.raises(
        ValueError,
        match="Only open events can be acknowledged",
    ):
        service.acknowledge_event(event.id)


def test_resolved_event_cannot_be_resolved_again(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None

    resolved_at = samples[-1].observed_at + timedelta(
        minutes=5
    )

    service.resolve_event(
        event.id,
        resolved_at=resolved_at,
    )

    with pytest.raises(
        ValueError,
        match="already resolved",
    ):
        service.resolve_event(
            event.id,
            resolved_at=resolved_at + timedelta(
                minutes=1
            ),
        )


def test_resolution_before_occurrence_is_rejected(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service, rule, samples = create_sustained_event(
        db_session,
        seeded_topology["switch"],
        packet_loss_metric,
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event is not None

    invalid_resolved_at = (
        event.occurred_at - timedelta(seconds=1)
    )

    with pytest.raises(
        ValueError,
        match="resolved_at cannot be earlier",
    ):
        service.resolve_event(
            event.id,
            resolved_at=invalid_resolved_at,
        )