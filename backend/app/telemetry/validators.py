from app.telemetry.models import MetricDefinition
from app.telemetry.schemas import TelemetryIngestRequest


class TelemetryValidationError(ValueError):
    """Raised when a telemetry sample violates domain rules."""


VALID_QUALITIES = {
    "good",
    "estimated",
    "stale",
    "invalid",
}


def validate_timestamps(request: TelemetryIngestRequest) -> None:
    """Validate telemetry timestamp relationships and timezone awareness."""

    if request.observed_at.tzinfo is None:
        raise TelemetryValidationError(
            "observed_at must include timezone information.",
        )

    if request.received_at.tzinfo is None:
        raise TelemetryValidationError(
            "received_at must include timezone information.",
        )

    if request.observed_at > request.received_at:
        raise TelemetryValidationError(
            "observed_at cannot be later than received_at.",
        )


def validate_quality(request: TelemetryIngestRequest) -> None:
    """Validate the telemetry quality classification."""

    if request.quality.lower() not in VALID_QUALITIES:
        allowed = ", ".join(sorted(VALID_QUALITIES))

        raise TelemetryValidationError(
            f"quality must be one of: {allowed}.",
        )


def validate_metric(
    request: TelemetryIngestRequest,
    metric_definition: MetricDefinition,
) -> None:
    """Validate a sample against its metric definition."""

    if not metric_definition.active:
        raise TelemetryValidationError(
            f"Metric '{metric_definition.code}' is inactive.",
        )

    if request.unit != metric_definition.unit:
        raise TelemetryValidationError(
            (
                f"Unit mismatch for metric "
                f"'{metric_definition.code}': "
                f"expected '{metric_definition.unit}', "
                f"received '{request.unit}'."
            ),
        )

    if (
        metric_definition.minimum_value is not None
        and request.value < metric_definition.minimum_value
    ):
        raise TelemetryValidationError(
            (
                f"Value {request.value} is below the minimum "
                f"{metric_definition.minimum_value} for metric "
                f"'{metric_definition.code}'."
            ),
        )

    if (
        metric_definition.maximum_value is not None
        and request.value > metric_definition.maximum_value
    ):
        raise TelemetryValidationError(
            (
                f"Value {request.value} is above the maximum "
                f"{metric_definition.maximum_value} for metric "
                f"'{metric_definition.code}'."
            ),
        )


def validate_request(
    request: TelemetryIngestRequest,
    metric_definition: MetricDefinition,
) -> None:
    """Run all domain-level telemetry validations."""

    validate_timestamps(request)
    validate_quality(request)
    validate_metric(request, metric_definition)