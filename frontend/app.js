// ==========================================
// CONFIG
// ==========================================
const API_BASE = "http://localhost:8000";
const GOONG_MAP_KEY = "DtWocjjwYy4U3vGHcDleTwzr4iCAmLfQP55tvpMS"; // <-- THAY BẰNG KEY THỰC CỦA BẠN

// ==========================================
// STATE
// ==========================================
/**
 * Global state object chứa tất cả trạng thái của ứng dụng
 * @typedef {Object} AppState
 * @property {Object|null} map - Goong GL JS map instance
 * @property {Object} markers - Đối tượng lưu markers (nodeId -> marker)
 * @property {Object} polylines - Đối tượng lưu polylines
 * @property {number|null} animationTimer - Timer cho animation
 * @property {number} animationStep - Bước hiện tại của animation
 * @property {Array} animationLog - Log các bước animation
 * @property {boolean} isPaused - Trạng thái tạm dừng animation
 * @property {boolean} isAnimating - Trạng thái đang chạy animation
 * @property {Object|null} graphData - Dữ liệu đồ thị (nodes + edges)
 * @property {Array} nodesData - Danh sách nodes cho dropdown
 * @property {Set} selectedWaypoints - Tập các waypoints được chọn cho TSP
 * @property {Object} pendingResults - Kết quả chờ hiển thị
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
  pendingResults: { finalPath: null, stats: null, explanation: null },
};

// ==========================================
// MAP MANAGER (Goong GL JS)
// ==========================================

/**
 * Khởi tạo bản đồ vector chính thức của Goong.
 */
function initMap() {
  console.log("[Map] Initializing Goong GL JS map...");

  if (!goongjs.supported()) {
    showLoading(true, "Trình duyệt không hỗ trợ Goong GL JS.");
    return;
  }

  goongjs.accessToken = GOONG_MAP_KEY;
  state.map = new goongjs.Map({
    container: "map",
    style: "https://tiles.goong.io/assets/goong_map_web.json",
    center: [106.698, 10.783], // Goong dùng [lng, lat]
    zoom: 16,
    minZoom: 10,
    maxZoom: 24,
    attributionControl: false,
  });

  state.map.addControl(new goongjs.NavigationControl(), "top-right");
  state.map.on("load", () => {
    console.log("[Map] Goong GL JS map ready ✅");
    showLoading(true, "Loading graph data...");
    loadGraph()
      .then(() => populateDropdowns())
      .finally(() => showLoading(false));
  });
}

/**
 * Trả về màu dựa trên mức độ kẹt xe
 * @param {number} congestion - Mức độ kẹt xe (1-10)
 * @returns {string} Màu hex (#22c55e, #f59e0b, #ef4444)
 */
function getCongestionColor(congestion) {
  if (congestion <= 3) return "#22c55e";
  if (congestion <= 6) return "#f59e0b";
  return "#ef4444";
}

/**
 * Vẽ các cạnh (đường nối) giữa các node lên bản đồ
 * @param {Array} edges - Danh sách edges
 * @param {Object} nodes - Đối tượng nodes
 */
function renderEdges(edges, nodes) {
  const seen = new Set();
  const features = [];
  for (const edge of edges) {
    const fromNode = nodes[edge.from];
    const toNode = nodes[edge.to];
    if (!fromNode || !toNode) continue;

    const edgeKey = [edge.from, edge.to].sort().join("--");
    if (seen.has(edgeKey)) continue;
    seen.add(edgeKey);

    const color = getCongestionColor(edge.congestion);
    features.push({
      type: "Feature",
      properties: { color },
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
    id: "graph-edges-layer",
    type: "line",
    source: "graph-edges",
    paint: {
      "line-color": ["get", "color"],
      "line-width": 2,
      "line-opacity": 0.6,
    },
  });
}

/**
 * Vẽ các node (điểm đánh dấu) lên bản đồ
 * @param {Object} nodes - Đối tượng nodes (nodeId -> node data)
 */
function renderNodes(nodes) {
  const features = [];
  for (const [id, node] of Object.entries(nodes)) {
    const feature = {
      type: "Feature",
      id,
      properties: {
        nodeId: id,
        type: node.type || "intersection",
        status: "reset",
        name: node.name,
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
      "circle-radius": 7,
      "circle-color": [
        "match",
        ["get", "status"],
        "frontier",
        "#ef4444",
        "visited",
        "#22c55e",
        "optimal",
        "#f59e0b",
        ["match", ["get", "type"], "food", "#fb923c", "#ffffff"],
      ],
      "circle-stroke-color": "#000000",
      "circle-stroke-width": 2,
    },
  });

  state.map.on("click", "graph-nodes-layer", (event) => {
    const node = event.features[0].properties;
    new goongjs.Popup({ closeButton: true, closeOnClick: true })
      .setLngLat(event.lngLat)
      .setHTML(`<strong>${node.name}</strong>`)
      .addTo(state.map);
  });
  state.map.on("mouseenter", "graph-nodes-layer", () => {
    state.map.getCanvas().style.cursor = "pointer";
  });
  state.map.on("mouseleave", "graph-nodes-layer", () => {
    state.map.getCanvas().style.cursor = "";
  });
}

/* Cập nhật dữ liệu source để Goong GL JS vẽ lại màu node. */
function refreshNodeSource() {
  if (!state.map.getSource("graph-nodes")) return;
  state.map.getSource("graph-nodes").setData({
    type: "FeatureCollection",
    features: Object.values(state.nodeFeatures),
  });
}

/**
 * Giới hạn viewport vào khu vực chứa toàn bộ graph.
 * Goong GL JS dùng thứ tự tọa độ [lng, lat].
 */
function constrainMapToGraph(nodes) {
  const coordinates = Object.values(nodes).map((node) => [node.lng, node.lat]);
  if (!coordinates.length) return;

  const longitudes = coordinates.map(([lng]) => lng);
  const latitudes = coordinates.map(([, lat]) => lat);
  const paddingLng = 0.005;
  const paddingLat = 0.005;
  const bounds = [
    [Math.min(...longitudes) - paddingLng, Math.min(...latitudes) - paddingLat],
    [Math.max(...longitudes) + paddingLng, Math.max(...latitudes) + paddingLat],
  ];

  state.map.setMaxBounds(bounds);
  state.map.fitBounds(bounds, { padding: 60, maxZoom: 18, duration: 0 });

  // Không cho thu nhỏ hơn viewport vừa bao phủ graph.
  state.map.setMinZoom(state.map.getZoom());
}

/** Hiển thị tối đa 40 địa điểm quán ăn từ Goong Places API. */
function renderFoodPlaces(places) {
  const features = places.slice(0, 40).map((place) => ({
    type: "Feature",
    properties: {
      name: place.name || "Quán ăn",
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
 * Đổi màu marker theo trạng thái animation
 * @param {string} nodeId - ID của node
 * @param {string} status - Trạng thái: frontier, visited, optimal, reset
 */
function updateMarkerColor(nodeId, status) {
  const feature = state.nodeFeatures[nodeId];
  if (!feature) return;
  feature.properties.status = status;
  refreshNodeSource();
}

/**
 * Vẽ đường đi tối ưu (polyline vàng) và đổi node thành vàng
 * @param {Array} path - Đường đi (danh sách node IDs)
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
    paint: { "line-color": "#f59e0b", "line-width": 6, "line-opacity": 0.85 },
  });

  path.forEach((nodeId) => updateMarkerColor(nodeId, "optimal"));
}

/**
 * Reset toàn bộ visualization (markers, path, results)
 */
function resetVisualization() {
  for (const id in state.nodeFeatures) {
    updateMarkerColor(id, "reset");
  }
  if (state.map.getLayer("optimal-path-layer")) {
    state.map.removeLayer("optimal-path-layer");
  }
  if (state.map.getSource("optimal-path")) {
    state.map.removeSource("optimal-path");
  }
  document.getElementById("results-panel").style.display = "none";
}

// ==========================================
// ANIMATION ENGINE
// ==========================================

/**
 * Tính toán khoảng thời gian giữa mỗi bước animation (ms)
 * @returns {number} Thời gian delay (ms)
 */
function getInterval() {
  const sliderVal = parseInt(document.getElementById("speed-slider").value);
  return Math.max(50, 1000 - (sliderVal - 1) * (950 / 99));
}

/**
 * Bắt đầu animation từ đầu
 * @param {Array} animationLog - Log các bước animation
 * @param {Array} finalPath - Đường đi cuối cùng
 * @param {Object} stats - Thống kê đường đi
 * @param {string} explanation - Giải thích kết quả
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
 * Chạy từng bước animation
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
 * Kết thúc animation: vẽ đường tối ưu + hiển thị kết quả
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
 * Chuyển đổi hiển thị giữa nút Start và các nút Pause/Resume/Reset
 * @param {boolean} animating - Trạng thái đang chạy animation
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

// ==========================================
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
 * Populate dropdowns (Start/End) và TSP checklist từ API
 */
async function populateDropdowns() {
  try {
    const res = await fetch(`${API_BASE}/api/nodes`);
    if (!res.ok) throw new Error("Failed to load nodes");
    const nodes = await res.json();
    state.nodesData = nodes;

    const startSelect = document.getElementById("start-select");
    const endSelect = document.getElementById("end-select");
    const tspList = document.getElementById("tsp-waypoints-list");

    startSelect.innerHTML = "";
    endSelect.innerHTML = "";
    tspList.innerHTML = "";

    nodes.sort((a, b) => a.name.localeCompare(b.name, "vi"));

    nodes.forEach((n) => {
      const label = n.name || `Node ${n.id}`;
      startSelect.add(new Option(label, n.id));
      endSelect.add(new Option(label, n.id));

      const div = document.createElement("div");
      div.className = "waypoint-item";
      div.innerHTML = `
                <input type="checkbox" id="tsp-${n.id}" value="${n.id}">
                <label for="tsp-${n.id}">${label}</label>
            `;
      const checkbox = div.querySelector("input");
      checkbox.addEventListener("change", (e) => {
        if (e.target.checked) state.selectedWaypoints.add(n.id);
        else state.selectedWaypoints.delete(n.id);
        document.getElementById("tsp-count").innerText =
          state.selectedWaypoints.size;
      });
      tspList.appendChild(div);
    });
  } catch (e) {
    console.error("Populate Dropdowns Error:", e);
  }
}

/**
 * Tải dữ liệu đồ thị từ Backend API
 */
async function loadGraph() {
  try {
    const [graphResponse, foodResponse] = await Promise.all([
      fetch(`${API_BASE}/api/graph`),
      fetch(`${API_BASE}/api/food-places`),
    ]);
    if (!graphResponse.ok) throw new Error("Failed to load graph");
    const data = await graphResponse.json();
    const foodData = foodResponse.ok
      ? await foodResponse.json()
      : { places: [] };
    state.graphData = data;
    renderEdges(data.edges, data.nodes);
    renderNodes(data.nodes);
    renderFoodPlaces(foodData.places || []);
    constrainMapToGraph(data.nodes);
  } catch (err) {
    console.error("Error loading graph:", err);
    alert(
      "Cannot connect to backend server. Make sure it is running at http://localhost:8000",
    );
  }
}

document.getElementById("algorithm-select").addEventListener("change", (e) => {
  const isTSP = e.target.value === "tsp";
  document.getElementById("end-group").style.display = isTSP ? "none" : "flex";
  document.getElementById("tsp-section").style.display = isTSP
    ? "flex"
    : "none";
});

document.getElementById("btn-select-all").addEventListener("click", () => {
  document
    .querySelectorAll('#tsp-waypoints-list input[type="checkbox"]')
    .forEach((cb) => {
      cb.checked = true;
      state.selectedWaypoints.add(cb.value);
    });
  document.getElementById("tsp-count").innerText = state.selectedWaypoints.size;
});

document.getElementById("btn-clear-all").addEventListener("click", () => {
  document
    .querySelectorAll('#tsp-waypoints-list input[type="checkbox"]')
    .forEach((cb) => {
      cb.checked = false;
    });
  state.selectedWaypoints.clear();
  document.getElementById("tsp-count").innerText = "0";
});

// ==========================================
// START SEARCH
// ==========================================
document.getElementById("btn-start").addEventListener("click", async () => {
  const algorithm = document.getElementById("algorithm-select").value;
  const start = document.getElementById("start-select").value;
  const costType = document.querySelector('input[name="cost"]:checked').value;

  if (!start) return alert("Please select a start point.");

  let payload = {};
  let endpoint = "";

  if (algorithm === "tsp") {
    if (state.selectedWaypoints.size < 2) {
      return alert("Please select at least 2 waypoints for TSP.");
    }
    endpoint = "/api/tsp";
    const waypoints = [
      start,
      ...Array.from(state.selectedWaypoints).filter((id) => id !== start),
    ];
    payload = { waypoints, cost_type: costType };
  } else {
    const end = document.getElementById("end-select").value;
    if (!end) return alert("Please select an end point.");
    if (start === end) return alert("Start and end points cannot be the same.");

    endpoint = "/api/search";
    payload = {
      start: start,
      end: end,
      algorithm: algorithm,
      cost_type: costType,
    };
  }

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
    startAnimation(data.animation_log, data.path, data.stats, data.explanation);
  } catch (e) {
    console.error("Search Error:", e);
    alert(`Error: ${e.message}`);
  } finally {
    showLoading(false);
  }
});

// ==========================================
// SHOW RESULTS
// ==========================================

/**
 * Hiển thị panel kết quả sau khi animation kết thúc
 * @param {Array} path - Đường đi
 * @param {Object} stats - Thống kê
 * @param {string} explanation - Giải thích
 */
function showResults(path, stats, explanation) {
  const panel = document.getElementById("results-panel");
  panel.style.display = "block";

  document.getElementById("stat-explored").innerText =
    stats.nodes_explored || 0;
  document.getElementById("stat-distance").innerText =
    stats.total_distance !== undefined
      ? `${stats.total_distance.toFixed(2)} km`
      : "N/A";
  document.getElementById("stat-time").innerText =
    stats.total_time !== undefined
      ? `${stats.total_time.toFixed(2)} min`
      : "N/A";
  document.getElementById("stat-cost").innerText =
    stats.total_cost !== undefined ? stats.total_cost.toFixed(2) : "N/A";
  document.getElementById("stat-proc-time").innerText =
    stats.processing_time_ms !== undefined
      ? `${stats.processing_time_ms.toFixed(2)} ms`
      : "N/A";

  if (path && path.length > 0) {
    const names = path.map((id) => {
      const node = state.nodesData.find((n) => n.id === id);
      return node ? node.name : id;
    });
    document.getElementById("route-text").innerText = names.join(" → ");
  } else {
    document.getElementById("route-text").innerText = "No path found";
  }

  document.getElementById("explanation-text").innerHTML =
    explanation || "Search completed.";
}

/**
 * Hiển thị/ẩn loading overlay
 * @param {boolean} show - Hiển thị hay ẩn
 * @param {string} message - Tin nhắn hiển thị
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
document.addEventListener("DOMContentLoaded", () => {
  initMap();
});
