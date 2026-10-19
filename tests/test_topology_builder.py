"""Comprehensive tests for Custom Network Topology Builder REST API and Workflows."""
import pytest
from app import create_app
from config import TestingConfig
from simulation.network import NetworkGraph

@pytest.fixture
def client():
    """Create test client for Flask application."""
    app = create_app(TestingConfig)
    with app.test_client() as test_client:
        yield test_client

def test_add_router_auto_id(client):
    """POST /api/topology/router auto-generates sequential ID if blank."""
    # Start fresh by loading sample
    client.post("/api/topology/sample", json={"preset": "mesh5"})
    
    res = client.post("/api/topology/router", json={})
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["router"]["id"].startswith("R")
    assert "topology" in data
    assert len(data["topology"]["nodes"]) == 6

def test_add_router_custom_id_and_label(client):
    """POST /api/topology/router with custom identifier and display label."""
    res = client.post("/api/topology/router", json={
        "id": "GW1",
        "label": "Gateway 1",
        "x": 250,
        "y": 180
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["router"]["id"] == "GW1"
    assert data["router"]["label"] == "Gateway 1"
    assert data["router"]["x"] == 250
    assert data["router"]["y"] == 180

def test_add_router_duplicate_prohibited(client):
    """POST /api/topology/router rejects duplicate router identifiers with HTTP 400."""
    client.post("/api/topology/router", json={"id": "CORE_X"})
    res = client.post("/api/topology/router", json={"id": "CORE_X"})
    assert res.status_code == 400
    data = res.get_json()
    assert data["status"] == "error"
    assert "already exists" in data["message"].lower()

def test_update_router(client):
    """PUT /api/topology/router/<id> updates router label and coordinates."""
    client.post("/api/topology/router", json={"id": "MOD_R", "label": "Initial"})
    res = client.put("/api/topology/router/MOD_R", json={
        "label": "Renamed Core",
        "x": 500,
        "y": 300
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["router"]["label"] == "Renamed Core"
    assert data["router"]["x"] == 500
    assert data["router"]["y"] == 300

def test_update_nonexistent_router(client):
    """PUT /api/topology/router/<id> returns 404 for unknown router."""
    res = client.put("/api/topology/router/UNKNOWN999", json={"label": "Ghost"})
    assert res.status_code == 404
    data = res.get_json()
    assert data["status"] == "error"

def test_delete_router_and_incident_links(client):
    """DELETE /api/topology/router/<id> removes router and cleans connected links."""
    # Reset to sample mesh5
    client.post("/api/topology/sample", json={"preset": "mesh5"})
    
    # Node C has links to A, B, D, E in mesh5
    res = client.delete("/api/topology/router/C")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "deleted successfully" in data["message"]

    # Verify C is gone from GET /api/topology
    top_res = client.get("/api/topology")
    top_data = top_res.get_json()
    node_ids = [n["id"] for n in top_data["nodes"]]
    assert "C" not in node_ids

    # Verify no remaining link references C
    for link in top_data["links"]:
        assert link["source"] != "C"
        assert link["target"] != "C"

def test_delete_nonexistent_router(client):
    """DELETE /api/topology/router/<id> returns 404 for unknown router."""
    res = client.delete("/api/topology/router/DOESNOTEXIST")
    assert res.status_code == 404

def test_add_link_success(client):
    """POST /api/topology/link adds weighted link between existing routers."""
    client.post("/api/topology/sample", json={"preset": "mesh5"})
    # Connect A and D directly
    res = client.post("/api/topology/link", json={
        "source": "A",
        "target": "D",
        "cost": 7
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["link_id"] == "A-D"

def test_add_link_validation(client):
    """POST /api/topology/link enforces validation on self-links, costs, and endpoints."""
    client.post("/api/topology/sample", json={"preset": "mesh5"})

    # Self link
    res1 = client.post("/api/topology/link", json={"source": "A", "target": "A", "cost": 5})
    assert res1.status_code == 400
    assert "self-loops" in res1.get_json()["message"].lower()

    # Zero or negative cost
    res2 = client.post("/api/topology/link", json={"source": "A", "target": "B", "cost": 0})
    assert res2.status_code == 400
    assert "positive" in res2.get_json()["message"].lower()

    res3 = client.post("/api/topology/link", json={"source": "A", "target": "B", "cost": -4})
    assert res3.status_code == 400

    # Non-existent node
    res4 = client.post("/api/topology/link", json={"source": "A", "target": "NONEXISTENT", "cost": 3})
    assert res4.status_code == 400

def test_update_link_cost_and_status(client):
    """PUT /api/topology/link/<id> modifies link weight or status."""
    client.post("/api/topology/sample", json={"preset": "mesh5"})
    
    # Update cost
    res = client.put("/api/topology/link/A-B", json={"cost": 15})
    assert res.status_code == 200
    data = res.get_json()
    assert data["link"]["cost"] == 15

    # Toggle to failed
    res_fail = client.put("/api/topology/link/A-B", json={"status": "failed"})
    assert res_fail.status_code == 200
    assert res_fail.get_json()["link"]["status"] == "failed"

def test_delete_link(client):
    """DELETE /api/topology/link/<id> removes link."""
    client.post("/api/topology/sample", json={"preset": "mesh5"})
    res = client.delete("/api/topology/link/A-B")
    assert res.status_code == 200
    
    # Second delete returns 404
    res2 = client.delete("/api/topology/link/A-B")
    assert res2.status_code == 404

def test_clear_topology(client):
    """POST /api/topology/clear empties the entire graph."""
    res = client.post("/api/topology/clear")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["topology"]["nodes"]) == 0
    assert len(data["topology"]["links"]) == 0

    top_res = client.get("/api/topology")
    assert len(top_res.get_json()["nodes"]) == 0
    assert len(top_res.get_json()["links"]) == 0

def test_load_sample_presets(client):
    """POST /api/topology/sample loads mesh5, nsfnet7, ring6 presets."""
    # Test mesh5
    res1 = client.post("/api/topology/sample", json={"preset": "mesh5"})
    assert res1.status_code == 200
    assert len(res1.get_json()["topology"]["nodes"]) == 5

    # Test nsfnet7
    res2 = client.post("/api/topology/sample", json={"preset": "nsfnet7"})
    assert res2.status_code == 200
    assert len(res2.get_json()["topology"]["nodes"]) == 7

    # Test ring6
    res3 = client.post("/api/topology/sample", json={"preset": "ring6"})
    assert res3.status_code == 200
    assert len(res3.get_json()["topology"]["nodes"]) == 6

    # Test invalid preset
    res4 = client.post("/api/topology/sample", json={"preset": "invalid_xyz"})
    assert res4.status_code == 400

def test_full_custom_topology_build_and_routing(client):
    """End-to-end test: build custom 3-router triangle, calculate Dijkstra & DV."""
    # 1. Clear
    client.post("/api/topology/clear")

    # 2. Add 3 routers
    client.post("/api/topology/router", json={"id": "X1", "label": "Node 1"})
    client.post("/api/topology/router", json={"id": "X2", "label": "Node 2"})
    client.post("/api/topology/router", json={"id": "X3", "label": "Node 3"})

    # 3. Add links: X1-X2 (cost 2), X2-X3 (cost 3), X1-X3 (cost 10)
    client.post("/api/topology/link", json={"source": "X1", "target": "X2", "cost": 2})
    client.post("/api/topology/link", json={"source": "X2", "target": "X3", "cost": 3})
    client.post("/api/topology/link", json={"source": "X1", "target": "X3", "cost": 10})

    # Fetch topology
    top = client.get("/api/topology").get_json()
    assert len(top["nodes"]) == 3
    assert len(top["links"]) == 3

    # 4. Run Dijkstra from X1 to X3 (optimal should be X1 -> X2 -> X3 with cost 5)
    dijkstra_res = client.post("/api/dijkstra", json={
        "nodes": top["nodes"],
        "edges": [{"source": l["source"], "target": l["target"], "cost": l["cost"], "active": True} for l in top["links"]],
        "source": "X1",
        "destination": "X3"
    })
    assert dijkstra_res.status_code == 200
    d_data = dijkstra_res.get_json()
    assert d_data["reachable"] is True
    assert d_data["path"] == ["X1", "X2", "X3"]
    assert d_data["total_cost"] == 5
    assert d_data["hop_count"] == 2

    # 5. Run Distance Vector from X1 to X3
    dv_res = client.post("/api/distance-vector", json={
        "nodes": top["nodes"],
        "edges": [{"source": l["source"], "target": l["target"], "cost": l["cost"], "active": True} for l in top["links"]],
        "source": "X1",
        "destination": "X3"
    })
    assert dv_res.status_code == 200
    dv_data = dv_res.get_json()
    assert dv_data["converged"] is True
    assert dv_data["path"] == ["X1", "X2", "X3"]
    assert dv_data["total_cost"] == 5
