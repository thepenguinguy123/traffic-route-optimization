"""HTTP API cho traffic graph core và giao diện mô phỏng tuyến đường."""

import os
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from ..algorithms.registry import ALGORITHM_REGISTRY
from ..core.cost_profiles import COST_PROFILES
from ..core.errors import NodeNotFoundError
from ..core.food_area import point_in_polygon
from ..core.graph import TrafficGraph
from ..core.search_models import SearchResult
from ..repositories.graph_data import NODES
from ..repositories.clean_dataset_repository import load_clean_graph
from ..services.multi_location_service import MultiLocationService
from ..services.metrics_service import (
    DEFAULT_COMPARISON_ALGORITHMS,
    MetricsService,
)


project_env = Path(__file__).resolve().parents[3] / ".env"
backend_env = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(backend_env)
load_dotenv(project_env, override=True)

app = Flask(__name__)
allowed_origins = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
)
CORS(app, origins=allowed_origins)

ALGORITHM_OPTIONS = [
    {
        "id": "bfs",
        "label": "BFS",
        "description": "Ưu tiên tuyến ít bước nhất.",
        "group": "graph_core",
    },
    {
        "id": "dfs",
        "label": "DFS",
        "description": "Đi sâu theo từng nhánh trước.",
        "group": "graph_core",
    },
    {
        "id": "ucs",
        "label": "UCS",
        "description": "Tối ưu chi phí giao thông tích lũy.",
        "group": "graph_core",
    },
    {
        "id": "astar",
        "label": "A*",
        "description": "UCS kết hợp heuristic khoảng cách.",
        "group": "graph_core",
    },
    {
        "id": "greedy_best_first",
        "label": "Greedy Best-First",
        "description": "Ưu tiên node gần đích theo heuristic.",
        "group": "graph_core",
    },
    {
        "id": "ida_star",
        "label": "IDA*",
        "description": "A* với bộ nhớ thấp và deepening bound.",
        "group": "graph_core",
    },
    {
        "id": "tsp",
        "label": "TSP",
        "description": "Đi qua nhiều waypoint theo thứ tự tối ưu.",
        "group": "multi_stop",
    },
]

COST_OPTIONS = [
    {"id": "balanced", "label": "Cân bằng", "description": "Cân đối khoảng cách, thời gian và rủi ro."},
    {"id": "shortest_distance", "label": "Ngắn nhất", "description": "Ưu tiên tổng quãng đường."},
    {"id": "fastest_route", "label": "Nhanh nhất", "description": "Ưu tiên thời gian di chuyển."},
    {"id": "avoid_congestion", "label": "Tránh ùn tắc", "description": "Giảm ảnh hưởng của congestion."},
]


def build_traffic_graph() -> TrafficGraph:
    """Tải đúng graph sạch từ nodes_clean.js và edges_clean.js."""

    return load_clean_graph()


TRAFFIC_GRAPH = build_traffic_graph()
MULTI_LOCATION_SERVICE = MultiLocationService()


def graph_response() -> dict:
    """Trả graph core theo shape mà frontend bản đồ đang sử dụng."""

    graph = TRAFFIC_GRAPH.to_dict()
    nodes = {
        node["id"]: {
            "name": node["name"],
            "lat": node["latitude"],
            "lng": node["longitude"],
            "type": node["node_type"],
            **{
                key: value
                for key, value in node.items()
                if key not in {"id", "name", "latitude", "longitude", "node_type"}
            },
        }
        for node in graph["nodes"]
    }
    edges = [
        {
            "from": edge["source"],
            "to": edge["target"],
            "distance_km": edge["distance_km"],
            "time_min": edge["base_time_min"],
            "congestion": edge["congestion_level"],
            "road_type": edge["road_type"],
            "risk_factor": edge["risk_factor"],
        }
        for edge in graph["edges"]
    ]
    return {"nodes": nodes, "edges": edges}


def profile_from_request(data: dict) -> str:
    """Đọc cost profile mới và vẫn hỗ trợ payload cost_type cũ."""

    profile = data.get("cost_profile")
    if profile in COST_PROFILES:
        return profile
    legacy_map = {
        "distance": "shortest_distance",
        "time": "fastest_route",
        "combined": "balanced",
    }
    return legacy_map.get(data.get("cost_type"), "balanced")


def serialize_core_result(result: SearchResult) -> dict:
    """Đổi SearchResult thành response animation ổn định cho frontend."""

    animation_log = []
    for trace in result.frontier_steps:
        animation_log.append(
            {
                "step": len(animation_log) + 1,
                "node": trace.current.node_id,
                "status": "frontier",
                "parent": trace.current.parent_id,
            }
        )
        animation_log.append(
            {
                "step": len(animation_log) + 1,
                "node": trace.current.node_id,
                "status": "visited",
                "parent": trace.current.parent_id,
            }
        )

    return {
        "path": result.path,
        "animation_log": animation_log,
        "stats": {
            "nodes_explored": result.explored_nodes,
            "total_distance": round(result.total_distance, 3),
            "total_time": round(result.total_time, 3),
            "total_cost": round(result.total_cost, 4),
            "processing_time_ms": round(result.processing_time_ms, 3),
        },
        "explanation": result.message,
        "algorithm": result.algorithm,
        "found": result.found,
        "trace": [asdict(trace) for trace in result.frontier_steps],
    }


@app.route("/")
def health_check():
    """Kiểm tra trạng thái server."""

    return jsonify({"status": "ok", "message": "API is running"})


@app.route("/api/config", methods=["GET"])
def get_public_config():
    """Chỉ trả cấu hình cần thiết cho frontend, không trả REST API key."""

    return jsonify({"map_tiles_key": os.getenv("GOONG_MAP_TILES_KEY", "")})


@app.route("/api/algorithms", methods=["GET"])
def get_algorithms():
    """Trả danh sách thuật toán để frontend dựng selection."""

    return jsonify(ALGORITHM_OPTIONS)


@app.route("/api/cost-profiles", methods=["GET"])
def get_cost_profiles():
    """Trả danh sách profile chi phí được graph core hỗ trợ."""

    return jsonify(COST_OPTIONS)


@app.route("/api/metrics", methods=["POST"])
def compare_metrics():
    """So sánh metrics của nhiều thuật toán trên cùng một cặp node."""

    data = request.get_json(silent=True) or {}
    start = str(data.get("start", ""))
    goal = str(data.get("end", data.get("goal", "")))
    profile = profile_from_request(data)
    algorithm_names = data.get("algorithms", DEFAULT_COMPARISON_ALGORITHMS)
    if not start or not goal or not isinstance(algorithm_names, (list, tuple)):
        return jsonify({"error": "Thiếu start, end hoặc algorithms hợp lệ."}), 400
    if not TRAFFIC_GRAPH.has_node(start) or not TRAFFIC_GRAPH.has_node(goal):
        return jsonify({"error": "Node bắt đầu hoặc kết thúc không hợp lệ."}), 400
    try:
        results = MetricsService.compare_algorithms(
            TRAFFIC_GRAPH,
            start,
            goal,
            profile,
            algorithm_names,
        )
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(
        {
            "start": start,
            "end": goal,
            "cost_profile": profile,
            "metrics": MetricsService.format_summary_metrics(results),
        }
    )


@app.route("/api/graph", methods=["GET"])
def get_graph():
    """Trả graph core theo format GeoJSON adapter của frontend."""

    return jsonify(graph_response())


@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Trả danh sách node cho selection."""

    return jsonify(
        [
            {
                "id": node_id,
                "name": node["name"],
                "type": node.get("type", "intersection"),
                "address": node.get("address", ""),
            }
            for node_id, node in sorted(NODES.items(), key=lambda item: item[0])
        ]
    )


@app.route("/api/food-places", methods=["GET"])
def get_food_places():
    """Trả tối đa 40 địa điểm nằm trong vùng lọc."""

    places = []
    for node_id, node in NODES.items():
        if node.get("type") != "food":
            continue
        places.append(
            {
                "id": node_id,
                "name": node["name"],
                "address": node.get("address", ""),
                "lat": node["lat"],
                "lng": node["lng"],
                "type": "food",
                "source": node.get("source", "clean_dataset"),
                "on_edge": node.get("on_edge"),
                "within_food_area": point_in_polygon(
                    float(node["lat"]), float(node["lng"])
                ),
            }
        )
    return jsonify({"count": len(places), "places": places})


@app.route("/api/search", methods=["POST"])
def search_route():
    """Chạy thuật toán graph core cho một cặp node."""

    data = request.get_json(silent=True) or {}
    start = str(data.get("start", ""))
    end = str(data.get("end", ""))
    algorithm = str(data.get("algorithm", "")).lower()
    profile_name = profile_from_request(data)
    if not start or not end or algorithm not in ALGORITHM_REGISTRY:
        return jsonify({"error": "Thiếu hoặc sai start, end, algorithm."}), 400
    if not TRAFFIC_GRAPH.has_node(start) or not TRAFFIC_GRAPH.has_node(end):
        return jsonify({"error": "Node bắt đầu hoặc kết thúc không hợp lệ."}), 400

    try:
        result = ALGORITHM_REGISTRY[algorithm](
            TRAFFIC_GRAPH,
            start,
            end,
            COST_PROFILES[profile_name],
        )
    except NodeNotFoundError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(serialize_core_result(result))


@app.route("/api/tsp", methods=["POST"])
def tsp_route():
    """Tối ưu nhiều waypoint bằng A* kết hợp Nearest Neighbor."""

    data = request.get_json(silent=True) or {}
    waypoints = data.get("waypoints")
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        return jsonify({"error": "Cần ít nhất 2 waypoint để tính TSP."}), 400
    if any(str(waypoint) not in NODES for waypoint in waypoints):
        return jsonify({"error": "Danh sách waypoint không hợp lệ."}), 400
    profile = profile_from_request(data)
    start_node = str(data.get("start", waypoints[0]))
    if start_node not in NODES:
        return jsonify({"error": "Start node không hợp lệ."}), 400

    try:
        result = MULTI_LOCATION_SERVICE.optimize_delivery_route(
            start_node=start_node,
            waypoints=[str(waypoint) for waypoint in waypoints],
            graph=TRAFFIC_GRAPH,
            profile=profile,
            return_to_start=bool(data.get("return_to_start", False)),
        )
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400

    animation_log = []
    for node_id in result["path"]:
        animation_log.extend(
            [
                {
                    "step": len(animation_log) + 1,
                    "node": node_id,
                    "status": "frontier",
                    "parent": None,
                },
                {
                    "step": len(animation_log) + 1,
                    "node": node_id,
                    "status": "visited",
                    "parent": None,
                },
            ]
        )
    return jsonify(
        {
            "path": result["path"],
            "visiting_order": result["visiting_order"],
            "animation_log": animation_log,
            "stats": {
                "nodes_explored": result["nodes_explored"],
                "total_distance": result["total_distance"],
                "total_time": result["total_time"],
                "total_cost": result["total_cost"],
                "processing_time_ms": result["processing_time_ms"],
            },
            "algorithm": result["algorithm"],
            "found": result["found"],
            "explanation": "Nearest Neighbor sắp xếp các waypoint theo chi phí A* thấp nhất ở mỗi bước.",
            "unvisited_left": result["unvisited_left"],
        }
    )


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=8000, debug=debug)
