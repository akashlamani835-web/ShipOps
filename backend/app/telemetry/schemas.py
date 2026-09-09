from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TelemetryIngestRequest(BaseModel):
    """Payload accepted by the telemetry ingestion service."""

    model_config = ConfigDict(extra="forbid")

    asset_identifier: str = Field(
        min_length=1,
        max_length=100,
    )

    metric: str = Field(
        min_length=1,
        max_length=100,
    )

    value: float

    unit: str = Field(
        min_length=1,
        max_length=50,
    )

    observed_at: datetime

    received_at: datetime

    source: str = Field(
        min_length=1,
        max_length=50,
    )

    source_sequence: int = Field(
        ge=0,
    )

    quality: str = Field(
        min_length=1,
        max_length=30,
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=200,
    )

    extra_data: dict | None = None


class TelemetryIngestResponse(BaseModel):
    """Result returned after processing a telemetry sample."""

    status: str
    telemetry_id: str | None
    asset_identifier: str
    metric: str
    idempotent_replay: bool