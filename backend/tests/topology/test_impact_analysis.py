from app.topology.schemas import TopologyEdge, TopologyNode
from app.topology.service import TopologyService


def build_service() -> TopologyService:
    nodes = [
        TopologyNode("router", "R1", "Core Router"),
        TopologyNode("switch", "SW1", "Deck 7 Switch"),
        TopologyNode("ap1", "AP1", "Deck 7 AP 1"),
        TopologyNode("ap2", "AP2", "Deck 7 AP 2"),
        TopologyNode("pos1", "POS1", "POS 1"),
        TopologyNode("pos2", "POS2", "POS 2"),
        TopologyNode("pos3", "POS3", "POS 3"),
        TopologyNode("isolated", "ISO1", "Isolated Device"),
    ]

    edges = [
        TopologyEdge("router", "switch"),
        TopologyEdge("switch", "ap1"),
        TopologyEdge("switch", "ap2"),
        TopologyEdge("ap1", "pos1"),
        TopologyEdge("ap1", "pos2"),
        TopologyEdge("ap2", "pos3"),
    ]

    return TopologyService(nodes, edges)


def test_physical_impact_includes_connected_assets():
    service = build_service()

    affected = service.impacted_assets("SW1")

    assert affected == {
        "R1",
        "AP1",
        "AP2",
        "POS1",
        "POS2",
        "POS3",
    }


def test_starting_asset_is_excluded():
    service = build_service()

    affected = service.impacted_assets("SW1")

    assert "SW1" not in affected


def test_isolated_asset_is_not_affected():
    service = build_service()

    affected = service.impacted_assets("SW1")

    assert "ISO1" not in affected


def test_unknown_asset_returns_empty_set():
    service = build_service()

    assert service.impacted_assets("does-not-exist") == set()


def test_failed_link_is_not_traversed():
    nodes = [
        TopologyNode("switch", "SW1", "Switch"),
        TopologyNode("ap", "AP1", "Access Point"),
        TopologyNode("pos", "POS1", "POS"),
    ]

    edges = [
        TopologyEdge(
            "switch",
            "ap",
            operational_up=False,
        ),
        TopologyEdge("ap", "pos"),
    ]

    service = TopologyService(nodes, edges)

    assert service.impacted_assets("SW1") == set()


def test_cycles_do_not_cause_infinite_traversal():
    nodes = [
        TopologyNode("a", "A", "A"),
        TopologyNode("b", "B", "B"),
        TopologyNode("c", "C", "C"),
    ]

    edges = [
        TopologyEdge("a", "b"),
        TopologyEdge("b", "c"),
        TopologyEdge("c", "a"),
    ]

    service = TopologyService(nodes, edges)

    affected = service.impacted_assets("A")

    assert affected == {"B", "C"}


def test_interface_level_analysis_still_works():
    service = build_service()

    affected = service.downstream_assets("switch")

    assert affected == {
        "R1",
        "AP1",
        "AP2",
        "POS1",
        "POS2",
        "POS3",
    }