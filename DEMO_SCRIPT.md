# 5-Minute Project Demonstration Script

**Project Title**: Intelligent Network Routing Simulator  
**Presenter**: Student / Engineering Candidate  
**Target Audience**: Viva Examiner, Project Reviewer, Lab Evaluator  
**Total Allocated Time**: 5 Minutes  

---

## Preparation (Pre-Demo Checklist)
- Open PowerShell in the project directory.
- Ensure the virtual environment `.venv` is activated.
- Have a clean browser window ready.
- Keep the terminal visible alongside the browser for live logging.

---

## Demonstration Timeline & Dialogue

### Minute 0:00 – 0:45 | System Startup & Architecture Overview
**Action**:
1. In PowerShell, activate the virtual environment and start the application:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python app.py
   ```
2. Open `http://127.0.0.1:5000/` in the browser.
3. Point out the top header:
   - Green **Backend: Online** status indicator.
   - Initial router, link, and failed link badges.

**Dialogue**:
> *"Good morning, respected examiners. Today I am presenting the Intelligent Network Routing Simulator, a full-stack educational platform built with Python Flask, vanilla JavaScript, and native SVG. The application demonstrates and contrasts the two fundamental routing paradigms in computer networks: Link-State routing via Dijkstra's algorithm, and Distance-Vector routing via the Bellman-Ford protocol. Notice that the entire application operates locally with zero external libraries, frameworks, or databases."*

---

### Minute 0:45 – 1:30 | Canvas Exploration & Topology Management
**Action**:
1. Point to the **Topology Presets** dropdown in the left panel.
2. Select `Sample 1: 5-Node Backbone Mesh` and click **Load Preset**.
3. Click and drag router `B` and router `E` to show that node positions are interactive and responsive.
4. Show the **Event Log** in the right column recording `[INFO] Loaded preset: 5-Node Backbone Mesh`.

**Dialogue**:
> *"The network canvas is rendered using native Scalable Vector Graphics. I have loaded our primary test topology: a 5-node redundant backbone mesh with routers A, B, C, D, and E. Each connection displays its weighted metric directly at the midpoint. Notice that I can drag any router freely, and its coordinates remain persistent across calculations."*

---

### Minute 1:30 – 2:30 | Dijkstra's Shortest Path & Step Playback
**Action**:
1. Under **Routing Simulation**, ensure **Dijkstra's Algorithm (Link-State)** is selected.
2. Set **Source Router** to `A` and **Destination** to `E`.
3. Click **▶ Run Simulation**.
4. Point out the visual changes:
   - The optimal path $A \to B \to E$ is immediately highlighted in glowing emerald on the SVG canvas.
   - **Optimal Path**: `A ➔ B ➔ E`.
   - **Total Metric / Cost**: `5` (Link $A-B$ cost 4 + Link $B-E$ cost 1).
   - **Hop Count**: `2`.
   - The **Routing Table** in the right panel displays all computed forwarding entries from router $A$.
5. Click **Next Step (&rarr;)** repeatedly to step through the algorithm trace:
   - Point out router `A` glowing cyan (`step-visiting`), relaxing neighbor links (`step-relaxing`), and the explanation box updating at every step.

**Dialogue**:
> *"When I click 'Run Simulation', a JSON payload is sent to our Flask backend at `/api/dijkstra`. The Python engine calculates the shortest path tree. Here, while route A-D-E has cost 2 + 7 = 9, the optimal route chosen is A-B-E with cost 4 + 1 = 5. Clicking 'Next Step' allows us to visually inspect each relaxation step and examine the tentative distance vector at each point in time."*

---

### Minute 2:30 – 3:30 | Distance-Vector Routing & Round-by-Round Convergence
**Action**:
1. Switch the **Routing Algorithm** dropdown to **Distance Vector Routing (Bellman-Ford)**.
2. Keep Source as `A` and Destination as `E`.
3. Click **▶ Run Simulation**.
4. Point out the **Results Summary Card**:
   - Status updates to: `Converged in 3 Round(s)`.
   - The routing table displays the converged vectors.
5. In the **Routing Tables** panel, change the router filter to `All Routers` to show full network tables.
6. Click **&larr; Prev Step** twice to return to **Round 0**:
   - Show that at Round 0, router $A$ only knows direct neighbors $B$ (cost 4) and $D$ (cost 2); $E$ is unreachable.
7. Click **Next Step (&rarr;)** to advance to **Round 1**:
   - Show the blue highlighting on table entries as neighbor $B$ advertises its link to $E$, allowing router $A$ to learn $E$ with cost 5.
8. Click **Next Step (&rarr;)** to reach **Round 3 (Convergence)**.

**Dialogue**:
> *"Now let us switch to Distance-Vector routing. Unlike Dijkstra's centralized calculation, Distance-Vector simulates distributed Bellman-Ford exchanges. At Round 0, routers possess only local link knowledge. By stepping forward to Round 1, direct neighbors exchange vectors, and router A discovers destination E through neighbor B. In Round 3, no routing entries change, and the protocol reaches global convergence."*

---

### Minute 3:30 – 4:15 | Dynamic Link Failure & Alternative Route Convergence
**Action**:
1. Click directly on link $B-E$ on the SVG canvas (or use the link failure dropdown).
2. Point out that link $B-E$ immediately becomes a crimson dashed line with a `[FAILED]` badge, and a red chip appears in the *Failed Links* container.
3. Point out that the previous path highlight is immediately cleared to prevent stale routing.
4. Click **▶ Run Simulation**.
5. Observe the new routing output:
   - Primary link $B-E$ is broken.
   - The new optimal path reroutes to $A \to D \to E$ with Total Cost `9` (Link $A-D$ cost 2 + Link $D-E$ cost 7).
   - Status updates to: `Optimal Route Found`.

**Dialogue**:
> *"In real-world networks, fiber cuts or hardware failures occur continuously. By clicking link B-E, I simulate a link failure. Notice that the previous route is immediately invalidated. When I click 'Run Simulation', our Python engine excludes the failed link and successfully reroutes traffic through alternate link A-D-E with cost 9."*

---

### Minute 4:15 – 4:45 | Network Partitioning & Link Recovery
**Action**:
1. Click on links $C-E$ and $D-E$ on the canvas to disable them as well.
2. Router `E` is now completely isolated from the network.
3. Click **▶ Run Simulation**.
   - **Status**: `Destination Unreachable`.
   - **Optimal Path**: `No Path Available`.
   - **Total Metric**: `Infinity`.
   - Routing table shows destination `E` with status `Unreachable` and cost `∞ (Inf)`.
4. Click **Recover All** in the Link Failure panel.
   - All links instantly return to solid active state.
5. Click **▶ Run Simulation**.
   - Original path $A \to B \to E$ (cost 5) is restored.

**Dialogue**:
> *"When I fail the remaining links to router E, the network becomes partitioned. Both Dijkstra and Distance-Vector gracefully detect that no path exists, reporting Infinity and marking the destination as Unreachable. Clicking 'Recover All' restores all links, and running the simulation recovers our optimal baseline route."*

---

### Minute 4:45 – 5:00 | Summary & Conclusion
**Action**:
1. Click **Reset** to restore the simulator to its clean initial state.
2. Conclude the presentation.

**Dialogue**:
> *"To conclude, the Intelligent Network Routing Simulator demonstrates accurate routing calculations, real-time fault tolerance, step-by-step educational visualization, and strict software architecture with 34 passing automated tests. Thank you, and I am now ready for your questions."*
