from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import OperationalEvent
from app.incidents.models import (
    Incident,
    IncidentPriority,
    IncidentStatus,
)
from app.incidents.repository import IncidentRepository


class IncidentService:
    """Business logic for IT operations incidents."""

    def __init__(
        self,
        db: Session,
    ) -> None:
        self._db = db
        self._repository = IncidentRepository(db)

    def create_incident(
        self,
        *,
        event_id: UUID,
        title: str,
        description: str | None,
        priority: IncidentPriority,
        assigned_to: str | None = None,
    ) -> Incident:
        """
        Create an incident from an operational event.

        One operational event can create at most one incident.
        """

        existing = self._repository.get_by_event_id(
            event_id,
        )

        if existing is not None:
            raise ValueError(
                f"Incident already exists for event '{event_id}'.",
            )

        event = self._db.get(
            OperationalEvent,
            event_id,
        )

        if event is None:
            raise ValueError(
                f"Operational event '{event_id}' not found.",
            )

        incident_number = self._generate_incident_number()

        return self._repository.create(
            incident_number=incident_number,
            title=title,
            description=description,
            priority=priority,
            event_id=event.id,
            asset_id=event.asset_id,
            root_cause_asset_id=None,
            assigned_to=assigned_to,
        )

    def assign_incident(
        self,
        incident_id: UUID,
        assigned_to: str,
    ) -> Incident:
        """Assign an incident to an operator."""

        incident = self._get_or_raise(
            incident_id,
        )

        if incident.status in {
            IncidentStatus.RESOLVED,
            IncidentStatus.CLOSED,
        }:
            raise ValueError(
                "Resolved or closed incidents cannot be assigned.",
            )

        incident.assigned_to = assigned_to

        if incident.status == IncidentStatus.OPEN:
            incident.status = IncidentStatus.IN_PROGRESS

        self._db.flush()

        return incident

    def acknowledge_incident(
        self,
        incident_id: UUID,
    ) -> Incident:
        """Acknowledge an incident and start active work."""

        incident = self._get_or_raise(
            incident_id,
        )

        if incident.status != IncidentStatus.OPEN:
            raise ValueError(
                "Only open incidents can be acknowledged.",
            )

        incident.status = IncidentStatus.IN_PROGRESS
        incident.acknowledged_at = datetime.now(
            timezone.utc,
        )

        self._db.flush()

        return incident

    def resolve_incident(
        self,
        incident_id: UUID,
        *,
        resolution_summary: str,
    ) -> Incident:
        """Resolve an incident."""

        incident = self._get_or_raise(
            incident_id,
        )

        if incident.status in {
            IncidentStatus.RESOLVED,
            IncidentStatus.CLOSED,
        }:
            raise ValueError(
                "Incident is already resolved or closed.",
            )

        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now(
            timezone.utc,
        )
        incident.resolution_summary = resolution_summary

        self._db.flush()

        return incident

    def close_incident(
        self,
        incident_id: UUID,
    ) -> Incident:
        """Close an already resolved incident."""

        incident = self._get_or_raise(
            incident_id,
        )

        if incident.status != IncidentStatus.RESOLVED:
            raise ValueError(
                "Only resolved incidents can be closed.",
            )

        incident.status = IncidentStatus.CLOSED

        self._db.flush()

        return incident

    def set_root_cause(
        self,
        incident_id: UUID,
        *,
        root_cause_asset_id: UUID,
    ) -> Incident:
        """Attach the deterministic RCA result to an incident."""

        incident = self._get_or_raise(
            incident_id,
        )

        if incident.status in {
            IncidentStatus.RESOLVED,
            IncidentStatus.CLOSED,
        }:
            raise ValueError(
                "Resolved or closed incidents cannot change root cause.",
            )

        incident.root_cause_asset_id = root_cause_asset_id

        self._db.flush()

        return incident

    def _generate_incident_number(self) -> str:
        """Generate the next human-readable incident number."""

        existing_numbers = list(
            self._db.scalars(
                select(
                    Incident.incident_number,
                )
            )
        )

        highest_number = 0

        for number in existing_numbers:
            if not number.startswith("INC-"):
                continue

            try:
                value = int(
                    number.removeprefix("INC-")
                )
            except ValueError:
                continue

            highest_number = max(
                highest_number,
                value,
            )

        return f"INC-{highest_number + 1:06d}"

    def _get_or_raise(
        self,
        incident_id: UUID,
    ) -> Incident:
        """Return an incident or raise a clear error."""

        incident = self._repository.get_by_id(
            incident_id,
        )

        if incident is None:
            raise ValueError(
                f"Incident '{incident_id}' not found.",
            )

        return incident