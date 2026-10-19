"""Distance-Vector Routing Algorithm Module.

Implements a deterministic, round-based distributed Bellman-Ford simulation
with local neighbor vector exchange, routing table maintenance,
convergence tracking, loop protection, and step-by-step trace generation.
"""
import copy
import math
from typing import Dict, List, Any, Optional, Tuple, Set


class DistanceVectorError(ValueError):
    """Raised when Distance Vector input data fails validation."""
    pass


def validate_topology(
    nodes: List[Any],
    edges: List[Dict[str, Any]],
    source: Optional[str] = None,
    destination: Optional[str] = None
) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    """Validate graph topology inputs and build active adjacency map.

    Args:
        nodes: List of node IDs or dicts with 'id' key.
        edges: List of edge dicts with 'source', 'target', 'cost', and 'active'/'status'.
        source: Optional source router identifier.
        destination: Optional destination router identifier.

    Returns:
        Tuple of (sorted_node_list, active_adjacency_dict).

    Raises:
        DistanceVectorError: If topology input is invalid.
    """
    if not nodes:
        raise DistanceVectorError("Topology must contain at least one router node.")

    node_set: Set[str] = set()
    node_list: List[str] = []
    for n in nodes:
        node_id = n.get("id") if isinstance(n, dict) else n
        if node_id is None:
            raise DistanceVectorError("Invalid node entry: missing 'id'.")
        node_id = str(node_id).strip()
        if not node_id:
            raise DistanceVectorError("Node identifier cannot be empty.")
        if node_id in node_set:
            raise DistanceVectorError(f"Duplicate node identifier detected: '{node_id}'.")
        node_set.add(node_id)
        node_list.append(node_id)

    sorted_nodes = sorted(node_list)

    if source is not None and str(source).strip():
        norm_source = str(source).strip()
        if norm_source not in node_set:
            raise DistanceVectorError(f"Source router '{norm_source}' does not exist in the topology.")

    if destination is not None and str(destination).strip():
        norm_dest = str(destination).strip()
        if norm_dest not in node_set:
            raise DistanceVectorError(f"Destination router '{norm_dest}' does not exist in the topology.")

    adjacency: Dict[str, Dict[str, float]] = {n: {} for n in sorted_nodes}

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise DistanceVectorError(f"Edge at index {idx} must be an object.")

        u = edge.get("source")
        v = edge.get("target")
        if u is None or v is None:
            raise DistanceVectorError(f"Edge at index {idx} is missing source or target endpoint.")

        u = str(u).strip()
        v = str(v).strip()

        if u not in node_set:
            raise DistanceVectorError(f"Edge references non-existent router '{u}'.")
        if v not in node_set:
            raise DistanceVectorError(f"Edge references non-existent router '{v}'.")
        if u == v:
            raise DistanceVectorError(f"Self-loops are not permitted: router '{u}' connects to itself.")

        raw_cost = edge.get("cost", edge.get("weight"))
        if raw_cost is None:
            raise DistanceVectorError(f"Edge {u}-{v} is missing cost/weight.")

        try:
            cost = float(raw_cost)
        except (ValueError, TypeError):
            raise DistanceVectorError(f"Edge {u}-{v} cost must be numeric; got {raw_cost!r}.")

        if math.isnan(cost) or math.isinf(cost):
            raise DistanceVectorError(f"Edge {u}-{v} cost must be finite; got {cost}.")
        if cost <= 0:
            raise DistanceVectorError(f"Edge {u}-{v} cost must be positive and greater than 0; got {cost}.")

        is_active = True
        if "active" in edge:
            is_active = bool(edge["active"])
        if "status" in edge:
            is_active = is_active and (edge["status"] == "active")

        if is_active:
            if v not in adjacency[u] or cost < adjacency[u][v]:
                adjacency[u][v] = cost
            if u not in adjacency[v] or cost < adjacency[v][u]:
                adjacency[v][u] = cost

    return sorted_nodes, adjacency


def distance_vector_routing(
    nodes: List[Any],
    edges: List[Dict[str, Any]],
    source: Optional[str] = None,
    destination: Optional[str] = None,
    max_rounds: int = 30
) -> Dict[str, Any]:
    """Execute round-based Distance-Vector (Bellman-Ford) routing simulation.

    Args:
        nodes: List of node IDs or dict objects with 'id'.
        edges: List of edges with 'source', 'target', 'cost', and 'active'/'status'.
        source: Optional source router identifier.
        destination: Optional destination router identifier.
        max_rounds: Upper bound on exchange iterations to detect non-convergence.

    Returns:
        Structured dictionary containing:
        - status: 'success'
        - converged: True if routing tables stabilized
        - total_rounds: Number of exchange rounds executed
        - iteration_limit_reached: True if capped by max_rounds
        - initial_tables: State of all router tables at Round 0
        - final_tables: State of all router tables after convergence
        - rounds: Detailed per-round vector exchanges, updates, and explanations
        - path: Shortest path between source and destination (if specified)
        - total_cost: Minimum cost for source-to-destination path
        - hop_count: Hop count on computed path
        - reachable: Reachability status of destination from source
        - routing_table: Standard routing table entries for the source router
    """
    sorted_nodes, adjacency = validate_topology(nodes, edges, source, destination)
    norm_source = str(source).strip() if source is not None and str(source).strip() else (sorted_nodes[0] if sorted_nodes else None)
    norm_dest = str(destination).strip() if destination is not None and str(destination).strip() else None

    # Step 1: Initialize Distance Vectors and Routing Tables for all routers
    # For router X:
    # - Distance to self is 0, next hop = local ("-")
    # - Distance to direct active neighbor V is c(X, V), next hop = V
    # - Distance to all other routers is infinity, next hop = None
    tables: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for x in sorted_nodes:
        tables[x] = {}
        for y in sorted_nodes:
            if x == y:
                tables[x][y] = {"cost": 0.0, "next_hop": "-", "status": "Direct"}
            elif y in adjacency[x]:
                tables[x][y] = {"cost": adjacency[x][y], "next_hop": y, "status": "Reachable"}
            else:
                tables[x][y] = {"cost": float("inf"), "next_hop": None, "status": "Unreachable"}

    def serialize_tables(tbls: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Convert internal tables into clean JSON-serializable list format per router."""
        res: Dict[str, List[Dict[str, Any]]] = {}
        for rtr in sorted_nodes:
            res[rtr] = []
            for dest in sorted_nodes:
                c = tbls[rtr][dest]["cost"]
                nh = tbls[rtr][dest]["next_hop"]
                st = tbls[rtr][dest]["status"]
                res[rtr].append({
                    "destination": dest,
                    "cost": (int(c) if c.is_integer() else c) if c != float("inf") else None,
                    "next_hop": nh if nh is not None else "-",
                    "status": st
                })
        return res

    initial_tables = serialize_tables(tables)
    rounds: List[Dict[str, Any]] = []

    # Record Round 0 (Initialization Snapshot)
    rounds.append({
        "round": 0,
        "type": "initialization",
        "tables": copy.deepcopy(initial_tables),
        "updates": [],
        "explanation": "Round 0 (Initial State): Each router initializes distance to itself as 0 and records costs only to directly connected active neighbors. All other destinations are marked unreachable."
    })

    # Step 2: Iterative Round-Based Neighbor Vector Exchanges
    converged = False
    current_round = 0
    iteration_limit_reached = False

    while current_round < max_rounds and not converged:
        current_round += 1
        round_updates: List[Dict[str, Any]] = []

        # Previous round vectors snapshot:
        # Distance vectors available to transmit to neighbors in this round
        prev_vectors: Dict[str, Dict[str, float]] = {
            rtr: {dest: tables[rtr][dest]["cost"] for dest in sorted_nodes}
            for rtr in sorted_nodes
        }

        # Next state scratch table for synchronous round transition
        new_tables = copy.deepcopy(tables)

        for x in sorted_nodes:
            direct_neighbors = sorted(list(adjacency[x].keys()))

            for y in sorted_nodes:
                if x == y:
                    continue

                best_cost = tables[x][y]["cost"]
                best_hop = tables[x][y]["next_hop"]
                best_via: Optional[str] = None
                improved = False

                # Bellman-Ford Equation:
                # D_X(Y) = min_V { c(X, V) + D_V(Y) } over all direct neighbors V
                for v in direct_neighbors:
                    link_cost = adjacency[x][v]
                    neighbor_dist_to_y = prev_vectors[v].get(y, float("inf"))

                    if neighbor_dist_to_y == float("inf"):
                        continue

                    candidate_cost = link_cost + neighbor_dist_to_y

                    # Update if strictly better candidate found
                    # On equal candidate cost, break tie deterministically by smaller neighbor ID
                    if candidate_cost < best_cost:
                        best_cost = candidate_cost
                        best_hop = v
                        best_via = v
                        improved = True

                if improved:
                    old_cost = tables[x][y]["cost"]
                    new_tables[x][y] = {
                        "cost": best_cost,
                        "next_hop": best_hop,
                        "status": "Reachable"
                    }
                    round_updates.append({
                        "router": x,
                        "destination": y,
                        "old_cost": int(old_cost) if old_cost != float("inf") and old_cost.is_integer() else (old_cost if old_cost != float("inf") else None),
                        "new_cost": int(best_cost) if best_cost.is_integer() else best_cost,
                        "next_hop": best_hop,
                        "via_neighbor": best_via
                    })

        # Check for convergence
        if not round_updates:
            converged = True
            rounds.append({
                "round": current_round,
                "type": "convergence",
                "tables": copy.deepcopy(serialize_tables(tables)),
                "updates": [],
                "explanation": f"Round {current_round}: Routing tables stabilized. No distance vectors changed across any router. Protocol converged successfully."
            })
            break
        else:
            tables = new_tables
            update_summary = "; ".join(
                f"Router {u['router']} -> {u['destination']}: cost {u['new_cost']} via {u['next_hop']}"
                for u in round_updates[:4]
            )
            if len(round_updates) > 4:
                update_summary += f"; and {len(round_updates) - 4} more..."

            rounds.append({
                "round": current_round,
                "type": "exchange",
                "tables": copy.deepcopy(serialize_tables(tables)),
                "updates": round_updates,
                "explanation": f"Round {current_round}: Direct neighbors exchanged distance vectors. {len(round_updates)} routing table entries improved ({update_summary})."
            })

    if not converged:
        iteration_limit_reached = True

    final_tables = serialize_tables(tables)

    # Step 3: Reconstruct Path from Source to Destination (if specified)
    path: List[str] = []
    reachable = False
    total_cost: Optional[float] = None
    hop_count = 0

    if norm_source and norm_dest:
        if norm_source == norm_dest:
            path = [norm_source]
            reachable = True
            total_cost = 0.0
            hop_count = 0
        else:
            dest_entry = next((item for item in final_tables.get(norm_source, []) if item["destination"] == norm_dest), None)
            if dest_entry and dest_entry["cost"] is not None:
                # Trace path by following next hops from router to router with loop detection
                curr = norm_source
                curr_path = [curr]
                visited_in_path: Set[str] = {curr}
                valid_path = True

                while curr != norm_dest:
                    curr_entry = next((item for item in final_tables.get(curr, []) if item["destination"] == norm_dest), None)
                    if not curr_entry or not curr_entry["next_hop"] or curr_entry["next_hop"] == "-":
                        valid_path = False
                        break

                    next_router = curr_entry["next_hop"]
                    if next_router in visited_in_path or next_router not in sorted_nodes:
                        # Cycle or invalid hop detected
                        valid_path = False
                        break

                    curr_path.append(next_router)
                    visited_in_path.add(next_router)
                    curr = next_router

                if valid_path and curr == norm_dest:
                    path = curr_path
                    reachable = True
                    total_cost = dest_entry["cost"]
                    hop_count = len(path) - 1

    # Extract source router's routing table for primary view
    source_routing_table = final_tables.get(norm_source, [])

    return {
        "status": "success",
        "source": norm_source,
        "destination": norm_dest,
        "converged": converged,
        "total_rounds": current_round,
        "iteration_limit_reached": iteration_limit_reached,
        "warning": "Iteration limit reached before convergence." if iteration_limit_reached else None,
        "initial_tables": initial_tables,
        "final_tables": final_tables,
        "rounds": rounds,
        "path": path,
        "total_cost": total_cost,
        "hop_count": hop_count,
        "reachable": reachable,
        "routing_table": source_routing_table
    }
