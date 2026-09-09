from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.telemetry.schemas import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)
from app.telemetry.service import TelemetryIngestionService
from app.telemetry.validators import TelemetryValidationError


router = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["telemetry"],
)


@router.post(
    "",
    response_model=TelemetryIngestResponse,
)
def ingest_telemetry(
    request: TelemetryIngestRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TelemetryIngestResponse:
    """Accept and persist a telemetry sample."""

    service = TelemetryIngestionService(db)

    try:
        result = service.ingest(request)
    except TelemetryValidationError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise

    if result.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    else:
        db.commit()
        response.status_code = status.HTTP_201_CREATED

    return result