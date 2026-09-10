from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
        received_at = base_time + timedelta(seconds=2)

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


def test_event_engine_is_triggered_after_telemetry_persistence(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """A persisted telemetry sample is forwarded to the event engine."""

    asset = seeded_topology["switch"]

    event_service = Mock()

    service = TelemetryIngestionService(
        db_session,
        event_service=event_service,
    )

    request = build_request(
        value=38,
        idempotency_key="event-integration-500",
        source_sequence=500,
    )

    result = service.ingest(request)

    assert result.status == "accepted"
    assert result.idempotent_replay is False

    event_service.process_sample.assert_called_once()

    persisted_sample = (
        event_service.process_sample.call_args.args[0]
    )

    assert str(persisted_sample.asset_id) == str(asset.id)
    assert persisted_sample.value == 38
    assert persisted_sample.source_sequence == 500