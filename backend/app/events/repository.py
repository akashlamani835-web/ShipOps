from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import (
    EventEvidence,
    EventRule,
    EventStatus,
    OperationalEvent,
)
from app.telemetry.models import MetricDefinition, TelemetrySample


class EventRepository:
    """Database operations for operational event processing."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active_rules_for_metric(
        self,
        metric_definition_id: UUID,
    ) -> list[EventRule]:
        """Return active rules configured for a metric."""
        return list(
            self._db.scalars(
                select(EventRule)
                .where(
                    EventRule.metric_definition_id
                    == metric_definition_id,
                    EventRule.active.is_(True),
                )
                .order_by(EventRule.code)
            )
        )

    def get_telemetry_samples_for_window(
        self,
        *,
        asset_id: UUID,
        metric_definition_id: UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> list[TelemetrySample]:
        """Return telemetry samples observed within a time window."""
        return list(
            self._db.scalars(
                select(TelemetrySample)
                .where(
                    TelemetrySample.asset_id == asset_id,
                    TelemetrySample.metric_definition_id
                    == metric_definition_id,
                    TelemetrySample.observed_at >= start_at,
                    TelemetrySample.observed_at <= end_at,
                )
                .order_by(
                    TelemetrySample.observed_at,
                )
            )
        )

    def get_open_event(
        self,
        *,
        asset_id: UUID,
        rule_id: UUID,
    ) -> OperationalEvent | None:
        """Return an existing open or acknowledged event."""
        return self._db.scalar(
            select(OperationalEvent)
            .where(
                OperationalEvent.asset_id == asset_id,
                OperationalEvent.rule_id == rule_id,
                OperationalEvent.status.in_(
                    [
                        EventStatus.OPEN,
                        EventStatus.ACKNOWLEDGED,
                    ]
                ),
            )
            .order_by(
                OperationalEvent.occurred_at.desc(),
            )
        )

    def get_evidence(
        self,
        *,
        event_id: UUID,
        telemetry_sample_id: UUID,
    ) -> EventEvidence | None:
        """Return evidence for an event/sample pair."""
        return self._db.scalar(
            select(EventEvidence).where(
                EventEvidence.event_id == event_id,
                EventEvidence.telemetry_sample_id
                == telemetry_sample_id,
            )
        )

    def create_event(
        self,
        *,
        asset_id: UUID,
        rule_id: UUID,
        event_type: str,
        severity,
        occurred_at: datetime,
        summary: str,
        details: dict | None = None,
    ) -> OperationalEvent:
        """Create and flush an operational event."""
        event = OperationalEvent(
            asset_id=asset_id,
            rule_id=rule_id,
            event_type=event_type,
            severity=severity,
            status=EventStatus.OPEN,
            occurred_at=occurred_at,
            summary=summary,
            details=details,
        )

        self._db.add(event)
        self._db.flush()

        return event

    def add_evidence(
        self,
        *,
        event_id: UUID,
        telemetry_sample_id: UUID,
        evidence_type: str,
        explanation: str | None = None,
    ) -> EventEvidence:
        """Attach one telemetry sample as event evidence."""
        evidence = EventEvidence(
            event_id=event_id,
            telemetry_sample_id=telemetry_sample_id,
            evidence_type=evidence_type,
            explanation=explanation,
        )

        self._db.add(evidence)
        self._db.flush()

        return evidence

    def get_metric_definition(
        self,
        metric_definition_id: UUID,
    ) -> MetricDefinition | None:
        """Return a metric definition by ID."""
        return self._db.scalar(
            select(MetricDefinition).where(
                MetricDefinition.id == metric_definition_id,
            )
        )

    def list_events(
        self,
        *,
        status: EventStatus | None = None,
        event_type: str | None = None,
        asset_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OperationalEvent]:
        """Return operational events with optional filters."""

        statement = select(OperationalEvent)

        if status is not None:
            statement = statement.where(
                OperationalEvent.status == status,
            )

        if event_type is not None:
            statement = statement.where(
                OperationalEvent.event_type == event_type,
            )

        if asset_id is not None:
            statement = statement.where(
                OperationalEvent.asset_id == asset_id,
            )

        statement = (
            statement
            .order_by(
                OperationalEvent.occurred_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self._db.scalars(statement)
        )

    def get_event(
        self,
        event_id: UUID,
    ) -> OperationalEvent | None:
        """Return one operational event by ID."""
        return self._db.scalar(
            select(OperationalEvent).where(
                OperationalEvent.id == event_id,
            )
        )