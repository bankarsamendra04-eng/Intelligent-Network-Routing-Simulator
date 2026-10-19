"""Unit and integration tests for network topology management, presets, and sync."""
import pytest
from simulation.network import NetworkGraph, get_default_topology_data, create_default_topology
from app import create_app
from config import TestingConfig

@pytest.fixture
def client():
    """Create test client for Flask application."""
    app = create_app(TestingConfig)
    with app.test_client() as test_client:
        yield test_client

def test_default_topology_data_schema():
    """Verify default topology specification matches 5 routers and 7 links."""
    data = get_default_topology_data()
    assert data["status"] == "success"
    assert len(data["nodes"]) == 5
    assert len(data["links"]) == 7

    node_ids = [n["id"] for n in data["nodes"]]
    assert node_ids == ["A", "B", "C", "D", "E"]

    expected_links = [
        ("A", "B", 4),
        ("A", "C", 2),
        ("B", "C", 1),
        ("B", "D", 5),
        ("C", "D", 8),
        ("C", "E", 10),
        ("D", "E", 2)
    ]
    actual_links = [
        (min(l["source"], l["target"]), max(l["source"], l["target"]), l["cost"])
        for l in data["links"]
    ]
    for exp in expected_links:
        assert (min(exp[0], exp[1]), max(exp[0], exp[1]), exp[2]) in actual_links

def test_create_default_topology_instance():
    """Verify create_default_topology returns fully functional NetworkGraph."""
    graph = create_default_topology()
    assert len(graph.nodes) == 5
    assert len(graph.links) == 7

    # Verify Dijkstra calculation A -> B gives A -> C -> B with cost 3
    result = graph.run_dijkstra("A", "B")
    assert result["reachable"] is True
    assert result["path"] == ["A", "C", "B"]
    assert result["total_cost"] == 3
    assert result["hop_count"] == 2

    # Verify Distance Vector converges to identical cost 3
    dv_result = graph.run_distance_vector("A", "B")
    assert dv_result["converged"] is True
    assert dv_result["path"] == ["A", "C", "B"]
    assert dv_result["total_cost"] == 3

def test_single_router_topology():
    """Verify network operations with a single router node."""
    graph = NetworkGraph()
    graph.add_node("R1")
    assert len(graph.nodes) == 1
    assert len(graph.links) == 0

    # Dijkstra from R1 to R1 is 0 cost
    res = graph.run_dijkstra("R1", "R1")
    assert res["reachable"] is True
    assert res["total_cost"] == 0
    assert res["hop_count"] == 0
    assert res["path"] == ["R1"]

def test_topology_link_failure_and_recovery():
    """Verify link status toggle updates active adjacency and path calculation."""
    graph = create_default_topology()

    # Disable B-C link
    status = graph.toggle_link("B", "C")
    assert status == "failed"
    
    # Path A -> B must now take direct link A-B with cost 4
    res = graph.run_dijkstra("A", "B")
    assert res["path"] == ["A", "B"]
    assert res["total_cost"] == 4

    # Recover all links
    recovered = graph.recover_all_links()
    assert recovered == 1
    
    # Path A -> B should return to A -> C -> B with cost 3
    res_recovered = graph.run_dijkstra("A", "B")
    assert res_recovered["path"] == ["A", "C", "B"]
    assert res_recovered["total_cost"] == 3

def test_api_post_topology_custom(client):
    """Verify POST /api/topology accepts and validates customized topology."""
    payload = {
        "nodes": [{"id": "X"}, {"id": "Y"}, {"id": "Z"}],
        "links": [
            {"source": "X", "target": "Y", "cost": 10},
            {"source": "Y", "target": "Z", "cost": 15}
        ]
    }
    response = client.post("/api/topology", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["nodes"]) == 3
    assert len(data["links"]) == 2

    # Verify subsequent GET /api/topology returns the updated network
    get_res = client.get("/api/topology")
    assert get_res.status_code == 200
    assert len(get_res.get_json()["nodes"]) == 3

    # Reset back to default
    reset_res = client.post("/api/topology", json={"reset": True})
    assert reset_res.status_code == 200
    assert len(reset_res.get_json()["nodes"]) == 5
