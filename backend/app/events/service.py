from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.events.duration import condition_sustained
from app.events.evaluator import evaluate_rule
from app.events.models import (
    EventRule,
    EventStatus,
    OperationalEvent,
)
from app.events.repository import EventRepository
from app.telemetry.models import TelemetrySample


class EventService:
    """Detect and manage operational events from telemetry."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repository = EventRepository(db)

    def process_sample(
        self,
        sample: TelemetrySample,
    ) -> list[OperationalEvent]:
        """Evaluate active rules for one telemetry sample."""

        rules = self._repository.get_active_rules_for_metric(
            sample.metric_definition_id,
        )

        created_events: list[OperationalEvent] = []

        for rule in rules:
            if not evaluate_rule(rule, sample):
                continue

            event = self._process_rule(
                rule=rule,
                sample=sample,
            )

            if event is not None:
                created_events.append(event)

        return created_events

    def _process_rule(
        self,
        *,
        rule: EventRule,
        sample: TelemetrySample,
    ) -> OperationalEvent | None:
        """Process one matching event rule."""

        open_event = self._repository.get_open_event(
            asset_id=sample.asset_id,
            rule_id=rule.id,
        )

        if open_event is not None:
            self._attach_evidence(
                event=open_event,
                rule=rule,
                sample=sample,
            )
            return None

        window_start = (
            sample.observed_at
            - timedelta(
                seconds=rule.duration_seconds,
            )
        )

        samples = self._repository.get_telemetry_samples_for_window(
            asset_id=sample.asset_id,
            metric_definition_id=sample.metric_definition_id,
            start_at=window_start,
            end_at=sample.observed_at,
        )

        if not condition_sustained(rule, samples):
            return None

        event = self._repository.create_event(
            asset_id=sample.asset_id,
            rule_id=rule.id,
            event_type=rule.event_type,
            severity=rule.severity,
            occurred_at=sample.observed_at,
            summary=(
                f"{rule.name} detected on asset "
                f"{sample.asset_id}."
            ),
            details={
                "rule_code": rule.code,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "duration_seconds": rule.duration_seconds,
            },
        )

        for evidence_sample in samples:
            if evaluate_rule(rule, evidence_sample):
                self._attach_evidence(
                    event=event,
                    rule=rule,
                    sample=evidence_sample,
                )

        return event

    def _attach_evidence(
        self,
        *,
        event: OperationalEvent,
        rule: EventRule,
        sample: TelemetrySample,
    ) -> None:
        """Attach telemetry as evidence when not already attached."""

        existing = self._repository.get_evidence(
            event_id=event.id,
            telemetry_sample_id=sample.id,
        )

        if existing is not None:
            return

        self._repository.add_evidence(
            event_id=event.id,
            telemetry_sample_id=sample.id,
            evidence_type="threshold_breach",
            explanation=(
                f"Telemetry value {sample.value} "
                f"satisfied event rule '{rule.code}'."
            ),
        )

    def acknowledge_event(
        self,
        event_id,
    ) -> OperationalEvent:
        """Move an open event to acknowledged."""

        event = self._get_event_or_raise(event_id)

        if event.status != EventStatus.OPEN:
            raise ValueError(
                "Only open events can be acknowledged.",
            )

        event.status = EventStatus.ACKNOWLEDGED
        self._db.flush()

        return event

    def resolve_event(
        self,
        event_id,
        *,
        resolved_at: datetime | None = None,
    ) -> OperationalEvent:
        """Resolve an open or acknowledged event."""

        event = self._get_event_or_raise(event_id)

        if event.status == EventStatus.RESOLVED:
            raise ValueError(
                "Event is already resolved.",
            )

        resolved_time = (
            resolved_at
            if resolved_at is not None
            else datetime.now(timezone.utc)
        )

        if resolved_time < event.occurred_at:
            raise ValueError(
                "resolved_at cannot be earlier than occurred_at.",
            )

        event.status = EventStatus.RESOLVED
        event.resolved_at = resolved_time

        self._db.flush()

        return event

    def _get_event_or_raise(
        self,
        event_id,
    ) -> OperationalEvent:
        """Return an event or raise a clear error."""

        event = self._db.get(
            OperationalEvent,
            event_id,
        )

        if event is None:
            raise ValueError(
                f"Operational event '{event_id}' not found.",
            )

        return event