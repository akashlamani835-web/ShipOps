from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.topology.repository import TopologyRepository
from app.topology.service import TopologyService


router = APIRouter(
    prefix="/api/v1/topology",
    tags=["topology"],
)


class ImpactAnalysisResponse(BaseModel):
    """Public response for topology impact analysis."""

    root_asset: str = Field(
        description="Identifier of the asset being analyzed.",
    )

    affected_assets: list[str] = Field(
        description="Identifiers of connected assets that may be affected.",
    )

    affected_count: int = Field(
        ge=0,
        description="Number of affected assets.",
    )


@router.get(
    "/assets/{identifier}/impact",
    response_model=ImpactAnalysisResponse,
)
def analyze_asset_impact(
    identifier: str,
    db: Session = Depends(get_db),
) -> ImpactAnalysisResponse:
    """Analyze the physical topology impact of an asset."""

    repository = TopologyRepository(db)

    asset = repository.get_asset_by_identifier(identifier)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{identifier}' not found.",
        )

    service = TopologyService.from_database(db)

    affected_ids = service.impacted_assets(
        str(asset.id),
    )

    affected_identifiers = repository.get_asset_identifiers(
        affected_ids,
    )

    affected_assets = sorted(
        affected_identifiers.values(),
    )

    return ImpactAnalysisResponse(
        root_asset=asset.identifier,
        affected_assets=affected_assets,
        affected_count=len(affected_assets),
    )