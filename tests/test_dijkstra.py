"""Unit tests for Dijkstra's shortest-path algorithm."""
import pytest
from algorithms.dijkstra import dijkstra_shortest_path, DijkstraError


def test_direct_route():
    """Verify simple direct link is selected."""
    nodes = [{"id": "A"}, {"id": "B"}]
    edges = [{"source": "A", "target": "B", "cost": 5, "active": True}]
    
    result = dijkstra_shortest_path(nodes, edges, source="A", destination="B")
    assert result["status"] == "success"
    assert result["reachable"] is True
    assert result["path"] == ["A", "B"]
    assert result["total_cost"] == 5
    assert result["hop_count"] == 1
    assert result["next_hops"]["B"] == "B"


def test_multiple_alternative_paths():
    """Verify Dijkstra chooses lower-cost multi-hop path over expensive direct link."""
    # A -> B cost 10
    # A -> C cost 2, C -> B cost 3 (Total cost 5 via C)
    nodes = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    edges = [
        {"source": "A", "target": "B", "cost": 10, "active": True},
        {"source": "A", "target": "C", "cost": 2, "active": True},
        {"source": "C", "target": "B", "cost": 3, "active": True}
    ]

    result = dijkstra_shortest_path(nodes, edges, source="A", destination="B")
    assert result["reachable"] is True
    assert result["path"] == ["A", "C", "B"]
    assert result["total_cost"] == 5
    assert result["hop_count"] == 2
    assert result["next_hops"]["B"] == "C"
    assert result["next_hops"]["C"] == "C"


def test_equal_cost_paths_deterministic():
    """Verify deterministic tie-breaking on equal-cost paths."""
    # Path 1: A -> B -> D (cost 2 + 3 = 5)
    # Path 2: A -> C -> D (cost 2 + 3 = 5)
    nodes = [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}]
    edges = [
        {"source": "A", "target": "B", "cost": 2, "active": True},
        {"source": "A", "target": "C", "cost": 2, "active": True},
        {"source": "B", "target": "D", "cost": 3, "active": True},
        {"source": "C", "target": "D", "cost": 3, "active": True}
    ]

    result = dijkstra_shortest_path(nodes, edges, source="A", destination="D")
    assert result["reachable"] is True
    assert result["total_cost"] == 5
    assert result["hop_count"] == 2
    # Lexicographical tie-breaking selects B first
    assert result["path"] == ["A", "B", "D"]
    assert result["next_hops"]["D"] == "B"


def test_disconnected_router():
    """Verify behavior when destination is completely unreachable."""
    nodes = [{"id": "A"}, {"id": "B"}, {"id": "ISO"}]
    edges = [{"source": "A", "target": "B", "cost": 4, "active": True}]

    result = dijkstra_shortest_path(nodes, edges, source="A", destination="ISO")
    assert result["reachable"] is False
    assert result["path"] == []
    assert result["total_cost"] is None
    assert result["hop_count"] == 0
    assert result["distances"]["ISO"] is None
    assert result["next_hops"]["ISO"] is None

    # Check routing table entry for isolated node
    iso_entry = next(item for item in result["routing_table"] if item["destination"] == "ISO")
    assert iso_entry["status"] == "Unreachable"
    assert iso_entry["cost"] is None
    assert iso_entry["next_hop"] == "-"


def test_source_equals_destination():
    """Verify source equal to destination produces cost 0, hop count 0, and path [source]."""
    nodes = [{"id": "A"}, {"id": "B"}]
    edges = [{"source": "A", "target": "B", "cost": 3, "active": True}]

    result = dijkstra_shortest_path(nodes, edges, source="A", destination="A")
    assert result["reachable"] is True
    assert result["path"] == ["A"]
    assert result["total_cost"] == 0
    assert result["hop_count"] == 0
    assert result["distances"]["A"] == 0
    assert result["next_hops"]["A"] is None


def test_disabled_links_ignored():
    """Verify disabled links (active=False or status='failed') are not traversed."""
    # A -> B cost 1 (failed/disabled)
    # A -> C cost 2, C -> B cost 2 (active, total cost 4)
    nodes = ["A", "B", "C"]
    edges = [
        {"source": "A", "target": "B", "cost": 1, "active": False},
        {"source": "A", "target": "C", "cost": 2, "status": "active"},
        {"source": "C", "target": "B", "cost": 2, "active": True}
    ]

    result = dijkstra_shortest_path(nodes, edges, source="A", destination="B")
    assert result["reachable"] is True
    assert result["path"] == ["A", "C", "B"]
    assert result["total_cost"] == 4
    assert result["next_hops"]["B"] == "C"


def test_invalid_weights_rejected():
    """Verify negative, zero, non-numeric, or non-finite costs raise DijkstraError."""
    nodes = ["A", "B"]

    # Negative cost
    with pytest.raises(DijkstraError, match="must be positive"):
        dijkstra_shortest_path(nodes, [{"source": "A", "target": "B", "cost": -2}], source="A")

    # Zero cost
    with pytest.raises(DijkstraError, match="must be positive"):
        dijkstra_shortest_path(nodes, [{"source": "A", "target": "B", "cost": 0}], source="A")

    # Non-numeric cost
    with pytest.raises(DijkstraError, match="must be numeric"):
        dijkstra_shortest_path(nodes, [{"source": "A", "target": "B", "cost": "free"}], source="A")


def test_self_loops_rejected():
    """Verify self-loop edges are rejected."""
    nodes = ["A", "B"]
    edges = [{"source": "A", "target": "A", "cost": 3}]
    with pytest.raises(DijkstraError, match="Self-loops are not permitted"):
        dijkstra_shortest_path(nodes, edges, source="A")


def test_missing_router_rejected():
    """Verify unknown source, destination or edge endpoints raise DijkstraError."""
    nodes = ["A", "B"]
    edges = [{"source": "A", "target": "B", "cost": 2}]

    # Unknown source
    with pytest.raises(DijkstraError, match="does not exist"):
        dijkstra_shortest_path(nodes, edges, source="X", destination="B")

    # Unknown destination
    with pytest.raises(DijkstraError, match="does not exist"):
        dijkstra_shortest_path(nodes, edges, source="A", destination="Y")


def test_original_graph_not_modified():
    """Verify input nodes and edges lists/dicts are not mutated."""
    nodes = [{"id": "A"}, {"id": "B"}]
    edges = [{"source": "A", "target": "B", "cost": 4, "active": True}]

    nodes_before = [{"id": "A"}, {"id": "B"}]
    edges_before = [{"source": "A", "target": "B", "cost": 4, "active": True}]

    dijkstra_shortest_path(nodes, edges, source="A", destination="B")

    assert nodes == nodes_before
    assert edges == edges_before


def test_step_trace_generated():
    """Verify algorithm execution steps are captured for visualization."""
    nodes = ["A", "B", "C"]
    edges = [
        {"source": "A", "target": "B", "cost": 2},
        {"source": "B", "target": "C", "cost": 3}
    ]

    result = dijkstra_shortest_path(nodes, edges, source="A", destination="C")
    assert "steps" in result
    assert len(result["steps"]) > 0
    init_step = result["steps"][0]
    assert init_step["type"] == "initialization"
    assert init_step["distances"]["A"] == 0
