from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.network_interface import NetworkInterface
from app.models.network_link import NetworkLink
from app.topology.schemas import TopologyEdge, TopologyNode


class TopologyRepository:
    """Read topology information from the ShipOps database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_nodes(self) -> list[TopologyNode]:
        """Return all network interfaces as topology nodes."""
        rows = self._db.execute(
            select(
                NetworkInterface.id,
                NetworkInterface.asset_id,
                NetworkInterface.name,
            )
        ).all()

        return [
            TopologyNode(
                id=str(row.id),
                asset_id=str(row.asset_id),
                name=row.name,
            )
            for row in rows
        ]

    def get_edges(self) -> list[TopologyEdge]:
        """Return all operational network links as topology edges."""
        rows = self._db.execute(
            select(
                NetworkLink.source_interface_id,
                NetworkLink.destination_interface_id,
                NetworkLink.operational_up,
            )
        ).all()

        return [
            TopologyEdge(
                source_node_id=str(row.source_interface_id),
                destination_node_id=str(row.destination_interface_id),
                operational_up=row.operational_up,
            )
            for row in rows
        ]

    def get_asset_by_identifier(self, identifier: str) -> Asset | None:
        """Return an asset using its human-readable identifier."""
        return self._db.scalar(
            select(Asset).where(
                Asset.identifier == identifier,
            )
        )

    def get_asset_identifiers(
        self,
        asset_ids: set[str],
    ) -> dict[str, str]:
        """Resolve asset UUID strings to human-readable identifiers."""
        if not asset_ids:
            return {}

        rows = self._db.execute(
            select(Asset.id, Asset.identifier).where(
                Asset.id.in_(asset_ids),
            )
        ).all()

        return {
            str(row.id): row.identifier
            for row in rows
        }