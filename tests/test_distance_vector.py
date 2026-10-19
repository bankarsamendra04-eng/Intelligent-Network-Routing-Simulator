"""Unit tests for Distance-Vector (Bellman-Ford) routing algorithm module."""
import pytest
from algorithms.distance_vector import distance_vector_routing, DistanceVectorError
from algorithms.dijkstra import dijkstra_shortest_path


def test_direct_route():
    """Verify single direct active link establishes correct routing tables."""
    nodes = [{"id": "A"}, {"id": "B"}]
    edges = [{"source": "A", "target": "B", "cost": 7, "active": True}]

    result = distance_vector_routing(nodes, edges, source="A", destination="B")
    assert result["status"] == "success"
    assert result["converged"] is True
    assert result["reachable"] is True
    assert result["path"] == ["A", "B"]
    assert result["total_cost"] == 7
    assert result["hop_count"] == 1

    # Check routing table for A
    table_a = result["final_tables"]["A"]
    b_entry = next(item for item in table_a if item["destination"] == "B")
    assert b_entry["cost"] == 7
    assert b_entry["next_hop"] == "B"
    assert b_entry["status"] == "Reachable"


def test_multihop_route_neighbor_propagation():
    """Verify multi-hop routes are discovered incrementally through direct neighbors."""
    # Topology: A - B - C - D (Chain)
    # Costs: A-B: 2, B-C: 3, C-D: 4
    nodes = ["A", "B", "C", "D"]
    edges = [
        {"source": "A", "target": "B", "cost": 2, "active": True},
        {"source": "B", "target": "C", "cost": 3, "active": True},
        {"source": "C", "target": "D", "cost": 4, "active": True}
    ]

    result = distance_vector_routing(nodes, edges, source="A", destination="D")
    assert result["converged"] is True
    assert result["path"] == ["A", "B", "C", "D"]
    assert result["total_cost"] == 9  # 2 + 3 + 4
    assert result["hop_count"] == 3

    # Check neighbor propagation in rounds
    rounds = result["rounds"]
    # Round 0: A only knows A (0) and B (2). C and D are unreachable.
    round0_a = {item["destination"]: item["cost"] for item in rounds[0]["tables"]["A"]}
    assert round0_a["B"] == 2
    assert round0_a["C"] is None
    assert round0_a["D"] is None

    # Round 1: B shares its vector with A. A learns of C (cost 2 + 3 = 5). D still not known to A!
    round1_a = {item["destination"]: item["cost"] for item in rounds[1]["tables"]["A"]}
    assert round1_a["C"] == 5
    assert round1_a["D"] is None

    # Round 2: A learns of D via B (cost 5 + 4 = 9 via B).
    round2_a = {item["destination"]: item["cost"] for item in rounds[2]["tables"]["A"]}
    assert round2_a["D"] == 9


def test_progressive_route_improvement():
    """Verify Distance Vector updates routing table when a cheaper alternate route arrives."""
    # A - B: 10
    # A - C: 2
    # C - B: 3
    nodes = ["A", "B", "C"]
    edges = [
        {"source": "A", "target": "B", "cost": 10, "active": True},
        {"source": "A", "target": "C", "cost": 2, "active": True},
        {"source": "C", "target": "B", "cost": 3, "active": True}
    ]

    result = distance_vector_routing(nodes, edges, source="A", destination="B")
    assert result["converged"] is True
    assert result["path"] == ["A", "C", "B"]
    assert result["total_cost"] == 5
    assert result["hop_count"] == 2

    # Check next hop from A to B is C
    table_a = result["final_tables"]["A"]
    entry_b = next(item for item in table_a if item["destination"] == "B")
    assert entry_b["cost"] == 5
    assert entry_b["next_hop"] == "C"


def test_disconnected_network():
    """Verify disconnected components leave destinations as unreachable with None cost."""
    nodes = ["A", "B", "ISO"]
    edges = [{"source": "A", "target": "B", "cost": 4, "active": True}]

    result = distance_vector_routing(nodes, edges, source="A", destination="ISO")
    assert result["converged"] is True
    assert result["reachable"] is False
    assert result["path"] == []
    assert result["total_cost"] is None

    table_a = result["final_tables"]["A"]
    iso_entry = next(item for item in table_a if item["destination"] == "ISO")
    assert iso_entry["cost"] is None
    assert iso_entry["next_hop"] == "-"
    assert iso_entry["status"] == "Unreachable"


def test_link_failure_exclusion():
    """Verify failed links are completely excluded from neighbor updates."""
    # A - B (cost 1, failed)
    # A - C (cost 2, active), C - B (cost 3, active)
    nodes = ["A", "B", "C"]
    edges = [
        {"source": "A", "target": "B", "cost": 1, "active": False},
        {"source": "A", "target": "C", "cost": 2, "active": True},
        {"source": "C", "target": "B", "cost": 3, "status": "active"}
    ]

    result = distance_vector_routing(nodes, edges, source="A", destination="B")
    assert result["converged"] is True
    assert result["path"] == ["A", "C", "B"]
    assert result["total_cost"] == 5
    assert result["hop_count"] == 2


def test_source_equals_destination():
    """Verify source equal to destination gives cost 0, 0 hops, and path [source]."""
    nodes = ["A", "B"]
    edges = [{"source": "A", "target": "B", "cost": 4}]

    result = distance_vector_routing(nodes, edges, source="A", destination="A")
    assert result["converged"] is True
    assert result["reachable"] is True
    assert result["path"] == ["A"]
    assert result["total_cost"] == 0
    assert result["hop_count"] == 0


def test_compare_with_dijkstra():
    """Verify Distance Vector converged costs match Dijkstra shortest paths on mesh topology."""
    nodes = ["A", "B", "C", "D", "E"]
    edges = [
        {"source": "A", "target": "B", "cost": 4, "active": True},
        {"source": "A", "target": "D", "cost": 2, "active": True},
        {"source": "B", "target": "C", "cost": 3, "active": True},
        {"source": "B", "target": "D", "cost": 5, "active": True},
        {"source": "B", "target": "E", "cost": 1, "active": True},
        {"source": "C", "target": "E", "cost": 2, "active": True},
        {"source": "D", "target": "E", "cost": 7, "active": True}
    ]

    dv_result = distance_vector_routing(nodes, edges, source="A", destination="C")
    dijkstra_result = dijkstra_shortest_path(nodes, edges, source="A", destination="C")

    assert dv_result["converged"] is True
    assert dv_result["total_cost"] == dijkstra_result["total_cost"]
    assert dv_result["path"] == dijkstra_result["path"]

    # Verify every destination cost from A matches
    for dest in ["A", "B", "C", "D", "E"]:
        dv_dest_cost = next(item["cost"] for item in dv_result["final_tables"]["A"] if item["destination"] == dest)
        dijkstra_dest_cost = dijkstra_result["distances"][dest]
        assert dv_dest_cost == dijkstra_dest_cost, f"Cost mismatch for destination {dest}"


def test_invalid_topology_rejection():
    """Verify validation errors for empty nodes, invalid costs, and self-loops."""
    # Empty nodes
    with pytest.raises(DistanceVectorError, match="at least one router"):
        distance_vector_routing([], [])

    # Self-loop
    with pytest.raises(DistanceVectorError, match="Self-loops are not permitted"):
        distance_vector_routing(["A"], [{"source": "A", "target": "A", "cost": 5}])

    # Negative cost
    with pytest.raises(DistanceVectorError, match="must be positive"):
        distance_vector_routing(["A", "B"], [{"source": "A", "target": "B", "cost": -3}])
