"""Integration tests for Network Simulation and Link Failure Scenarios.

Verifies:
1. Shortest path routing over redundant mesh.
2. Link failure on the active route causes automatic re-routing over alternative path.
3. Multiple link failures causing total partition result in explicit unreachable status.
4. Link recovery restores connectivity and re-establishes optimal paths.
5. Inactive/failed links are never traversed by either Dijkstra or Distance-Vector.
"""
import pytest
from app import create_app
from config import TestingConfig
from simulation.network import NetworkGraph


@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app(TestingConfig)
    with app.test_client() as test_client:
        yield test_client


def test_network_graph_lifecycle_and_failure_scenarios():
    """Verify link failure and recovery lifecycle using NetworkGraph domain model."""
    net = NetworkGraph()

    # Build 5-Node Redundant Mesh (Preset 1)
    for node_id in ["A", "B", "C", "D", "E"]:
        net.add_node(node_id)

    # Initial links:
    # A-B (4), A-D (2), B-C (3), B-D (5), B-E (1), C-E (2), D-E (7)
    net.add_link("A", "B", 4)
    net.add_link("A", "D", 2)
    net.add_link("B", "C", 3)
    net.add_link("B", "D", 5)
    net.add_link("B", "E", 1)
    net.add_link("C", "E", 2)
    net.add_link("D", "E", 7)

    # 1. Initial Shortest Path from A to E:
    # Option 1: A -> B -> E (Cost: 4 + 1 = 5)
    # Option 2: A -> D -> E (Cost: 2 + 7 = 9)
    # Option 3: A -> B -> C -> E (Cost: 4 + 3 + 2 = 9)
    dijkstra_init = net.run_dijkstra("A", "E")
    dv_init = net.run_distance_vector("A", "E")

    assert dijkstra_init["reachable"] is True
    assert dijkstra_init["path"] == ["A", "B", "E"]
    assert dijkstra_init["total_cost"] == 5
    assert dv_init["converged"] is True
    assert dv_init["path"] == ["A", "B", "E"]
    assert dv_init["total_cost"] == 5

    # 2. Simulate Link Failure on the active route (B-E fails)
    status = net.toggle_link("B", "E")
    assert status == "failed"

    # Re-calculate routing under failure
    dijkstra_fail1 = net.run_dijkstra("A", "E")
    dv_fail1 = net.run_distance_vector("A", "E")

    # B-E is broken. New alternative paths:
    # Path A -> D -> E (cost 2 + 7 = 9)
    # Path A -> B -> C -> E (cost 4 + 3 + 2 = 9)
    # Deterministic tie-breaking selects A -> B -> C -> E
    assert dijkstra_fail1["reachable"] is True
    assert "B-E" not in [f"{u}-{v}" for u, v in zip(dijkstra_fail1["path"][:-1], dijkstra_fail1["path"][1:])]
    assert dijkstra_fail1["total_cost"] == 9
    assert dv_fail1["total_cost"] == 9
    assert dijkstra_fail1["reachable"] is True
    assert dv_fail1["reachable"] is True

    # 3. Fail all remaining ingress links to E: C-E and D-E
    net.set_link_status("C", "E", "failed")
    net.set_link_status("D", "E", "failed")

    # Now router E is completely disconnected from the network
    dijkstra_part = net.run_dijkstra("A", "E")
    dv_part = net.run_distance_vector("A", "E")

    assert dijkstra_part["reachable"] is False
    assert dijkstra_part["path"] == []
    assert dijkstra_part["total_cost"] is None
    assert dijkstra_part["hop_count"] == 0

    assert dv_part["reachable"] is False
    assert dv_part["path"] == []
    assert dv_part["total_cost"] is None

    # Check routing table for E is marked Unreachable
    entry_e_dijkstra = next(r for r in dijkstra_part["routing_table"] if r["destination"] == "E")
    assert entry_e_dijkstra["status"] == "Unreachable"
    assert entry_e_dijkstra["cost"] is None
    assert entry_e_dijkstra["next_hop"] == "-"

    # 4. Recover link B-E
    net.set_link_status("B", "E", "active")

    dijkstra_recovered = net.run_dijkstra("A", "E")
    dv_recovered = net.run_distance_vector("A", "E")

    assert dijkstra_recovered["reachable"] is True
    assert dijkstra_recovered["path"] == ["A", "B", "E"]
    assert dijkstra_recovered["total_cost"] == 5

    assert dv_recovered["reachable"] is True
    assert dv_recovered["path"] == ["A", "B", "E"]
    assert dv_recovered["total_cost"] == 5

    # 5. Recover all links
    recovered_count = net.recover_all_links()
    assert recovered_count == 2  # C-E and D-E were still failed


def test_api_link_failure_workflow(client):
    """Verify full end-to-end link failure workflow via Flask API endpoints."""
    nodes = [{"id": "R1"}, {"id": "R2"}, {"id": "R3"}]
    # R1 - R2 (cost 1, active)
    # R1 - R3 (cost 5, active)
    # R2 - R3 (cost 2, active)
    edges = [
        {"source": "R1", "target": "R2", "cost": 1, "active": True},
        {"source": "R1", "target": "R3", "cost": 5, "active": True},
        {"source": "R2", "target": "R3", "cost": 2, "active": True}
    ]

    # Step 1: Initial shortest path from R1 to R3 via R2 (1 + 2 = 3)
    res1 = client.post("/api/dijkstra", json={
        "nodes": nodes,
        "edges": edges,
        "source": "R1",
        "destination": "R3"
    })
    data1 = res1.get_json()
    assert data1["reachable"] is True
    assert data1["path"] == ["R1", "R2", "R3"]
    assert data1["total_cost"] == 3

    # Step 2: Simulate failure of link R2-R3
    for e in edges:
        if (e["source"] == "R2" and e["target"] == "R3") or (e["source"] == "R3" and e["target"] == "R2"):
            e["active"] = False

    res2 = client.post("/api/dijkstra", json={
        "nodes": nodes,
        "edges": edges,
        "source": "R1",
        "destination": "R3"
    })
    data2 = res2.get_json()
    # Now route must divert to direct link R1-R3 (Cost: 5)
    assert data2["reachable"] is True
    assert data2["path"] == ["R1", "R3"]
    assert data2["total_cost"] == 5

    # Also test Distance Vector on the same failed network
    res2_dv = client.post("/api/distance-vector", json={
        "nodes": nodes,
        "edges": edges,
        "source": "R1",
        "destination": "R3"
    })
    data2_dv = res2_dv.get_json()
    assert data2_dv["converged"] is True
    assert data2_dv["reachable"] is True
    assert data2_dv["path"] == ["R1", "R3"]
    assert data2_dv["total_cost"] == 5

    # Step 3: Fail link R1-R3 as well -> R3 is completely unreachable
    for e in edges:
        if (e["source"] == "R1" and e["target"] == "R3") or (e["source"] == "R3" and e["target"] == "R1"):
            e["active"] = False

    res3 = client.post("/api/dijkstra", json={
        "nodes": nodes,
        "edges": edges,
        "source": "R1",
        "destination": "R3"
    })
    data3 = res3.get_json()
    assert data3["reachable"] is False
    assert data3["path"] == []
    assert data3["total_cost"] is None

    res3_dv = client.post("/api/distance-vector", json={
        "nodes": nodes,
        "edges": edges,
        "source": "R1",
        "destination": "R3"
    })
    data3_dv = res3_dv.get_json()
    assert data3_dv["reachable"] is False
    assert data3_dv["path"] == []
    assert data3_dv["total_cost"] is None
