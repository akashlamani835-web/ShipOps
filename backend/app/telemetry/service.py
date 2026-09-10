import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.events.service import EventService
from app.telemetry.cache import TelemetryCache
from app.telemetry.repository import TelemetryRepository
from app.telemetry.schemas import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)
from app.telemetry.validators import (
    TelemetryValidationError,
    validate_request,
)


logger = logging.getLogger(__name__)


class TelemetryIngestionService:
    """Validate, persist, cache, and evaluate incoming telemetry."""

    def __init__(
        self,
        db: Session,
        cache: TelemetryCache | None = None,
        event_service: EventService | None = None,
    ) -> None:
        self._db = db
        self._repository = TelemetryRepository(db)
        self._cache = cache or TelemetryCache()
        self._event_service = event_service or EventService(db)

    def ingest(
        self,
        request: TelemetryIngestRequest,
    ) -> TelemetryIngestResponse:
        """
        Validate and persist a telemetry sample.

        PostgreSQL is the durable source of truth.
        Redis is a best-effort latest-value cache.

        Event processing happens after the telemetry sample has
        been created. Event processing is isolated in a nested
        transaction so an event-processing failure cannot roll
        back the telemetry persistence.
        """

        asset = self._repository.get_asset_by_identifier(
            request.asset_identifier,
        )

        if asset is None:
            raise TelemetryValidationError(
                f"Asset '{request.asset_identifier}' not found.",
            )

        metric_definition = self._repository.get_metric_by_code(
            request.metric,
        )

        if metric_definition is None:
            raise TelemetryValidationError(
                f"Metric '{request.metric}' not found.",
            )

        validate_request(
            request,
            metric_definition,
        )

        existing_sample = (
            self._repository.get_sample_by_idempotency_key(
                request.idempotency_key,
            )
        )

        if existing_sample is not None:
            return TelemetryIngestResponse(
                status="accepted",
                telemetry_id=str(existing_sample.id),
                asset_identifier=asset.identifier,
                metric=metric_definition.code,
                idempotent_replay=True,
            )

        existing_sequence = (
            self._repository.get_sample_by_source_sequence(
                asset_id=asset.id,
                source=request.source,
                source_sequence=request.source_sequence,
            )
        )

        if existing_sequence is not None:
            return TelemetryIngestResponse(
                status="accepted",
                telemetry_id=str(existing_sequence.id),
                asset_identifier=asset.identifier,
                metric=metric_definition.code,
                idempotent_replay=True,
            )

        try:
            sample = self._repository.create_sample(
                asset_id=asset.id,
                metric_definition_id=metric_definition.id,
                value=request.value,
                observed_at=request.observed_at,
                received_at=request.received_at,
                source=request.source,
                source_sequence=request.source_sequence,
                quality=request.quality.lower(),
                idempotency_key=request.idempotency_key,
                extra_data=request.extra_data,
            )
        except IntegrityError:
            self._db.rollback()

            existing_sample = (
                self._repository.get_sample_by_idempotency_key(
                    request.idempotency_key,
                )
            )

            if existing_sample is not None:
                return TelemetryIngestResponse(
                    status="accepted",
                    telemetry_id=str(existing_sample.id),
                    asset_identifier=asset.identifier,
                    metric=metric_definition.code,
                    idempotent_replay=True,
                )

            existing_sequence = (
                self._repository.get_sample_by_source_sequence(
                    asset_id=asset.id,
                    source=request.source,
                    source_sequence=request.source_sequence,
                )
            )

            if existing_sequence is not None:
                return TelemetryIngestResponse(
                    status="accepted",
                    telemetry_id=str(existing_sequence.id),
                    asset_identifier=asset.identifier,
                    metric=metric_definition.code,
                    idempotent_replay=True,
                )

            raise

        self._cache.set_latest(
            asset_id=sample.asset_id,
            metric_code=metric_definition.code,
            value=sample.value,
            unit=metric_definition.unit,
            observed_at=sample.observed_at,
            received_at=sample.received_at,
            source=sample.source,
            quality=sample.quality,
            source_sequence=sample.source_sequence,
            telemetry_id=sample.id,
        )

        try:
            with self._db.begin_nested():
                self._event_service.process_sample(sample)
        except Exception:
            logger.exception(
                "Event processing failed after telemetry persistence",
                extra={
                    "telemetry_id": str(sample.id),
                    "asset_id": str(sample.asset_id),
                    "metric": metric_definition.code,
                },
            )

        return TelemetryIngestResponse(
            status="accepted",
            telemetry_id=str(sample.id),
            asset_identifier=asset.identifier,
            metric=metric_definition.code,
            idempotent_replay=False,
        )