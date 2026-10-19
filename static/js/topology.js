/**
 * Intelligent Network Routing Simulator - SVG Topology Module
 * Vanilla JavaScript & Native SVG
 * 
 * Handles router node positioning, dragging, link rendering,
 * cost display, link failure state, and path highlights.
 */

const Topology = {
    svg: null,
    linksGroup: null,
    linkLabelsGroup: null,
    nodesGroup: null,

    // Topology State
    nodes: new Map(), // id -> { id, label, x, y }
    links: [],        // [ { id, source, target, cost, status } ]

    // Selection & Builder State
    sourceNodeId: null,
    destNodeId: null,
    highlightedRoute: [], // array of node IDs in route order: ['A', 'B', 'D']
    activeStepNodeId: null,
    activeStepEdge: null,
    selectedNodeId: null,
    selectedLinkId: null,
    isConnectingMode: false,
    connectSourceNodeId: null,

    // Dragging & Interaction State
    draggedNodeId: null,
    dragOffset: { x: 0, y: 0 },
    dragStartPos: { x: 0, y: 0 },
    hasDragged: false,

    // ViewBox & Zoom State
    viewBox: { x: 0, y: 0, w: 960, h: 540 },

    // Predefined Topologies
    presets: {
        mesh5: {
            name: "5-Node Backbone Mesh",
            nodes: [
                { id: "A", label: "A", x: 180, y: 160 },
                { id: "B", label: "B", x: 480, y: 120 },
                { id: "C", label: "C", x: 320, y: 360 },
                { id: "D", label: "D", x: 680, y: 200 },
                { id: "E", label: "E", x: 740, y: 400 }
            ],
            links: [
                { source: "A", target: "B", cost: 4 },
                { source: "A", target: "C", cost: 2 },
                { source: "B", target: "C", cost: 1 },
                { source: "B", target: "D", cost: 5 },
                { source: "C", target: "D", cost: 8 },
                { source: "C", target: "E", cost: 10 },
                { source: "D", target: "E", cost: 2 }
            ]
        },
        nsfnet7: {
            name: "7-Node Regional NSFNET Core",
            nodes: [
                { id: "R1", label: "R1", x: 140, y: 260 },
                { id: "R2", label: "R2", x: 310, y: 120 },
                { id: "R3", label: "R3", x: 520, y: 130 },
                { id: "R4", label: "R4", x: 760, y: 170 },
                { id: "R5", label: "R5", x: 840, y: 370 },
                { id: "R6", label: "R6", x: 570, y: 420 },
                { id: "R7", label: "R7", x: 320, y: 390 }
            ],
            links: [
                { source: "R1", target: "R2", cost: 3 },
                { source: "R1", target: "R7", cost: 6 },
                { source: "R2", target: "R3", cost: 2 },
                { source: "R2", target: "R7", cost: 4 },
                { source: "R3", target: "R4", cost: 5 },
                { source: "R3", target: "R6", cost: 3 },
                { source: "R4", target: "R5", cost: 2 },
                { source: "R4", target: "R6", cost: 1 },
                { source: "R5", target: "R6", cost: 4 },
                { source: "R6", target: "R7", cost: 2 }
            ]
        },
        ring6: {
            name: "6-Node Ring with Cross-Links",
            nodes: [
                { id: "N1", label: "N1", x: 200, y: 130 },
                { id: "N2", label: "N2", x: 480, y: 90 },
                { id: "N3", label: "N3", x: 760, y: 130 },
                { id: "N4", label: "N4", x: 760, y: 390 },
                { id: "N5", label: "N5", x: 480, y: 430 },
                { id: "N6", label: "N6", x: 200, y: 390 }
            ],
            links: [
                { source: "N1", target: "N2", cost: 3 },
                { source: "N2", target: "N3", cost: 4 },
                { source: "N3", target: "N4", cost: 2 },
                { source: "N4", target: "N5", cost: 5 },
                { source: "N5", target: "N6", cost: 3 },
                { source: "N6", target: "N1", cost: 6 },
                { source: "N2", target: "N5", cost: 7 },
                { source: "N1", target: "N4", cost: 9 }
            ]
        }
    },

    /**
     * Initialize SVG canvas elements and mouse listeners for node drag & drop.
     */
    init(svgId) {
        this.svg = document.getElementById(svgId);
        if (!this.svg) return;

        this.linksGroup = document.getElementById('linksGroup');
        this.linkLabelsGroup = document.getElementById('linkLabelsGroup');
        this.nodesGroup = document.getElementById('nodesGroup');

        this.attachSvgListeners();
        // Default to 5-node mesh preset
        this.loadPreset('mesh5');
    },

    attachSvgListeners() {
        this.svg.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.svg.addEventListener('mouseup', () => this.handleMouseUp());
        this.svg.addEventListener('mouseleave', () => this.handleMouseUp());

        // Deselect if clicking on empty canvas background
        this.svg.addEventListener('click', (e) => {
            if (e.target === this.svg || e.target.tagName === 'rect') {
                if (!this.isConnectingMode) {
                    this.selectedNodeId = null;
                    this.selectedLinkId = null;
                    this.render();
                    if (window.App && typeof window.App.onSelectionCleared === 'function') {
                        window.App.onSelectionCleared();
                    }
                }
            }
        });

        // Touch support for mobile/tablets
        this.svg.addEventListener('touchmove', (e) => {
            if (e.touches.length === 1 && this.draggedNodeId) {
                e.preventDefault();
                this.handleMouseMove(e.touches[0]);
            }
        }, { passive: false });
        this.svg.addEventListener('touchend', () => this.handleMouseUp());
    },

    zoom(factor) {
        if (!this.svg) return;
        const newW = Math.max(320, Math.min(2400, this.viewBox.w * factor));
        const newH = Math.max(180, Math.min(1350, this.viewBox.h * factor));
        this.viewBox.x += (this.viewBox.w - newW) / 2;
        this.viewBox.y += (this.viewBox.h - newH) / 2;
        this.viewBox.w = newW;
        this.viewBox.h = newH;
        this.updateViewBox();
    },

    resetZoom() {
        if (!this.svg) return;
        this.viewBox = { x: 0, y: 0, w: 960, h: 540 };
        this.updateViewBox();
    },

    updateViewBox() {
        if (this.svg) {
            this.svg.setAttribute('viewBox', `${this.viewBox.x} ${this.viewBox.y} ${this.viewBox.w} ${this.viewBox.h}`);
        }
    },

    getSvgCoordinates(evt) {
        const CTM = this.svg.getScreenCTM();
        if (!CTM) return { x: 0, y: 0 };
        return {
            x: (evt.clientX - CTM.e) / CTM.a,
            y: (evt.clientY - CTM.f) / CTM.d
        };
    },

    handleMouseDown(nodeId, evt) {
        evt.stopPropagation();
        this.draggedNodeId = nodeId;
        this.hasDragged = false;
        const coords = this.getSvgCoordinates(evt);
        this.dragStartPos = { x: coords.x, y: coords.y };
        const node = this.nodes.get(nodeId);
        if (node) {
            this.dragOffset = {
                x: coords.x - node.x,
                y: coords.y - node.y
            };
        }
    },

    handleMouseMove(evt) {
        if (!this.draggedNodeId) return;
        const coords = this.getSvgCoordinates(evt);
        const dist = Math.hypot(coords.x - this.dragStartPos.x, coords.y - this.dragStartPos.y);
        if (dist > 4) {
            this.hasDragged = true;
        }
        const node = this.nodes.get(this.draggedNodeId);
        if (node) {
            // Constrain within base boundaries [0, 960] x [0, 540]
            const padding = 35;
            node.x = Math.max(padding, Math.min(960 - padding, coords.x - this.dragOffset.x));
            node.y = Math.max(padding, Math.min(540 - padding, coords.y - this.dragOffset.y));
            this.render();
        }
    },

    handleMouseUp() {
        if (this.draggedNodeId) {
            const id = this.draggedNodeId;
            const node = this.nodes.get(id);
            const wasDragged = this.hasDragged;
            this.draggedNodeId = null;

            if (wasDragged && node && window.App && typeof window.App.onNodeMoved === 'function') {
                window.App.onNodeMoved(id, node.x, node.y);
            }
        }
    },

    /**
     * Load a predefined sample topology by key.
     */
    loadPreset(presetKey) {
        const preset = this.presets[presetKey];
        if (!preset) return false;

        this.nodes.clear();
        this.links = [];
        this.highlightedRoute = [];

        preset.nodes.forEach(n => {
            this.nodes.set(n.id, { ...n });
        });

        preset.links.forEach(l => {
            this.links.push({
                id: this.generateLinkId(l.source, l.target),
                source: l.source,
                target: l.target,
                cost: l.cost,
                status: 'active'
            });
        });

        // Set default Source and Destination: prefer first and second router
        const nodeIds = Array.from(this.nodes.keys());
        this.sourceNodeId = nodeIds[0] || null;
        this.destNodeId = (nodeIds.length > 1) ? nodeIds[1] : (nodeIds[0] || null);

        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Loaded preset: ${preset.name}`);
        }
        return true;
    },

    /**
     * Load network graph directly from node and link definitions (e.g. from backend API).
     */
    loadGraph(nodesArray, linksArray) {
        if (!Array.isArray(nodesArray)) return false;

        this.nodes.clear();
        this.links = [];
        this.highlightedRoute = [];

        nodesArray.forEach(n => {
            const id = (n.id || n.label || '').toUpperCase();
            if (!id) return;
            this.nodes.set(id, {
                id: id,
                label: n.label || id,
                x: n.x !== undefined ? n.x : 100,
                y: n.y !== undefined ? n.y : 100
            });
        });

        if (Array.isArray(linksArray)) {
            linksArray.forEach(l => {
                const u = String(l.source).toUpperCase();
                const v = String(l.target).toUpperCase();
                this.links.push({
                    id: this.generateLinkId(u, v),
                    source: u < v ? u : v,
                    target: u < v ? v : u,
                    cost: parseInt(l.cost, 10) || 1,
                    status: l.status === 'failed' ? 'failed' : 'active'
                });
            });
        }

        const nodeIds = Array.from(this.nodes.keys());
        this.sourceNodeId = nodeIds[0] || null;
        this.destNodeId = (nodeIds.length > 1) ? nodeIds[1] : (nodeIds[0] || null);

        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated('Loaded active network topology');
        }
        return true;
    },

    /**
     * Clear all nodes and links from canvas.
     */
    clearTopology() {
        this.nodes.clear();
        this.links = [];
        this.sourceNodeId = null;
        this.destNodeId = null;
        this.highlightedRoute = [];
        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated('Cleared topology');
        }
    },

    /**
     * Generate canonical link identifier (alphabetically sorted endpoints).
     */
    generateLinkId(u, v) {
        return u < v ? `${u}-${v}` : `${v}-${u}`;
    },

    /**
     * Auto-generate sequential router identifier (R1, R2, R3...).
     */
    autoGenerateRouterId() {
        let i = 1;
        while (this.nodes.has(`R${i}`)) {
            i++;
        }
        return `R${i}`;
    },

    /**
     * Add a new router node with validation and optional auto-ID assignment.
     */
    addNode(nodeId = null, label = null, x = null, y = null) {
        const id = (!nodeId || !String(nodeId).trim())
            ? this.autoGenerateRouterId()
            : String(nodeId).trim().toUpperCase();

        if (this.nodes.has(id)) {
            throw new Error(`Router "${id}" already exists. Duplicate IDs are prohibited.`);
        }

        // Auto-position if not specified
        const finalX = (x !== null && !isNaN(x)) ? x : Math.floor(220 + Math.random() * 520);
        const finalY = (y !== null && !isNaN(y)) ? y : Math.floor(140 + Math.random() * 260);

        this.nodes.set(id, {
            id: id,
            label: label ? String(label).trim() : id,
            x: finalX,
            y: finalY
        });

        if (!this.sourceNodeId) this.sourceNodeId = id;
        else if (!this.destNodeId) this.destNodeId = id;

        this.selectedNodeId = id;
        this.selectedLinkId = null;
        this.render();

        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Added router ${id}`);
        }
        return id;
    },

    /**
     * Update display label and/or canvas coordinates for an existing router.
     */
    updateNode(nodeId, label = null, x = null, y = null) {
        const id = String(nodeId).trim().toUpperCase();
        const node = this.nodes.get(id);
        if (!node) {
            throw new Error(`Router "${id}" does not exist.`);
        }

        if (label !== null && String(label).trim()) {
            node.label = String(label).trim();
        }
        if (x !== null && !isNaN(x)) node.x = x;
        if (y !== null && !isNaN(y)) node.y = y;

        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Updated router ${id}`);
        }
        return node;
    },

    /**
     * Remove router node and any incident links.
     */
    removeNode(nodeId) {
        if (!this.nodes.has(nodeId)) {
            throw new Error(`Router "${nodeId}" does not exist.`);
        }

        this.nodes.delete(nodeId);
        // Remove connected links
        this.links = this.links.filter(l => l.source !== nodeId && l.target !== nodeId);

        // Update selection if removed node was selected
        if (this.sourceNodeId === nodeId) {
            this.sourceNodeId = Array.from(this.nodes.keys())[0] || null;
        }
        if (this.destNodeId === nodeId) {
            this.destNodeId = Array.from(this.nodes.keys())[this.nodes.size - 1] || null;
        }
        if (this.selectedNodeId === nodeId) {
            this.selectedNodeId = null;
        }

        this.highlightedRoute = [];
        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Removed router ${nodeId}`);
        }
    },

    /**
     * Update cost of an existing transmission link.
     */
    updateLinkCost(linkId, cost) {
        const link = this.links.find(l => l.id === linkId);
        if (!link) {
            throw new Error(`Link "${linkId}" not found.`);
        }

        const numericCost = parseInt(cost, 10);
        if (isNaN(numericCost) || numericCost <= 0) {
            throw new Error("Link cost must be a positive integer greater than 0.");
        }

        link.cost = numericCost;
        this.highlightedRoute = [];
        this.render();

        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Updated link ${link.source} — ${link.target} cost to ${numericCost}`);
        }
        return link;
    },

    /**
     * Balance and arrange existing nodes in a circular layout.
     */
    resetLayout() {
        const nodesList = Array.from(this.nodes.values());
        if (nodesList.length === 0) return;

        const centerX = 480;
        const centerY = 270;
        const radius = Math.min(300, Math.max(140, 70 + nodesList.length * 28));

        nodesList.forEach((n, idx) => {
            const angle = (2 * Math.PI * idx) / nodesList.length - Math.PI / 2;
            n.x = Math.round(centerX + radius * Math.cos(angle));
            n.y = Math.round(centerY + radius * Math.sin(angle));
        });

        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated("Reset layout to balanced circular arrangement.");
        }
    },

    /**
     * Set interactive Connection Mode state.
     */
    setConnectingMode(active) {
        this.isConnectingMode = !!active;
        this.connectSourceNodeId = null;

        const banner = document.getElementById('canvasModeBanner');
        const text = document.getElementById('canvasModeText');
        const tbBtn = document.getElementById('tbBtnConnect');
        const sideBtn = document.getElementById('btnSidebarConnectMode');

        if (banner) {
            banner.style.display = this.isConnectingMode ? 'flex' : 'none';
        }
        if (text) {
            text.innerHTML = '<strong>Connection Mode:</strong> Click the first router, then the second router to connect.';
        }
        if (tbBtn) {
            if (this.isConnectingMode) tbBtn.classList.add('active');
            else tbBtn.classList.remove('active');
        }
        if (sideBtn) {
            if (this.isConnectingMode) sideBtn.classList.add('active');
            else sideBtn.classList.remove('active');
        }

        this.render();
    },

    /**
     * Add or update a weighted transmission link with thorough validation.
     */
    addLink(source, target, cost) {
        const u = String(source).trim().toUpperCase();
        const v = String(target).trim().toUpperCase();
        const numericCost = parseInt(cost, 10);

        if (!u || !v) {
            throw new Error('Please select both router endpoints.');
        }
        if (u === v) {
            throw new Error(`Self-links are invalid: cannot connect router "${u}" to itself.`);
        }
        if (!this.nodes.has(u)) {
            throw new Error(`Router "${u}" does not exist in the topology.`);
        }
        if (!this.nodes.has(v)) {
            throw new Error(`Router "${v}" does not exist in the topology.`);
        }
        if (isNaN(numericCost) || numericCost <= 0) {
            throw new Error('Link cost must be a positive integer greater than 0.');
        }

        const linkId = this.generateLinkId(u, v);
        const existingIndex = this.links.findIndex(l => l.id === linkId);

        if (existingIndex >= 0) {
            // Update cost
            this.links[existingIndex].cost = numericCost;
        } else {
            this.links.push({
                id: linkId,
                source: u < v ? u : v,
                target: u < v ? v : u,
                cost: numericCost,
                status: 'active'
            });
        }

        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Saved link ${u} &harr; ${v} (Cost: ${numericCost})`);
        }
    },

    /**
     * Remove a transmission link.
     */
    removeLink(linkId) {
        const initialLen = this.links.length;
        this.links = this.links.filter(l => l.id !== linkId);
        if (this.links.length === initialLen) {
            throw new Error(`Link "${linkId}" not found.`);
        }

        this.highlightedRoute = [];
        this.render();
        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Removed link ${linkId}`);
        }
    },

    /**
     * Toggle status of a link between 'active' and 'failed'.
     */
    toggleLinkStatus(linkId) {
        const link = this.links.find(l => l.id === linkId);
        if (!link) {
            throw new Error(`Link "${linkId}" not found.`);
        }

        link.status = (link.status === 'active') ? 'failed' : 'active';
        this.highlightedRoute = [];
        this.render();

        const msg = link.status === 'failed' 
            ? `Link failure simulated on ${link.source}&harr;${link.target}`
            : `Link ${link.source}&harr;${link.target} recovered to active`;

        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(msg, link.status === 'failed' ? 'warn' : 'success');
        }
        return link.status;
    },

    /**
     * Recover all failed links back to active state.
     */
    recoverAllLinks() {
        let count = 0;
        this.links.forEach(l => {
            if (l.status === 'failed') {
                l.status = 'active';
                count++;
            }
        });
        this.highlightedRoute = [];
        this.render();

        if (window.App && typeof window.App.onTopologyUpdated === 'function') {
            window.App.onTopologyUpdated(`Recovered ${count} link(s) to active state`, 'success');
        }
        return count;
    },

    /**
     * Check if a specific link is part of the currently highlighted route.
     */
    isLinkInRoute(u, v) {
        if (!this.highlightedRoute || this.highlightedRoute.length < 2) return false;
        for (let i = 0; i < this.highlightedRoute.length - 1; i++) {
            const rU = this.highlightedRoute[i];
            const rV = this.highlightedRoute[i + 1];
            if ((rU === u && rV === v) || (rU === v && rV === u)) {
                return true;
            }
        }
        return false;
    },

    /**
     * Set highlighted calculated path.
     */
    setHighlightedRoute(pathArray) {
        this.highlightedRoute = Array.isArray(pathArray) ? pathArray : [];
        this.render();
    },

    /**
     * Set currently active step element for algorithm step playback.
     */
    setActiveStep(nodeId = null, edgeData = null) {
        this.activeStepNodeId = nodeId;
        this.activeStepEdge = edgeData;
        this.render();
    },

    /**
     * Render the entire SVG topology.
     */
    render() {
        if (!this.svg) return;

        // 1. Render Links
        this.linksGroup.innerHTML = '';
        this.linkLabelsGroup.innerHTML = '';

        this.links.forEach(link => {
            const u = this.nodes.get(link.source);
            const v = this.nodes.get(link.target);
            if (!u || !v) return;

            const isFailed = link.status === 'failed';
            const isRoute = !isFailed && this.isLinkInRoute(link.source, link.target);
            const isStepRelaxing = !isFailed && this.activeStepEdge &&
                ((link.source === this.activeStepEdge.source && link.target === this.activeStepEdge.target) ||
                 (link.source === this.activeStepEdge.target && link.target === this.activeStepEdge.source));

            const isSelectedLink = (link.id === this.selectedLinkId);

            // Link Line element
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', u.x);
            line.setAttribute('y1', u.y);
            line.setAttribute('x2', v.x);
            line.setAttribute('y2', v.y);
            line.setAttribute('class', `link-line ${isFailed ? 'failed' : ''} ${isRoute ? 'route-active' : ''} ${isStepRelaxing ? 'step-relaxing' : ''} ${isSelectedLink ? 'selected-link' : ''}`);
            line.setAttribute('data-link-id', link.id);
            line.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isConnectingMode) return;
                this.selectedLinkId = link.id;
                this.selectedNodeId = null;
                this.render();
                if (window.App && typeof window.App.onLinkSelected === 'function') {
                    window.App.onLinkSelected(link.id);
                }
            });
            line.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                if (window.App && typeof window.App.openEditCostModal === 'function') {
                    window.App.openEditCostModal(link.id);
                }
            });
            this.linksGroup.appendChild(line);

            // Cost Pill Badge at Line Midpoint
            const midX = (u.x + v.x) / 2;
            const midY = (u.y + v.y) / 2;

            const labelGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            labelGroup.setAttribute('class', `link-cost-group ${isFailed ? 'failed' : ''} ${isSelectedLink ? 'selected-link' : ''}`);
            labelGroup.setAttribute('transform', `translate(${midX}, ${midY})`);
            labelGroup.style.cursor = 'pointer';
            labelGroup.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isConnectingMode) return;
                this.toggleLinkStatus(link.id);
            });
            labelGroup.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                if (window.App && typeof window.App.openEditCostModal === 'function') {
                    window.App.openEditCostModal(link.id);
                }
            });

            const badgeWidth = isFailed ? 36 : 28;
            const badgeHeight = 18;

            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', -badgeWidth / 2);
            rect.setAttribute('y', -badgeHeight / 2);
            rect.setAttribute('width', badgeWidth);
            rect.setAttribute('height', badgeHeight);
            rect.setAttribute('class', 'link-cost-bg');

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', 0);
            text.setAttribute('y', 0);
            text.setAttribute('class', 'link-cost-text');
            text.textContent = isFailed ? '✕' : link.cost;

            labelGroup.appendChild(rect);
            labelGroup.appendChild(text);
            this.linkLabelsGroup.appendChild(labelGroup);
        });

        // 2. Render Router Nodes
        this.nodesGroup.innerHTML = '';
        this.nodes.forEach(node => {
            const isSource = node.id === this.sourceNodeId;
            const isDest = node.id === this.destNodeId;
            const isStepVisiting = (node.id === this.activeStepNodeId);
            const isSelected = (node.id === this.selectedNodeId);
            const isConnectingSrc = (node.id === this.connectSourceNodeId);

            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('class', `router-node ${isSource ? 'source' : ''} ${isDest ? 'dest' : ''} ${isStepVisiting ? 'step-visiting' : ''} ${isSelected ? 'selected' : ''} ${isConnectingSrc ? 'connecting-source' : ''}`);
            g.setAttribute('transform', `translate(${node.x}, ${node.y})`);
            g.setAttribute('data-node-id', node.id);

            // Drag listener
            g.addEventListener('mousedown', (e) => this.handleMouseDown(node.id, e));
            g.addEventListener('touchstart', (e) => {
                if (e.touches.length === 1) {
                    this.handleMouseDown(node.id, e.touches[0]);
                }
            }, { passive: true });

            // Click listener for Selection & Connection Mode
            g.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.hasDragged) {
                    this.hasDragged = false;
                    return;
                }

                if (this.isConnectingMode) {
                    if (!this.connectSourceNodeId) {
                        this.connectSourceNodeId = node.id;
                        this.render();
                        if (window.App && typeof window.App.onConnectingSourceSelected === 'function') {
                            window.App.onConnectingSourceSelected(node.id);
                        }
                    } else {
                        if (this.connectSourceNodeId === node.id) {
                            if (window.App && typeof window.App.toast === 'function') {
                                window.App.toast('Cannot connect router to itself. Select a different router or Cancel.', 'warning');
                            }
                            return;
                        }
                        const src = this.connectSourceNodeId;
                        const dst = node.id;
                        this.setConnectingMode(false);
                        if (window.App && typeof window.App.promptConnectCost === 'function') {
                            window.App.promptConnectCost(src, dst);
                        }
                    }
                    return;
                }

                // Normal Mode: Select Node & notify App
                this.selectedNodeId = node.id;
                this.selectedLinkId = null;
                this.render();
                if (window.App && typeof window.App.onNodeSelected === 'function') {
                    window.App.onNodeSelected(node.id);
                }
                if (window.App && typeof window.App.onNodeClicked === 'function') {
                    window.App.onNodeClicked(node.id);
                }
            });

            // Outer decorative ring / circle
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', 22);
            circle.setAttribute('class', 'router-circle');

            // Router label text
            const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            labelText.setAttribute('y', -1);
            labelText.setAttribute('class', 'router-text');
            labelText.textContent = node.label || node.id;

            // Optional role badge (SRC / DST)
            if (isSource || isDest) {
                const badgeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                badgeText.setAttribute('y', 32);
                badgeText.setAttribute('class', 'router-subtext');
                badgeText.textContent = isSource ? 'SOURCE' : 'DEST';
                g.appendChild(badgeText);
            }

            g.appendChild(circle);
            g.appendChild(labelText);
            this.nodesGroup.appendChild(g);
        });

        // 3. Update Empty Canvas State Visibility
        const emptyGroup = document.getElementById('emptyCanvasGroup');
        if (emptyGroup) {
            emptyGroup.style.display = (this.nodes.size === 0) ? 'block' : 'none';
        }
    },

    /**
     * Export network graph in standard adjacency format for backend API payload.
     */
    exportGraph() {
        const activeAdj = {};
        const fullAdj = {};

        this.nodes.forEach(n => {
            activeAdj[n.id] = {};
            fullAdj[n.id] = {};
        });

        this.links.forEach(l => {
            const u = l.source;
            const v = l.target;
            const cost = l.cost;

            if (fullAdj[u] && fullAdj[v]) {
                fullAdj[u][v] = cost;
                fullAdj[v][u] = cost;
            }

            if (l.status === 'active' && activeAdj[u] && activeAdj[v]) {
                activeAdj[u][v] = cost;
                activeAdj[v][u] = cost;
            }
        });

        return {
            nodes: Array.from(this.nodes.values()),
            links: [...this.links],
            activeAdjacency: activeAdj,
            fullAdjacency: fullAdj
        };
    }
};

window.Topology = Topology;
