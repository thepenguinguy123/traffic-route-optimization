"""Flask API for graph search, metrics, TSP, and public map configuration."""

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
from ..repositories.clean_dataset_repository import (
    load_clean_graph,
    load_traffic_scenarios,
)
from ..services.multi_location_service import MultiLocationService
from ..services.route_explanation_service import RouteExplanationService
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
        "description": "Prioritize routes with the fewest hops.",
        "group": "graph_core",
    },
    {
        "id": "dfs",
        "label": "DFS",
        "description": "Explore each branch depth-first.",
        "group": "graph_core",
    },
    {
        "id": "ucs",
        "label": "UCS",
        "description": "Minimize accumulated traffic cost.",
        "group": "graph_core",
    },
    {
        "id": "astar",
        "label": "A*",
        "description": "Combine UCS with a distance heuristic.",
        "group": "graph_core",
    },
    {
        "id": "greedy_best_first",
        "label": "Greedy Best-First",
        "description": "Prioritize nodes nearest to the destination.",
        "group": "graph_core",
    },
    {
        "id": "ida_star",
        "label": "IDA*",
        "description": "Use iterative-deepening A* with bounded memory.",
        "group": "graph_core",
    },
    {
        "id": "tsp",
        "label": "TSP",
        "description": "Visit multiple waypoints in an optimized order.",
        "group": "multi_stop",
    },
]

COST_OPTIONS = [
    {
        "id": "balanced",
        "label": "Balanced",
        "description": "Balance distance, travel time, and risk.",
    },
    {
        "id": "shortest_distance",
        "label": "Shortest Distance",
        "description": "Prioritize total distance.",
    },
    {
        "id": "fastest_route",
        "label": "Fastest Route",
        "description": "Prioritize travel time.",
    },
    {
        "id": "avoid_congestion",
        "label": "Avoid Congestion",
        "description": "Reduce the impact of congestion.",
    },
]


def build_traffic_graph() -> TrafficGraph:
    """Load the clean node and edge datasets into the traffic graph."""

    return load_clean_graph()


TRAFFIC_GRAPH = build_traffic_graph()
MULTI_LOCATION_SERVICE = MultiLocationService()
TRAFFIC_SCENARIOS = load_traffic_scenarios()
DEFAULT_SCENARIO = "normal"


def scenario_from_request(data: dict) -> str:
    """Resolve and validate a requested traffic scenario."""

    scenario = str(data.get("scenario", DEFAULT_SCENARIO))
    if scenario not in TRAFFIC_SCENARIOS:
        raise ValueError(f"Unknown traffic scenario: {scenario}")
    return scenario


def graph_from_request(data: dict) -> TrafficGraph:
    """Return the cached graph variant selected by the request."""

    return load_clean_graph(scenario=scenario_from_request(data))


def graph_response(graph: TrafficGraph = TRAFFIC_GRAPH) -> dict:
    """Serialize the traffic graph for the frontend map adapter."""

    graph = graph.to_dict()
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
    """Resolve the requested cost profile with legacy cost_type support."""

    profile = data.get("cost_profile")
    if profile in COST_PROFILES:
        return profile
    legacy_map = {
        "distance": "shortest_distance",
        "time": "fastest_route",
        "combined": "balanced",
    }
    return legacy_map.get(data.get("cost_type"), "balanced")


def serialize_core_result(
    result: SearchResult,
    explanation: str | None = None,
    explanation_details: dict | None = None,
) -> dict:
    """Serialize a search result and its animation trace for the frontend."""

    animation_log = []
    for trace in result.frontier_steps:
        for frontier_item in trace.frontier:
            animation_log.append(
                {
                    "step": len(animation_log) + 1,
                    "node": frontier_item.node_id,
                    "status": "frontier",
                    "parent": frontier_item.parent_id,
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
        "visited_order": result.visited_order,
        "animation_log": animation_log,
        "stats": {
            "nodes_explored": result.explored_nodes,
            "total_distance": round(result.total_distance, 3),
            "total_time": round(result.total_time, 3),
            "total_cost": round(result.total_cost, 4),
            "processing_time_ms": round(result.processing_time_ms, 3),
        },
        "explanation": explanation if explanation is not None else result.message,
        "explanation_details": explanation_details or {},
        "algorithm": result.algorithm,
        "found": result.found,
        "trace": [asdict(trace) for trace in result.frontier_steps],
    }


@app.route("/")
def health_check():
    """Return the backend health status."""

    return jsonify({"status": "ok", "message": "API is running"})


@app.route("/api/config", methods=["GET"])
def get_public_config():
    """Return only public configuration required by the frontend."""

    return jsonify(
        {
            "map_tiles_key": os.getenv("GOONG_MAP_TILES_KEY", ""),
            "traffic_scenarios": [
                {"id": key, "description": value.get("description", "")}
                for key, value in TRAFFIC_SCENARIOS.items()
            ],
        }
    )


@app.route("/api/traffic-scenarios", methods=["GET"])
def get_traffic_scenarios():
    """Return selectable reproducible traffic scenarios."""

    return jsonify(
        [
            {"id": key, "description": value.get("description", "")}
            for key, value in TRAFFIC_SCENARIOS.items()
        ]
    )


@app.route("/api/algorithms", methods=["GET"])
def get_algorithms():
    """Return algorithm options for the frontend selector."""

    return jsonify(ALGORITHM_OPTIONS)


@app.route("/api/cost-profiles", methods=["GET"])
def get_cost_profiles():
    """Return supported cost profiles for the frontend selector."""

    return jsonify(COST_OPTIONS)


@app.route("/api/metrics", methods=["POST"])
def compare_metrics():
    """Compare algorithms for the same endpoints and cost profile."""

    data = request.get_json(silent=True) or {}
    start = str(data.get("start", ""))
    goal = str(data.get("end", data.get("goal", "")))
    profile = profile_from_request(data)
    try:
        graph = graph_from_request(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    algorithm_names = data.get("algorithms", DEFAULT_COMPARISON_ALGORITHMS)
    if not start or not goal or not isinstance(algorithm_names, (list, tuple)):
        return jsonify({"error": "Valid start, end, and algorithms are required."}), 400
    if not graph.has_node(start) or not graph.has_node(goal):
        return jsonify({"error": "The start or end node is invalid."}), 400
    try:
        results = MetricsService.compare_algorithms(
            graph,
            start,
            goal,
            profile,
            algorithm_names,
        )
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    metric_rows = MetricsService.format_summary_metrics(results)
    for metric, result in zip(metric_rows, results):
        explanation, explanation_details = RouteExplanationService.explain_search(
            graph,
            result,
            start,
            goal,
            COST_PROFILES[profile],
            include_alternative=False,
        )
        serialized = serialize_core_result(result, explanation, explanation_details)
        metric.update(
            {
                "path": serialized["path"],
                "visited_order": serialized["visited_order"],
                "animation_log": serialized["animation_log"],
                "trace": serialized["trace"],
                "explanation": serialized["explanation"],
                "explanation_details": serialized["explanation_details"],
            }
        )

    return jsonify(
        {
            "start": start,
            "end": goal,
            "cost_profile": profile,
            "scenario": scenario_from_request(data),
            "metrics": metric_rows,
        }
    )


@app.route("/api/graph", methods=["GET"])
def get_graph():
    """Return the runtime graph used by the frontend."""

    return jsonify(graph_response())


@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Return selectable runtime graph nodes."""

    return jsonify(
        [
            {
                "id": node.id,
                "name": node.name,
                "type": node.node_type,
                "address": node.metadata.get("address", ""),
            }
            for node in sorted(
                TRAFFIC_GRAPH.get_all_nodes(),
                key=lambda item: item.id,
            )
        ]
    )


@app.route("/api/food-places", methods=["GET"])
def get_food_places():
    """Return up to 40 food places from the runtime graph."""

    places = []
    for node in TRAFFIC_GRAPH.get_all_nodes():
        if node.node_type != "food":
            continue
        places.append(
            {
                "id": node.id,
                "name": node.name,
                "address": node.metadata.get("address", ""),
                "lat": node.latitude,
                "lng": node.longitude,
                "type": "food",
                "source": node.metadata.get("source", "clean_dataset"),
                "on_edge": node.metadata.get("on_edge"),
                "within_food_area": point_in_polygon(
                    node.latitude,
                    node.longitude,
                ),
            }
        )
    return jsonify({"count": len(places), "places": places})


@app.route("/api/search", methods=["POST"])
def search_route():
    """Run one registered graph-search algorithm."""

    data = request.get_json(silent=True) or {}
    start = str(data.get("start", ""))
    end = str(data.get("end", ""))
    algorithm = str(data.get("algorithm", "")).lower()
    profile_name = profile_from_request(data)
    try:
        graph = graph_from_request(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if not start or not end or algorithm not in ALGORITHM_REGISTRY:
        return (
            jsonify({"error": "Valid start, end, and algorithm values are required."}),
            400,
        )
    if not graph.has_node(start) or not graph.has_node(end):
        return jsonify({"error": "The start or end node is invalid."}), 400

    try:
        result = ALGORITHM_REGISTRY[algorithm](
            graph,
            start,
            end,
            COST_PROFILES[profile_name],
        )
    except NodeNotFoundError as error:
        return jsonify({"error": str(error)}), 400
    explanation, explanation_details = RouteExplanationService.explain_search(
        graph,
        result,
        start,
        end,
        COST_PROFILES[profile_name],
    )
    serialized = serialize_core_result(result, explanation, explanation_details)
    serialized["scenario"] = scenario_from_request(data)
    return jsonify(serialized)


@app.route("/api/tsp", methods=["POST"])
def tsp_route():
    """Build a multi-stop route using A* segment costs."""

    data = request.get_json(silent=True) or {}
    waypoints = data.get("waypoints")
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        return jsonify({"error": "At least two waypoints are required for TSP."}), 400
    profile = profile_from_request(data)
    try:
        graph = graph_from_request(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if any(not graph.has_node(str(waypoint)) for waypoint in waypoints):
        return jsonify({"error": "The waypoint list is invalid."}), 400
    start_node = str(data.get("start", waypoints[0]))
    if not graph.has_node(start_node):
        return jsonify({"error": "The start node is invalid."}), 400

    try:
        result = MULTI_LOCATION_SERVICE.optimize_delivery_route(
            start_node=start_node,
            waypoints=[str(waypoint) for waypoint in waypoints],
            graph=graph,
            profile=profile,
            return_to_start=bool(data.get("return_to_start", False)),
            order_mode=str(data.get("order_mode", "auto")),
        )
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400

    explanation, explanation_details = RouteExplanationService.explain_multi_location(
        graph,
        result,
        COST_PROFILES[profile],
        str(data.get("order_mode", "auto")),
    )

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
            "scenario": scenario_from_request(data),
            "found": result["found"],
            "explanation": explanation,
            "explanation_details": explanation_details,
            "is_optimal": explanation_details["is_optimal"],
            "unvisited_left": result["unvisited_left"],
        }
    )


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=8000, debug=debug)
