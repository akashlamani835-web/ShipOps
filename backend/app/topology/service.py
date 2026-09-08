from collections import deque

from sqlalchemy.orm import Session

from app.topology.repository import TopologyRepository
from app.topology.schemas import TopologyEdge, TopologyNode


class TopologyService:
    """Algorithms for analyzing ShipOps network topology."""

    @classmethod
    def from_database(cls, db: Session) -> "TopologyService":
        """Build a topology service from current database state."""
        repository = TopologyRepository(db)

        return cls(
            nodes=repository.get_nodes(),
            edges=repository.get_edges(),
        )

    def __init__(
        self,
        nodes: list[TopologyNode],
        edges: list[TopologyEdge],
    ) -> None:
        self._nodes = {node.id: node for node in nodes}

        self._asset_to_nodes: dict[str, set[str]] = {}

        for node in nodes:
            self._asset_to_nodes.setdefault(node.asset_id, set()).add(
                node.id
            )

        self._adjacency: dict[str, set[str]] = {
            node.id: set() for node in nodes
        }

        for edge in edges:
            if not edge.operational_up:
                continue

            if edge.source_node_id not in self._nodes:
                continue

            if edge.destination_node_id not in self._nodes:
                continue

            # Physical connectivity is bidirectional.
            self._adjacency[edge.source_node_id].add(
                edge.destination_node_id
            )
            self._adjacency[edge.destination_node_id].add(
                edge.source_node_id
            )

    def downstream_assets(self, node_id: str) -> set[str]:
        """
        Return assets reachable through the physical topology.

        This method is retained for compatibility with the original
        interface-level analysis. Because physical links are
        bidirectional, the result represents connected impact rather
        than strict traffic direction.
        """
        if node_id not in self._nodes:
            return set()

        root_asset_id = self._nodes[node_id].asset_id

        return self._traverse_from_nodes(
            self._asset_to_nodes.get(root_asset_id, set()),
            excluded_asset_ids={root_asset_id},
        )

    def impacted_assets(self, asset_id: str) -> set[str]:
        """
        Return all assets physically reachable from the supplied asset.

        The supplied asset itself is excluded.
        """
        if asset_id not in self._asset_to_nodes:
            return set()

        return self._traverse_from_nodes(
            self._asset_to_nodes[asset_id],
            excluded_asset_ids={asset_id},
        )

    def _traverse_from_nodes(
        self,
        start_nodes: set[str],
        *,
        excluded_asset_ids: set[str],
    ) -> set[str]:
        """Traverse the physical topology from multiple interfaces."""
        visited: set[str] = set(start_nodes)
        queue: deque[str] = deque(start_nodes)
        affected_assets: set[str] = set()

        while queue:
            current_node_id = queue.popleft()

            for neighbor_id in self._adjacency[current_node_id]:
                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)

                neighbor = self._nodes[neighbor_id]

                if neighbor.asset_id not in excluded_asset_ids:
                    affected_assets.add(neighbor.asset_id)

                queue.append(neighbor_id)

        return affected_assets