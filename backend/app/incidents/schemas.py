from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.incidents.models import (
    IncidentPriority,
    IncidentStatus,
)


class IncidentCreateRequest(BaseModel):
    """Request for manually creating an incident."""

    event_id: UUID
    title: str = Field(
        min_length=1,
        max_length=300,
    )
    description: str | None = None
    priority: IncidentPriority
    assigned_to: str | None = Field(
        default=None,
        max_length=150,
    )


class IncidentResponse(BaseModel):
    """Public incident representation."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    incident_number: str
    title: str
    description: str | None
    priority: IncidentPriority
    status: IncidentStatus
    event_id: UUID
    asset_id: UUID
    root_cause_asset_id: UUID | None
    assigned_to: str | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolution_summary: str | None
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    """Paginated incident response."""

    items: list[IncidentResponse]
    count: int


class IncidentAssignRequest(BaseModel):
    """Request to assign an incident."""

    assigned_to: str = Field(
        min_length=1,
        max_length=150,
    )


class IncidentResolveRequest(BaseModel):
    """Request to resolve an incident."""

    resolution_summary: str = Field(
        min_length=1,
        max_length=5000,
    )