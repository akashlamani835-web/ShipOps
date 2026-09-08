from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopologyNode:
    """A node in the network topology graph."""

    id: str
    asset_id: str
    name: str


@dataclass(frozen=True, slots=True)
class TopologyEdge:
    """A directed traversal edge between two topology nodes."""

    source_node_id: str
    destination_node_id: str
    operational_up: bool = True