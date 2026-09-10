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
            self._asset_to_nodes.setdefault(
                node.asset_id,
                set(),
            ).add(node.id)

        self._adjacency: dict[str, set[str]] = {
            node.id: set()
            for node in nodes
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

    def asset_distances(
        self,
        asset_id: str,
    ) -> dict[str, int]:
        """
        Return shortest physical-topology distance to reachable assets.

        Distance is measured in interface-to-interface hops and then
        converted to asset-level candidates. The supplied asset is
        excluded from the result.
        """
        start_nodes = self._asset_to_nodes.get(asset_id)

        if not start_nodes:
            return {}

        queue: deque[tuple[str, int]] = deque()
        visited_nodes: set[str] = set()

        for node_id in start_nodes:
            queue.append((node_id, 0))
            visited_nodes.add(node_id)

        distances: dict[str, int] = {}

        while queue:
            current_node_id, distance = queue.popleft()

            for neighbor_id in self._adjacency[current_node_id]:
                if neighbor_id in visited_nodes:
                    continue

                visited_nodes.add(neighbor_id)

                neighbor = self._nodes[neighbor_id]
                next_distance = distance + 1
                neighbor_asset_id = neighbor.asset_id

                if neighbor_asset_id != asset_id:
                    existing_distance = distances.get(
                        neighbor_asset_id,
                    )

                    if (
                        existing_distance is None
                        or next_distance < existing_distance
                    ):
                        distances[neighbor_asset_id] = next_distance

                queue.append(
                    (
                        neighbor_id,
                        next_distance,
                    )
                )

        return distances

    def asset_connectivity_degree(
        self,
        asset_id: str,
    ) -> int:
        """
        Return the number of active physical links touching an asset.

        Higher connectivity indicates that the asset participates in
        more physical network relationships and can therefore be a
        stronger root-cause candidate for infrastructure events.
        """
        node_ids = self._asset_to_nodes.get(asset_id)

        if not node_ids:
            return 0

        return sum(
            len(self._adjacency[node_id])
            for node_id in node_ids
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