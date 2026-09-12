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


class TopologyNodeResponse(BaseModel):
    """Public representation of a network interface in the topology."""

    id: str
    asset_id: str
    identifier: str = Field(description="Human-readable asset identifier.")
    name: str


class TopologyEdgeResponse(BaseModel):
    """Public representation of a physical network link."""

    source_node_id: str
    destination_node_id: str
    operational_up: bool


class TopologyGraphResponse(BaseModel):
    """Public topology graph used by the operations console."""

    nodes: list[TopologyNodeResponse]
    edges: list[TopologyEdgeResponse]


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
    "/graph",
    response_model=TopologyGraphResponse,
)
def get_topology_graph(
    db: Session = Depends(get_db),
) -> TopologyGraphResponse:
    """Return the current operational physical topology graph."""
    repository = TopologyRepository(db)
    nodes = repository.get_nodes()
    edges = repository.get_edges()

    asset_ids = {node.asset_id for node in nodes}
    asset_identifiers = repository.get_asset_identifiers(asset_ids)

    graph_nodes = [
        TopologyNodeResponse(
            id=node.id,
            asset_id=node.asset_id,
            identifier=asset_identifiers.get(node.asset_id, node.asset_id),
            name=node.name,
        )
        for node in nodes
    ]

    graph_edges = [
        TopologyEdgeResponse(
            source_node_id=edge.source_node_id,
            destination_node_id=edge.destination_node_id,
            operational_up=edge.operational_up,
        )
        for edge in edges
    ]

    return TopologyGraphResponse(
        nodes=graph_nodes,
        edges=graph_edges,
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
