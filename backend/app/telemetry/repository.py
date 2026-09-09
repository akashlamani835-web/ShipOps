from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.telemetry.models import MetricDefinition, TelemetrySample


class TelemetryRepository:
    """Database operations for telemetry ingestion."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_asset_by_identifier(
        self,
        identifier: str,
    ) -> Asset | None:
        """Return an asset by its human-readable identifier."""
        return self._db.scalar(
            select(Asset).where(
                Asset.identifier == identifier,
            )
        )

    def get_metric_by_code(
        self,
        code: str,
    ) -> MetricDefinition | None:
        """Return a metric definition by its unique code."""
        return self._db.scalar(
            select(MetricDefinition).where(
                MetricDefinition.code == code,
            )
        )

    def get_sample_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> TelemetrySample | None:
        """Return an existing sample for an idempotency key."""
        return self._db.scalar(
            select(TelemetrySample).where(
                TelemetrySample.idempotency_key == idempotency_key,
            )
        )

    def get_sample_by_source_sequence(
        self,
        *,
        asset_id,
        source: str,
        source_sequence: int,
    ) -> TelemetrySample | None:
        """Return an existing sample for an asset/source sequence."""
        return self._db.scalar(
            select(TelemetrySample).where(
                TelemetrySample.asset_id == asset_id,
                TelemetrySample.source == source,
                TelemetrySample.source_sequence == source_sequence,
            )
        )

    def create_sample(
        self,
        *,
        asset_id,
        metric_definition_id,
        value: float,
        observed_at,
        received_at,
        source: str,
        source_sequence: int,
        quality: str,
        idempotency_key: str,
        extra_data: dict | None,
    ) -> TelemetrySample:
        """Create and flush a telemetry sample."""
        sample = TelemetrySample(
            asset_id=asset_id,
            metric_definition_id=metric_definition_id,
            value=value,
            observed_at=observed_at,
            received_at=received_at,
            source=source,
            source_sequence=source_sequence,
            quality=quality,
            idempotency_key=idempotency_key,
            extra_data=extra_data,
        )

        self._db.add(sample)
        self._db.flush()

        return sample