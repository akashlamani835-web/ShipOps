from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.rca.engine import RCAEngine


router = APIRouter(
    prefix="/api/v1/rca",
    tags=["rca"],
)


class RCAEventCandidateResponse(BaseModel):
    """Public RCA candidate representation."""

    asset_id: UUID
    identifier: str
    asset_type: str
    distance: int
    score: float
    telemetry_support: int
    shared_event_support: int
    reasons: list[str]


class RCAEventResponse(BaseModel):
    """Public single-event RCA response."""

    event_id: UUID
    affected_asset_id: UUID
    affected_asset_identifier: str
    root_cause_asset_id: UUID | None
    root_cause_identifier: str | None
    confidence: float
    severity: str
    explanation: str
    candidates: list[RCAEventCandidateResponse]


class RCAClusterRequest(BaseModel):
    """Request body for multi-event RCA."""

    event_ids: list[UUID] = Field(
        min_length=1,
        max_length=100,
    )


class RCAClusterResponse(BaseModel):
    """Public multi-event RCA response."""

    event_ids: list[UUID]
    affected_asset_ids: list[UUID]
    affected_asset_identifiers: list[str]
    root_cause_asset_id: UUID | None
    root_cause_identifier: str | None
    confidence: float
    severity: str
    explanation: str
    candidates: list[RCAEventCandidateResponse]


def _candidate_to_response(candidate) -> RCAEventCandidateResponse:
    """Convert an RCA candidate into its public API form."""

    return RCAEventCandidateResponse(
        asset_id=candidate.asset_id,
        identifier=candidate.identifier,
        asset_type=candidate.asset_type,
        distance=candidate.distance,
        score=candidate.score,
        telemetry_support=candidate.telemetry_support,
        shared_event_support=candidate.shared_event_support,
        reasons=list(candidate.reasons),
    )


@router.get(
    "/events/{event_id}",
    response_model=RCAEventResponse,
)
def analyze_event(
    event_id: UUID,
    db: Session = Depends(get_db),
) -> RCAEventResponse:
    """Run deterministic RCA for one operational event."""

    engine = RCAEngine(db)

    try:
        result = engine.analyze(event_id)
    except ValueError as exc:
        message = str(exc)

        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    return RCAEventResponse(
        event_id=result.event_id,
        affected_asset_id=result.affected_asset_id,
        affected_asset_identifier=result.affected_asset_identifier,
        root_cause_asset_id=result.root_cause_asset_id,
        root_cause_identifier=result.root_cause_identifier,
        confidence=result.confidence,
        severity=result.severity.value,
        explanation=result.explanation,
        candidates=[
            _candidate_to_response(candidate)
            for candidate in result.candidates
        ],
    )


@router.post(
    "/clusters",
    response_model=RCAClusterResponse,
)
def analyze_cluster(
    request: RCAClusterRequest,
    db: Session = Depends(get_db),
) -> RCAClusterResponse:
    """Run deterministic RCA across multiple operational events."""

    engine = RCAEngine(db)

    try:
        result = engine.analyze_cluster(
            request.event_ids,
        )
    except ValueError as exc:
        message = str(exc)

        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    return RCAClusterResponse(
        event_ids=list(result.event_ids),
        affected_asset_ids=list(result.affected_asset_ids),
        affected_asset_identifiers=list(
            result.affected_asset_identifiers,
        ),
        root_cause_asset_id=result.root_cause_asset_id,
        root_cause_identifier=result.root_cause_identifier,
        confidence=result.confidence,
        severity=result.severity.value,
        explanation=result.explanation,
        candidates=[
            _candidate_to_response(candidate)
            for candidate in result.candidates
        ],
    )