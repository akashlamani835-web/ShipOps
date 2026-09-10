from dataclasses import dataclass
from uuid import UUID

from app.events.models import EventSeverity


@dataclass(frozen=True, slots=True)
class RCACandidate:
    """A candidate asset considered as a possible root cause."""

    asset_id: UUID
    identifier: str
    asset_type: str
    distance: int
    score: float
    telemetry_support: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RCAResult:
    """Deterministic root-cause analysis result."""

    event_id: UUID
    affected_asset_id: UUID
    affected_asset_identifier: str
    root_cause_asset_id: UUID | None
    root_cause_identifier: str | None
    confidence: float
    severity: EventSeverity
    explanation: str
    candidates: tuple[RCACandidate, ...]