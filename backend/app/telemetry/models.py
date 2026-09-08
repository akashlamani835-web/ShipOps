from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset


class MetricDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Define a telemetry metric and its validation rules."""

    __tablename__ = "metric_definitions"

    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_metric_definitions_code",
        ),
        CheckConstraint(
            "minimum_value IS NULL OR maximum_value IS NULL "
            "OR minimum_value <= maximum_value",
            name="metric_definition_valid_range",
        ),
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    minimum_value: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    maximum_value: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    telemetry_samples: Mapped[list["TelemetrySample"]] = relationship(
        back_populates="metric_definition",
    )


class TelemetrySample(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Store an immutable telemetry observation."""

    __tablename__ = "telemetry_samples"

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_telemetry_samples_idempotency_key",
        ),
        Index(
            "ix_telemetry_samples_asset_metric_observed_at",
            "asset_id",
            "metric_definition_id",
            "observed_at",
        ),
        CheckConstraint(
            "observed_at <= received_at",
            name="telemetry_observed_before_received",
        ),
    )

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metric_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "metric_definitions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    value: Mapped[float] = mapped_column(
        nullable=False,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    quality: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="good",
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    extra_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    asset: Mapped["Asset"] = relationship()

    metric_definition: Mapped["MetricDefinition"] = relationship(
        back_populates="telemetry_samples",
    )