from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.events.models import EventSeverity, EventStatus


class EventEvidenceResponse(BaseModel):
    """Evidence attached to an operational event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telemetry_sample_id: UUID
    evidence_type: str
    explanation: str | None


class OperationalEventResponse(BaseModel):
    """API representation of an operational event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    rule_id: UUID
    event_type: str
    severity: EventSeverity
    status: EventStatus
    occurred_at: datetime
    resolved_at: datetime | None
    summary: str
    details: dict | None
    evidence: list[EventEvidenceResponse] = Field(
        default_factory=list,
    )


class EventListResponse(BaseModel):
    """Event collection response."""

    items: list[OperationalEventResponse]
    count: int


class ResolveEventRequest(BaseModel):
    """Optional timestamp supplied when resolving an event."""

    model_config = ConfigDict(extra="forbid")

    resolved_at: datetime | None = None