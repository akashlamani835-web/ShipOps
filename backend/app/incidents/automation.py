import logging

from sqlalchemy.orm import Session

from app.events.models import EventSeverity, OperationalEvent
from app.incidents.models import Incident, IncidentPriority
from app.incidents.repository import IncidentRepository
from app.incidents.service import IncidentService
from app.rca.engine import RCAEngine


logger = logging.getLogger(__name__)


class IncidentAutomationService:
    """
    Automatically connect operational events to incidents and RCA.

    Only HIGH and CRITICAL operational events are promoted into
    incidents automatically. RCA is best-effort so an RCA failure
    cannot prevent the incident from being created.
    """

    _AUTO_INCIDENT_SEVERITIES = {
        EventSeverity.HIGH,
        EventSeverity.CRITICAL,
    }

    def __init__(self, db: Session) -> None:
        self._db = db
        self._incident_repository = IncidentRepository(db)
        self._incident_service = IncidentService(db)
        self._rca_engine = RCAEngine(db)

    def handle_event(
        self,
        event: OperationalEvent,
    ) -> Incident | None:
        """
        Create an incident for an eligible event and attach RCA.

        Returns the incident when an incident was created or already
        exists for the event. Returns None for events that do not
        meet the automatic incident severity threshold.
        """

        if event.severity not in self._AUTO_INCIDENT_SEVERITIES:
            return None

        existing = self._incident_repository.get_by_event_id(
            event.id,
        )

        if existing is not None:
            self._attach_rca(
                incident=existing,
                event=event,
            )
            return existing

        incident = self._incident_service.create_incident(
            event_id=event.id,
            title=event.summary,
            description=self._build_description(event),
            priority=self._map_priority(event.severity),
        )

        self._attach_rca(
            incident=incident,
            event=event,
        )

        return incident

    def _attach_rca(
        self,
        *,
        incident: Incident,
        event: OperationalEvent,
    ) -> None:
        """
        Run deterministic RCA and attach the winning root-cause asset.

        RCA is intentionally best-effort. An incident remains valid even
        when no root cause can be established or RCA encounters an error.
        """

        if incident.root_cause_asset_id is not None:
            return

        try:
            result = self._rca_engine.analyze(
                event.id,
            )
        except Exception:
            logger.exception(
                "Automatic RCA failed for incident",
                extra={
                    "incident_id": str(incident.id),
                    "incident_number": incident.incident_number,
                    "event_id": str(event.id),
                },
            )
            return

        if result.root_cause_asset_id is None:
            logger.info(
                "RCA completed without a root cause",
                extra={
                    "incident_id": str(incident.id),
                    "incident_number": incident.incident_number,
                    "event_id": str(event.id),
                    "confidence": result.confidence,
                },
            )
            return

        try:
            self._incident_service.set_root_cause(
                incident.id,
                root_cause_asset_id=result.root_cause_asset_id,
            )
        except Exception:
            logger.exception(
                "Failed to attach RCA root cause to incident",
                extra={
                    "incident_id": str(incident.id),
                    "incident_number": incident.incident_number,
                    "event_id": str(event.id),
                    "root_cause_asset_id": str(
                        result.root_cause_asset_id,
                    ),
                },
            )

    @staticmethod
    def _map_priority(
        severity: EventSeverity,
    ) -> IncidentPriority:
        """Map operational-event severity to incident priority."""

        if severity == EventSeverity.CRITICAL:
            return IncidentPriority.CRITICAL

        return IncidentPriority.HIGH

    @staticmethod
    def _build_description(
        event: OperationalEvent,
    ) -> str:
        """Build a useful incident description from event details."""

        if not event.details:
            return (
                f"Automatically created from operational event "
                f"{event.id}."
            )

        return (
            f"Automatically created from operational event "
            f"{event.id}. Event details: {event.details}"
        )