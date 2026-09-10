from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.events.models import EventStatus
from app.events.repository import EventRepository
from app.events.schemas import (
    EventEvidenceResponse,
    EventListResponse,
    OperationalEventResponse,
    ResolveEventRequest,
)
from app.events.service import EventService


router = APIRouter(
    prefix="/api/v1/events",
    tags=["events"],
)


def _event_to_response(event) -> OperationalEventResponse:
    """Convert an ORM event into the public API schema."""

    evidence = [
        EventEvidenceResponse.model_validate(item)
        for item in event.evidence
    ]

    return OperationalEventResponse(
        id=event.id,
        asset_id=event.asset_id,
        rule_id=event.rule_id,
        event_type=event.event_type,
        severity=event.severity,
        status=event.status,
        occurred_at=event.occurred_at,
        resolved_at=event.resolved_at,
        summary=event.summary,
        details=event.details,
        evidence=evidence,
    )


@router.get(
    "",
    response_model=EventListResponse,
)
def list_events(
    event_status: EventStatus | None = None,
    event_type: str | None = None,
    asset_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> EventListResponse:
    """List operational events with optional filters."""

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 500.",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset cannot be negative.",
        )

    repository = EventRepository(db)

    events = repository.list_events(
        status=event_status,
        event_type=event_type,
        asset_id=asset_id,
        limit=limit,
        offset=offset,
    )

    return EventListResponse(
        items=[
            _event_to_response(event)
            for event in events
        ],
        count=len(events),
    )


@router.get(
    "/{event_id}",
    response_model=OperationalEventResponse,
)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
) -> OperationalEventResponse:
    """Return one operational event."""

    repository = EventRepository(db)

    event = repository.get_event(event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational event '{event_id}' not found.",
        )

    return _event_to_response(event)


@router.post(
    "/{event_id}/acknowledge",
    response_model=OperationalEventResponse,
)
def acknowledge_event(
    event_id: UUID,
    db: Session = Depends(get_db),
) -> OperationalEventResponse:
    """Acknowledge an open operational event."""

    service = EventService(db)

    try:
        event = service.acknowledge_event(event_id)
        db.commit()
    except ValueError as exc:
        db.rollback()

        message = str(exc)

        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from exc

    return _event_to_response(event)


@router.post(
    "/{event_id}/resolve",
    response_model=OperationalEventResponse,
)
def resolve_event(
    event_id: UUID,
    request: ResolveEventRequest | None = None,
    db: Session = Depends(get_db),
) -> OperationalEventResponse:
    """Resolve an open or acknowledged operational event."""

    service = EventService(db)

    try:
        event = service.resolve_event(
            event_id,
            resolved_at=(
                request.resolved_at
                if request is not None
                else None
            ),
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        message = str(exc)

        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from exc

    return _event_to_response(event)