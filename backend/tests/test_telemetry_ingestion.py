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
from app.telemetry.models import TelemetrySample
from app.telemetry.schemas import TelemetryIngestRequest
from app.telemetry.service import TelemetryIngestionService
from app.telemetry.validators import TelemetryValidationError


def build_request(
    *,
    value: float = 38,
    unit: str = "percent",
    quality: str = "good",
    observed_at: datetime | None = None,
    received_at: datetime | None = None,
    idempotency_key: str = "test-sample-001",
    source: str = "simulator",
    source_sequence: int = 1,
) -> TelemetryIngestRequest:
    """Build a valid telemetry request for tests."""

    base_time = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    if observed_at is None:
        observed_at = base_time

    if received_at is None:
        received_at = observed_at + timedelta(seconds=2)

    return TelemetryIngestRequest(
        asset_identifier="SW-07",
        metric="packet_loss",
        value=value,
        unit=unit,
        observed_at=observed_at,
        received_at=received_at,
        source=source,
        source_sequence=source_sequence,
        quality=quality,
        idempotency_key=idempotency_key,
    )


def build_event_rule(
    metric_id,
    *,
    duration_seconds: int = 180,
    threshold: float = 30,
    active: bool = True,
) -> EventRule:
    """Build a deterministic packet-loss event rule."""

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


def test_valid_telemetry_is_persisted(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    request = build_request(
        value=38,
        idempotency_key="valid-sample-001",
        source_sequence=1,
    )

    result = service.ingest(request)

    assert result.status == "accepted"
    assert result.idempotent_replay is False
    assert result.telemetry_id is not None

    sample = db_session.scalar(
        select(TelemetrySample).where(
            TelemetrySample.idempotency_key == "valid-sample-001",
        )
    )

    assert sample is not None
    assert sample.value == 38
    assert sample.source == "simulator"
    assert sample.source_sequence == 1
    assert sample.quality == "good"


def test_unknown_asset_is_rejected(
    db_session: Session,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    request = build_request(
        idempotency_key="unknown-asset-001",
        source_sequence=1,
    ).model_copy(
        update={
            "asset_identifier": "DOES-NOT-EXIST",
        }
    )

    with pytest.raises(
        TelemetryValidationError,
        match="Asset 'DOES-NOT-EXIST' not found",
    ):
        service.ingest(request)


def test_unknown_metric_is_rejected(
    db_session: Session,
    seeded_topology,
):
    service = TelemetryIngestionService(db_session)

    request = build_request(
        idempotency_key="unknown-metric-001",
        source_sequence=1,
    ).model_copy(
        update={
            "metric": "does_not_exist",
        }
    )

    with pytest.raises(
        TelemetryValidationError,
        match="Metric 'does_not_exist' not found",
    ):
        service.ingest(request)


def test_wrong_unit_is_rejected(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    request = build_request(
        unit="milliseconds",
        idempotency_key="wrong-unit-001",
        source_sequence=1,
    )

    with pytest.raises(
        TelemetryValidationError,
        match="Unit mismatch",
    ):
        service.ingest(request)


def test_out_of_range_value_is_rejected(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    request = build_request(
        value=101,
        idempotency_key="out-of-range-001",
        source_sequence=1,
    )

    with pytest.raises(
        TelemetryValidationError,
        match="above the maximum",
    ):
        service.ingest(request)


def test_inactive_metric_is_rejected(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    packet_loss_metric.active = False
    db_session.flush()

    service = TelemetryIngestionService(db_session)

    request = build_request(
        idempotency_key="inactive-metric-001",
        source_sequence=1,
    )

    with pytest.raises(
        TelemetryValidationError,
        match="inactive",
    ):
        service.ingest(request)


def test_delayed_telemetry_is_accepted(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    observed_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    received_at = observed_at + timedelta(minutes=7)

    request = build_request(
        observed_at=observed_at,
        received_at=received_at,
        idempotency_key="delayed-sample-001",
        source_sequence=1,
    )

    result = service.ingest(request)

    assert result.status == "accepted"
    assert result.idempotent_replay is False


def test_duplicate_idempotency_key_returns_existing_sample(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    first_request = build_request(
        value=38,
        idempotency_key="duplicate-sample-001",
        source_sequence=1,
    )

    first_result = service.ingest(first_request)

    second_request = build_request(
        value=42,
        idempotency_key="duplicate-sample-001",
        source_sequence=2,
    )

    second_result = service.ingest(second_request)

    assert first_result.telemetry_id == second_result.telemetry_id
    assert first_result.idempotent_replay is False
    assert second_result.idempotent_replay is True

    count = db_session.scalar(
        select(func.count())
        .select_from(TelemetrySample)
        .where(
            TelemetrySample.idempotency_key
            == "duplicate-sample-001"
        )
    )

    assert count == 1


def test_duplicate_source_sequence_returns_existing_sample(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    first_request = build_request(
        value=38,
        idempotency_key="sequence-first-001",
        source="edge_gateway",
        source_sequence=104,
    )

    first_result = service.ingest(first_request)

    replay_request = build_request(
        value=42,
        idempotency_key="sequence-replay-001",
        source="edge_gateway",
        source_sequence=104,
    )

    replay_result = service.ingest(replay_request)

    assert first_result.telemetry_id == replay_result.telemetry_id
    assert replay_result.idempotent_replay is True


def test_out_of_order_sequence_is_accepted(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    service = TelemetryIngestionService(db_session)

    first = build_request(
        value=38,
        idempotency_key="sequence-105",
        source="edge_gateway",
        source_sequence=105,
    )

    second = build_request(
        value=37,
        idempotency_key="sequence-103",
        source="edge_gateway",
        source_sequence=103,
    )

    first_result = service.ingest(first)
    second_result = service.ingest(second)

    assert first_result.idempotent_replay is False
    assert second_result.idempotent_replay is False
    assert first_result.telemetry_id != second_result.telemetry_id

    count = db_session.scalar(
        select(func.count())
        .select_from(TelemetrySample)
        .where(
            TelemetrySample.source == "edge_gateway"
        )
    )

    assert count == 2


def test_event_engine_creates_real_event_after_sustained_telemetry(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """
    Telemetry ingestion automatically invokes the real EventService.

    Three telemetry samples remain above the event threshold for the
    required duration, causing a real OperationalEvent and evidence
    records to be created.
    """

    asset = seeded_topology["switch"]

    rule = build_event_rule(
        packet_loss_metric.id,
        duration_seconds=180,
        threshold=30,
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

    service = TelemetryIngestionService(db_session)

    requests = [
        build_request(
            value=38,
            observed_at=start,
            received_at=start + timedelta(seconds=2),
            idempotency_key="event-e2e-001",
            source_sequence=1,
        ),
        build_request(
            value=41,
            observed_at=start + timedelta(minutes=1),
            received_at=start + timedelta(minutes=1, seconds=2),
            idempotency_key="event-e2e-002",
            source_sequence=2,
        ),
        build_request(
            value=37,
            observed_at=start + timedelta(minutes=3),
            received_at=start + timedelta(minutes=3, seconds=2),
            idempotency_key="event-e2e-003",
            source_sequence=3,
        ),
    ]

    results = [
        service.ingest(request)
        for request in requests
    ]

    assert all(
        result.status == "accepted"
        for result in results
    )

    assert all(
        result.idempotent_replay is False
        for result in results
    )

    event = db_session.scalar(
        select(OperationalEvent).where(
            OperationalEvent.rule_id == rule.id,
            OperationalEvent.asset_id == asset.id,
        )
    )

    assert event is not None
    assert event.status == EventStatus.OPEN
    assert event.event_type == "NETWORK_DEGRADATION"
    assert event.severity == EventSeverity.HIGH
    assert event.occurred_at == start + timedelta(minutes=3)

    evidence = list(
        db_session.scalars(
            select(EventEvidence)
            .where(
                EventEvidence.event_id == event.id,
            )
            .order_by(EventEvidence.telemetry_sample_id)
        )
    )

    assert len(evidence) == 3

    evidence_sample_ids = {
        item.telemetry_sample_id
        for item in evidence
    }

    telemetry_samples = list(
        db_session.scalars(
            select(TelemetrySample)
            .where(
                TelemetrySample.asset_id == asset.id,
                TelemetrySample.idempotency_key.in_(
                    [
                        "event-e2e-001",
                        "event-e2e-002",
                        "event-e2e-003",
                    ]
                ),
            )
        )
    )

    assert len(telemetry_samples) == 3

    assert evidence_sample_ids == {
        sample.id
        for sample in telemetry_samples
    }


def test_event_engine_does_not_create_event_before_duration_is_met(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """A threshold breach shorter than the required duration creates no event."""

    rule = build_event_rule(
        packet_loss_metric.id,
        duration_seconds=180,
        threshold=30,
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

    service = TelemetryIngestionService(db_session)

    requests = [
        build_request(
            value=40,
            observed_at=start,
            received_at=start + timedelta(seconds=2),
            idempotency_key="no-event-e2e-001",
            source_sequence=1,
        ),
        build_request(
            value=42,
            observed_at=start + timedelta(minutes=1),
            received_at=start + timedelta(minutes=1, seconds=2),
            idempotency_key="no-event-e2e-002",
            source_sequence=2,
        ),
        build_request(
            value=41,
            observed_at=start + timedelta(minutes=2),
            received_at=start + timedelta(minutes=2, seconds=2),
            idempotency_key="no-event-e2e-003",
            source_sequence=3,
        ),
    ]

    for request in requests:
        result = service.ingest(request)
        assert result.status == "accepted"

    event_count = db_session.scalar(
        select(func.count())
        .select_from(OperationalEvent)
        .where(
            OperationalEvent.rule_id == rule.id,
        )
    )

    assert event_count == 0


def test_duplicate_telemetry_does_not_create_duplicate_event(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """Idempotent telemetry replay does not create duplicate events."""

    asset = seeded_topology["switch"]

    rule = build_event_rule(
        packet_loss_metric.id,
        duration_seconds=180,
        threshold=30,
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

    service = TelemetryIngestionService(db_session)

    first_request = build_request(
        value=38,
        observed_at=start,
        received_at=start + timedelta(seconds=2),
        idempotency_key="duplicate-event-e2e-001",
        source_sequence=1,
    )

    second_request = build_request(
        value=41,
        observed_at=start + timedelta(minutes=1),
        received_at=start + timedelta(minutes=1, seconds=2),
        idempotency_key="duplicate-event-e2e-002",
        source_sequence=2,
    )

    third_request = build_request(
        value=37,
        observed_at=start + timedelta(minutes=3),
        received_at=start + timedelta(minutes=3, seconds=2),
        idempotency_key="duplicate-event-e2e-003",
        source_sequence=3,
    )

    first_result = service.ingest(first_request)
    second_result = service.ingest(second_request)
    third_result = service.ingest(third_request)

    assert first_result.idempotent_replay is False
    assert second_result.idempotent_replay is False
    assert third_result.idempotent_replay is False

    replay_result = service.ingest(
        third_request.model_copy(
            update={
                "value": 99,
            }
        )
    )

    assert replay_result.idempotent_replay is True
    assert replay_result.telemetry_id == third_result.telemetry_id

    event_count = db_session.scalar(
        select(func.count())
        .select_from(OperationalEvent)
        .where(
            OperationalEvent.rule_id == rule.id,
            OperationalEvent.asset_id == asset.id,
            OperationalEvent.status.in_(
                [
                    EventStatus.OPEN,
                    EventStatus.ACKNOWLEDGED,
                ]
            ),
        )
    )

    assert event_count == 1