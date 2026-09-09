import json
import logging
from datetime import datetime
from uuid import UUID

from redis import Redis

from app.core.redis import redis_client


logger = logging.getLogger(__name__)


class TelemetryCache:
    """Cache the latest known telemetry value for an asset and metric."""

    PREFIX = "shipops:telemetry:latest"

    def __init__(
        self,
        client: Redis | None = None,
    ) -> None:
        self._client = client or redis_client

    @classmethod
    def _key(
        cls,
        asset_id: UUID | str,
        metric_code: str,
    ) -> str:
        """Build the Redis key for the latest metric value."""
        return f"{cls.PREFIX}:{asset_id}:{metric_code}"

    def set_latest(
        self,
        *,
        asset_id: UUID | str,
        metric_code: str,
        value: float,
        unit: str,
        observed_at: datetime,
        received_at: datetime,
        source: str,
        quality: str,
        source_sequence: int,
        telemetry_id: UUID | str,
    ) -> bool:
        """
        Store the latest telemetry value.

        For samples from the same source, a lower source sequence
        cannot replace a higher sequence already in the cache.

        For different sources, the sample with the newer observed_at
        timestamp becomes the cached value.

        Redis is a best-effort cache; PostgreSQL remains the source
        of truth.
        """
        key = self._key(asset_id, metric_code)

        try:
            existing_raw = self._client.get(key)

            if existing_raw is not None:
                if isinstance(existing_raw, bytes):
                    existing_raw = existing_raw.decode("utf-8")

                existing = json.loads(existing_raw)

                existing_source = existing.get("source")
                existing_sequence = existing.get("source_sequence")
                existing_observed_at = existing.get("observed_at")

                # Same telemetry source: sequence determines ordering.
                if (
                    existing_source == source
                    and existing_sequence is not None
                    and source_sequence <= int(existing_sequence)
                ):
                    return True

                # Different source: compare observation time.
                if (
                    existing_source != source
                    and existing_observed_at is not None
                ):
                    try:
                        existing_time = datetime.fromisoformat(
                            existing_observed_at
                        )
                    except (TypeError, ValueError):
                        existing_time = None

                    if (
                        existing_time is not None
                        and observed_at <= existing_time
                    ):
                        return True

            payload = {
                "telemetry_id": str(telemetry_id),
                "asset_id": str(asset_id),
                "metric": metric_code,
                "value": value,
                "unit": unit,
                "observed_at": observed_at.isoformat(),
                "received_at": received_at.isoformat(),
                "source": source,
                "quality": quality,
                "source_sequence": source_sequence,
            }

            self._client.set(
                key,
                json.dumps(payload),
            )

            return True

        except Exception:
            logger.exception(
                "Failed to update telemetry cache",
                extra={
                    "asset_id": str(asset_id),
                    "metric": metric_code,
                },
            )
            return False

    def get_latest(
        self,
        *,
        asset_id: UUID | str,
        metric_code: str,
    ) -> dict | None:
        """Return the cached latest telemetry value."""
        try:
            raw = self._client.get(
                self._key(asset_id, metric_code),
            )

            if raw is None:
                return None

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            return json.loads(raw)

        except Exception:
            logger.exception(
                "Failed to read telemetry cache",
                extra={
                    "asset_id": str(asset_id),
                    "metric": metric_code,
                },
            )
            return None

    def delete(
        self,
        *,
        asset_id: UUID | str,
        metric_code: str,
    ) -> bool:
        """Remove a cached telemetry value."""
        try:
            self._client.delete(
                self._key(asset_id, metric_code),
            )
            return True
        except Exception:
            logger.exception(
                "Failed to delete telemetry cache",
                extra={
                    "asset_id": str(asset_id),
                    "metric": metric_code,
                },
            )
            return False