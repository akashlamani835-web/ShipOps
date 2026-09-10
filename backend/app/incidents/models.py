from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.events.models import OperationalEvent
    from app.models.asset import Asset


class IncidentPriority(str, Enum):
    """Priority assigned to an incident."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    """Lifecycle state of an incident."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represent an actionable IT operations incident."""

    __tablename__ = "incidents"

    __table_args__ = (
        UniqueConstraint(
            "incident_number",
            name="uq_incidents_incident_number",
        ),
        Index(
            "ix_incidents_status_priority",
            "status",
            "priority",
        ),
        Index(
            "ix_incidents_asset_id_created_at",
            "asset_id",
            "created_at",
        ),
        Index(
            "ix_incidents_event_id",
            "event_id",
        ),
    )

    incident_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    priority: Mapped[IncidentPriority] = mapped_column(
        SAEnum(
            IncidentPriority,
            name="incident_priority",
            native_enum=False,
        ),
        nullable=False,
    )

    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(
            IncidentStatus,
            name="incident_status",
            native_enum=False,
        ),
        nullable=False,
        default=IncidentStatus.OPEN,
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "operational_events.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "assets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    root_cause_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "assets.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    assigned_to: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolution_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    event: Mapped["OperationalEvent"] = relationship()

    asset: Mapped["Asset"] = relationship(
        foreign_keys=[asset_id],
    )

    root_cause_asset: Mapped["Asset | None"] = relationship(
        foreign_keys=[root_cause_asset_id],
    )