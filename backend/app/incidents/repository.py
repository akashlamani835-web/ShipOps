from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.incidents.models import Incident, IncidentStatus


class IncidentRepository:
    """Database operations for incidents."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(
        self,
        incident_id: UUID,
    ) -> Incident | None:
        """Return an incident by ID."""

        return self._db.scalar(
            select(Incident).where(
                Incident.id == incident_id,
            )
        )

    def get_by_number(
        self,
        incident_number: str,
    ) -> Incident | None:
        """Return an incident by its human-readable number."""

        return self._db.scalar(
            select(Incident).where(
                Incident.incident_number
                == incident_number,
            )
        )

    def get_by_event_id(
        self,
        event_id: UUID,
    ) -> Incident | None:
        """Return the incident associated with an operational event."""

        return self._db.scalar(
            select(Incident).where(
                Incident.event_id == event_id,
            )
        )

    def list_incidents(
        self,
        *,
        status: IncidentStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Incident]:
        """Return incidents with optional status filtering."""

        statement = select(Incident)

        if status is not None:
            statement = statement.where(
                Incident.status == status,
            )

        statement = (
            statement
            .order_by(
                Incident.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self._db.scalars(statement)
        )

    def create(
        self,
        *,
        incident_number: str,
        title: str,
        description: str | None,
        priority,
        event_id: UUID,
        asset_id: UUID,
        root_cause_asset_id: UUID | None,
        assigned_to: str | None,
    ) -> Incident:
        """Create and flush an incident."""

        incident = Incident(
            incident_number=incident_number,
            title=title,
            description=description,
            priority=priority,
            status=IncidentStatus.OPEN,
            event_id=event_id,
            asset_id=asset_id,
            root_cause_asset_id=root_cause_asset_id,
            assigned_to=assigned_to,
        )

        self._db.add(incident)
        self._db.flush()

        return incident