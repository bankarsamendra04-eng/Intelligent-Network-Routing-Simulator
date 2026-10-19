"""Main application factory and entry point for Intelligent Network Routing Simulator."""
import os
from flask import Flask, render_template, jsonify, request
from algorithms.dijkstra import dijkstra_shortest_path, DijkstraError
from algorithms.distance_vector import distance_vector_routing, DistanceVectorError
from simulation.network import NetworkGraph, create_default_topology

def create_app(config_class=None):
    """Factory function to create and configure Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.current_graph = create_default_topology()
    
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object("config.DevelopmentConfig")

    @app.route("/")
    def index():
        """Serve the single-page application frontend."""
        return render_template("index.html")

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Sanity check endpoint for verifying server status."""
        return jsonify({
            "status": "healthy",
            "service": "Intelligent Network Routing Simulator API",
            "version": "1.0.0"
        })

    @app.route("/api/topology", methods=["GET", "POST"])
    def handle_topology():
        """Get or update the active network topology."""
        if request.method == "GET":
            return jsonify(app.current_graph.to_dict()), 200

        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({
                "status": "error",
                "message": "Invalid request: JSON body required."
            }), 400

        if payload.get("reset") is True:
            app.current_graph = create_default_topology()
            return jsonify(app.current_graph.to_dict()), 200

        nodes = payload.get("nodes")
        links = payload.get("links", payload.get("edges", []))
        if not isinstance(nodes, list):
            return jsonify({
                "status": "error",
                "message": "Invalid request: 'nodes' must be an array."
            }), 400

        try:
            new_graph = NetworkGraph()
            for n in nodes:
                nid = n.get("id") if isinstance(n, dict) else str(n)
                lbl = n.get("label", nid) if isinstance(n, dict) else str(n)
                x = n.get("x", 100) if isinstance(n, dict) else 100
                y = n.get("y", 100) if isinstance(n, dict) else 100
                new_graph.add_node(nid, label=lbl, x=x, y=y)
            for l in links:
                new_graph.add_link(
                    l["source"],
                    l["target"],
                    l["cost"],
                    status=l.get("status", "active")
                )
            app.current_graph = new_graph
            return jsonify(app.current_graph.to_dict()), 200
        except Exception as ex:
            return jsonify({
                "status": "error",
                "message": f"Failed to update topology: {str(ex)}"
            }), 400

    @app.route("/api/topology/router", methods=["POST"])
    def add_router():
        """Add a new router to the active topology."""
        payload = request.get_json(silent=True) or {}
        node_id = payload.get("id")
        label = payload.get("label")
        x = payload.get("x", 150)
        y = payload.get("y", 150)

        try:
            created_id = app.current_graph.add_node(node_id, label=label, x=x, y=y)
            return jsonify({
                "status": "success",
                "router": app.current_graph.nodes[created_id],
                "topology": app.current_graph.to_dict()
            }), 201
        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 400
        except Exception as ex:
            return jsonify({"status": "error", "message": f"Server error adding router: {str(ex)}"}), 500

    @app.route("/api/topology/router/<router_id>", methods=["PUT", "DELETE"])
    def modify_router(router_id):
        """Update or delete an existing router."""
        norm_id = str(router_id).strip().upper()
        if request.method == "DELETE":
            try:
                app.current_graph.remove_node(norm_id)
                return jsonify({
                    "status": "success",
                    "message": f"Router '{norm_id}' deleted successfully.",
                    "topology": app.current_graph.to_dict()
                }), 200
            except ValueError as ve:
                return jsonify({"status": "error", "message": str(ve)}), 404

        # PUT: update label or position
        payload = request.get_json(silent=True) or {}
        try:
            updated_node = app.current_graph.update_node(
                norm_id,
                label=payload.get("label"),
                x=payload.get("x"),
                y=payload.get("y")
            )
            return jsonify({
                "status": "success",
                "router": updated_node,
                "topology": app.current_graph.to_dict()
            }), 200
        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 404

    @app.route("/api/topology/link", methods=["POST"])
    def add_link():
        """Add or update a transmission link."""
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"status": "error", "message": "JSON body required."}), 400

        source = payload.get("source")
        target = payload.get("target")
        cost = payload.get("cost")
        status = payload.get("status", "active")

        if not source or not target:
            return jsonify({"status": "error", "message": "Both 'source' and 'target' endpoints are required."}), 400
        if cost is None:
            return jsonify({"status": "error", "message": "Link 'cost' is required."}), 400

        try:
            link_id = app.current_graph.add_link(source, target, cost, status=status)
            return jsonify({
                "status": "success",
                "link_id": link_id,
                "topology": app.current_graph.to_dict()
            }), 201
        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 400

    @app.route("/api/topology/link/<link_id>", methods=["PUT", "DELETE"])
    def modify_link(link_id):
        """Update cost/status or delete a link."""
        canonical_id = str(link_id).strip()
        if request.method == "DELETE":
            try:
                app.current_graph.remove_link(canonical_id)
                return jsonify({
                    "status": "success",
                    "message": f"Link '{canonical_id}' deleted successfully.",
                    "topology": app.current_graph.to_dict()
                }), 200
            except ValueError as ve:
                return jsonify({"status": "error", "message": str(ve)}), 404

        # PUT: update cost or status
        payload = request.get_json(silent=True) or {}
        try:
            updated_link = app.current_graph.update_link(
                canonical_id,
                cost=payload.get("cost"),
                status=payload.get("status")
            )
            return jsonify({
                "status": "success",
                "link": updated_link,
                "topology": app.current_graph.to_dict()
            }), 200
        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 400

    @app.route("/api/topology/clear", methods=["POST"])
    def clear_topology():
        """Clear all routers and links from the active topology."""
        app.current_graph.clear()
        return jsonify({
            "status": "success",
            "message": "Topology cleared.",
            "topology": app.current_graph.to_dict()
        }), 200

    @app.route("/api/topology/sample", methods=["POST"])
    def load_sample():
        """Load a predefined topology preset."""
        payload = request.get_json(silent=True) or {}
        preset = payload.get("preset", "mesh5")
        try:
            top_dict = app.current_graph.load_preset(preset)
            return jsonify({
                "status": "success",
                "preset": preset,
                "topology": top_dict
            }), 200
        except ValueError as ve:
            return jsonify({"status": "error", "message": str(ve)}), 400

    @app.route("/api/dijkstra", methods=["POST"])
    def calculate_dijkstra():
        """Calculate shortest path using Dijkstra algorithm.
        
        Expects JSON payload with:
        - nodes: list of node IDs or node objects [{"id": "A"}, ...]
        - edges: list of edges [{"source": "A", "target": "B", "cost": 4, "active": true}, ...]
        - source: source router ID
        - destination: (optional) destination router ID
        """
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({
                "status": "error",
                "message": "Invalid request: JSON body required."
            }), 400

        nodes = payload.get("nodes")
        if not nodes or not isinstance(nodes, list):
            return jsonify({
                "status": "error",
                "message": "Invalid request: 'nodes' must be a non-empty array."
            }), 400

        edges = payload.get("edges", payload.get("links", []))
        if not isinstance(edges, list):
            return jsonify({
                "status": "error",
                "message": "Invalid request: 'edges' must be an array."
            }), 400

        source = payload.get("source")
        if not source:
            return jsonify({
                "status": "error",
                "message": "Invalid request: 'source' router is required."
            }), 400

        destination = payload.get("destination", payload.get("target"))

        try:
            result = dijkstra_shortest_path(
                nodes=nodes,
                edges=edges,
                source=source,
                destination=destination
            )
            return jsonify(result), 200
        except DijkstraError as de:
            return jsonify({
                "status": "error",
                "message": str(de)
            }), 400
        except Exception as ex:
            return jsonify({
                "status": "error",
                "message": f"Unexpected error calculating shortest path: {str(ex)}"
            }), 500

    @app.route("/api/distance-vector", methods=["POST"])
    def calculate_distance_vector():
        """Simulate Distance Vector routing protocol (Bellman-Ford).
        
        Expects JSON payload with:
        - nodes: list of node IDs or node objects [{"id": "A"}, ...]
        - edges: list of edges [{"source": "A", "target": "B", "cost": 4, "active": true}, ...]
        - source: (optional) source router ID for primary routing table view
        - destination: (optional) destination router ID for path reconstruction
        """
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({
                "status": "error",
                "message": "Invalid request: JSON body required."
            }), 400

        nodes = payload.get("nodes")
        if not nodes or not isinstance(nodes, list):
            return jsonify({
                "status": "error",
                "message": "Invalid request: 'nodes' must be a non-empty array."
            }), 400

        edges = payload.get("edges", payload.get("links", []))
        if not isinstance(edges, list):
            return jsonify({
                "status": "error",
                "message": "Invalid request: 'edges' must be an array."
            }), 400

        source = payload.get("source")
        destination = payload.get("destination", payload.get("target"))

        try:
            result = distance_vector_routing(
                nodes=nodes,
                edges=edges,
                source=source,
                destination=destination
            )
            return jsonify(result), 200
        except DistanceVectorError as dve:
            return jsonify({
                "status": "error",
                "message": str(dve)
            }), 400
        except Exception as ex:
            return jsonify({
                "status": "error",
                "message": f"Unexpected error executing Distance Vector simulation: {str(ex)}"
            }), 500

    @app.errorhandler(404)
    def handle_not_found(error):
        """Custom 404 handler for API routes."""
        if request.path.startswith("/api/"):
            return jsonify({
                "status": "error",
                "message": f"API endpoint not found: {request.path}"
            }), 404
        return render_template("index.html"), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Custom 405 handler for API routes."""
        if request.path.startswith("/api/"):
            return jsonify({
                "status": "error",
                "message": f"HTTP method '{request.method}' not allowed on endpoint '{request.path}'."
            }), 405
        return "Method Not Allowed", 405

    @app.errorhandler(500)
    def handle_server_error(error):
        """Custom 500 handler for API routes."""
        if request.path.startswith("/api/"):
            return jsonify({
                "status": "error",
                "message": "Internal server error occurred."
            }), 500
        return "Internal Server Error", 500

    return app

if __name__ == "__main__":
    application = create_app()
    # Runs locally on host 127.0.0.1, port 5000
    application.run(host="127.0.0.1", port=5000, debug=True)
