"""Dijkstra's Shortest Path Algorithm Module.

Implements Dijkstra's algorithm for weighted network topologies with
support for link failure filtering, path reconstruction, next-hop computation,
step-by-step execution traces, and strict validation.
"""
import math
from typing import Dict, List, Any, Optional, Tuple, Set


class DijkstraError(ValueError):
    """Raised when Dijkstra input data fails validation."""
    pass


def validate_topology(
    nodes: List[Any],
    edges: List[Dict[str, Any]],
    source: str,
    destination: Optional[str] = None
) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    """Validate graph topology inputs and construct active adjacency list.

    Args:
        nodes: List of node IDs or dicts with 'id' key.
        edges: List of edge dicts with 'source', 'target', 'cost', and optional 'active'/'status'.
        source: Source router identifier.
        destination: Optional destination router identifier.

    Returns:
        Tuple of (normalized_node_list, active_adjacency_dict).

    Raises:
        DijkstraError: If validation fails.
    """
    if not nodes:
        raise DijkstraError("Topology must contain at least one router node.")

    # Normalize node IDs
    node_set: Set[str] = set()
    node_list: List[str] = []
    for n in nodes:
        node_id = n.get("id") if isinstance(n, dict) else n
        if node_id is None:
            raise DijkstraError("Invalid node entry: missing 'id'.")
        node_id = str(node_id).strip()
        if not node_id:
            raise DijkstraError("Node identifier cannot be empty.")
        if node_id in node_set:
            raise DijkstraError(f"Duplicate node identifier detected: '{node_id}'.")
        node_set.add(node_id)
        node_list.append(node_id)

    if not source or not str(source).strip():
        raise DijkstraError("Source router must be specified.")
    norm_source = str(source).strip()
    if norm_source not in node_set:
        raise DijkstraError(f"Source router '{norm_source}' does not exist in the topology.")

    if destination is not None and str(destination).strip():
        norm_dest = str(destination).strip()
        if norm_dest not in node_set:
            raise DijkstraError(f"Destination router '{norm_dest}' does not exist in the topology.")

    # Build adjacency list with only active links
    adjacency: Dict[str, Dict[str, float]] = {n: {} for n in node_list}

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise DijkstraError(f"Edge at index {idx} must be an object.")

        u = edge.get("source")
        v = edge.get("target")
        if u is None or v is None:
            raise DijkstraError(f"Edge at index {idx} is missing source or target endpoint.")

        u = str(u).strip()
        v = str(v).strip()

        if u not in node_set:
            raise DijkstraError(f"Edge references non-existent router '{u}'.")
        if v not in node_set:
            raise DijkstraError(f"Edge references non-existent router '{v}'.")
        if u == v:
            raise DijkstraError(f"Self-loops are not permitted: router '{u}' connects to itself.")

        raw_cost = edge.get("cost", edge.get("weight"))
        if raw_cost is None:
            raise DijkstraError(f"Edge {u}-{v} is missing cost/weight.")

        try:
            cost = float(raw_cost)
        except (ValueError, TypeError):
            raise DijkstraError(f"Edge {u}-{v} cost must be numeric; got {raw_cost!r}.")

        if math.isnan(cost) or math.isinf(cost):
            raise DijkstraError(f"Edge {u}-{v} cost must be finite; got {cost}.")
        if cost <= 0:
            raise DijkstraError(f"Edge {u}-{v} cost must be positive and greater than 0; got {cost}.")

        # Determine link active state
        # Supports both "active": true/false and "status": "active"/"failed"
        is_active = True
        if "active" in edge:
            is_active = bool(edge["active"])
        if "status" in edge:
            is_active = is_active and (edge["status"] == "active")

        if is_active:
            # If multiple active edges connect u and v, retain the lower cost
            if v not in adjacency[u] or cost < adjacency[u][v]:
                adjacency[u][v] = cost
            if u not in adjacency[v] or cost < adjacency[v][u]:
                adjacency[v][u] = cost

    return node_list, adjacency


def dijkstra_shortest_path(
    nodes: List[Any],
    edges: List[Dict[str, Any]],
    source: str,
    destination: Optional[str] = None
) -> Dict[str, Any]:
    """Execute Dijkstra's algorithm to compute shortest paths and step trace.

    Args:
        nodes: List of node IDs or dict objects with 'id'.
        edges: List of edges with 'source', 'target', 'cost', and 'active'/'status'.
        source: Source router identifier.
        destination: Optional destination router identifier.

    Returns:
        Structured dictionary containing:
        - source: Normalized source identifier
        - destination: Normalized destination identifier or None
        - reachable: True if destination is reachable from source
        - path: Ordered list of router IDs representing the shortest path
        - total_cost: Minimum path cost (None if unreachable)
        - hop_count: Number of link transitions on path
        - distances: Dict mapping each router to its minimum cost (None for unreachable)
        - previous: Dict mapping each router to its immediate predecessor
        - next_hops: Dict mapping each router to next hop from source
        - routing_table: Standard router routing table entries
        - steps: Step-by-step state snapshots for interactive playback
    """
    node_list, adjacency = validate_topology(nodes, edges, source, destination)
    norm_source = str(source).strip()
    norm_dest = str(destination).strip() if destination is not None and str(destination).strip() else None

    # Algorithm Data Structures
    # Internal distances use float('inf') for unreached nodes
    distances: Dict[str, float] = {node: float("inf") for node in node_list}
    distances[norm_source] = 0.0

    previous: Dict[str, Optional[str]] = {node: None for node in node_list}
    visited: Set[str] = set()
    unvisited: Set[str] = set(node_list)

    steps: List[Dict[str, Any]] = []

    def make_snapshot(step_num: int, event_type: str, current_node: Optional[str], explanation: str, edge_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a serializable step trace snapshot."""
        return {
            "step": step_num,
            "type": event_type,
            "current_node": current_node,
            "visited": sorted(list(visited)),
            "unvisited": sorted(list(unvisited)),
            "distances": {n: (d if d != float("inf") else None) for n, d in distances.items()},
            "previous": {n: p for n, p in previous.items()},
            "edge": edge_data,
            "explanation": explanation
        }

    # Step 0: Initialization
    step_counter = 0
    steps.append(make_snapshot(
        step_counter,
        "initialization",
        norm_source,
        f"Initialized routing calculation. Source router '{norm_source}' set to distance 0; all other routers set to infinity."
    ))

    # Main Dijkstra Loop
    while unvisited:
        # Find unvisited node with minimum tentative distance
        # Break ties deterministically by lexicographical order of node ID
        min_node: Optional[str] = None
        min_dist: float = float("inf")

        for node in sorted(unvisited):
            d = distances[node]
            if d < min_dist:
                min_dist = d
                min_node = node

        # If minimum distance is infinity, all remaining unvisited nodes are disconnected
        if min_node is None or min_dist == float("inf"):
            step_counter += 1
            steps.append(make_snapshot(
                step_counter,
                "unreachable_remaining",
                None,
                f"Remaining unvisited routers {sorted(list(unvisited))} cannot be reached from source '{norm_source}'."
            ))
            break

        current = min_node
        unvisited.remove(current)
        visited.add(current)

        step_counter += 1
        steps.append(make_snapshot(
            step_counter,
            "visit_node",
            current,
            f"Visiting router '{current}' with finalized minimum distance {distances[current]:.1f}."
        ))

        # Relax each outgoing link from current router
        neighbors = adjacency.get(current, {})
        for neighbor in sorted(neighbors.keys()):
            if neighbor in visited:
                continue

            edge_weight = neighbors[neighbor]
            tentative_dist = distances[current] + edge_weight
            old_dist = distances[neighbor]

            updated = False
            if tentative_dist < old_dist:
                distances[neighbor] = tentative_dist
                previous[neighbor] = current
                updated = True
                explanation = (
                    f"Relaxed link {current} -> {neighbor} (cost {edge_weight:.1f}). "
                    f"New distance {tentative_dist:.1f} is lower than previous {('inf' if old_dist == float('inf') else f'{old_dist:.1f}')}. Updated predecessor to '{current}'."
                )
            else:
                explanation = (
                    f"Evaluated link {current} -> {neighbor} (cost {edge_weight:.1f}). "
                    f"Tentative distance {tentative_dist:.1f} is not better than current {old_dist:.1f}. Unchanged."
                )

            step_counter += 1
            steps.append(make_snapshot(
                step_counter,
                "relax_edge",
                current,
                explanation,
                edge_data={
                    "source": current,
                    "target": neighbor,
                    "weight": edge_weight,
                    "old_distance": old_dist if old_dist != float("inf") else None,
                    "new_distance": distances[neighbor],
                    "updated": updated
                }
            ))

    # Path Reconstruction for target destination (if specified)
    path: List[str] = []
    reachable = False
    total_cost: Optional[float] = None
    hop_count = 0

    if norm_dest:
        if norm_dest == norm_source:
            path = [norm_source]
            reachable = True
            total_cost = 0.0
            hop_count = 0
        elif distances[norm_dest] != float("inf"):
            curr: Optional[str] = norm_dest
            backtrack: List[str] = []
            while curr is not None:
                backtrack.append(curr)
                if curr == norm_source:
                    break
                curr = previous.get(curr)

            if backtrack and backtrack[-1] == norm_source:
                backtrack.reverse()
                path = backtrack
                reachable = True
                total_cost = distances[norm_dest]
                hop_count = len(path) - 1
            else:
                path = []
                reachable = False
                total_cost = None
                hop_count = 0
        else:
            path = []
            reachable = False
            total_cost = None
            hop_count = 0

    # Determine Next Hop for all routers from perspective of source
    next_hops: Dict[str, Optional[str]] = {}
    for node in node_list:
        if node == norm_source:
            next_hops[node] = None  # Direct / local
        elif distances[node] == float("inf"):
            next_hops[node] = None  # Unreachable
        else:
            # Backtrack from node to source to find first hop
            curr = node
            pred = previous.get(curr)
            if pred is None:
                next_hops[node] = None
                continue

            chain: List[str] = [curr]
            while pred is not None and pred != norm_source:
                chain.append(pred)
                pred = previous.get(pred)

            if pred == norm_source:
                next_hops[node] = chain[-1]
            else:
                next_hops[node] = None

    # Construct Standard Routing Table entries
    routing_table: List[Dict[str, Any]] = []
    for node in sorted(node_list):
        cost_val = distances[node]
        is_direct = (node == norm_source)
        is_reach = (cost_val != float("inf"))

        routing_table.append({
            "destination": node,
            "cost": 0 if is_direct else (int(cost_val) if cost_val.is_integer() else cost_val) if is_reach else None,
            "next_hop": "-" if is_direct else (next_hops.get(node) or "-"),
            "status": "Direct" if is_direct else ("Reachable" if is_reach else "Unreachable")
        })

    # Prepare JSON-serializable distance map
    json_distances = {
        node: (int(d) if d.is_integer() else d) if d != float("inf") else None
        for node, d in distances.items()
    }

    step_counter += 1
    final_msg = (
        f"Calculation complete. Destination '{norm_dest}' is reachable via path {' -> '.join(path)} with cost {total_cost}."
        if (norm_dest and reachable)
        else (f"Calculation complete. Destination '{norm_dest}' is unreachable." if norm_dest else "Calculation complete.")
    )
    steps.append(make_snapshot(step_counter, "complete", norm_dest, final_msg))

    return {
        "status": "success",
        "source": norm_source,
        "destination": norm_dest,
        "reachable": reachable,
        "path": path,
        "total_cost": (int(total_cost) if total_cost is not None and total_cost.is_integer() else total_cost),
        "hop_count": hop_count,
        "distances": json_distances,
        "previous": previous,
        "next_hops": next_hops,
        "routing_table": routing_table,
        "steps": steps
    }
