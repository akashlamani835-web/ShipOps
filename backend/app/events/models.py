from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.telemetry.models import MetricDefinition, TelemetrySample


class EventSeverity(str, Enum):
    """Severity assigned to an operational event."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    """Lifecycle state of an operational event."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class EventRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Define when telemetry should produce an operational event."""

    __tablename__ = "event_rules"

    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_event_rules_code",
        ),
        Index(
            "ix_event_rules_metric_definition_id",
            "metric_definition_id",
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

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    metric_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "metric_definitions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    severity: Mapped[EventSeverity] = mapped_column(
        SAEnum(
            EventSeverity,
            name="event_severity",
            native_enum=False,
        ),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metric_definition: Mapped["MetricDefinition"] = relationship()

    events: Mapped[list["OperationalEvent"]] = relationship(
        back_populates="rule",
    )


class OperationalEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represent a detected operational condition."""

    __tablename__ = "operational_events"

    __table_args__ = (
        Index(
            "ix_operational_events_asset_id_occurred_at",
            "asset_id",
            "occurred_at",
        ),
        Index(
            "ix_operational_events_event_type_occurred_at",
            "event_type",
            "occurred_at",
        ),
    )

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "assets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "event_rules.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    severity: Mapped[EventSeverity] = mapped_column(
        SAEnum(
            EventSeverity,
            name="event_severity",
            native_enum=False,
        ),
        nullable=False,
    )

    status: Mapped[EventStatus] = mapped_column(
        SAEnum(
            EventStatus,
            name="event_status",
            native_enum=False,
        ),
        nullable=False,
        default=EventStatus.OPEN,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    summary: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    asset: Mapped["Asset"] = relationship()

    rule: Mapped["EventRule"] = relationship(
        back_populates="events",
    )

    evidence: Mapped[list["EventEvidence"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class EventEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Record why an operational event was created."""

    __tablename__ = "event_evidence"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "telemetry_sample_id",
            name="uq_event_evidence_event_sample",
        ),
        Index(
            "ix_event_evidence_event_id",
            "event_id",
        ),
        Index(
            "ix_event_evidence_telemetry_sample_id",
            "telemetry_sample_id",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "operational_events.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    telemetry_sample_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "telemetry_samples.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    event: Mapped["OperationalEvent"] = relationship(
        back_populates="evidence",
    )

    telemetry_sample: Mapped["TelemetrySample"] = relationship()