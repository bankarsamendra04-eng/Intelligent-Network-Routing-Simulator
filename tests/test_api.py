"""API and Frontend Integration Tests for Intelligent Network Routing Simulator."""
import pytest
from app import create_app
from config import TestingConfig

@pytest.fixture
def client():
    """Create test client for Flask application."""
    app = create_app(TestingConfig)
    with app.test_client() as test_client:
        yield test_client

def test_health_check_endpoint(client):
    """Verify health check endpoint returns 200, status healthy, and JSON header."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = response.get_json()
    assert data is not None
    assert data["status"] == "healthy"
    assert "Intelligent Network Routing Simulator" in data["service"]

def test_index_dashboard_layout(client):
    """Verify dashboard index serves HTML containing all Phase 2 UI panels and controls."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    html = response.data.decode("utf-8")

    # Header & Status
    assert "Intelligent Network Routing Simulator" in html
    assert "backendStatusBadge" in html
    assert "statusIndicator" in html

    # Canvas & Layers
    assert "networkSvg" in html
    assert "linksGroup" in html
    assert "linkLabelsGroup" in html
    assert "nodesGroup" in html
    assert "canvasContainer" in html

    # Preset Topologies
    assert "topologyPresetSelect" in html
    assert "mesh5" in html
    assert "nsfnet7" in html
    assert "ring6" in html
    assert "btnLoadPreset" in html

    # Topology Editing Controls (Routers & Links)
    assert "formAddRouter" in html
    assert "routerIdInput" in html
    assert "formRemoveRouter" in html
    assert "removeRouterSelect" in html
    assert "formAddLink" in html
    assert "linkSourceSelect" in html
    assert "linkTargetSelect" in html
    assert "linkCostInput" in html
    assert "formRemoveLink" in html
    assert "removeLinkSelect" in html

    # Simulation & Algorithm Selection
    assert "algorithmSelect" in html
    assert "dijkstra" in html
    assert "distance_vector" in html
    assert "sourceRouterSelect" in html
    assert "destRouterSelect" in html
    assert "btnRunSimulation" in html
    assert "btnNextStep" in html
    assert "btnPrevStep" in html
    assert "btnResetSimulation" in html

    # Link Failure and Recovery
    assert "failureLinkSelect" in html
    assert "btnToggleLinkFailure" in html
    assert "btnRecoverAllLinks" in html
    assert "failedLinksContainer" in html

    # Results, Routing Tables & Event Log
    assert "resultsCard" in html
    assert "resultStatus" in html
    assert "resultPath" in html
    assert "resultCost" in html
    assert "resultHops" in html
    assert "routingTableDisplay" in html
    assert "eventLogContainer" in html
    assert "eventLogEntries" in html

def test_static_css_served(client):
    """Verify static CSS stylesheet is served with status 200."""
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert "text/css" in response.content_type
    content = response.data.decode("utf-8")
    assert "--node-default-fill" in content
    assert ".router-node" in content
    assert ".link-line" in content

def test_static_topology_js_served(client):
    """Verify static topology.js module is served with status 200."""
    response = client.get("/static/js/topology.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type
    content = response.data.decode("utf-8")
    assert "Topology" in content
    assert "mesh5" in content
    assert "nsfnet7" in content
    assert "addNode" in content
    assert "addLink" in content
    assert "toggleLinkStatus" in content

def test_static_app_js_served(client):
    """Verify static app.js coordinator script is served with status 200."""
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type
    content = response.data.decode("utf-8")
    assert "App" in content
    assert "checkBackendHealth" in content
    assert "handleRunSimulationClick" in content
    assert "syncDropdowns" in content

def test_api_dijkstra_success(client):
    """Verify POST /api/dijkstra computes shortest path correctly."""
    payload = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [
            {"source": "A", "target": "B", "cost": 4, "active": True},
            {"source": "A", "target": "C", "cost": 1, "active": True},
            {"source": "C", "target": "B", "cost": 1, "active": True}
        ],
        "source": "A",
        "destination": "B"
    }
    response = client.post("/api/dijkstra", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["source"] == "A"
    assert data["destination"] == "B"
    assert data["reachable"] is True
    assert data["path"] == ["A", "C", "B"]
    assert data["total_cost"] == 2
    assert data["hop_count"] == 2
    assert data["next_hops"]["B"] == "C"
    assert len(data["steps"]) > 0

def test_api_dijkstra_missing_body(client):
    """Verify POST /api/dijkstra returns 400 when body is missing."""
    response = client.post("/api/dijkstra", data="not json", content_type="text/plain")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"

def test_api_dijkstra_missing_source(client):
    """Verify POST /api/dijkstra returns 400 when source is omitted."""
    payload = {
        "nodes": [{"id": "A"}, {"id": "B"}],
        "edges": [{"source": "A", "target": "B", "cost": 2}]
    }
    response = client.post("/api/dijkstra", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert "source" in data["message"].lower()

def test_api_dijkstra_invalid_cost(client):
    """Verify POST /api/dijkstra returns 400 when cost is non-positive."""
    payload = {
        "nodes": [{"id": "A"}, {"id": "B"}],
        "edges": [{"source": "A", "target": "B", "cost": -5}],
        "source": "A",
        "destination": "B"
    }
    response = client.post("/api/dijkstra", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert "positive" in data["message"].lower()

def test_api_distance_vector_success(client):
    """Verify POST /api/distance-vector simulates Bellman-Ford correctly."""
    payload = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [
            {"source": "A", "target": "B", "cost": 4, "active": True},
            {"source": "A", "target": "C", "cost": 1, "active": True},
            {"source": "C", "target": "B", "cost": 1, "active": True}
        ],
        "source": "A",
        "destination": "B"
    }
    response = client.post("/api/distance-vector", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["converged"] is True
    assert data["total_rounds"] >= 1
    assert data["path"] == ["A", "C", "B"]
    assert data["total_cost"] == 2
    assert "final_tables" in data
    assert "rounds" in data
    assert len(data["rounds"]) > 0

def test_api_distance_vector_invalid_request(client):
    """Verify POST /api/distance-vector returns 400 when invalid input is provided."""
    # Missing body
    response = client.post("/api/distance-vector", data="bad", content_type="text/plain")
    assert response.status_code == 400

    # Empty nodes
    response = client.post("/api/distance-vector", json={"nodes": [], "edges": []})
    assert response.status_code == 400

def test_api_404_json(client):
    """Verify non-existent API routes return 404 JSON error."""
    response = client.get("/api/nonexistent_endpoint")
    assert response.status_code == 404
    data = response.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

def test_api_405_method_not_allowed(client):
    """Verify invalid HTTP method on API routes returns 405 JSON error."""
    response = client.get("/api/dijkstra")  # dijkstra only accepts POST
    assert response.status_code == 405
    data = response.get_json()
    assert data["status"] == "error"
    assert "not allowed" in data["message"].lower()

def test_api_get_topology_default(client):
    """Verify GET /api/topology returns the canonical 5-router, 7-link network."""
    response = client.get("/api/topology")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    
    # Verify 5 nodes: A, B, C, D, E
    node_ids = {n["id"] for n in data["nodes"]}
    assert node_ids == {"A", "B", "C", "D", "E"}
    
    # Verify 7 links with exact costs
    links_map = {f"{min(l['source'], l['target'])}-{max(l['source'], l['target'])}": l["cost"] for l in data["links"]}
    assert links_map == {
        "A-B": 4,
        "A-C": 2,
        "B-C": 1,
        "B-D": 5,
        "C-D": 8,
        "C-E": 10,
        "D-E": 2
    }

def test_api_post_topology_reset(client):
    """Verify POST /api/topology with reset=True restores the default topology."""
    reset_res = client.post("/api/topology", json={"reset": True})
    assert reset_res.status_code == 200
    data = reset_res.get_json()
    assert data["status"] == "success"
    assert len(data["nodes"]) == 5
    assert len(data["links"]) == 7

def test_default_topology_dijkstra_and_dv_workflow(client):
    """Verify routing simulations on default topology: A->B path is A->C->B (cost 3, hops 2)."""
    top_res = client.get("/api/topology")
    top_data = top_res.get_json()
    
    # Run Dijkstra A -> B
    dijkstra_payload = {
        "nodes": top_data["nodes"],
        "edges": top_data["links"],
        "source": "A",
        "destination": "B"
    }
    d_res = client.post("/api/dijkstra", json=dijkstra_payload)
    assert d_res.status_code == 200
    d_data = d_res.get_json()
    assert d_data["reachable"] is True
    assert d_data["path"] == ["A", "C", "B"]
    assert d_data["total_cost"] == 3
    assert d_data["hop_count"] == 2

    # Run Distance Vector A -> B
    dv_res = client.post("/api/distance-vector", json=dijkstra_payload)
    assert dv_res.status_code == 200
    dv_data = dv_res.get_json()
    assert dv_data["converged"] is True
    assert dv_data["path"] == ["A", "C", "B"]
    assert dv_data["total_cost"] == 3

    # Link failure test: disable B-C
    modified_links = [
        {**l, "active": False} if (l["source"] == "B" and l["target"] == "C") or (l["source"] == "C" and l["target"] == "B")
        else {**l, "active": True}
        for l in top_data["links"]
    ]
    d_failed_res = client.post("/api/dijkstra", json={
        "nodes": top_data["nodes"],
        "edges": modified_links,
        "source": "A",
        "destination": "B"
    })
    assert d_failed_res.status_code == 200
    d_failed_data = d_failed_res.get_json()
    # Path should failover to direct A-B link with cost 4
    assert d_failed_data["path"] == ["A", "B"]
    assert d_failed_data["total_cost"] == 4

