"""Network topology and state management module.

Represents routers (nodes) and weighted transmission links (edges),
providing state management for link failure, recovery, and routing execution.
"""
from typing import Dict, List, Any, Optional
from algorithms.dijkstra import dijkstra_shortest_path
from algorithms.distance_vector import distance_vector_routing


class NetworkGraph:
    """Represents a simulated network of routers and communication links."""

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.links: List[Dict[str, Any]] = []

    def auto_generate_router_id(self) -> str:
        """Generate the next available sequential router ID (R1, R2, R3...)."""
        i = 1
        while f"R{i}" in self.nodes:
            i += 1
        return f"R{i}"

    def add_node(self, node_id: Optional[str] = None, label: Optional[str] = None, x: int = 100, y: int = 100) -> str:
        """Add a router node to the topology. Auto-generates ID if None or empty."""
        if not node_id or not str(node_id).strip():
            norm_id = self.auto_generate_router_id()
        else:
            norm_id = str(node_id).strip().upper()

        if norm_id in self.nodes:
            raise ValueError(f"Router '{norm_id}' already exists in topology.")

        self.nodes[norm_id] = {
            "id": norm_id,
            "label": str(label).strip() if label else norm_id,
            "x": int(x),
            "y": int(y)
        }
        return norm_id

    def update_node(self, node_id: str, label: Optional[str] = None, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        """Update display label and/or canvas coordinates for an existing router."""
        norm_id = str(node_id).strip().upper()
        if norm_id not in self.nodes:
            raise ValueError(f"Router '{norm_id}' does not exist.")

        node = self.nodes[norm_id]
        if label is not None:
            lbl = str(label).strip()
            if lbl:
                node["label"] = lbl
        if x is not None:
            node["x"] = int(x)
        if y is not None:
            node["y"] = int(y)
        return node

    def remove_node(self, node_id: str) -> None:
        """Remove a router node and any incident links."""
        norm_id = str(node_id).strip().upper()
        if norm_id not in self.nodes:
            raise ValueError(f"Router '{norm_id}' does not exist.")

        del self.nodes[norm_id]
        self.links = [l for l in self.links if l["source"] != norm_id and l["target"] != norm_id]

    def clear(self) -> None:
        """Clear all router nodes and transmission links from the topology."""
        self.nodes.clear()
        self.links.clear()

    def add_link(self, source: str, target: str, cost: float, status: str = "active") -> str:
        """Add or update an undirected weighted transmission link."""
        u = str(source).strip().upper()
        v = str(target).strip().upper()

        if u == v:
            raise ValueError(f"Self-loops are invalid: cannot connect '{u}' to itself.")
        if u not in self.nodes:
            raise ValueError(f"Endpoint '{u}' does not exist in topology.")
        if v not in self.nodes:
            raise ValueError(f"Endpoint '{v}' does not exist in topology.")

        numeric_cost = float(cost)
        if numeric_cost <= 0:
            raise ValueError(f"Link cost must be positive; got {cost}.")

        canonical_id = f"{min(u, v)}-{max(u, v)}"
        existing = next((l for l in self.links if l["id"] == canonical_id), None)

        if existing:
            existing["cost"] = numeric_cost
            existing["status"] = status
        else:
            self.links.append({
                "id": canonical_id,
                "source": min(u, v),
                "target": max(u, v),
                "cost": int(numeric_cost) if numeric_cost.is_integer() else numeric_cost,
                "status": status
            })
        return canonical_id

    def remove_link(self, link_id: str) -> None:
        """Remove a link by its canonical ID or endpoints."""
        initial_count = len(self.links)
        self.links = [l for l in self.links if l["id"] != link_id]
        if len(self.links) == initial_count:
            raise ValueError(f"Link '{link_id}' not found.")

    def set_link_status(self, source: str, target: str, status: str) -> None:
        """Set link status ('active' or 'failed')."""
        canonical_id = f"{min(source, target)}-{max(source, target)}"
        link = next((l for l in self.links if l["id"] == canonical_id), None)
        if not link:
            raise ValueError(f"Link '{canonical_id}' does not exist.")
        if status not in ("active", "failed"):
            raise ValueError(f"Invalid status '{status}'. Must be 'active' or 'failed'.")
        link["status"] = status

    def toggle_link(self, source: str, target: str) -> str:
        """Toggle link between 'active' and 'failed'."""
        canonical_id = f"{min(source, target)}-{max(source, target)}"
        link = next((l for l in self.links if l["id"] == canonical_id), None)
        if not link:
            raise ValueError(f"Link '{canonical_id}' does not exist.")
        link["status"] = "failed" if link["status"] == "active" else "active"
        return link["status"]

    def recover_all_links(self) -> int:
        """Recover all failed links to active state. Returns count of recovered links."""
        recovered = 0
        for l in self.links:
            if l["status"] == "failed":
                l["status"] = "active"
                recovered += 1
        return recovered

    def get_active_adjacency_list(self) -> Dict[str, Dict[str, float]]:
        """Return adjacency list containing only currently active links."""
        adj = {node: {} for node in self.nodes}
        for link in self.links:
            if link["status"] == "active":
                u, v, cost = link["source"], link["target"], float(link["cost"])
                if u in adj and v in adj:
                    adj[u][v] = cost
                    adj[v][u] = cost
        return adj

    def run_dijkstra(self, source: str, destination: Optional[str] = None) -> Dict[str, Any]:
        """Compute shortest paths using Dijkstra algorithm on current active topology."""
        nodes_payload = [{"id": n} for n in self.nodes]
        edges_payload = [
            {"source": l["source"], "target": l["target"], "cost": l["cost"], "active": (l["status"] == "active")}
            for l in self.links
        ]
        return dijkstra_shortest_path(nodes_payload, edges_payload, source, destination)

    def run_distance_vector(self, source: Optional[str] = None, destination: Optional[str] = None) -> Dict[str, Any]:
        """Simulate Distance-Vector protocol on current active topology."""
        nodes_payload = [{"id": n} for n in self.nodes]
        edges_payload = [
            {"source": l["source"], "target": l["target"], "cost": l["cost"], "active": (l["status"] == "active")}
            for l in self.links
        ]
        return distance_vector_routing(nodes_payload, edges_payload, source, destination)

    def update_link(self, link_id: str, cost: Optional[float] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Update weight cost and/or active/failed status of an existing link."""
        link = next((l for l in self.links if l["id"] == link_id), None)
        if not link:
            raise ValueError(f"Link '{link_id}' not found.")

        if cost is not None:
            numeric_cost = float(cost)
            if numeric_cost <= 0:
                raise ValueError("Link cost must be positive.")
            link["cost"] = int(numeric_cost) if numeric_cost.is_integer() else numeric_cost

        if status is not None:
            if status not in ("active", "failed"):
                raise ValueError(f"Invalid status '{status}'. Must be 'active' or 'failed'.")
            link["status"] = status

        return link

    def load_preset(self, preset_key: str) -> Dict[str, Any]:
        """Load a predefined network topology preset (mesh5, nsfnet7, ring6)."""
        presets = get_sample_presets()
        if preset_key not in presets:
            raise ValueError(f"Unknown topology preset '{preset_key}'. Available: {list(presets.keys())}")

        preset = presets[preset_key]
        self.clear()
        for n in preset["nodes"]:
            self.add_node(n["id"], label=n.get("label"), x=n.get("x", 100), y=n.get("y", 100))
        for l in preset["links"]:
            self.add_link(l["source"], l["target"], l["cost"], status=l.get("status", "active"))
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize current network state to dictionary."""
        return {
            "status": "success",
            "nodes": list(self.nodes.values()),
            "links": list(self.links),
            "active_adjacency": self.get_active_adjacency_list()
        }


def get_sample_presets() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of predefined sample network topologies."""
    return {
        "mesh5": get_default_topology_data(),
        "nsfnet7": {
            "status": "success",
            "name": "7-Node Regional NSFNET Core",
            "nodes": [
                {"id": "R1", "label": "R1", "x": 140, "y": 260},
                {"id": "R2", "label": "R2", "x": 310, "y": 120},
                {"id": "R3", "label": "R3", "x": 520, "y": 130},
                {"id": "R4", "label": "R4", "x": 760, "y": 170},
                {"id": "R5", "label": "R5", "x": 840, "y": 370},
                {"id": "R6", "label": "R6", "x": 570, "y": 420},
                {"id": "R7", "label": "R7", "x": 320, "y": 390}
            ],
            "links": [
                {"id": "R1-R2", "source": "R1", "target": "R2", "cost": 3, "status": "active"},
                {"id": "R1-R7", "source": "R1", "target": "R7", "cost": 6, "status": "active"},
                {"id": "R2-R3", "source": "R2", "target": "R3", "cost": 2, "status": "active"},
                {"id": "R2-R7", "source": "R2", "target": "R7", "cost": 4, "status": "active"},
                {"id": "R3-R4", "source": "R3", "target": "R4", "cost": 5, "status": "active"},
                {"id": "R3-R6", "source": "R3", "target": "R6", "cost": 3, "status": "active"},
                {"id": "R4-R5", "source": "R4", "target": "R5", "cost": 2, "status": "active"},
                {"id": "R4-R6", "source": "R4", "target": "R6", "cost": 1, "status": "active"},
                {"id": "R5-R6", "source": "R5", "target": "R6", "cost": 4, "status": "active"},
                {"id": "R6-R7", "source": "R6", "target": "R7", "cost": 2, "status": "active"}
            ]
        },
        "ring6": {
            "status": "success",
            "name": "6-Node Ring with Cross-Links",
            "nodes": [
                {"id": "N1", "label": "N1", "x": 200, "y": 130},
                {"id": "N2", "label": "N2", "x": 480, "y": 90},
                {"id": "N3", "label": "N3", "x": 760, "y": 130},
                {"id": "N4", "label": "N4", "x": 760, "y": 390},
                {"id": "N5", "label": "N5", "x": 480, "y": 430},
                {"id": "N6", "label": "N6", "x": 200, "y": 390}
            ],
            "links": [
                {"id": "N1-N2", "source": "N1", "target": "N2", "cost": 3, "status": "active"},
                {"id": "N2-N3", "source": "N2", "target": "N3", "cost": 4, "status": "active"},
                {"id": "N3-N4", "source": "N3", "target": "N4", "cost": 2, "status": "active"},
                {"id": "N4-N5", "source": "N4", "target": "N5", "cost": 5, "status": "active"},
                {"id": "N5-N6", "source": "N5", "target": "N6", "cost": 3, "status": "active"},
                {"id": "N1-N6", "source": "N1", "target": "N6", "cost": 6, "status": "active"},
                {"id": "N2-N5", "source": "N2", "target": "N5", "cost": 7, "status": "active"},
                {"id": "N1-N4", "source": "N1", "target": "N4", "cost": 9, "status": "active"}
            ]
        }
    }


def get_default_topology_data() -> Dict[str, Any]:
    """Return the canonical 5-router, 7-link default topology dictionary."""
    return {
        "status": "success",
        "nodes": [
            {"id": "A", "label": "A", "x": 180, "y": 160},
            {"id": "B", "label": "B", "x": 480, "y": 120},
            {"id": "C", "label": "C", "x": 320, "y": 360},
            {"id": "D", "label": "D", "x": 680, "y": 200},
            {"id": "E", "label": "E", "x": 740, "y": 400}
        ],
        "links": [
            {"id": "A-B", "source": "A", "target": "B", "cost": 4, "status": "active"},
            {"id": "A-C", "source": "A", "target": "C", "cost": 2, "status": "active"},
            {"id": "B-C", "source": "B", "target": "C", "cost": 1, "status": "active"},
            {"id": "B-D", "source": "B", "target": "D", "cost": 5, "status": "active"},
            {"id": "C-D", "source": "C", "target": "D", "cost": 8, "status": "active"},
            {"id": "C-E", "source": "C", "target": "E", "cost": 10, "status": "active"},
            {"id": "D-E", "source": "D", "target": "E", "cost": 2, "status": "active"}
        ]
    }


def create_default_topology() -> NetworkGraph:
    """Instantiate and return a NetworkGraph loaded with the canonical 5-router default topology."""
    graph = NetworkGraph()
    data = get_default_topology_data()
    for n in data["nodes"]:
        graph.add_node(n["id"], label=n.get("label"), x=n.get("x", 100), y=n.get("y", 100))
    for l in data["links"]:
        graph.add_link(l["source"], l["target"], l["cost"], status=l.get("status", "active"))
    return graph

