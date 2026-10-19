/**
 * Intelligent Network Routing Simulator - Main Application Coordinator
 * Vanilla JavaScript (ES6)
 * 
 * Manages dashboard state, UI event listeners, form validations,
 * dropdown synchronization, backend health monitoring, Dijkstra & Distance-Vector APIs,
 * step-by-step playback, and event logs.
 */

const App = {
    backendOnline: false,
    backendPollInterval: null,

    // Simulation State
    currentAlgorithm: 'dijkstra',
    simulationSteps: [],
    currentStepIndex: -1,
    activeRoutingTable: [],
    allRouterTables: null, // Map of { routerId: [ { destination, cost, next_hop, status } ] }
    lastSourceRouter: null,

    // Builder & Modal State
    modalCostMode: 'connect', // 'connect' | 'edit'
    editingLinkId: null,
    connectingEndpoints: { source: null, target: null },
    modalRouterMode: 'add',   // 'add' | 'rename'
    editingRouterId: null,

    /**
     * Initialize application on DOM ready.
     */
    async init() {
        window.App = this;
        this.log('INFO', 'Initializing Intelligent Network Routing Simulator UI...');
        
        // 1. Initialize SVG Canvas Topology
        if (window.Topology) {
            window.Topology.init('networkSvg');
        }

        // 2. Setup UI Listeners & Tabs
        this.setupEventListeners();
        this.setupTabs();

        // 3. Load Active Network Topology from Backend API
        await this.loadInitialTopology();

        // 4. Force synchronization of all dropdowns, counters and badges
        this.syncDropdowns();

        // 5. Check Backend Health
        this.checkBackendHealth();
        // Periodically verify backend connection every 15s
        this.log('SUCCESS', 'Dashboard initialized. Ready for routing protocol simulation.');

        // URL Parameter automation helper for screenshots / direct link presets
        const params = new URLSearchParams(window.location.search);
        const view = params.get('view');
        if (view) {
            setTimeout(async () => {
                if (view === 'custom') {
                    if (window.Topology) {
                        const presetSelect = document.getElementById('topologyPresetSelect');
                        if (presetSelect) presetSelect.value = 'nsfnet7';
                        window.Topology.loadPreset('nsfnet7');
                        const src = document.getElementById('sourceRouterSelect');
                        const dst = document.getElementById('destRouterSelect');
                        if (src) { src.value = 'R1'; window.Topology.sourceNodeId = 'R1'; }
                        if (dst) { dst.value = 'R5'; window.Topology.destNodeId = 'R5'; }
                        window.Topology.render();
                        this.syncDropdowns();
                        this.toast('Custom topology editor: Loaded NSFNET 7-Node Core Topology', 'info');
                    }
                } else if (view === 'dijkstra') {
                    const src = document.getElementById('sourceRouterSelect');
                    const dst = document.getElementById('destRouterSelect');
                    if (src) { src.value = 'A'; window.Topology.sourceNodeId = 'A'; }
                    if (dst) { dst.value = 'D'; window.Topology.destNodeId = 'D'; }
                    window.Topology.render();
                    await this.handleRunSimulationClick();
                } else if (view === 'distance_vector') {
                    const algo = document.getElementById('algorithmSelect');
                    if (algo) {
                        algo.value = 'distance_vector';
                        this.currentAlgorithm = 'distance_vector';
                    }
                    const src = document.getElementById('sourceRouterSelect');
                    const dst = document.getElementById('destRouterSelect');
                    if (src) { src.value = 'A'; window.Topology.sourceNodeId = 'A'; }
                    if (dst) { dst.value = 'D'; window.Topology.destNodeId = 'D'; }
                    window.Topology.render();
                    await this.handleRunSimulationClick();
                } else if (view === 'link_failure') {
                    const src = document.getElementById('sourceRouterSelect');
                    const dst = document.getElementById('destRouterSelect');
                    if (src) { src.value = 'A'; window.Topology.sourceNodeId = 'A'; }
                    if (dst) { dst.value = 'D'; window.Topology.destNodeId = 'D'; }
                    if (window.Topology) {
                        const link = window.Topology.links.find(l => (l.source === 'A' && l.target === 'B') || (l.source === 'B' && l.target === 'A'));
                        if (link) {
                            window.Topology.toggleLinkStatus(link.id);
                        }
                    }
                    this.syncDropdowns();
                    await this.handleRunSimulationClick();
                    this.toast('Fault Injected: Link A-B severed. Recomputed dynamic route via C & E.', 'warning');
                }
            }, 400);
        }
    },

    /**
     * Fetch active default topology from Flask backend API (/api/topology).
     */
    async loadInitialTopology() {
        try {
            const res = await fetch('/api/topology');
            if (res.ok) {
                const data = await res.json();
                if (data && data.status === 'success' && Array.isArray(data.nodes) && data.nodes.length > 0) {
                    if (window.Topology) {
                        window.Topology.loadGraph(data.nodes, data.links || []);
                    }
                    this.log('SUCCESS', `Synchronized default topology from backend (${data.nodes.length} routers, ${(data.links || []).length} links).`);
                    return;
                }
            }
            throw new Error(`Server returned HTTP ${res.status}`);
        } catch (err) {
            const cached = this.loadFromLocalStorage();
            if (cached && Array.isArray(cached.nodes) && cached.nodes.length > 0 && window.Topology) {
                window.Topology.loadGraph(cached.nodes, cached.links || []);
                this.log('INFO', `Restored topology from local browser storage (${cached.nodes.length} routers).`);
                return;
            }
            this.log('WARN', `Could not fetch backend topology (${err.message}). Using built-in default topology.`);
            if (window.Topology) {
                window.Topology.loadPreset('mesh5');
            }
        }
    },

    /**
     * Check backend status using native Fetch API.
     */
    async checkBackendHealth() {
        const badge = document.getElementById('backendStatusBadge');
        const indicator = document.getElementById('statusIndicator');

        try {
            const res = await fetch('/api/health');
            if (!res.ok) {
                throw new Error(`Server returned HTTP ${res.status}`);
            }
            const data = await res.json();
            
            if (data && data.status === 'healthy') {
                if (!this.backendOnline) {
                    this.log('SUCCESS', `Backend connected: ${data.service} (v${data.version})`);
                }
                this.backendOnline = true;
                if (badge) {
                    badge.textContent = 'Backend: Online';
                    badge.className = 'badge healthy';
                }
                if (indicator) {
                    indicator.className = 'status-indicator online';
                }
            } else {
                throw new Error('Unexpected health response schema');
            }
        } catch (error) {
            if (this.backendOnline || (badge && badge.textContent.includes('Connecting'))) {
                this.log('ERROR', `Backend connection failed: ${error.message}`);
                this.toast(`Backend unavailable: ${error.message}`, 'error');
            }
            this.backendOnline = false;
            if (badge) {
                badge.textContent = 'Backend: Offline';
                badge.className = 'badge offline';
            }
            if (indicator) {
                indicator.className = 'status-indicator offline';
            }
        }
    },

    /**
     * Setup UI button and form listeners.
     */
    setupEventListeners() {
        // Preset Topology Loader
        const btnLoadPreset = document.getElementById('btnLoadPreset');
        const presetSelect = document.getElementById('topologyPresetSelect');
        if (btnLoadPreset && presetSelect) {
            btnLoadPreset.addEventListener('click', () => {
                const key = presetSelect.value;
                if (window.Topology) {
                    this.resetSimulationState();
                    window.Topology.loadPreset(key);
                    this.toast(`Loaded preset topology: ${key.toUpperCase()}`, 'success');
                }
            });
        }

        // Clear Topology
        const clearHandler = () => {
            if (confirm('Are you sure you want to clear all routers and links from the canvas?')) {
                if (window.Topology) {
                    this.resetSimulationState();
                    window.Topology.clearTopology();
                    this.toast('Topology cleared.', 'info');
                }
            }
        };
        const btnClear = document.getElementById('btnClearTopology');
        if (btnClear) btnClear.addEventListener('click', clearHandler);
        const tbBtnClear = document.getElementById('tbBtnClear');
        if (tbBtnClear) tbBtnClear.addEventListener('click', clearHandler);

        // Reset View / Balance Layout
        const resetLayoutHandler = () => {
            if (window.Topology) {
                this.resetSimulationState();
                window.Topology.resetLayout();
                this.toast('Rearranged routers in balanced circular layout.', 'info');
            }
        };
        const btnResetView = document.getElementById('btnResetView');
        if (btnResetView) btnResetView.addEventListener('click', resetLayoutHandler);
        const tbBtnResetLayout = document.getElementById('tbBtnResetLayout');
        if (tbBtnResetLayout) tbBtnResetLayout.addEventListener('click', resetLayoutHandler);
        const btnResetLayoutSidebar = document.getElementById('btnResetLayoutSidebar');
        if (btnResetLayoutSidebar) btnResetLayoutSidebar.addEventListener('click', resetLayoutHandler);

        // Add Router Form (Sidebar)
        const formAddRouter = document.getElementById('formAddRouter');
        const routerIdInput = document.getElementById('routerIdInput');
        const routerLabelInput = document.getElementById('routerLabelInput');
        if (formAddRouter) {
            formAddRouter.addEventListener('submit', (e) => {
                e.preventDefault();
                const id = routerIdInput.value.trim().toUpperCase();
                const label = routerLabelInput ? routerLabelInput.value.trim() : null;
                try {
                    this.resetSimulationState();
                    const createdId = window.Topology.addNode(id || null, label || null);
                    this.toast(`Router "${createdId}" added successfully.`, 'success');
                    routerIdInput.value = '';
                    if (routerLabelInput) routerLabelInput.value = '';
                } catch (err) {
                    this.toast(err.message, 'error');
                    this.log('ERROR', `Failed to add router: ${err.message}`);
                }
            });
        }

        // Rename Router Form (Sidebar)
        const formRenameRouter = document.getElementById('formRenameRouter');
        const renameRouterSelect = document.getElementById('renameRouterSelect');
        const renameRouterNewName = document.getElementById('renameRouterNewName');
        if (formRenameRouter) {
            formRenameRouter.addEventListener('submit', (e) => {
                e.preventDefault();
                const id = renameRouterSelect.value;
                const newName = renameRouterNewName.value.trim();
                if (!id) {
                    this.toast('Please select a router to rename.', 'warning');
                    return;
                }
                try {
                    this.resetSimulationState();
                    window.Topology.updateNode(id, newName);
                    this.toast(`Router "${id}" renamed to "${newName}".`, 'success');
                } catch (err) {
                    this.toast(err.message, 'error');
                }
            });
        }
        if (renameRouterSelect) {
            renameRouterSelect.addEventListener('change', () => {
                const node = window.Topology.nodes.get(renameRouterSelect.value);
                if (node && renameRouterNewName) {
                    renameRouterNewName.value = node.label || node.id;
                }
            });
        }

        // Remove Router Form (Sidebar)
        const formRemoveRouter = document.getElementById('formRemoveRouter');
        const removeRouterSelect = document.getElementById('removeRouterSelect');
        if (formRemoveRouter) {
            formRemoveRouter.addEventListener('submit', (e) => {
                e.preventDefault();
                const id = removeRouterSelect.value;
                if (!id) {
                    this.toast('Please select a router to remove.', 'warning');
                    return;
                }
                try {
                    this.resetSimulationState();
                    window.Topology.removeNode(id);
                    this.toast(`Router "${id}" removed.`, 'info');
                } catch (err) {
                    this.toast(err.message, 'error');
                    this.log('ERROR', `Failed to remove router: ${err.message}`);
                }
            });
        }

        // Add Link Form (Sidebar)
        const formAddLink = document.getElementById('formAddLink');
        const linkSourceSelect = document.getElementById('linkSourceSelect');
        const linkTargetSelect = document.getElementById('linkTargetSelect');
        const linkCostInput = document.getElementById('linkCostInput');
        if (formAddLink) {
            formAddLink.addEventListener('submit', (e) => {
                e.preventDefault();
                const u = linkSourceSelect.value;
                const v = linkTargetSelect.value;
                const cost = parseInt(linkCostInput.value, 10);
                try {
                    this.resetSimulationState();
                    window.Topology.addLink(u, v, cost);
                    this.toast(`Link ${u} ↔ ${v} saved with cost ${cost}.`, 'success');
                } catch (err) {
                    this.toast(err.message, 'error');
                    this.log('ERROR', `Failed to add link: ${err.message}`);
                }
            });
        }

        // Edit Link Cost Form (Sidebar)
        const formEditLinkCost = document.getElementById('formEditLinkCost');
        const editLinkCostSelect = document.getElementById('editLinkCostSelect');
        const editLinkCostNewValue = document.getElementById('editLinkCostNewValue');
        if (formEditLinkCost) {
            formEditLinkCost.addEventListener('submit', (e) => {
                e.preventDefault();
                const linkId = editLinkCostSelect.value;
                const cost = parseInt(editLinkCostNewValue.value, 10);
                if (!linkId) {
                    this.toast('Please select a link to edit.', 'warning');
                    return;
                }
                try {
                    this.resetSimulationState();
                    window.Topology.updateLinkCost(linkId, cost);
                    this.toast(`Link ${linkId} cost updated to ${cost}.`, 'success');
                } catch (err) {
                    this.toast(err.message, 'error');
                }
            });
        }
        if (editLinkCostSelect) {
            editLinkCostSelect.addEventListener('change', () => {
                const link = window.Topology.links.find(l => l.id === editLinkCostSelect.value);
                if (link && editLinkCostNewValue) {
                    editLinkCostNewValue.value = link.cost;
                }
            });
        }

        // Remove Link Form (Sidebar)
        const formRemoveLink = document.getElementById('formRemoveLink');
        const removeLinkSelect = document.getElementById('removeLinkSelect');
        if (formRemoveLink) {
            formRemoveLink.addEventListener('submit', (e) => {
                e.preventDefault();
                const linkId = removeLinkSelect.value;
                if (!linkId) {
                    this.toast('Please select a link to remove.', 'warning');
                    return;
                }
                try {
                    this.resetSimulationState();
                    window.Topology.removeLink(linkId);
                    this.toast(`Link "${linkId}" removed.`, 'info');
                } catch (err) {
                    this.toast(err.message, 'error');
                    this.log('ERROR', `Failed to remove link: ${err.message}`);
                }
            });
        }

        // Toggle Link Failure Button
        const btnToggleLinkFailure = document.getElementById('btnToggleLinkFailure');
        const failureLinkSelect = document.getElementById('failureLinkSelect');
        if (btnToggleLinkFailure && failureLinkSelect) {
            btnToggleLinkFailure.addEventListener('click', () => {
                const linkId = failureLinkSelect.value;
                if (!linkId) {
                    this.toast('Please select a link to toggle.', 'warning');
                    return;
                }
                try {
                    this.resetSimulationState();
                    const newStatus = window.Topology.toggleLinkStatus(linkId);
                    const toastType = newStatus === 'failed' ? 'warning' : 'success';
                    this.toast(`Link ${linkId} is now ${newStatus.toUpperCase()}`, toastType);
                } catch (err) {
                    this.toast(err.message, 'error');
                }
            });
        }

        // Recover All Links
        const btnRecoverAll = document.getElementById('btnRecoverAllLinks');
        if (btnRecoverAll) {
            btnRecoverAll.addEventListener('click', () => {
                this.resetSimulationState();
                const recovered = window.Topology.recoverAllLinks();
                if (recovered > 0) {
                    this.toast(`Recovered ${recovered} link(s) to active state.`, 'success');
                } else {
                    this.toast('No links are currently failed.', 'info');
                }
            });
        }

        // Toolbar Buttons
        const tbBtnAddRouter = document.getElementById('tbBtnAddRouter');
        if (tbBtnAddRouter) {
            tbBtnAddRouter.addEventListener('click', () => this.openRouterModal('add'));
        }

        const connectModeHandler = () => {
            const nextMode = !window.Topology.isConnectingMode;
            window.Topology.setConnectingMode(nextMode);
            if (nextMode) {
                this.toast('Connection Mode activated: Click router A, then router B.', 'info');
            }
        };
        const tbBtnConnect = document.getElementById('tbBtnConnect');
        if (tbBtnConnect) tbBtnConnect.addEventListener('click', connectModeHandler);
        const btnSidebarConnectMode = document.getElementById('btnSidebarConnectMode');
        if (btnSidebarConnectMode) btnSidebarConnectMode.addEventListener('click', connectModeHandler);

        const btnCancelMode = document.getElementById('btnCancelMode');
        if (btnCancelMode) {
            btnCancelMode.addEventListener('click', () => {
                window.Topology.setConnectingMode(false);
                this.toast('Connection Mode cancelled.', 'info');
            });
        }

        const tbBtnEditLink = document.getElementById('tbBtnEditLink');
        if (tbBtnEditLink) {
            tbBtnEditLink.addEventListener('click', () => {
                if (window.Topology.selectedLinkId) {
                    this.openEditCostModal(window.Topology.selectedLinkId);
                } else if (window.Topology.links.length > 0) {
                    this.openEditCostModal(window.Topology.links[0].id);
                } else {
                    this.toast('No links exist to edit. Connect two routers first.', 'warning');
                }
            });
        }

        const tbBtnDeleteSelected = document.getElementById('tbBtnDeleteSelected');
        if (tbBtnDeleteSelected) {
            tbBtnDeleteSelected.addEventListener('click', () => {
                if (window.Topology.selectedNodeId) {
                    const id = window.Topology.selectedNodeId;
                    if (confirm(`Delete router "${id}" and all incident links?`)) {
                        this.resetSimulationState();
                        window.Topology.removeNode(id);
                        this.toast(`Router "${id}" deleted.`, 'info');
                    }
                } else if (window.Topology.selectedLinkId) {
                    const linkId = window.Topology.selectedLinkId;
                    if (confirm(`Delete link "${linkId}"?`)) {
                        this.resetSimulationState();
                        window.Topology.removeLink(linkId);
                        this.toast(`Link "${linkId}" deleted.`, 'info');
                    }
                } else {
                    this.toast('Click a router or link on the canvas to select it first.', 'info');
                }
            });
        }

        // File Save / Load Handlers
        const exportHandler = () => this.exportTopologyJSON();
        const tbBtnExport = document.getElementById('tbBtnExport');
        if (tbBtnExport) tbBtnExport.addEventListener('click', exportHandler);
        const btnExportTopology = document.getElementById('btnExportTopology');
        if (btnExportTopology) btnExportTopology.addEventListener('click', exportHandler);

        const fileInput = document.getElementById('topologyFileInput');
        const triggerImport = () => { if (fileInput) fileInput.click(); };
        const tbBtnImport = document.getElementById('tbBtnImport');
        if (tbBtnImport) tbBtnImport.addEventListener('click', triggerImport);
        const btnImportTopologyTrigger = document.getElementById('btnImportTopologyTrigger');
        if (btnImportTopologyTrigger) btnImportTopologyTrigger.addEventListener('click', triggerImport);

        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    this.importTopologyJSON(e.target.files[0]);
                    e.target.value = '';
                }
            });
        }

        // Zoom Controls
        const btnZoomIn = document.getElementById('btnZoomIn');
        if (btnZoomIn) btnZoomIn.addEventListener('click', () => window.Topology.zoom(0.85));
        const btnZoomOut = document.getElementById('btnZoomOut');
        if (btnZoomOut) btnZoomOut.addEventListener('click', () => window.Topology.zoom(1.18));
        const btnZoomFit = document.getElementById('btnZoomFit');
        if (btnZoomFit) btnZoomFit.addEventListener('click', () => window.Topology.resetZoom());

        // Modals Setup
        const modalCostClose = document.getElementById('modalCostClose');
        const btnModalCostCancel = document.getElementById('btnModalCostCancel');
        if (modalCostClose) modalCostClose.addEventListener('click', () => this.closeCostModal());
        if (btnModalCostCancel) btnModalCostCancel.addEventListener('click', () => this.closeCostModal());

        const formModalCost = document.getElementById('formModalCost');
        if (formModalCost) {
            formModalCost.addEventListener('submit', (e) => {
                e.preventDefault();
                const cost = parseInt(document.getElementById('modalCostInput').value, 10);
                if (isNaN(cost) || cost <= 0) {
                    this.toast('Link cost must be a positive integer greater than 0.', 'error');
                    return;
                }
                this.resetSimulationState();
                if (this.modalCostMode === 'edit') {
                    window.Topology.updateLinkCost(this.editingLinkId, cost);
                    this.toast(`Link ${this.editingLinkId} cost updated to ${cost}.`, 'success');
                } else if (this.modalCostMode === 'connect') {
                    window.Topology.addLink(this.connectingEndpoints.source, this.connectingEndpoints.target, cost);
                    this.toast(`Connected ${this.connectingEndpoints.source} ↔ ${this.connectingEndpoints.target} (Cost: ${cost}).`, 'success');
                }
                this.closeCostModal();
            });
        }

        const modalRouterClose = document.getElementById('modalRouterClose');
        const btnModalRouterCancel = document.getElementById('btnModalRouterCancel');
        if (modalRouterClose) modalRouterClose.addEventListener('click', () => this.closeRouterModal());
        if (btnModalRouterCancel) btnModalRouterCancel.addEventListener('click', () => this.closeRouterModal());

        const formModalRouter = document.getElementById('formModalRouter');
        if (formModalRouter) {
            formModalRouter.addEventListener('submit', (e) => {
                e.preventDefault();
                const idInput = document.getElementById('modalRouterIdInput');
                const labelInput = document.getElementById('modalRouterLabelInput');
                const id = idInput.value.trim().toUpperCase();
                const label = labelInput ? labelInput.value.trim() : null;

                this.resetSimulationState();
                if (this.modalRouterMode === 'add') {
                    try {
                        const newId = window.Topology.addNode(id || null, label || null);
                        this.toast(`Router "${newId}" added successfully.`, 'success');
                        this.closeRouterModal();
                    } catch (err) {
                        this.toast(err.message, 'error');
                    }
                } else if (this.modalRouterMode === 'rename') {
                    try {
                        window.Topology.updateNode(this.editingRouterId, label || null);
                        this.toast(`Router "${this.editingRouterId}" updated.`, 'success');
                        this.closeRouterModal();
                    } catch (err) {
                        this.toast(err.message, 'error');
                    }
                }
            });
        }

        // Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (window.Topology && window.Topology.isConnectingMode) {
                    window.Topology.setConnectingMode(false);
                    this.toast('Connection Mode cancelled.', 'info');
                }
                this.closeCostModal();
                this.closeRouterModal();
            } else if (e.key === 'Delete' || e.key === 'Backspace') {
                const tag = document.activeElement ? document.activeElement.tagName : '';
                if (['INPUT', 'TEXTAREA', 'SELECT'].indexOf(tag) === -1) {
                    const tbDel = document.getElementById('tbBtnDeleteSelected');
                    if (tbDel) tbDel.click();
                }
            }
        });

        // Source & Destination Select dropdown change
        const sourceSelect = document.getElementById('sourceRouterSelect');
        const destSelect = document.getElementById('destRouterSelect');
        if (sourceSelect) {
            sourceSelect.addEventListener('change', () => {
                window.Topology.sourceNodeId = sourceSelect.value || null;
                window.Topology.render();
                this.log('INFO', `Source router set to: ${sourceSelect.value}`);
            });
        }
        if (destSelect) {
            destSelect.addEventListener('change', () => {
                window.Topology.destNodeId = destSelect.value || null;
                window.Topology.render();
                this.log('INFO', `Destination router set to: ${destSelect.value}`);
            });
        }

        // Run Simulation Button
        const btnRunSim = document.getElementById('btnRunSimulation');
        if (btnRunSim) {
            btnRunSim.addEventListener('click', () => this.handleRunSimulationClick());
        }

        // Step Navigation Buttons
        const btnNextStep = document.getElementById('btnNextStep');
        if (btnNextStep) {
            btnNextStep.addEventListener('click', () => this.nextStep());
        }

        const btnPrevStep = document.getElementById('btnPrevStep');
        if (btnPrevStep) {
            btnPrevStep.addEventListener('click', () => this.prevStep());
        }

        // Reset Simulation Button
        const btnResetSim = document.getElementById('btnResetSimulation');
        if (btnResetSim) {
            btnResetSim.addEventListener('click', () => {
                this.resetSimulationState();
                this.toast('Simulation state reset.', 'info');
            });
        }

        // Clear Log
        const btnClearLog = document.getElementById('btnClearLog');
        if (btnClearLog) {
            btnClearLog.addEventListener('click', () => {
                const logEntries = document.getElementById('eventLogEntries');
                if (logEntries) logEntries.innerHTML = '';
            });
        }

        // Routing Table Router Filter Change
        const tableFilter = document.getElementById('routingTableRouterSelect');
        if (tableFilter) {
            tableFilter.addEventListener('change', () => {
                this.renderRoutingTable(tableFilter.value);
            });
        }
    },

    /**
     * Setup tab switching in panels.
     */
    setupTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const parentGroup = btn.closest('.card-tabs') || btn.closest('.sub-tabs') || btn.closest('.card-header');
                const card = btn.closest('.card');
                const targetTabId = btn.getAttribute('data-tab');

                if (parentGroup) {
                    parentGroup.querySelectorAll('.tab-btn').forEach(b => {
                        b.classList.remove('active');
                        b.setAttribute('aria-selected', 'false');
                    });
                }
                if (card) {
                    card.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                }

                btn.classList.add('active');
                btn.setAttribute('aria-selected', 'true');
                const targetContent = document.getElementById(targetTabId);
                if (targetContent) targetContent.classList.add('active');

                // Inspection card header tools toggle
                const filterWrap = document.getElementById('routingTableFilterWrap');
                const clearLogBtn = document.getElementById('btnClearLog');
                if (filterWrap && clearLogBtn) {
                    if (targetTabId === 'tabEventLog') {
                        filterWrap.style.display = 'none';
                        clearLogBtn.style.display = 'inline-flex';
                    } else if (targetTabId === 'tabRoutingTables') {
                        filterWrap.style.display = 'flex';
                        clearLogBtn.style.display = 'none';
                    }
                }
            });
        });
    },

    /**
     * Reset simulation results, step traces, and UI indicators.
     */
    resetSimulationState() {
        if (window.Topology) {
            window.Topology.setHighlightedRoute([]);
            window.Topology.setActiveStep(null, null);
        }
        this.simulationSteps = [];
        this.currentStepIndex = -1;
        this.activeRoutingTable = [];
        this.allRouterTables = null;

        document.getElementById('resultStatus').textContent = 'Idle';
        document.getElementById('resultPath').textContent = '—';
        document.getElementById('resultCost').textContent = '—';
        document.getElementById('resultHops').textContent = '—';
        document.getElementById('stepCounter').textContent = 'Step: Idle';
        document.getElementById('stepExplanationText').textContent = 'Select an algorithm and run simulation to compute routing paths.';

        const btnNext = document.getElementById('btnNextStep');
        const btnPrev = document.getElementById('btnPrevStep');
        if (btnNext) btnNext.disabled = true;
        if (btnPrev) btnPrev.disabled = true;

        this.renderRoutingTable();
    },

    /**
     * Handle user click on a router node in the SVG canvas.
     */
    onNodeClicked(nodeId) {
        if (!window.Topology.sourceNodeId || (window.Topology.sourceNodeId && window.Topology.destNodeId)) {
            window.Topology.sourceNodeId = nodeId;
            window.Topology.destNodeId = null;
            this.toast(`Source set to Router ${nodeId}. Select Destination.`, 'info');
        } else if (window.Topology.sourceNodeId === nodeId) {
            window.Topology.sourceNodeId = null;
            this.toast(`Source deselected.`, 'info');
        } else {
            window.Topology.destNodeId = nodeId;
            this.toast(`Destination set to Router ${nodeId}.`, 'info');
        }

        this.syncDropdowns();
        window.Topology.render();
    },

    /**
     * Callback invoked whenever topology nodes or links are modified.
     */
    onTopologyUpdated(logMessage, logType = 'info') {
        // Invalidate stale simulation results immediately
        if (window.Topology) {
            window.Topology.setHighlightedRoute([]);
        }
        if (this.simulationSteps && this.simulationSteps.length > 0) {
            this.simulationSteps = [];
            this.currentStepIndex = -1;
            const resStatus = document.getElementById('resultStatus');
            if (resStatus) resStatus.textContent = 'Topology Modified (Rerun Simulation)';
            const resPath = document.getElementById('resultPath');
            if (resPath) resPath.textContent = '— (Stale Route Cleared)';
            const exp = document.getElementById('stepExplanationText');
            if (exp) exp.textContent = 'Topology changed. Stale routes cleared. Click "Run Simulation" to compute updated paths under current link states.';
            const btnNext = document.getElementById('btnNextStep');
            const btnPrev = document.getElementById('btnPrevStep');
            if (btnNext) btnNext.disabled = true;
            if (btnPrev) btnPrev.disabled = true;
        }

        this.syncDropdowns();
        this.saveToLocalStorage();

        if (logMessage) {
            this.log(logType.toUpperCase(), logMessage);
        }
    },

    /**
     * Callback invoked when a router node has been dragged to a new position.
     */
    onNodeMoved(nodeId, x, y) {
        this.saveToLocalStorage();
    },

    /**
     * Selection callbacks from SVG Topology canvas.
     */
    onNodeSelected(nodeId) {
        if (!window.Topology) return;
        const node = window.Topology.nodes.get(nodeId);
        if (!node) return;

        const renameSel = document.getElementById('renameRouterSelect');
        const renameInput = document.getElementById('renameRouterNewName');
        const removeSel = document.getElementById('removeRouterSelect');

        if (renameSel) renameSel.value = nodeId;
        if (renameInput) renameInput.value = node.label || node.id;
        if (removeSel) removeSel.value = nodeId;
    },

    onLinkSelected(linkId) {
        if (!window.Topology) return;
        const link = window.Topology.links.find(l => l.id === linkId);
        if (!link) return;

        const editSel = document.getElementById('editLinkCostSelect');
        const editCost = document.getElementById('editLinkCostNewValue');
        const removeSel = document.getElementById('removeLinkSelect');
        const failSel = document.getElementById('failureLinkSelect');

        if (editSel) editSel.value = linkId;
        if (editCost) editCost.value = link.cost;
        if (removeSel) removeSel.value = linkId;
        if (failSel) failSel.value = linkId;
    },

    onConnectingSourceSelected(nodeId) {
        const text = document.getElementById('canvasModeText');
        if (text) {
            text.innerHTML = `<strong>Connecting:</strong> Router <strong>${nodeId}</strong> selected. Now click the destination router to connect.`;
        }
    },

    onSelectionCleared() {
        // Selection cleared on empty canvas click
    },

    /**
     * Modal Dialog Controllers
     */
    openRouterModal(mode = 'add', nodeId = null) {
        this.modalRouterMode = mode;
        this.editingRouterId = nodeId;

        const dialog = document.getElementById('modalRouterDialog');
        const title = document.getElementById('modalRouterTitle');
        const idGroup = document.getElementById('groupModalRouterId');
        const idInput = document.getElementById('modalRouterIdInput');
        const labelInput = document.getElementById('modalRouterLabelInput');
        const confirmBtn = document.getElementById('btnModalRouterConfirm');

        if (!dialog) return;

        if (mode === 'add') {
            if (title) title.textContent = 'Add Router Node';
            if (idGroup) idGroup.style.display = 'block';
            if (idInput) {
                idInput.value = window.Topology ? window.Topology.autoGenerateRouterId() : '';
                idInput.readOnly = false;
            }
            if (labelInput) labelInput.value = '';
            if (confirmBtn) confirmBtn.textContent = 'Add Router';
        } else {
            const node = window.Topology ? window.Topology.nodes.get(nodeId) : null;
            if (title) title.textContent = `Rename Router ${nodeId}`;
            if (idGroup) idGroup.style.display = 'none';
            if (labelInput) labelInput.value = node ? (node.label || node.id) : '';
            if (confirmBtn) confirmBtn.textContent = 'Update Router';
        }

        dialog.style.display = 'flex';
        setTimeout(() => {
            if (labelInput) labelInput.focus();
        }, 50);
    },

    closeRouterModal() {
        const dialog = document.getElementById('modalRouterDialog');
        if (dialog) dialog.style.display = 'none';
    },

    promptConnectCost(src, dst) {
        this.modalCostMode = 'connect';
        this.connectingEndpoints = { source: src, target: dst };

        const dialog = document.getElementById('modalCostDialog');
        const title = document.getElementById('modalCostTitle');
        const text = document.getElementById('modalCostEndpointsText');
        const input = document.getElementById('modalCostInput');
        const confirmBtn = document.getElementById('btnModalCostConfirm');

        if (!dialog) return;

        const linkId = window.Topology ? window.Topology.generateLinkId(src, dst) : `${src}-${dst}`;
        const existing = window.Topology ? window.Topology.links.find(l => l.id === linkId) : null;

        if (title) title.textContent = existing ? 'Update Link Weight' : 'Connect Routers';
        if (text) text.innerHTML = `Set transmission metric / cost between <strong>Router ${src}</strong> &harr; <strong>Router ${dst}</strong>:`;
        if (input) input.value = existing ? existing.cost : 5;
        if (confirmBtn) confirmBtn.textContent = existing ? 'Update Link' : 'Create Link';

        dialog.style.display = 'flex';
        setTimeout(() => {
            if (input) { input.focus(); input.select(); }
        }, 50);
    },

    openEditCostModal(linkId) {
        if (!window.Topology) return;
        const link = window.Topology.links.find(l => l.id === linkId);
        if (!link) {
            this.toast(`Link ${linkId} not found.`, 'warning');
            return;
        }

        this.modalCostMode = 'edit';
        this.editingLinkId = linkId;

        const dialog = document.getElementById('modalCostDialog');
        const title = document.getElementById('modalCostTitle');
        const text = document.getElementById('modalCostEndpointsText');
        const input = document.getElementById('modalCostInput');
        const confirmBtn = document.getElementById('btnModalCostConfirm');

        if (!dialog) return;

        if (title) title.textContent = 'Edit Link Cost';
        if (text) text.innerHTML = `Configure transmission metric for link <strong>${link.source} &harr; ${link.target}</strong>:`;
        if (input) input.value = link.cost;
        if (confirmBtn) confirmBtn.textContent = 'Save Cost';

        dialog.style.display = 'flex';
        setTimeout(() => {
            if (input) { input.focus(); input.select(); }
        }, 50);
    },

    closeCostModal() {
        const dialog = document.getElementById('modalCostDialog');
        if (dialog) dialog.style.display = 'none';
    },

    /**
     * File Export & Import Operations
     */
    exportTopologyJSON() {
        if (!window.Topology) return;
        const exportData = {
            version: "1.0",
            appName: "Intelligent Network Routing Simulator",
            exportedAt: new Date().toISOString(),
            nodes: Array.from(window.Topology.nodes.values()),
            links: window.Topology.links.map(l => ({
                source: l.source,
                target: l.target,
                cost: l.cost,
                status: l.status
            }))
        };

        const jsonStr = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `network-topology-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.toast('Topology exported to JSON file.', 'success');
        this.log('SUCCESS', `Exported topology configuration with ${exportData.nodes.length} routers and ${exportData.links.length} links.`);
    },

    async importTopologyJSON(file) {
        if (!file) return;
        try {
            const text = await file.text();
            const data = JSON.parse(text);

            if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.links)) {
                throw new Error('Invalid topology file: must contain "nodes" and "links" arrays.');
            }

            for (const n of data.nodes) {
                if (!n.id && !n.label) {
                    throw new Error('Invalid node definition: missing router identifier.');
                }
            }
            for (const l of data.links) {
                if (!l.source || !l.target) {
                    throw new Error('Invalid link definition: missing source or target endpoint.');
                }
                const cost = parseInt(l.cost, 10);
                if (isNaN(cost) || cost <= 0) {
                    throw new Error(`Invalid cost "${l.cost}" for link ${l.source} - ${l.target}: must be positive integer.`);
                }
            }

            this.resetSimulationState();
            window.Topology.loadGraph(data.nodes, data.links);
            this.saveToLocalStorage();
            this.toast(`Imported topology (${data.nodes.length} routers, ${data.links.length} links).`, 'success');
            this.log('SUCCESS', `Imported custom topology from "${file.name}" with ${data.nodes.length} routers and ${data.links.length} links.`);
        } catch (err) {
            console.error('Import error:', err);
            this.toast(`Import failed: ${err.message}`, 'error');
            this.log('ERROR', `Failed to import topology JSON: ${err.message}`);
        }
    },

    /**
     * LocalStorage Caching
     */
    saveToLocalStorage() {
        if (!window.Topology) return;
        try {
            const data = {
                nodes: Array.from(window.Topology.nodes.values()),
                links: window.Topology.links
            };
            localStorage.setItem('inrs_topology_cache', JSON.stringify(data));
        } catch (e) {
            // ignore localStorage quota errors
        }
    },

    loadFromLocalStorage() {
        try {
            const raw = localStorage.getItem('inrs_topology_cache');
            if (raw) {
                const data = JSON.parse(raw);
                if (data && Array.isArray(data.nodes) && data.nodes.length > 0) {
                    return data;
                }
            }
        } catch (e) {
            // ignore
        }
        return null;
    },

    /**
     * Synchronize all select dropdowns, metrics, and badges across the UI.
     */
    syncDropdowns() {
        if (!window.Topology) return;

        const nodes = Array.from(window.Topology.nodes.values());
        const links = window.Topology.links;

        // 1. Update Badges
        const nodeBadge = document.getElementById('nodeCountBadge');
        const linkBadge = document.getElementById('linkCountBadge');
        const failedBadge = document.getElementById('failedCountBadge');

        const failedLinks = links.filter(l => l.status === 'failed');

        if (nodeBadge) nodeBadge.textContent = nodes.length;
        if (linkBadge) linkBadge.textContent = links.length;
        if (failedBadge) failedBadge.textContent = failedLinks.length;

        // 2. Sync Router Selects
        const sourceSelect = document.getElementById('sourceRouterSelect');
        const destSelect = document.getElementById('destRouterSelect');
        const removeRouterSelect = document.getElementById('removeRouterSelect');
        const renameRouterSelect = document.getElementById('renameRouterSelect');
        const renameRouterNewName = document.getElementById('renameRouterNewName');
        const linkSourceSelect = document.getElementById('linkSourceSelect');
        const linkTargetSelect = document.getElementById('linkTargetSelect');
        const routingTableFilter = document.getElementById('routingTableRouterSelect');

        if (nodes.length === 0) {
            // Useful empty state when zero routers exist
            if (sourceSelect) sourceSelect.innerHTML = '<option value="" disabled selected>No routers available</option>';
            if (destSelect) destSelect.innerHTML = '<option value="" disabled selected>No routers available</option>';
            if (removeRouterSelect) removeRouterSelect.innerHTML = '<option value="" disabled selected>No routers available</option>';
            if (renameRouterSelect) renameRouterSelect.innerHTML = '<option value="" disabled selected>No routers available</option>';
            if (renameRouterNewName) renameRouterNewName.value = '';
            if (linkSourceSelect) linkSourceSelect.innerHTML = '<option value="" disabled selected>No routers</option>';
            if (linkTargetSelect) linkTargetSelect.innerHTML = '<option value="" disabled selected>No routers</option>';
            if (routingTableFilter) routingTableFilter.innerHTML = '<option value="">All Routers</option>';
            window.Topology.sourceNodeId = null;
            window.Topology.destNodeId = null;
        } else {
            // Populate Source Router
            if (sourceSelect) {
                const prevSource = sourceSelect.value;
                sourceSelect.innerHTML = '';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    sourceSelect.appendChild(opt);
                });

                if (window.Topology.sourceNodeId && nodes.some(n => n.id === window.Topology.sourceNodeId)) {
                    sourceSelect.value = window.Topology.sourceNodeId;
                } else if (nodes.some(n => n.id === prevSource)) {
                    sourceSelect.value = prevSource;
                } else {
                    sourceSelect.value = nodes[0].id;
                }
                window.Topology.sourceNodeId = sourceSelect.value;
            }

            // Populate Destination Router
            if (destSelect) {
                const prevDest = destSelect.value;
                destSelect.innerHTML = '';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    destSelect.appendChild(opt);
                });

                if (window.Topology.destNodeId && nodes.some(n => n.id === window.Topology.destNodeId)) {
                    destSelect.value = window.Topology.destNodeId;
                } else if (nodes.some(n => n.id === prevDest)) {
                    destSelect.value = prevDest;
                } else if (nodes.length > 1) {
                    const candidate = nodes.find(n => n.id !== window.Topology.sourceNodeId);
                    destSelect.value = candidate ? candidate.id : nodes[1].id;
                } else {
                    destSelect.value = nodes[0].id;
                }
                window.Topology.destNodeId = destSelect.value;
            }

            // Populate Remove Router Select
            if (removeRouterSelect) {
                const prevRemove = removeRouterSelect.value;
                removeRouterSelect.innerHTML = '';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    removeRouterSelect.appendChild(opt);
                });
                if (nodes.some(n => n.id === prevRemove)) {
                    removeRouterSelect.value = prevRemove;
                }
            }

            // Populate Rename Router Select
            if (renameRouterSelect) {
                const prevRename = renameRouterSelect.value;
                renameRouterSelect.innerHTML = '';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    renameRouterSelect.appendChild(opt);
                });
                if (nodes.some(n => n.id === prevRename)) {
                    renameRouterSelect.value = prevRename;
                } else {
                    renameRouterSelect.value = nodes[0].id;
                }
                if (renameRouterNewName) {
                    const curNode = nodes.find(n => n.id === renameRouterSelect.value);
                    if (curNode) renameRouterNewName.value = curNode.label || curNode.id;
                }
            }

            // Populate Link Endpoints Editor Selects
            if (linkSourceSelect) {
                const prevLinkSrc = linkSourceSelect.value;
                linkSourceSelect.innerHTML = '';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    linkSourceSelect.appendChild(opt);
                });
                if (nodes.some(n => n.id === prevLinkSrc)) {
                    linkSourceSelect.value = prevLinkSrc;
                }
            }

            if (linkTargetSelect) {
                const prevLinkTgt = linkTargetSelect.value;
                linkTargetSelect.innerHTML = '';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    linkTargetSelect.appendChild(opt);
                });
                if (nodes.some(n => n.id === prevLinkTgt)) {
                    linkTargetSelect.value = prevLinkTgt;
                } else if (nodes.length > 1) {
                    linkTargetSelect.value = nodes[1].id;
                }
            }

            // Populate Routing Table Router Filter
            if (routingTableFilter) {
                const prevFilter = routingTableFilter.value;
                routingTableFilter.innerHTML = '<option value="">All Routers</option>';
                nodes.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.id;
                    opt.textContent = `Router ${n.label || n.id}`;
                    routingTableFilter.appendChild(opt);
                });
                if (nodes.some(n => n.id === prevFilter)) {
                    routingTableFilter.value = prevFilter;
                }
            }
        }

        // 3. Sync Link Selects (Target Link, Remove Link, and Edit Cost)
        const linkSelects = [
            document.getElementById('removeLinkSelect'),
            document.getElementById('failureLinkSelect'),
            document.getElementById('editLinkCostSelect')
        ];

        linkSelects.forEach(select => {
            if (!select) return;
            const currentVal = select.value;
            select.innerHTML = '';

            if (links.length === 0) {
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = 'No links available';
                emptyOpt.disabled = true;
                emptyOpt.selected = true;
                select.appendChild(emptyOpt);
                return;
            }

            links.forEach(l => {
                const opt = document.createElement('option');
                opt.value = l.id;
                opt.textContent = `${l.source} — ${l.target} (Cost: ${l.cost})${l.status === 'failed' ? ' [FAILED]' : ''}`;
                select.appendChild(opt);
            });

            if (links.some(l => l.id === currentVal)) {
                select.value = currentVal;
            } else {
                select.value = links[0].id;
            }
        });

        // Sync edit link cost input
        const editCostInput = document.getElementById('editLinkCostNewValue');
        const editSelect = document.getElementById('editLinkCostSelect');
        if (editCostInput && editSelect && links.length > 0) {
            const curLink = links.find(l => l.id === editSelect.value);
            if (curLink) editCostInput.value = curLink.cost;
        }

        // 4. Update Failed Links List Container
        const failedContainer = document.getElementById('failedLinksContainer');
        if (failedContainer) {
            failedContainer.innerHTML = '';
            if (failedLinks.length === 0) {
                failedContainer.innerHTML = '<span class="text-muted">No links currently failed</span>';
            } else {
                failedLinks.forEach(fl => {
                    const chip = document.createElement('div');
                    chip.className = 'failed-link-chip';
                    chip.innerHTML = `<span>${fl.source}&harr;${fl.target}</span> <button class="chip-remove-btn" title="Recover link">&times;</button>`;
                    chip.querySelector('.chip-remove-btn').addEventListener('click', () => {
                        window.Topology.toggleLinkStatus(fl.id);
                    });
                    failedContainer.appendChild(chip);
                });
            }
        }
    },

    /**
     * Handle Run Simulation button click.
     */
    async handleRunSimulationClick() {
        const source = document.getElementById('sourceRouterSelect').value;
        const dest = document.getElementById('destRouterSelect').value;
        const algo = document.getElementById('algorithmSelect').value;

        if (!source || !dest) {
            this.toast('Please select both a Source and a Destination router.', 'error');
            return;
        }

        if (source === dest) {
            this.toast('Source and Destination are the same router (Cost: 0, Hops: 0).', 'info');
        }

        this.currentAlgorithm = algo;

        if (algo === 'dijkstra') {
            await this.runDijkstraSimulation(source, dest);
        } else if (algo === 'distance_vector') {
            await this.runDistanceVectorSimulation(source, dest);
        }
    },

    /**
     * Dispatch Dijkstra simulation request to Flask backend API.
     */
    async runDijkstraSimulation(source, destination) {
        if (!window.Topology) return;

        const payload = {
            nodes: Array.from(window.Topology.nodes.values()).map(n => ({ id: n.id })),
            edges: window.Topology.links.map(l => ({
                source: l.source,
                target: l.target,
                cost: l.cost,
                active: (l.status === 'active')
            })),
            source: source,
            destination: destination
        };

        this.log('SIM', `Requesting Dijkstra route calculation for ${source} &rarr; ${destination}...`);
        document.getElementById('resultStatus').textContent = 'Computing...';

        try {
            const response = await fetch('/api/dijkstra', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok || data.status === 'error') {
                throw new Error(data.message || `Server returned HTTP ${response.status}`);
            }

            this.lastSourceRouter = source;
            this.activeRoutingTable = data.routing_table || [];
            this.allRouterTables = null;
            this.simulationSteps = data.steps || [];
            this.currentStepIndex = -1;

            if (data.reachable && data.path && data.path.length > 0) {
                window.Topology.setHighlightedRoute(data.path);
                document.getElementById('resultStatus').textContent = 'Optimal Route Found';
                document.getElementById('resultPath').textContent = data.path.join(' ➔ ');
                document.getElementById('resultCost').textContent = data.total_cost !== null ? data.total_cost : '—';
                document.getElementById('resultHops').textContent = data.hop_count;

                this.log('SUCCESS', `Dijkstra computed path ${data.path.join(' -> ')} (Cost: ${data.total_cost}, Hops: ${data.hop_count})`);
                this.toast(`Optimal Path Found: ${data.path.join(' ➔ ')} (Cost: ${data.total_cost})`, 'success');
            } else {
                window.Topology.setHighlightedRoute([]);
                document.getElementById('resultStatus').textContent = 'Destination Unreachable';
                document.getElementById('resultPath').textContent = 'No Path Available';
                document.getElementById('resultCost').textContent = 'Infinity';
                document.getElementById('resultHops').textContent = '0';

                this.log('WARN', `Router ${destination} is unreachable from ${source} under active topology.`);
                this.toast(`Router ${destination} is unreachable from ${source}.`, 'warning');
            }

            this.renderRoutingTable(document.getElementById('routingTableRouterSelect').value);

            const btnNext = document.getElementById('btnNextStep');
            const btnPrev = document.getElementById('btnPrevStep');
            if (this.simulationSteps.length > 0) {
                if (btnNext) btnNext.disabled = false;
                if (btnPrev) btnPrev.disabled = true;
                this.applyStep(0);
            }

        } catch (err) {
            console.error('Dijkstra API Error:', err);
            this.log('ERROR', `Dijkstra API failure: ${err.message}`);
            this.toast(`Simulation failed: ${err.message}`, 'error');
            document.getElementById('resultStatus').textContent = 'Calculation Error';
            document.getElementById('stepExplanationText').textContent = `Error: ${err.message}`;
        }
    },

    /**
     * Dispatch Distance Vector simulation request to Flask backend API.
     */
    async runDistanceVectorSimulation(source, destination) {
        if (!window.Topology) return;

        const payload = {
            nodes: Array.from(window.Topology.nodes.values()).map(n => ({ id: n.id })),
            edges: window.Topology.links.map(l => ({
                source: l.source,
                target: l.target,
                cost: l.cost,
                active: (l.status === 'active')
            })),
            source: source,
            destination: destination
        };

        this.log('SIM', `Requesting Distance-Vector Bellman-Ford simulation for network...`);
        document.getElementById('resultStatus').textContent = 'Simulating Rounds...';

        try {
            const response = await fetch('/api/distance-vector', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok || data.status === 'error') {
                throw new Error(data.message || `Server returned HTTP ${response.status}`);
            }

            this.lastSourceRouter = source;
            this.allRouterTables = data.final_tables || {};
            this.activeRoutingTable = data.routing_table || [];
            this.simulationSteps = data.rounds || [];
            this.currentStepIndex = -1;

            // Update Status Metric
            if (data.converged) {
                document.getElementById('resultStatus').textContent = `Converged in ${data.total_rounds} Round(s)`;
                this.log('SUCCESS', `Distance-Vector protocol converged in ${data.total_rounds} rounds.`);
            } else {
                document.getElementById('resultStatus').textContent = `Non-converged (Max Rounds Limit)`;
                this.log('WARN', `Distance-Vector simulation hit iteration limit without full convergence.`);
            }

            // Path highlighting
            if (data.reachable && data.path && data.path.length > 0) {
                window.Topology.setHighlightedRoute(data.path);
                document.getElementById('resultPath').textContent = data.path.join(' ➔ ');
                document.getElementById('resultCost').textContent = data.total_cost !== null ? data.total_cost : '—';
                document.getElementById('resultHops').textContent = data.hop_count;
                this.toast(`Distance Vector Path: ${data.path.join(' ➔ ')} (Cost: ${data.total_cost})`, 'success');
            } else {
                window.Topology.setHighlightedRoute([]);
                document.getElementById('resultPath').textContent = destination ? 'No Path Available' : '—';
                document.getElementById('resultCost').textContent = destination ? 'Infinity' : '—';
                document.getElementById('resultHops').textContent = '0';
            }

            // Render Routing Table
            this.renderRoutingTable(document.getElementById('routingTableRouterSelect').value);

            // Enable Step Controls for Rounds
            const btnNext = document.getElementById('btnNextStep');
            const btnPrev = document.getElementById('btnPrevStep');
            if (this.simulationSteps.length > 0) {
                if (btnNext) btnNext.disabled = false;
                if (btnPrev) btnPrev.disabled = true;
                this.applyStep(0);
            }

        } catch (err) {
            console.error('Distance Vector API Error:', err);
            this.log('ERROR', `Distance-Vector API failure: ${err.message}`);
            this.toast(`Distance Vector failed: ${err.message}`, 'error');
            document.getElementById('resultStatus').textContent = 'Simulation Error';
            document.getElementById('stepExplanationText').textContent = `Error: ${err.message}`;
        }
    },

    /**
     * Advance to next algorithm execution step.
     */
    nextStep() {
        if (this.currentStepIndex < this.simulationSteps.length - 1) {
            this.applyStep(this.currentStepIndex + 1);
        }
    },

    /**
     * Return to previous algorithm execution step.
     */
    prevStep() {
        if (this.currentStepIndex > 0) {
            this.applyStep(this.currentStepIndex - 1);
        }
    },

    /**
     * Apply step trace state snapshot to UI explanation, counter, and live tables.
     */
    applyStep(index) {
        if (!this.simulationSteps || index < 0 || index >= this.simulationSteps.length) return;

        this.currentStepIndex = index;
        const step = this.simulationSteps[index];

        const stepCounter = document.getElementById('stepCounter');
        if (stepCounter) {
            if (this.currentAlgorithm === 'distance_vector') {
                stepCounter.textContent = `Round ${step.round} of ${this.simulationSteps.length - 1} (${step.type})`;
            } else {
                stepCounter.textContent = `Step ${index + 1} of ${this.simulationSteps.length}`;
            }
        }

        const explanationText = document.getElementById('stepExplanationText');
        if (explanationText) {
            explanationText.textContent = step.explanation;
        }

        // For Distance Vector: dynamically update the live table to match this specific round!
        if (this.currentAlgorithm === 'distance_vector' && step.tables) {
            this.allRouterTables = step.tables;
            const filter = document.getElementById('routingTableRouterSelect').value;
            this.renderRoutingTable(filter, step.updates);
        }

        // Step Canvas Visualizations
        if (window.Topology) {
            if (this.currentAlgorithm === 'dijkstra') {
                if (step.type === 'complete') {
                    window.Topology.setActiveStep(null, null);
                } else {
                    window.Topology.setActiveStep(step.current_node || null, step.edge || null);
                }
            } else {
                window.Topology.setActiveStep(null, null);
            }
        }

        // Update button states
        const btnNext = document.getElementById('btnNextStep');
        const btnPrev = document.getElementById('btnPrevStep');
        if (btnNext) btnNext.disabled = (index >= this.simulationSteps.length - 1);
        if (btnPrev) btnPrev.disabled = (index <= 0);
    },

    /**
     * Render routing tables for selected router filter with change highlighting.
     */
    renderRoutingTable(filterRouterId = '', highlightUpdates = []) {
        const table = document.getElementById('routingTableDisplay');
        const placeholder = document.getElementById('routingTablePlaceholder');
        const tbody = document.getElementById('routingTableBody');

        if (!tbody) return;

        // Collect changed router-destination keys for visual highlighting
        const changedKeys = new Set();
        if (Array.isArray(highlightUpdates)) {
            highlightUpdates.forEach(u => changedKeys.add(`${u.router}-${u.destination}`));
        }

        if (this.allRouterTables) {
            // Distance-Vector multi-router table mode
            tbody.innerHTML = '';
            const routersToRender = filterRouterId ? [filterRouterId] : Object.keys(this.allRouterTables).sort();

            routersToRender.forEach(rtr => {
                const entries = this.allRouterTables[rtr] || [];
                entries.forEach(row => {
                    const isChanged = changedKeys.has(`${rtr}-${row.destination}`);
                    const tr = document.createElement('tr');
                    if (isChanged) tr.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';

                    tr.innerHTML = `
                        <td><strong>${rtr}</strong></td>
                        <td>${row.destination}</td>
                        <td><strong>${row.cost !== null ? row.cost : '∞ (Inf)'}</strong></td>
                        <td>${row.next_hop || '-'}</td>
                        <td><span class="badge ${row.status === 'Direct' || row.status === 'Reachable' ? 'healthy' : 'offline'}">${row.status}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            });

            if (placeholder) placeholder.style.display = 'none';
            if (table) table.style.display = 'table';
            return;
        }

        // Single routing table mode (Dijkstra)
        if (!this.activeRoutingTable || this.activeRoutingTable.length === 0) {
            if (table) table.style.display = 'none';
            if (placeholder) {
                placeholder.style.display = 'block';
                placeholder.innerHTML = '<p class="text-muted">Run simulation to view computed routing table entries.</p>';
            }
            return;
        }

        let filtered = this.activeRoutingTable;
        if (filterRouterId) {
            filtered = this.activeRoutingTable.filter(r => r.destination === filterRouterId);
        }

        tbody.innerHTML = '';
        filtered.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${this.lastSourceRouter || 'Source'}</strong></td>
                <td>${row.destination}</td>
                <td>${row.cost !== null ? row.cost : '∞ (Inf)'}</td>
                <td>${row.next_hop || '-'}</td>
                <td><span class="badge ${row.status === 'Direct' || row.status === 'Reachable' ? 'healthy' : 'offline'}">${row.status}</span></td>
            `;
            tbody.appendChild(tr);
        });

        if (placeholder) placeholder.style.display = 'none';
        if (table) table.style.display = 'table';
    },

    /**
     * Append message to network event log with timestamp.
     */
    log(tag, message) {
        const logEntries = document.getElementById('eventLogEntries');
        if (!logEntries) return;

        const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const tagClass = `tag-${tag.toLowerCase()}`;
        entry.innerHTML = `<span class="log-time">[${timeStr}]</span> <span class="log-tag ${tagClass}">[${tag}]</span> <span class="log-msg">${message}</span>`;

        logEntries.appendChild(entry);
        const container = document.getElementById('eventLogContainer');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    },

    /**
     * Show non-blocking toast alert in top-right corner.
     */
    toast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
};

window.App = App;

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

