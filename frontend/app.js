// ==========================================
// CONFIG
// ==========================================
const API_BASE = window.TRAFFIC_ROUTE_API_BASE || "http://localhost:8000";
let GOONG_MAP_KEY = "";

// ==========================================
// STATE
// ==========================================
/**

 * @typedef {Object} AppState
 * @property {Object|null} map - Goong GL JS map instance


 * @property {number|null} animationTimer - Timer cho animation
 * @property {number} animationStep - Current animation step



 * @property {Object|null} graphData - Graph data (nodes and edges)


 * @property {Object} pendingResults - Results waiting to be displayed
 */
let state = {
  map: null,
  markers: {},
  polylines: {},
  animationTimer: null,
  animationStep: 0,
  animationLog: [],
  isPaused: false,
  isAnimating: false,
  graphData: null,
  nodesData: [],
  nodeFeatures: {},
  foodFeatures: [],
  selectedWaypoints: new Set(),
  tspQueue: [],
  tspMode: "auto",
  draggedWaypointId: null,
  selectedEndpoints: { start: "", end: "" },
  edgeMetric: "congestion",
  selectedRouteInteractionsBound: false,
  searchGeneration: 0,
  pendingResults: { finalPath: null, stats: null, explanation: null },
  routeReview: { path: [], steps: [], activeIndex: -1 },
  comparisonMetrics: [],
  comparisonMetric: "total_cost",
};

// ==========================================
// MAP MANAGER (Goong GL JS)
// ==========================================

/**


 */
function hideGoongPoiIcons() {
  const layers = state.map.getStyle()?.layers || [];
  let hiddenCount = 0;

  layers
    .filter(
      (layer) =>
        layer.type === "symbol" &&
        layer.layout &&
        Object.prototype.hasOwnProperty.call(layer.layout, "icon-image"),
    )
    .forEach((layer) => {
      try {
        state.map.setPaintProperty(layer.id, "icon-opacity", 0);
        hiddenCount += 1;
      } catch (error) {
        console.warn(`[Map] Could not hide icon layer ${layer.id}:`, error);
      }
    });

  console.log(`[Map] Hid ${hiddenCount} Goong POI icon layers.`);
}

/**

 */
function initMap() {
  console.log("[Map] Initializing Goong GL JS map...");

  if (!GOONG_MAP_KEY) {
    showLoading(true, "GOONG_MAP_TILES_KEY is missing from the .env file.");
    return;
  }

  if (!goongjs.supported()) {
    showLoading(true, "This browser does not support Goong GL JS.");
    return;
  }

  goongjs.accessToken = GOONG_MAP_KEY;
  state.map = new goongjs.Map({
    container: "map",
    style: "https://tiles.goong.io/assets/goong_map_web.json",
    center: [106.698, 10.783], // Goong uses [lng, lat].
    zoom: 21,
    minZoom: 10,
    maxZoom: 31,
    attributionControl: false,
  });

  state.map.addControl(new goongjs.NavigationControl(), "top-right");
  state.map.on("load", () => {
    console.log("[Map] Goong GL JS map is ready.");
    hideGoongPoiIcons();
    showLoading(true, "Loading graph data...");
    loadGraph()
      .then(() => populateDropdowns())
      .finally(() => showLoading(false));
  });
}

/**

 * @param {number} congestion - Congestion level from 1 to 10.

 */
const EDGE_METRIC_CONFIG = {
  congestion: {
    low: "Free-flowing",
    high: "Congested",
    colors: ["#16a34a", "#facc15", "#f97316", "#ef4444"],
  },
  risk: {
    low: "Low risk",
    high: "High risk",
    colors: ["#16a34a", "#facc15", "#f97316", "#ef4444"],
  },
};

function edgeMetricExpression() {
  const property = state.edgeMetric === "risk" ? "risk" : "congestion";
  return [
    "step", ["coalesce", ["get", property], 0],
    EDGE_METRIC_CONFIG[property].colors[0], 3,
    EDGE_METRIC_CONFIG[property].colors[1], 6,
    EDGE_METRIC_CONFIG[property].colors[2], 8,
    EDGE_METRIC_CONFIG[property].colors[3],
  ];
}

function updateEdgeLegend() {
  const config = EDGE_METRIC_CONFIG[state.edgeMetric] || EDGE_METRIC_CONFIG.congestion;
  const scale = document.getElementById("edge-scale");
  const low = document.getElementById("edge-low-label");
  const high = document.getElementById("edge-high-label");
  if (scale) scale.style.background = `linear-gradient(90deg, ${config.colors.join(", ")})`;
  if (low) low.textContent = config.low;
  if (high) high.textContent = config.high;
}
function getCongestionColor(congestion) {
  if (congestion <= 3) return "#22c55e";
  if (congestion <= 6) return "#f59e0b";
  return "#ef4444";
}

/**



 */
function renderEdges(edges, nodes) {
  const features = [];
  const seenDirected = new Set();

  for (const edge of edges) {
    const fromNode = nodes[edge.from];
    const toNode = nodes[edge.to];
    if (!fromNode || !toNode) continue;

    const direction = String(edge.direction || edge.road_type || edge.one_way || "").toLowerCase();
    const isOneWay = direction.includes("one_way") || direction.includes("one-way") || edge.bidirectional === false;
    const directedKey = `${edge.from}->${edge.to}`;
    if (seenDirected.has(directedKey)) continue;
    seenDirected.add(directedKey);

    features.push({
      type: "Feature",
      properties: {
        edgeId: edge.id || directedKey,
        from: String(edge.from),
        to: String(edge.to),
        direction: isOneWay ? "one-way" : "two-way",
        congestion: Number(edge.congestion ?? edge.congestion_level ?? edge.traffic ?? 0),
        risk: Number(edge.risk ?? edge.risk_factor ?? edge.risk_score ?? 0),
        distance: Number(edge.distance ?? edge.distance_km ?? 0),
        time: Number(edge.time ?? edge.travel_time ?? edge.time_min ?? 0),
      },
      geometry: {
        type: "LineString",
        coordinates: [
          [fromNode.lng, fromNode.lat],
          [toNode.lng, toNode.lat],
        ],
      },
    });
  }

  state.map.addSource("graph-edges", {
    type: "geojson",
    data: { type: "FeatureCollection", features },
  });
  state.map.addLayer({
    id: "graph-edges-casing",
    type: "line",
    source: "graph-edges",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": "#ffffff",
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 4, 16, 7, 20, 10],
      "line-opacity": 0.92,
      "line-offset": ["interpolate", ["linear"], ["zoom"], 12, 0.7, 20, 1.4],
    },
  });
  state.map.addLayer({
    id: "graph-edges-layer",
    type: "line",
    source: "graph-edges",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": edgeMetricExpression(),
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 2, 16, 4, 20, 6],
      "line-opacity": 0.9,
      "line-offset": ["interpolate", ["linear"], ["zoom"], 12, 0.7, 20, 1.4],
    },
  });
  state.map.addLayer({
    id: "graph-edges-arrows",
    type: "symbol",
    source: "graph-edges",
    filter: ["==", ["get", "direction"], "one-way"],
    layout: {
      "symbol-placement": "line",
      "symbol-spacing": 70,
      "text-field": "\u25b6",
      "text-size": ["interpolate", ["linear"], ["zoom"], 12, 10, 18, 14],
      "text-keep-upright": false,
      "text-allow-overlap": true,
      "text-offset": [0, -0.2],
    },
    paint: {
      "text-color": edgeMetricExpression(),
      "text-halo-color": "#ffffff",
      "text-halo-width": 1.2,
    },
  });

  state.map.on("click", "graph-edges-layer", (event) => {
    const edge = event.features?.[0]?.properties;
    if (!edge) return;
    const metric = state.edgeMetric === "risk" ? edge.risk : edge.congestion;
    new goongjs.Popup({ closeButton: true, closeOnClick: true })
      .setLngLat(event.lngLat)
      .setHTML(`<strong>${edge.direction === "one-way" ? "One-way road" : "Two-way road"}</strong><br>${state.edgeMetric}: ${Number(metric).toFixed(1)}`)
      .addTo(state.map);
  });
  state.map.on("mouseenter", "graph-edges-layer", () => { state.map.getCanvas().style.cursor = "pointer"; });
  state.map.on("mouseleave", "graph-edges-layer", () => { state.map.getCanvas().style.cursor = ""; });
}
function renderNodes(nodes) {
  const features = [];
  state.nodeFeatures = {};
  for (const [id, node] of Object.entries(nodes)) {
    const feature = {
      type: "Feature",
      id,
      properties: {
        nodeId: id,
        type: node.type || "intersection",
        status: "reset",
        name: node.name || `Node ${id}`,
        address: node.address || "",
        source: node.source || "",
      },
      geometry: { type: "Point", coordinates: [node.lng, node.lat] },
    };
    features.push(feature);
    state.nodeFeatures[id] = feature;
  }

  state.map.addSource("graph-nodes", {
    type: "geojson",
    data: { type: "FeatureCollection", features },
  });
  state.map.addLayer({
    id: "graph-nodes-layer",
    type: "circle",
    source: "graph-nodes",
    paint: {
      "circle-radius": 6,
      "circle-color": [
        "match", ["get", "status"],
        "frontier", "#facc15",
        "visited", "#16a34a",
        "current", "#ef4444",
        "optimal", "#1769f9",
        ["match", ["get", "type"], "food", "#f97316", "#ffffff"],
      ],
      "circle-stroke-color": [
        "match", ["get", "status"],
        "frontier", "#a16207",
        "visited", "#166534",
        "current", "#b91c1c",
        "optimal", "#0b4fbd",
        ["match", ["get", "type"], "food", "#c2410c", "#000000"],
      ],
      "circle-stroke-width": 2,
    },
  });

  state.map.on("click", "graph-nodes-layer", (event) => {
    const node = event.features?.[0]?.properties;
    if (!node) return;
    const address = node.address ? `<br>${node.address}` : "";
    new goongjs.Popup({ closeButton: true, closeOnClick: true })
      .setLngLat(event.lngLat)
      .setHTML(`<strong>${node.name}</strong>${address}`)
      .addTo(state.map);
  });
  state.map.on("mouseenter", "graph-nodes-layer", () => { state.map.getCanvas().style.cursor = "pointer"; });
  state.map.on("mouseleave", "graph-nodes-layer", () => { state.map.getCanvas().style.cursor = ""; });
}

function refreshNodeSource() {
  if (!state.map.getSource("graph-nodes")) return;
  state.map.getSource("graph-nodes").setData({
    type: "FeatureCollection",
    features: Object.values(state.nodeFeatures),
  });
}

/**


 */
function buildSelectedRouteFeatures() {
  if (!state.graphData) return [];
  const features = [];
  const isTsp = document.getElementById("algorithm-select")?.value === "tsp";
  const selectedStart = String(
    document.getElementById("start-select")?.value || state.selectedEndpoints.start || "",
  );
  const endpointSelection = {
    ...state.selectedEndpoints,
    start: selectedStart,
  };

  Object.entries(endpointSelection).forEach(([role, nodeId]) => {
    if (!nodeId || (isTsp && role === "end")) return;
    const node = state.graphData.nodes[String(nodeId)];
    if (!node) return;
    features.push({
      type: "Feature",
      properties: { role, label: role === "start" ? "S" : "E", nodeId: String(nodeId) },
      geometry: { type: "Point", coordinates: [node.lng, node.lat] },
    });
  });

  if (!isTsp) return features;
  state.tspQueue
    .map(String)
    .filter((nodeId) => nodeId !== selectedStart)
    .forEach((nodeId, index) => {
      const node = state.graphData.nodes[nodeId];
      if (!node) return;
      features.push({
        type: "Feature",
        properties: { role: "waypoint", label: String(index + 1), nodeId },
        geometry: { type: "Point", coordinates: [node.lng, node.lat] },
      });
    });
  return features;
}
function removeSelectedRouteLayers() {
  [
    "selected-route-start-arrow",
    "selected-route-labels",
    "selected-route-core",
    "selected-route-ring",
    "selected-route-outer",
  ].forEach((layerId) => {
    if (state.map?.getLayer(layerId)) state.map.removeLayer(layerId);
  });
  if (state.map?.getSource("selected-route-points")) state.map.removeSource("selected-route-points");
}

function renderEndpointLayers() {
  if (!state.map || !state.graphData) return;
  removeSelectedRouteLayers();
  const features = buildSelectedRouteFeatures();
  state.map.addSource("selected-route-points", {
    type: "geojson",
    data: { type: "FeatureCollection", features },
  });
  const selectedFilter = ["in", "role", "start", "end", "waypoint"];
  state.map.addLayer({
    id: "selected-route-outer",
    type: "circle",
    source: "selected-route-points",
    filter: selectedFilter,
    paint: {
      "circle-radius": 20,
      "circle-color": "#1769f9",
      "circle-opacity": 0,
      "circle-stroke-color": "#1769f9",
      "circle-stroke-width": 1,
      "circle-stroke-opacity": 0,
    },
  });
  state.map.addLayer({
    id: "selected-route-ring",
    type: "circle",
    source: "selected-route-points",
    filter: selectedFilter,
    paint: {
      "circle-radius": 12,
      "circle-color": "#ffffff",
      "circle-opacity": 0.94,
      "circle-stroke-color": "#1769f9",
      "circle-stroke-width": 2,
    },
  });
  state.map.addLayer({
    id: "selected-route-core",
    type: "circle",
    source: "selected-route-points",
    filter: selectedFilter,
    paint: {
      "circle-radius": 6,
      "circle-color": "#1769f9",
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
    },
  });
  state.map.addLayer({
    id: "selected-route-labels",
    type: "symbol",
    source: "selected-route-points",
    filter: selectedFilter,
    layout: {
      "text-field": ["get", "label"],
      "text-size": 16,
      "text-offset": [0, -1],
      "text-anchor": "bottom",
      "text-allow-overlap": true,
      "text-ignore-placement": true,
    },
    paint: {
      "text-color": "#ffffff",
      "text-halo-color": "#1769f9",
      "text-halo-width": 2.5,
      "text-halo-blur": 0,
    },
  });
  state.map.addLayer({
    id: "selected-route-start-arrow",
    type: "symbol",
    source: "selected-route-points",
    filter: ["==", ["get", "role"], "start"],
    layout: {
      "text-field": "\u25b2",
      "text-size": 9,
      "text-offset": [0, -1.45],
      "text-anchor": "bottom",
      "text-allow-overlap": true,
    },
    paint: {
      "text-color": "#1769f9",
      "text-halo-color": "#ffffff",
      "text-halo-width": 1.5,
    },
  });
  if (!state.selectedRouteInteractionsBound) {
    state.map.on("click", "selected-route-core", (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      const nodeId = feature.properties.nodeId;
      const node = state.nodesData.find((item) => String(item.id) === String(nodeId));
      if (!node) return;
      new goongjs.Popup({ closeButton: true, closeOnClick: true })
        .setLngLat(event.lngLat)
        .setHTML(`<strong>${escapeHtml(feature.properties.label)} &middot; ${escapeHtml(node.name)}</strong><br>${escapeHtml(node.address || "")}`)
        .addTo(state.map);
    });
    state.map.on("mouseenter", "selected-route-core", () => { state.map.getCanvas().style.cursor = "pointer"; });
    state.map.on("mouseleave", "selected-route-core", () => { state.map.getCanvas().style.cursor = ""; });
    state.selectedRouteInteractionsBound = true;
  }
}

function renderTspWaypointLabels() {
  if (!state.map || !state.graphData) return;
  renderEndpointLayers();
}

function initTspWaypointLayers() {
  renderTspWaypointLabels();
}
function updateSelectedEndpoints() {
  if (!state.map || !state.graphData) return;
  renderEndpointLayers();
}
function updateEndpointSelection(role, nodeId) {
  state.selectedEndpoints[role] = String(nodeId || "");
  clearSearchResults();
  const node = state.nodesData.find((item) => String(item.id) === String(nodeId));
  const summary = document.getElementById(`${role}-selection-summary`);
  if (summary) summary.textContent = node ? (node.address || node.name || "") : `Choose a place to ${role === "start" ? "start" : "finish"}.`;
  updateSelectedEndpoints();
  syncTspQueueFromSelection();
}
function constrainMapToGraph(nodes) {
  const coordinates = Object.values(nodes).map((node) => [node.lng, node.lat]);
  if (!coordinates.length) return;

  const longitudes = coordinates.map(([lng]) => lng);
  const latitudes = coordinates.map(([, lat]) => lat);
  const paddingLng = 0.02;
  const paddingLat = 0.02;
  const bounds = [
    [Math.min(...longitudes) - paddingLng, Math.min(...latitudes) - paddingLat],
    [Math.max(...longitudes) + paddingLng, Math.max(...latitudes) + paddingLat],
  ];

  state.map.setMaxBounds(bounds);
  state.map.fitBounds(bounds, { padding: 120, maxZoom: 23, duration: 0 });


  const fittedZoom = state.map.getZoom();
  const overviewZoom = Math.max(10, fittedZoom - 0.4);
  state.map.setMinZoom(8);
  state.map.setZoom(overviewZoom);
}


function renderFoodPlaces(places) {
  const features = places.slice(0, 40).map((place) => ({
    type: "Feature",
    properties: {
      name: place.name || "Food place",
      address: place.address || "",
    },
    geometry: { type: "Point", coordinates: [place.lng, place.lat] },
  }));
  state.foodFeatures = features;

  if (state.map.getLayer("food-places-layer")) {
    state.map.removeLayer("food-places-layer");
  }
  if (state.map.getSource("food-places")) {
    state.map.removeSource("food-places");
  }

  state.map.addSource("food-places", {
    type: "geojson",
    data: { type: "FeatureCollection", features },
  });
  state.map.addLayer({
    id: "food-places-layer",
    type: "circle",
    source: "food-places",
    paint: {
      "circle-radius": 6,
      "circle-color": "#f97316",
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
    },
  });

  state.map.on("click", "food-places-layer", (event) => {
    const place = event.features[0].properties;
    new goongjs.Popup({ closeButton: true, closeOnClick: true })
      .setLngLat(event.lngLat)
      .setHTML(`<strong>${place.name}</strong><br>${place.address}`)
      .addTo(state.map);
  });
}

/**

 * @param {string} nodeId - Node identifier

 */
function updateMarkerColor(nodeId, status) {
  const feature = state.nodeFeatures[nodeId];
  if (!feature) return;
  feature.properties.status = status;
  refreshNodeSource();
}

/**


 */
function highlightPath(path) {
  if (!path || path.length < 2) return;

  const coordinates = path
    .filter((nodeId) => state.graphData.nodes[nodeId])
    .map((nodeId) => {
      const node = state.graphData.nodes[nodeId];
      return [node.lng, node.lat];
    });

  if (state.map.getLayer("optimal-path-layer")) {
    state.map.removeLayer("optimal-path-layer");
  }
  if (state.map.getSource("optimal-path")) {
    state.map.removeSource("optimal-path");
  }

  state.map.addSource("optimal-path", {
    type: "geojson",
    data: {
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates },
    },
  });
  state.map.addLayer({
    id: "optimal-path-layer",
    type: "line",
    source: "optimal-path",
    paint: { "line-color": "#1769f9", "line-width": 6, "line-opacity": 0.95 },
  });

  path.forEach((nodeId) => updateMarkerColor(nodeId, "optimal"));
}

/**

 */
function resetVisualization() {
  for (const id in state.nodeFeatures) updateMarkerColor(id, "reset");
  if (state.map) {
    if (state.map.getLayer("optimal-path-layer")) state.map.removeLayer("optimal-path-layer");
    if (state.map.getSource("optimal-path")) state.map.removeSource("optimal-path");
    drawRouteReviewStep(null);
  }
  state.routeReview = { path: [], steps: [], activeIndex: -1 };
  const results = document.getElementById("results-panel"), metrics = document.getElementById("metrics-panel"), list = document.getElementById("route-step-list");
  if (results) results.style.display = "none";
  if (metrics) metrics.hidden = true;
  if (list) list.innerHTML = "";
  setResultsDrawerVisible(false);
  setCompareDrawerVisible(false);
}

// ==========================================
// ANIMATION ENGINE
// ==========================================

/**

 * @returns {number} Delay in milliseconds
 */
function getInterval() {
  const sliderVal = parseInt(document.getElementById("speed-slider").value);
  return Math.max(50, 1000 - (sliderVal - 1) * (950 / 99));
}

/**
 * Start the animation from the beginning.




 */
function startAnimation(animationLog, finalPath, stats, explanation) {
  resetVisualization();
  state.animationLog = animationLog;
  state.animationStep = 0;
  state.isAnimating = true;
  state.isPaused = false;
  state.pendingResults = { finalPath, stats, explanation };
  togglePlaybackControls(true);
  runAnimationStep();
}

/**
 * Advance the animation by one step.
 */
function runAnimationStep() {
  if (state.isPaused) return;
  if (state.animationStep >= state.animationLog.length) {
    finishAnimation();
    return;
  }
  const logEntry = state.animationLog[state.animationStep];
  updateMarkerColor(logEntry.node, logEntry.status);
  state.animationStep++;
  state.animationTimer = setTimeout(runAnimationStep, getInterval());
}

/**

 */
function finishAnimation() {
  state.isAnimating = false;
  togglePlaybackControls(false);
  const { finalPath, stats, explanation } = state.pendingResults;
  if (finalPath && finalPath.length > 0) {
    highlightPath(finalPath);
  }
  showResults(finalPath, stats, explanation);
}

/**


 */
function togglePlaybackControls(animating) {
  const btnStart = document.getElementById("btn-start");
  const playbackControls = document.querySelector(".playback-controls");
  if (animating) {
    btnStart.style.display = "none";
    playbackControls.style.display = "flex";
    document.getElementById("btn-pause").style.display = "flex";
    document.getElementById("btn-resume").style.display = "none";
  } else {
    btnStart.style.display = "flex";
    playbackControls.style.display = "none";
  }
}

function clearSearchResults() {
  state.searchGeneration += 1;
  clearTimeout(state.animationTimer);
  state.animationTimer = null;
  state.animationLog = [];
  state.animationStep = 0;
  state.isAnimating = false;
  state.isPaused = false;
  state.pendingResults = { finalPath: null, stats: null, explanation: null };
  togglePlaybackControls(false);
  resetVisualization();
}
// ==========================================
function initDrawerResizer(drawerId, handleId) {
  const drawer = document.getElementById(drawerId);
  const handle = document.getElementById(handleId);
  if (!drawer || !handle) return;
  let dragging = false;
  handle.addEventListener("pointerdown", (event) => {
    dragging = true;
    handle.setPointerCapture(event.pointerId);
    document.body.classList.add("is-resizing-panel");
  });
  handle.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const mapRect = document.querySelector(".map-container")?.getBoundingClientRect();
    if (!mapRect) return;
    const isCompareMode = drawer.classList.contains("is-compare-mode");
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    if (isCompareMode) {
      const height = Math.min(440, Math.max(230, mapRect.bottom - event.clientY));
      drawer.style.setProperty("--compare-panel-height", height + "px");
    } else if (!isMobile) {
      const width = Math.min(640, Math.max(300, mapRect.right - event.clientX));
      drawer.style.setProperty("--results-drawer-width", width + "px");
    }
    state.map?.resize();
  });
  const stop = () => {
    dragging = false;
    document.body.classList.remove("is-resizing-panel");
  };
  handle.addEventListener("pointerup", stop);
  handle.addEventListener("pointercancel", stop);
}
initDrawerResizer("results-drawer", "results-drawer-resizer");
initDrawerResizer("compare-drawer", "compare-drawer-resizer");

const resultsDrawerClose = document.getElementById("results-drawer-close");
resultsDrawerClose?.addEventListener("click", () => setResultsDrawerVisible(false));
const compareDrawerClose = document.getElementById("compare-drawer-close");
compareDrawerClose?.addEventListener("click", () => setCompareDrawerVisible(false));
const resultsDrawerToggle = document.getElementById("results-drawer-toggle");
resultsDrawerToggle?.addEventListener("click", () => {
  const drawer = document.getElementById("results-drawer");
  if (!drawer) return;
  if (drawer.classList.contains("is-collapsed")) {
    drawer.classList.remove("is-collapsed");
    drawer.classList.add("is-open");
    setCompareDrawerVisible(false);
  } else {
    drawer.classList.add("is-collapsed");
  }
  syncResultsDrawerToggle(drawer);
});
const compareDrawerToggle = document.getElementById("compare-drawer-toggle");
compareDrawerToggle?.addEventListener("click", () => {
  const drawer = document.getElementById("compare-drawer");
  const resultsDrawer = document.getElementById("results-drawer");
  if (!drawer) return;
  if (drawer.classList.contains("is-collapsed")) {
    drawer.classList.remove("is-collapsed");
    drawer.classList.add("is-open");
    if (resultsDrawer) {
      resultsDrawer.classList.add("is-collapsed");
      syncResultsDrawerToggle(resultsDrawer);
    }
  } else {
    drawer.classList.add("is-collapsed");
  }
  syncCompareDrawerToggle(drawer);
});
document.getElementById("route-step-prev")?.addEventListener("click", () => selectRouteReviewStep(state.routeReview.activeIndex - 1));
document.getElementById("route-step-next")?.addEventListener("click", () => selectRouteReviewStep(state.routeReview.activeIndex + 1));
document.addEventListener("keydown", (event) => {
  const drawer = document.getElementById("results-drawer");
  const tag = document.activeElement?.tagName;
  if (!drawer || drawer.hidden || drawer.classList.contains("is-collapsed") || ["INPUT", "SELECT", "TEXTAREA"].includes(tag)) return;
  if (event.key === "ArrowLeft") { event.preventDefault(); selectRouteReviewStep(state.routeReview.activeIndex - 1); }
  if (event.key === "ArrowRight") { event.preventDefault(); selectRouteReviewStep(state.routeReview.activeIndex + 1); }
});
// CONTROL PANEL
// ==========================================
document.getElementById("btn-pause").addEventListener("click", () => {
  state.isPaused = true;
  clearTimeout(state.animationTimer);
  document.getElementById("btn-pause").style.display = "none";
  document.getElementById("btn-resume").style.display = "flex";
});

document.getElementById("btn-resume").addEventListener("click", () => {
  state.isPaused = false;
  document.getElementById("btn-pause").style.display = "flex";
  document.getElementById("btn-resume").style.display = "none";
  runAnimationStep();
});

document.getElementById("btn-reset").addEventListener("click", () => {
  clearTimeout(state.animationTimer);
  state.isAnimating = false;
  state.isPaused = false;
  togglePlaybackControls(false);
  resetVisualization();
});

document.getElementById("speed-slider").addEventListener("input", () => {
  if (state.isAnimating && !state.isPaused) {
    clearTimeout(state.animationTimer);
    state.animationTimer = setTimeout(runAnimationStep, getInterval());
  }
});

/**

 */

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function syncDrawerToggle(drawer, toggleId, isCompareMode) {
  const toggle = document.getElementById(toggleId);
  if (!toggle || !drawer) return;
  const collapsed = drawer.classList.contains("is-collapsed");
  toggle.textContent = isCompareMode
    ? (collapsed ? "\u2191" : "\u2193")
    : (collapsed ? "\u2039" : "\u203a");
  toggle.setAttribute("aria-expanded", String(!collapsed));
  toggle.setAttribute("aria-label", collapsed ? "Open panel" : "Collapse panel");
}

function syncResultsDrawerToggle(drawer) {
  syncDrawerToggle(drawer, "results-drawer-toggle", false);
}

function syncCompareDrawerToggle(drawer) {
  syncDrawerToggle(drawer, "compare-drawer-toggle", true);
}
function setResultsDrawerVisible(visible) {
  const drawer = document.getElementById("results-drawer");
  if (!drawer) return;
  drawer.hidden = !visible;
  drawer.setAttribute("aria-hidden", String(!visible));
  if (visible) drawer.classList.remove("is-collapsed");
  drawer.classList.toggle("is-open", visible);
  syncResultsDrawerToggle(drawer);
}

function setCompareDrawerVisible(visible) {
  const drawer = document.getElementById("compare-drawer");
  const resultsDrawer = document.getElementById("results-drawer");
  if (!drawer) return;
  drawer.hidden = !visible;
  drawer.setAttribute("aria-hidden", String(!visible));
  if (visible) {
    drawer.classList.remove("is-collapsed");
    drawer.classList.add("is-open");
    if (resultsDrawer) {
      resultsDrawer.classList.add("is-collapsed");
      syncResultsDrawerToggle(resultsDrawer);
    }
  } else {
    drawer.classList.remove("is-open");
  }
  syncCompareDrawerToggle(drawer);
}
function getRouteNode(nodeId) { return state.graphData?.nodes?.[String(nodeId)] || null; }
function getRouteEdge(fromId, toId) {
  const edges = state.graphData?.edges || [];
  const direct = edges.find((edge) => String(edge.from) === String(fromId) && String(edge.to) === String(toId));
  if (direct) return { edge: direct, reversed: false };
  const reverse = edges.find((edge) => String(edge.from) === String(toId) && String(edge.to) === String(fromId));
  if (!reverse) return { edge: null, reversed: false };
  const direction = String(reverse.direction || reverse.road_type || reverse.one_way || "").toLowerCase();
  const oneWay = direction.includes("one_way") || direction.includes("one-way") || reverse.bidirectional === false;
  return oneWay ? { edge: null, reversed: false } : { edge: reverse, reversed: true };
}
function routeMetric(edge, keys) {
  if (!edge) return 0;
  for (const key of keys) if (edge[key] !== undefined && edge[key] !== null) return Number(edge[key]) || 0;
  return 0;
}
function buildRouteReview(path) {
  const ids = (path || []).map(String);
  return ids.slice(0, -1).map((fromId, index) => {
    const toId = ids[index + 1], from = getRouteNode(fromId), to = getRouteNode(toId), matched = getRouteEdge(fromId, toId), edge = matched.edge;
    return { index: index + 1, fromId, toId, fromName: from?.name || "Node " + fromId, toName: to?.name || "Node " + toId,
      distance: routeMetric(edge, ["distance", "distance_km"]), time: routeMetric(edge, ["time", "travel_time", "time_min"]),
      congestion: routeMetric(edge, ["congestion", "congestion_level", "traffic"]), risk: routeMetric(edge, ["risk", "risk_factor", "risk_score"]),
      direction: edge ? (matched.reversed ? "two-way / reverse direction" : "forward") : "No edge metadata" };
  });
}
function formatRouteMetric(value, suffix = "") { return Number(value || 0).toFixed(2) + suffix; }
function drawRouteReviewStep(step) {
  if (!state.map) return;
  const source = state.map.getSource("route-review-active-step");
  if (!step) {
    if (state.map.getLayer("route-review-active-step-layer")) state.map.removeLayer("route-review-active-step-layer");
    if (source) state.map.removeSource("route-review-active-step");
    return;
  }
  const from = getRouteNode(step.fromId), to = getRouteNode(step.toId);
  if (!from || !to) return;
  const data = { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[from.lng, from.lat], [to.lng, to.lat]] } };
  if (source) { source.setData(data); return; }
  state.map.addSource("route-review-active-step", { type: "geojson", data });
  state.map.addLayer({ id: "route-review-active-step-layer", type: "line", source: "route-review-active-step",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#22d3ee", "line-width": ["interpolate", ["linear"], ["zoom"], 12, 7, 18, 11], "line-opacity": 0.92 } });
}
function selectRouteReviewStep(index) {
  const steps = state.routeReview.steps;
  state.routeReview.activeIndex = steps.length ? Math.max(0, Math.min(index, steps.length - 1)) : -1;
  const active = steps[state.routeReview.activeIndex], counter = document.getElementById("route-step-counter"), detail = document.getElementById("route-step-detail"), list = document.getElementById("route-step-list");
  if (counter) counter.textContent = steps.length ? (state.routeReview.activeIndex + 1) + " / " + steps.length : "0 / 0";
  const previous = document.getElementById("route-step-prev"), next = document.getElementById("route-step-next");
  if (previous) previous.disabled = !steps.length || state.routeReview.activeIndex <= 0;
  if (next) next.disabled = !steps.length || state.routeReview.activeIndex >= steps.length - 1;
  if (detail) detail.textContent = active ? active.fromName + " -> " + active.toName + " / " + formatRouteMetric(active.distance, " km") + " / " + formatRouteMetric(active.time, " min") + " / congestion " + active.congestion.toFixed(1) + " / risk " + active.risk.toFixed(1) : "No route available.";
  list?.querySelectorAll(".route-step-list__item").forEach((item, itemIndex) => { item.classList.toggle("is-active", itemIndex === state.routeReview.activeIndex); item.setAttribute("aria-current", itemIndex === state.routeReview.activeIndex ? "step" : "false"); });
  drawRouteReviewStep(active);
}
function renderRouteReview(path) {
  const list = document.getElementById("route-step-list");
  if (!list) return;
  state.routeReview.path = (path || []).map(String); state.routeReview.steps = buildRouteReview(state.routeReview.path); state.routeReview.activeIndex = -1; list.innerHTML = "";
  state.routeReview.steps.forEach((step, index) => {
    const item = document.createElement("li"); item.className = "route-step-list__item"; item.tabIndex = 0; item.setAttribute("role", "button");
    item.innerHTML = '<span class="route-step-list__index">' + (index + 1) + '</span><span class="route-step-list__text"><strong>' + escapeHtml(step.toName) + '</strong><small>' + escapeHtml(step.fromName) + ' ? ' + escapeHtml(step.toName) + '</small></span>';
    item.addEventListener("click", () => selectRouteReviewStep(index));
    item.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectRouteReviewStep(index); } });
    list.appendChild(item);
  });
  selectRouteReviewStep(state.routeReview.steps.length ? 0 : -1);
}
function getCurrentStartId() {
  return String(document.getElementById("start-select")?.value || "");
}

function getTspNodeLabel(node) {
  if (!node) return "Waypoint";
  return `${node.type === "food" ? "Food" : "Node"} / ${node.name || `Node ${node.id}`}`;
}

function renderTspQueue() {
  const queue = document.getElementById("tsp-queue");
  const empty = document.getElementById("tsp-queue-empty");
  const count = document.getElementById("tsp-queue-count");
  if (!queue || !empty || !count) return;

  queue.innerHTML = "";
  count.textContent = String(state.tspQueue.length);
  empty.hidden = state.tspQueue.length > 0;

  state.tspQueue.forEach((nodeId, index) => {
    const node = state.nodesData.find((item) => String(item.id) === String(nodeId));
    if (!node) return;
    const item = document.createElement("li");
    item.className = "tsp-queue__item";
    item.draggable = true;
    item.dataset.nodeId = nodeId;
    item.innerHTML = `
      <span class="tsp-queue__position">${index + 1}</span>
      <span class="tsp-queue__handle" aria-hidden="true">&#8942;</span>
      <span class="tsp-queue__name" title="${escapeHtml(node.address || node.name)}">${escapeHtml(getTspNodeLabel(node))}</span>
      <button type="button" class="tsp-queue__remove" aria-label="Remove ${escapeHtml(node.name)}" title="Remove waypoint">&times;</button>
    `;
    item.querySelector(".tsp-queue__remove").addEventListener("click", () => {
      clearSearchResults();
      state.selectedWaypoints.delete(nodeId);
      state.tspQueue = state.tspQueue.filter((id) => id !== nodeId);
      const checkbox = document.getElementById(`tsp-${nodeId}`);
      if (checkbox) checkbox.checked = false;
      renderTspQueue();
    });
    item.addEventListener("dragstart", (event) => {
      state.draggedWaypointId = nodeId;
      item.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", nodeId);
    });
    item.addEventListener("dragend", () => {
      state.draggedWaypointId = null;
      item.classList.remove("is-dragging");
    });
    item.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    });
    item.addEventListener("drop", (event) => {
      event.preventDefault();
      const sourceId = state.draggedWaypointId || event.dataTransfer.getData("text/plain");
      const fromIndex = state.tspQueue.indexOf(sourceId);
      const toIndex = state.tspQueue.indexOf(nodeId);
      if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return;
      const [moved] = state.tspQueue.splice(fromIndex, 1);
      clearSearchResults();
      state.tspQueue.splice(toIndex, 0, moved);
      renderTspQueue();
    });
    queue.appendChild(item);
  });
  renderTspWaypointLabels();
}

function syncTspQueueFromSelection() {
  const startId = getCurrentStartId();
  const startCheckbox = document.getElementById(`tsp-${startId}`);
  if (startCheckbox) startCheckbox.checked = false;
  state.selectedWaypoints.delete(startId);
  state.tspQueue = state.tspQueue
    .map(String)
    .filter((id) => id !== startId && state.selectedWaypoints.has(id));
  state.nodesData.forEach((node) => {
    const nodeId = String(node.id);
    if (nodeId !== startId && state.selectedWaypoints.has(nodeId) && !state.tspQueue.includes(nodeId)) {
      state.tspQueue.push(nodeId);
    }
  });
  const count = document.getElementById("tsp-count");
  if (count) count.textContent = String(state.tspQueue.length);
  renderTspQueue();
}async function populateDropdowns() {
  try {
    const [nodesResponse, algorithmsResponse, profilesResponse] =
      await Promise.all([
        fetch(`${API_BASE}/api/nodes`),
        fetch(`${API_BASE}/api/algorithms`),
        fetch(`${API_BASE}/api/cost-profiles`),
      ]);
    if (!nodesResponse.ok || !algorithmsResponse.ok || !profilesResponse.ok) {
      throw new Error("Failed to load route options");
    }
    const [nodes, algorithms, profiles] = await Promise.all([
      nodesResponse.json(),
      algorithmsResponse.json(),
      profilesResponse.json(),
    ]);
    state.nodesData = nodes;

    const algorithmSelect = document.getElementById("algorithm-select");
    const profileSelect = document.getElementById("cost-profile-select");
    const startSelect = document.getElementById("start-select");
    const endSelect = document.getElementById("end-select");
    const tspList = document.getElementById("tsp-waypoints-list");

    algorithmSelect.innerHTML = "";
    algorithms.forEach((algorithm) => {
      const option = new Option(algorithm.label, algorithm.id);
      option.dataset.description = algorithm.description;
      algorithmSelect.add(option);
    });
    algorithmSelect.value = "astar";
    updateAlgorithmDescription();

    profileSelect.innerHTML = "";
    profiles.forEach((profile) => {
      const option = new Option(profile.label, profile.id);
      option.dataset.description = profile.description;
      profileSelect.add(option);
    });
    updateCostDescription();

    startSelect.innerHTML = "";
    endSelect.innerHTML = "";
    startSelect.add(new Option("No node selected", ""));
    endSelect.add(new Option("No node selected", ""));
    startSelect.value = "";
    endSelect.value = "";
    state.selectedEndpoints = { start: "", end: "" };
    tspList.innerHTML = "";
    state.selectedWaypoints.clear();
    state.tspQueue = [];
    renderTspQueue();

    nodes.sort((a, b) => a.name.localeCompare(b.name, "vi"));
    const foodNodes = nodes.filter(
      (node) => node.type === "food",
    );

    foodNodes.forEach((n) => {
      const nodeKind = n.type === "food" ? "Food" : "Intersection";
      const label = `${nodeKind} / ${n.name || `Node ${n.id}`} (#${n.id})`;
      startSelect.add(new Option(label, n.id));
      endSelect.add(new Option(label, n.id));
    });

    nodes.forEach((n) => {
      const nodeKind = n.type === "food" ? "Food" : "Intersection";
      const label = `${nodeKind} / ${n.name || `Node ${n.id}`} (#${n.id})`;
      const div = document.createElement("div");
      div.className = "waypoint-item";
      div.innerHTML = `
                <input type="checkbox" id="tsp-${n.id}" value="${n.id}">
                <label for="tsp-${n.id}">${label}</label>
            `;
      const checkbox = div.querySelector("input");
      checkbox.addEventListener("change", (e) => {
        clearSearchResults();
        if (e.target.checked) state.selectedWaypoints.add(String(n.id));
        else state.selectedWaypoints.delete(String(n.id));
        document.getElementById("tsp-count").innerText =
          state.selectedWaypoints.size;
      });

      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          if (!state.tspQueue.includes(String(n.id))) state.tspQueue.push(String(n.id));
        } else {
          state.tspQueue = state.tspQueue.filter((id) => String(id) !== String(n.id));
        }
        syncTspQueueFromSelection();
      });
      tspList.appendChild(div);
    });
  } catch (e) {
    console.error("Populate Dropdowns Error:", e);
  }
}

/**
 * Load graph data from the backend API.
 */
async function loadGraph() {
  try {
    const graphResponse = await fetch(`${API_BASE}/api/graph`);
    if (!graphResponse.ok) throw new Error("Failed to load graph");
    const data = await graphResponse.json();
    state.graphData = data;
    renderEdges(data.edges, data.nodes);
    renderNodes(data.nodes);
    renderEndpointLayers();
    initTspWaypointLayers();
    constrainMapToGraph(data.nodes);
    updateSelectedEndpoints();
  } catch (err) {
    console.error("Error loading graph:", err);
    alert(
      "Cannot connect to backend server. Make sure it is running at http://localhost:8000",
    );
  }
}


document.getElementById("start-select").addEventListener("change", (event) => {
  updateEndpointSelection("start", event.target.value);
});
document.getElementById("end-select").addEventListener("change", (event) => {
  updateEndpointSelection("end", event.target.value);
});

document.querySelectorAll("[data-edge-metric]").forEach((button) => {
  button.addEventListener("click", () => {
    state.edgeMetric = button.dataset.edgeMetric === "risk" ? "risk" : "congestion";
    document.querySelectorAll("[data-edge-metric]").forEach((item) => item.classList.toggle("is-active", item === button));
    if (state.map?.getLayer("graph-edges-layer")) state.map.setPaintProperty("graph-edges-layer", "line-color", edgeMetricExpression());
    if (state.map?.getLayer("graph-edges-arrows")) state.map.setPaintProperty("graph-edges-arrows", "text-color", edgeMetricExpression());
    updateEdgeLegend();
  });
});
updateEdgeLegend();

function initPanelResizer() {
  const panel = document.getElementById("control-panel");
  const handle = document.getElementById("panel-resizer");
  if (!panel || !handle) return;
  let dragging = false;
  handle.addEventListener("pointerdown", (event) => {
    dragging = true;
    handle.setPointerCapture(event.pointerId);
    document.body.classList.add("is-resizing-panel");
  });
  handle.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const width = Math.min(520, Math.max(300, event.clientX));
    panel.style.setProperty("--panel-width", `${width}px`);
    state.map?.resize();
  });
  const stop = () => {
    dragging = false;
    document.body.classList.remove("is-resizing-panel");
  };
  handle.addEventListener("pointerup", stop);
  handle.addEventListener("pointercancel", stop);
}
initPanelResizer();
document.getElementById("algorithm-select").addEventListener("change", (e) => {
  const isTSP = e.target.value === "tsp";
  document.getElementById("end-group").style.display = isTSP ? "none" : "flex";
  const tspSection = document.getElementById("tsp-section");
  tspSection.style.display = isTSP ? "flex" : "none";
  tspSection.setAttribute("aria-hidden", String(!isTSP));
  if (isTSP) renderTspQueue();
  else renderEndpointLayers();
  clearSearchResults();
  if (isTSP) {
    state.selectedEndpoints.end = "";
    updateSelectedEndpoints();
  }
  document.querySelector(".algorithm-control .control-kicker").innerText =
    isTSP ? "MULTI-STOP" : "GRAPH CORE";
  document.getElementById("btn-compare").disabled = isTSP;
  updateAlgorithmDescription();
});

function updateAlgorithmDescription() {
  const select = document.getElementById("algorithm-select");
  const option = select.options[select.selectedIndex];
  document.getElementById("algorithm-description").innerText =
    option?.dataset.description || "Choose a graph exploration strategy.";
}

function updateCostDescription() {
  const select = document.getElementById("cost-profile-select");
  const option = select.options[select.selectedIndex];
  document.getElementById("cost-description").innerText =
    option?.dataset.description || "Balance traffic factors.";
}

document
  .getElementById("cost-profile-select")
  .addEventListener("change", () => {
    clearSearchResults();
    updateCostDescription();
  });

document.querySelectorAll('input[name="tsp-mode"]').forEach((input) => {
  input.addEventListener("change", () => {
    if (state.tspMode !== input.value) clearSearchResults();
    state.tspMode = input.value;
  });
});

document.getElementById("btn-select-all").addEventListener("click", () => {
  clearSearchResults();
  document
    .querySelectorAll('#tsp-waypoints-list input[type="checkbox"]')
    .forEach((cb) => {
      cb.checked = true;
      state.selectedWaypoints.add(String(cb.value));
    });
  document.getElementById("tsp-count").innerText = state.selectedWaypoints.size;
  syncTspQueueFromSelection();
});

document.getElementById("btn-clear-all").addEventListener("click", () => {
  clearSearchResults();
  document
    .querySelectorAll('#tsp-waypoints-list input[type="checkbox"]')
    .forEach((cb) => {
      cb.checked = false;
    });
  state.selectedWaypoints.clear();
  state.tspQueue = [];
  document.getElementById("tsp-count").innerText = "0";
  renderTspQueue();
});

document.getElementById("btn-compare").addEventListener("click", async () => {
  const start = document.getElementById("start-select").value;
  const end = document.getElementById("end-select").value;
  const profile = document.getElementById("cost-profile-select").value;
  if (!start || !end) {
    alert("Select start and end points before comparing algorithms.");
    return;
  }
  if (start === end) {
    alert("Start and end points must be different.");
    return;
  }

  const button = document.getElementById("btn-compare");
  button.disabled = true;
  button.innerText = "Comparing...";
  try {
    const response = await fetch(`${API_BASE}/api/metrics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start, end, cost_profile: profile }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Metrics failed");
    renderMetrics(data.metrics, profile, { start, end });
  } catch (error) {
    console.error("Metrics Error:", error);
    alert(`Metrics error: ${error.message}`);
  } finally {
    button.disabled = false;
    button.innerText = "Compare Algorithms";
  }
});

const COMPARE_METRIC_CONFIG = {
  total_cost: { label: "Total Cost", shortLabel: "cost", unit: "", decimals: 4 },
  processing_time_ms: { label: "Runtime", shortLabel: "runtime", unit: " ms", decimals: 2 },
  explored_nodes: { label: "Explored Nodes", shortLabel: "explored nodes", unit: "", decimals: 0 },
  total_distance_km: { label: "Distance", shortLabel: "distance", unit: " km", decimals: 3 },
  total_time_min: { label: "Travel Time", shortLabel: "travel time", unit: " min", decimals: 2 },
};

function formatAlgorithmName(value) {
  const names = {
    bfs: "BFS",
    dfs: "DFS",
    ucs: "UCS",
    astar: "A*",
    ida_star: "IDA*",
    greedy_best_first: "Greedy Best-First",
  };
  return names[value] || String(value || "Unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatCompareValue(value, config) {
  if (value === null || value === undefined || value === "") return "\u2014";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "\u2014";
  return numeric.toFixed(config.decimals) + config.unit;
}

function renderComparisonView(metricKey = state.comparisonMetric) {
  const config = COMPARE_METRIC_CONFIG[metricKey] || COMPARE_METRIC_CONFIG.total_cost;
  const winner = document.getElementById("compare-winner");
  const detail = document.getElementById("compare-winner-detail");
  const summary = document.getElementById("compare-metric-summary");
  if (!winner || !detail || !summary) return;

  state.comparisonMetric = metricKey;
  document.querySelectorAll("[data-compare-metric]").forEach((button) => {
    const active = button.dataset.compareMetric === metricKey;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  const getComparable = (key) => state.comparisonMetrics
    .filter((metric) => metric.found && Number.isFinite(Number(metric[key])))
    .sort((left, right) => Number(left[key]) - Number(right[key]));

  Object.entries(COMPARE_METRIC_CONFIG).forEach(([key, metricConfig]) => {
    const valueElement = summary.querySelector('[data-compare-summary="' + key + '"]');
    if (!valueElement) return;
    const ranked = getComparable(key);
    if (!ranked.length) {
      valueElement.textContent = "No result";
      return;
    }
    const best = ranked[0];
    valueElement.textContent = formatAlgorithmName(best.algorithm) + " / " +
      formatCompareValue(best[key], metricConfig);
  });

  const comparable = getComparable(metricKey);
  if (!comparable.length) {
    winner.textContent = "No result";
    detail.textContent = "No algorithm found a route.";
    return;
  }

  const bestValue = Number(comparable[0][metricKey]);
  const winners = comparable.filter((metric) =>
    Math.abs(Number(metric[metricKey]) - bestValue) < 1e-9
  );
  winner.textContent = winners.length === 1
    ? formatAlgorithmName(winners[0].algorithm)
    : winners.length + " algorithms tied";
  detail.textContent = "Lowest by " + config.shortLabel + ": " +
    formatCompareValue(bestValue, config) + ".";
}
function renderMetrics(metrics, profile, context = {}) {
  const panel = document.getElementById("metrics-panel");
  const body = document.getElementById("metrics-table-body");
  state.comparisonMetrics = Array.isArray(metrics) ? metrics : [];

  document.getElementById("metrics-profile").textContent = String(profile || "").toUpperCase();
  const startNode = state.nodesData.find((node) => String(node.id) === String(context.start || ""));
  const endNode = state.nodesData.find((node) => String(node.id) === String(context.end || ""));
  document.getElementById("compare-context").textContent =
    (startNode?.name || context.start || "\u2014") + " -> " + (endNode?.name || context.end || "\u2014");
  const compareContent = document.getElementById("compare-drawer-content");
  const drawerResizer = document.getElementById("compare-drawer-resizer");
  if (compareContent && panel && panel.parentElement !== compareContent) {
    compareContent.appendChild(panel);
  }
  document.getElementById("compare-drawer-kicker").textContent = "ALGORITHM BENCHMARK / " + String(profile || "").toUpperCase();
  document.getElementById("compare-drawer-title").textContent = "Algorithm Comparison";
  drawerResizer?.setAttribute("aria-label", "Resize the comparison panel");
  drawerResizer?.setAttribute("title", "Drag to resize the comparison panel");
  body.innerHTML = state.comparisonMetrics
    .map((metric) => {
      const found = Boolean(metric.found);
      return '<tr class="' + (found ? "" : "is-unavailable") + '">' +
        '<th scope="row">' + escapeHtml(formatAlgorithmName(metric.algorithm)) + '</th>' +
        '<td><span class="compare-status ' + (found ? "is-found" : "is-missing") + '">' +
        (found ? "Found" : "No path") + '</span></td>' +
        '<td class="is-numeric">' + escapeHtml(String(metric.explored_nodes ?? "\u2014")) + '</td>' +
        '<td class="is-numeric">' + escapeHtml(formatCompareValue(metric.processing_time_ms, COMPARE_METRIC_CONFIG.processing_time_ms)) + '</td>' +
        '<td class="is-numeric">' + escapeHtml(formatCompareValue(metric.total_cost, COMPARE_METRIC_CONFIG.total_cost)) + '</td>' +
        '<td class="is-numeric">' + escapeHtml(formatCompareValue(metric.total_distance_km, COMPARE_METRIC_CONFIG.total_distance_km)) + '</td>' +
        '<td class="is-numeric">' + escapeHtml(formatCompareValue(metric.total_time_min, COMPARE_METRIC_CONFIG.total_time_min)) + '</td></tr>';
    })
    .join("");

  renderComparisonView(state.comparisonMetric);
  panel.hidden = false;
  setCompareDrawerVisible(true);
}

document.querySelectorAll("[data-compare-metric]").forEach((button) => {
  button.setAttribute("aria-pressed", String(button.classList.contains("is-active")));
  button.addEventListener("click", () => renderComparisonView(button.dataset.compareMetric));
});
// ==========================================
// START SEARCH
// ==========================================
document.getElementById("btn-start").addEventListener("click", async () => {
  const algorithm = document.getElementById("algorithm-select").value;
  const start = document.getElementById("start-select").value;
  const costProfile = document.getElementById("cost-profile-select").value;

  if (!start) return alert("Please select a start point.");

  let payload = {};
  let endpoint = "";

  if (algorithm === "tsp") {
    if (state.tspQueue.length < 2) {
      return alert("Please select at least 2 waypoints for TSP.");
    }
    endpoint = "/api/tsp";
    const waypoints = [
      start,
      ...state.tspQueue.filter((id) => id !== start),
    ];
    payload = {
      waypoints,
      cost_profile: costProfile,
      order_mode: state.tspMode,
    };
  } else {
    const end = document.getElementById("end-select").value;
    if (!end) return alert("Please select an end point.");
    if (start === end) return alert("Start and end points cannot be the same.");

    endpoint = "/api/search";
    payload = {
      start: start,
      end: end,
      algorithm: algorithm,
      cost_profile: costProfile,
    };
  }

  clearSearchResults();
  const requestGeneration = state.searchGeneration;
  showLoading(true, "Calculating route...");

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.detail || "Search failed");
    }

    const data = await response.json();
    if (requestGeneration !== state.searchGeneration) return;
    startAnimation(data.animation_log, data.path, data.stats, data.explanation);
  } catch (e) {
    console.error("Search Error:", e);
    alert(`Error: ${e.message}`);
  } finally {
    if (requestGeneration === state.searchGeneration) showLoading(false);
  }
});

// ==========================================
// SHOW RESULTS
// ==========================================

/**




 */
function showResults(path, stats = {}, explanation) {
  const panel = document.getElementById("results-panel");
  const metricsPanel = document.getElementById("metrics-panel");
  const routeReview = document.getElementById("route-review-panel");
  const drawer = document.getElementById("results-drawer");
  const resultsContent = drawer?.querySelector(".results-drawer__content");
  document.getElementById("results-drawer-kicker").textContent = "ROUTE REVIEW";
  document.getElementById("results-drawer-title").textContent = "Search Results";
  const drawerResizer = document.getElementById("results-drawer-resizer");
  drawerResizer?.setAttribute("aria-label", "Resize the results panel");
  drawerResizer?.setAttribute("title", "Drag to resize the results panel");
  if (metricsPanel && resultsContent && metricsPanel.parentElement !== resultsContent) {
    resultsContent.appendChild(metricsPanel);
  }
  if (metricsPanel) metricsPanel.hidden = true;
  if (routeReview) routeReview.style.display = "block";
  panel.style.display = "block";
  setCompareDrawerVisible(false);
  setResultsDrawerVisible(true);
  document.getElementById("stat-explored").innerText = stats.nodes_explored || 0;
  document.getElementById("stat-distance").innerText = stats.total_distance !== undefined ? stats.total_distance.toFixed(2) + " km" : "N/A";
  document.getElementById("stat-time").innerText = stats.total_time !== undefined ? stats.total_time.toFixed(2) + " min" : "N/A";
  document.getElementById("stat-cost").innerText = stats.total_cost !== undefined ? stats.total_cost.toFixed(2) : "N/A";
  document.getElementById("stat-proc-time").innerText = stats.processing_time_ms !== undefined ? stats.processing_time_ms.toFixed(2) + " ms" : "N/A";
  document.getElementById("explanation-text").textContent = explanation || "Search completed.";
  renderRouteReview(path || []);
}

/**
 * Show or hide the loading overlay.
 * @param {boolean} show - Whether the overlay is visible
 * @param {string} message - Message displayed in the overlay
 */
function showLoading(show, message = "Loading...") {
  const overlay = document.getElementById("loading-overlay");
  if (show) {
    overlay.querySelector("p").innerText = message;
    overlay.style.display = "flex";
  } else {
    overlay.style.display = "none";
  }
}

// ==========================================
// INITIALIZE APP
// ==========================================
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const response = await fetch(`${API_BASE}/api/config`);
    if (!response.ok) throw new Error("Could not load the map configuration.");
    const config = await response.json();
    GOONG_MAP_KEY = config.map_tiles_key || "";
    initMap();
  } catch (error) {
    console.error("Config Error:", error);
    showLoading(true, "Could not load the Goong Maps configuration.");
  }
});
