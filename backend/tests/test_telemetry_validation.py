from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.telemetry.models import MetricDefinition
from app.telemetry.schemas import TelemetryIngestRequest
from app.telemetry.validators import (
    TelemetryValidationError,
    validate_request,
)


def build_metric(
    *,
    active: bool = True,
) -> MetricDefinition:
    return MetricDefinition(
        id=uuid4(),
        code="packet_loss",
        name="Packet Loss",
        unit="percent",
        minimum_value=0,
        maximum_value=100,
        active=active,
    )


def build_request(
    *,
    value: float = 38,
    unit: str = "percent",
    quality: str = "good",
    observed_offset_seconds: int = 0,
    received_offset_seconds: int = 2,
    source_sequence: int = 1,
) -> TelemetryIngestRequest:
    base_time = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    return TelemetryIngestRequest(
        asset_identifier="SW-07",
        metric="packet_loss",
        value=value,
        unit=unit,
        observed_at=base_time.replace(
            second=observed_offset_seconds,
        ),
        received_at=base_time.replace(
            second=received_offset_seconds,
        ),
        source="simulator",
        source_sequence=source_sequence,
        quality=quality,
        idempotency_key=f"test-{uuid4()}",
    )


def test_valid_request_passes():
    request = build_request()

    validate_request(
        request,
        build_metric(),
    )


def test_value_above_metric_range_is_rejected():
    request = build_request(value=101)

    with pytest.raises(TelemetryValidationError):
        validate_request(
            request,
            build_metric(),
        )


def test_value_below_metric_range_is_rejected():
    request = build_request(value=-1)

    with pytest.raises(TelemetryValidationError):
        validate_request(
            request,
            build_metric(),
        )


def test_unit_mismatch_is_rejected():
    request = build_request(unit="milliseconds")

    with pytest.raises(TelemetryValidationError):
        validate_request(
            request,
            build_metric(),
        )


def test_inactive_metric_is_rejected():
    request = build_request()

    with pytest.raises(TelemetryValidationError):
        validate_request(
            request,
            build_metric(active=False),
        )


def test_invalid_quality_is_rejected():
    request = build_request(quality="unknown")

    with pytest.raises(TelemetryValidationError):
        validate_request(
            request,
            build_metric(),
        )


def test_observed_after_received_is_rejected():
    request = build_request(
        observed_offset_seconds=10,
        received_offset_seconds=2,
    )

    with pytest.raises(TelemetryValidationError):
        validate_request(
            request,
            build_metric(),
        )


def test_negative_source_sequence_is_rejected():
    with pytest.raises(ValueError):
        build_request(source_sequence=-1)