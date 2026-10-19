# Comprehensive Viva Voce Preparation Guide

**Subject**: Computer Networks & Distributed Systems  
**Project**: Intelligent Network Routing Simulator  
**Coverage**: 28 Essential Viva Questions & Model Answers across all Core Modules  

---

## Category 1: Network Layer, OSI/TCP Models & Routers

### Q1. At which layer of the OSI and TCP/IP models do routing protocols operate?
> **Answer**: Routing protocols operate at the **Network Layer** (Layer 3 of the OSI model, or the Internet Layer in the TCP/IP model). Their primary responsibility is logical addressing (IPv4/IPv6), path determination, and forwarding packets from a source network to a destination network across intermediate routers.

### Q2. What is the fundamental difference between routing and forwarding?
> **Answer**:
> - **Routing** is the *control plane* process of running algorithms (e.g., Dijkstra, Bellman-Ford) to determine the end-to-end optimal paths through the network and construct the routing table.
> - **Forwarding** is the *data plane* process of transferring an arriving packet from a router's incoming interface to the appropriate outgoing interface based on its destination IP address and the routing table lookup.

### Q3. What is a Routing Table and what core information does it contain?
> **Answer**: A routing table is a data structure maintained inside a router's memory containing:
> 1. **Destination Network / Host**: The target IP or router ID.
> 2. **Metric / Cost**: The administrative distance, latency, or hop count required to reach that destination.
> 3. **Next Hop**: The IP address or identifier of the adjacent downstream router to which packets should be forwarded.
> 4. **Interface / Status**: The physical or logical egress interface (or reachability status).

### Q4. What is a "Next Hop" and why does a router only care about the next hop rather than the entire path?
> **Answer**: The next hop is the immediate neighbor router along the shortest path. Under the **hop-by-hop routing paradigm**, each intermediate router is only responsible for moving the packet one step closer to its destination. Storing only the next hop instead of complete path histories drastically minimizes memory overhead and scales to global networks like the Internet.

---

## Category 2: Graph Theory & Network Modeling

### Q5. How is a computer network modeled mathematically in this project?
> **Answer**: The network is modeled as a weighted undirected graph $G = (V, E)$, where:
> - $V$ is the set of vertices representing **router nodes**.
> - $E$ is the set of edges representing **bidirectional transmission links**.
> - A weight function $w: E \to \mathbb{R}^+$ assigns each link a positive cost representing metric parameters such as latency (in ms), inverse bandwidth, or administrative distance.

### Q6. Why must link costs in standard Dijkstra and Distance-Vector implementations be positive ($> 0$)?
> **Answer**: Dijkstra's algorithm assumes that extending a path always increases its total cost. If zero or negative costs were permitted, the greedy invariant breaks because an unvisited node could later reduce the cost of an already-visited node. Furthermore, negative cycles would cause algorithms to loop infinitely, continuously decreasing path cost to negative infinity.

### Q7. What is an Adjacency List and why is it preferred over an Adjacency Matrix?
> **Answer**: An adjacency list maps each node to a collection of its directly connected neighbors and edge weights (e.g., `{A: {B: 4, D: 2}}`). It requires $O(V + E)$ space, making it significantly more memory-efficient for sparse network graphs than an $O(V^2)$ adjacency matrix, and enables fast $O(\text{deg}(u))$ neighbor iterations during link relaxations.

---

## Category 3: Dijkstra's Link-State Algorithm

### Q8. What is the core working principle of Dijkstra's algorithm?
> **Answer**: Dijkstra's algorithm is a greedy, centralized single-source shortest path algorithm. It initializes the source distance to $0$ and all other nodes to infinity. In each iteration, it selects the unvisited node $u$ with the minimum tentative distance, marks it as visited (finalized), and "relaxes" all outgoing links $(u, v)$ by testing if traveling through $u$ offers a shorter path to $v$:
> $$d[v] = \min(d[v], d[u] + c(u, v))$$

### Q9. What real-world routing protocols utilize Dijkstra's algorithm?
> **Answer**: **Link-State routing protocols** such as **OSPF (Open Shortest Path First)** and **IS-IS (Intermediate System to Intermediate System)** use Dijkstra's algorithm (often termed the Shortest Path First or SPF algorithm).

### Q10. What is the time complexity of Dijkstra's algorithm?
> **Answer**:
> - Using an array/list for minimum extraction: $O(V^2)$.
> - Using a binary min-heap / priority queue: $O((V + E) \log V)$.
> - Using a Fibonacci heap: $O(E + V \log V)$.
> For our simulator's educational graphs ($V \le 50$), linear priority scanning with deterministic tie-breaking executes in less than 5 milliseconds.

### Q11. How does the simulator reconstruct the path and determine next hops from Dijkstra's output?
> **Answer**: During edge relaxation, whenever a shorter path to neighbor $v$ is discovered via $u$, the algorithm updates a predecessor mapping: `previous[v] = u`. To reconstruct the path to destination $D$, the simulator backtracks: $D \to \pi[D] \to \pi[\pi[D]] \dots \to S$, then reverses the sequence. The next hop is identified as the first node in this sequence immediately following the source router.

### Q12. How does Dijkstra handle equal-cost alternative paths in this implementation?
> **Answer**: Real networks can use equal-cost multi-path (ECMP) load balancing. In our simulator, equal-cost paths are resolved **deterministically** using lexicographical comparison of router IDs (e.g., node $B$ is evaluated before node $C$). This ensures reproducible test outcomes and stable step-by-step visualizations without non-deterministic jitter.

---

## Category 4: Distance-Vector & Bellman-Ford Routing

### Q13. What is the core working principle of Distance-Vector routing?
> **Answer**: Distance-Vector is a distributed, iterative routing algorithm based on the Bellman-Ford equation:
> $$D_X(Y) = \min_V \{ c(X, V) + D_V(Y) \}$$
> Routers do not possess global topology knowledge. Instead, each router $X$ periodically sends its own distance vector $D_X$ to its directly connected neighbors $V$, who use that information to update their own tables if a shorter path is found.

### Q14. What real-world routing protocols utilize the Distance-Vector paradigm?
> **Answer**: **RIP (Routing Information Protocol)**, Cisco's legacy **IGRP**, and the **BGP (Border Gateway Protocol)** which uses a path-vector variant where the full autonomous system path is advertised to avoid loops.

### Q15. What is "Convergence" in routing protocols?
> **Answer**: Convergence is the state where all routers in the network agree on optimal routes and no further routing table updates occur. In our simulator, convergence is explicitly detected when an exchange round produces zero table modifications across every router in the topology.

### Q16. How does Distance-Vector handle multi-hop destination discovery over discrete rounds?
> **Answer**:
> - **Round 0**: Routers only know themselves (distance 0) and direct neighbors (link cost). Non-adjacent routers are unreachable ($\infty$).
> - **Round 1**: Routers exchange vectors with direct neighbors, discovering destinations 2 hops away.
> - **Round $k$**: Routing information propagates across $k+1$ hops until the entire network diameter is spanned and tables stabilize.

### Q17. What is the "Count-to-Infinity" problem in Distance-Vector routing and how is it mitigated in real networks?
> **Answer**: When a link fails, two adjacent routers may continuously advertise routes to each other based on obsolete information, incrementing the metric by link cost on every exchange until reaching infinity. Real-world protocols mitigate this using:
> 1. **Split Horizon**: A router never advertises a route back out of the interface through which it learned it.
> 2. **Poison Reverse**: The router advertises the route back to the source with an infinite metric ($\infty$).
> 3. **Hop Limit**: RIP caps maximum valid metric at 15; metric 16 represents infinity.

---

## Category 5: Link Failure, Recovery & Network Partitioning

### Q18. How does the simulator detect and process a link failure?
> **Answer**: When a link is marked as `failed` (via UI toggle or API payload), the backend filters it out during graph parsing. The link is excluded from the active adjacency list. As a result, Dijkstra cannot relax along that edge, and Distance-Vector nodes cannot exchange vectors across that interface.

### Q19. What happens when a link failure partitions the network?
> **Answer**: A partitioned network contains two or more disconnected components. When computing routes to a node in an isolated component:
> - Dijkstra finds that the destination's tentative distance remains `float("inf")`.
> - Distance-Vector receives no vector updates containing that node.
> Both algorithms return `reachable: false`, `path: []`, `total_cost: null`, and set the routing table status to `"Unreachable"` with cost `"∞ (Inf)"`.

### Q20. Why must stale route highlights be cleared immediately when a topology changes?
> **Answer**: Under the single-source-of-truth principle, displaying a cached path that traverses a currently broken link creates hazardous misinformation for network operators. Our simulator invalidates previous route highlights immediately in `onTopologyUpdated()` and prompts the user to re-run the simulation.

---

## Category 6: Software Architecture, REST APIs & Testing

### Q21. Explain the architectural separation between backend Python and frontend JavaScript in this project.
> **Answer**: The project follows a strict decoupled client-server architecture:
> - **Backend (Python Flask)**: Acts as the computational engine. It parses JSON payloads, validates graph topology, executes the pure routing algorithms, compiles step-by-step traces, and serves JSON responses.
> - **Frontend (Vanilla JS & Native SVG)**: Acts as the presentation layer. It manages DOM events, user inputs, canvas drag-and-drop, and visual rendering. It never computes or hardcodes routing paths client-side.

### Q22. What endpoints are exposed by the Flask REST API?
> **Answer**:
> 1. `GET /`: Serves the single-page HTML frontend.
> 2. `GET /api/health`: Health-check endpoint returning service name, status, and version.
> 3. `POST /api/dijkstra`: Accepts topology nodes, edges, source, and destination; returns shortest path, metrics, and step traces.
> 4. `POST /api/distance-vector`: Accepts topology nodes, edges, source, and destination; returns round-based vector exchanges and convergence tables.

### Q23. Why was native SVG chosen over HTML5 `<canvas>` or third-party libraries (like D3.js or Cytoscape)?
> **Answer**:
> - **DOM Element Binding**: Each router `<circle>` and link `<line>` is a distinct DOM node that supports direct mouse click and drag event listeners without manual pixel coordinate hit-testing.
> - **Resolution Independence**: SVG is vector-based; it scales crisply to any screen resolution or zoom level without pixelation.
> - **Zero External Footprint**: Third-party libraries add megabytes of external dependencies and security risks. Native SVG requires zero external scripts.

### Q24. How are errors and invalid inputs handled across the application?
> **Answer**: Input validation is enforced at both layers:
> - **Frontend**: Checks duplicate router IDs, self-links, missing endpoints, and non-positive weights, alerting the user via non-blocking toast notifications.
> - **Backend**: Server-side defensive validation in `validate_topology()` rejects malformed JSON, negative weights, zero weights, self-loops, and unknown routers with HTTP `400 Bad Request`.
> - **HTTP 404/405**: Custom error handlers return structured JSON objects for all `/api/*` routes.

### Q25. What automated test methodology was used and how many tests were written?
> **Answer**: We employed **pytest** with test fixtures (`client`) across 4 test modules totaling **34 tests**:
> - `test_api.py` (13 tests): Verifies API contracts, HTTP status codes, and JSON error structures.
> - `test_dijkstra.py` (11 tests): Verifies direct routes, multi-hop routes, tie-breaking, graph immutability, and validation.
> - `test_distance_vector.py` (8 tests): Verifies neighbor propagation, progressive improvement, and equivalence with Dijkstra.
> - `test_simulation_integration.py` (2 tests): Verifies the full failure lifecycle (baseline $\to$ link cut $\to$ reroute $\to$ partition $\to$ recovery).

---

## Category 7: Advanced Networking & Comparative Analysis

### Q26. Compare Link-State (Dijkstra) vs Distance-Vector (Bellman-Ford) routing.
| Feature | Link-State (OSPF) | Distance-Vector (RIP) |
|---|---|---|
| **Topology View** | Global map of all routers and links | Local view of directly connected neighbors |
| **Algorithm** | Dijkstra's shortest path | Bellman-Ford equation |
| **Convergence Speed** | Fast (instant recalculation upon LSA receipt) | Slower (requires round-by-round vector propagation) |
| **Message Overhead** | Floods link-state advertisements (LSAs) | Exchanges full/incremental distance vectors |
| **Memory / CPU** | Higher memory to store link-state database (LSDB) | Low memory; stores only neighbor vectors |
| **Routing Loops** | Immune to loops (calculates loop-free tree) | Susceptible to loops / count-to-infinity if unmitigated |

### Q27. Does Distance-Vector always compute the same shortest path as Dijkstra?
> **Answer**: **Yes.** For static, undirected graphs with non-negative edge weights that have reached full convergence without active routing loops, both algorithms mathematically minimize the path metric $\sum_{(u,v) \in P} c(u, v)$ and arrive at identical shortest path costs and routing tables. Our automated test `test_compare_with_dijkstra` rigorously verifies this equivalence.

### Q28. What are the key educational takeaways from building this project?
> **Answer**:
> 1. Deep theoretical and practical comprehension of Network Layer path determination.
> 2. Direct observation of how distributed vector exchanges differ from centralized tree calculations.
> 3. Mastering resilient software engineering by decoupling Python algorithmic models from JavaScript presentation layers without external dependencies.
