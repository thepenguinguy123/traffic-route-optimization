"""Route planning across multiple graph locations."""

from time import perf_counter
from typing import Any, Callable

from ..algorithms.astar import search as astar_search
from ..algorithms.nearest_neighbor import nearest_neighbor_tsp
from ..core.cost_profiles import COST_PROFILES
from ..core.graph import TrafficGraph
from ..core.models import CostProfile

SearchFunction = Callable[..., Any]


class MultiLocationService:
    """Plan routes that visit multiple graph locations."""

    def __init__(self, search_fn: SearchFunction | None = None) -> None:
        self.search_fn = search_fn or astar_search

    def set_search_function(self, search_fn: SearchFunction) -> None:
        """Replace the algorithm used to solve each route segment."""

        self.search_fn = search_fn

    def build_matrices(
        self,
        graph: TrafficGraph,
        nodes: list[str],
        profile: CostProfile | str = "balanced",
        search_fn: SearchFunction | None = None,
    ) -> tuple[dict, dict, dict, dict]:
        """Build pairwise route, cost, distance, and duration matrices."""

        selected_profile = _resolve_profile(profile)
        search = search_fn or self.search_fn
        cost_matrix: dict = {node: {} for node in nodes}
        path_matrix: dict = {node: {} for node in nodes}
        distance_matrix: dict = {node: {} for node in nodes}
        time_matrix: dict = {node: {} for node in nodes}

        for source in nodes:
            for target in nodes:
                if source == target:
                    cost_matrix[source][target] = 0.0
                    path_matrix[source][target] = [source]
                    distance_matrix[source][target] = 0.0
                    time_matrix[source][target] = 0.0
                    continue
                result = search(graph, source, target, selected_profile)
                path, cost, distance, duration = _read_search_result(result)
                cost_matrix[source][target] = cost
                path_matrix[source][target] = path
                distance_matrix[source][target] = distance
                time_matrix[source][target] = duration

        return cost_matrix, path_matrix, distance_matrix, time_matrix

    def optimize_delivery_route(
        self,
        start_node: str,
        waypoints: list[str],
        graph: TrafficGraph,
        profile: CostProfile | str = "balanced",
        return_to_start: bool = False,
        order_mode: str = "auto",
        search_fn: SearchFunction | None = None,
    ) -> dict[str, Any]:
        """Build an automatic or explicitly ordered multi-stop route."""

        started_at = perf_counter()
        if order_mode not in {"auto", "ordered"}:
            raise ValueError("order_mode must be either auto or ordered.")

        clean_waypoints = list(
            dict.fromkeys(node for node in waypoints if node != start_node)
        )
        if not clean_waypoints:
            return {
                "algorithm": (
                    "ordered_tsp" if order_mode == "ordered" else "nearest_neighbor"
                ),
                "found": True,
                "visiting_order": [start_node],
                "path": [start_node],
                "total_cost": 0.0,
                "total_distance": 0.0,
                "total_time": 0.0,
                "nodes_explored": 0,
                "unvisited_left": [],
                "processing_time_ms": 0.0,
            }

        all_locations = [start_node, *clean_waypoints]
        matrices = self.build_matrices(graph, all_locations, profile, search_fn)
        cost_matrix, path_matrix, distance_matrix, time_matrix = matrices
        if order_mode == "ordered":
            ordered_visit = [start_node, *clean_waypoints]
            if return_to_start:
                ordered_visit.append(start_node)
            ordered_segments = list(zip(ordered_visit, ordered_visit[1:]))
            unreachable = [
                target
                for source, target in ordered_segments
                if cost_matrix[source][target] == float("inf")
            ]
            nearest = {
                "visiting_order": ordered_visit,
                "total_cost": sum(
                    cost_matrix[source][target] for source, target in ordered_segments
                ),
                "nodes_explored": len(ordered_visit),
                "unvisited_left": unreachable,
            }
        else:
            nearest = nearest_neighbor_tsp(
                start_node,
                clean_waypoints,
                cost_matrix,
                return_to_start,
            )

        full_path: list[str] = []
        total_distance = 0.0
        total_time = 0.0
        visiting_order = nearest["visiting_order"]
        for source, target in zip(visiting_order, visiting_order[1:]):
            segment = path_matrix.get(source, {}).get(target, [])
            if not segment:
                break
            full_path.extend(segment if not full_path else segment[1:])
            total_distance += distance_matrix.get(source, {}).get(target, 0.0)
            total_time += time_matrix.get(source, {}).get(target, 0.0)

        all_waypoints_reached = not nearest["unvisited_left"]
        return_trip_completed = not return_to_start or visiting_order[-1] == start_node

        return {
            "algorithm": (
                "ordered_tsp" if order_mode == "ordered" else "nearest_neighbor"
            ),
            "found": all_waypoints_reached and return_trip_completed,
            "visiting_order": visiting_order,
            "path": full_path or [start_node],
            "total_cost": nearest["total_cost"],
            "total_distance": round(total_distance, 3),
            "total_time": round(total_time, 3),
            "nodes_explored": nearest["nodes_explored"],
            "unvisited_left": nearest["unvisited_left"],
            "processing_time_ms": round((perf_counter() - started_at) * 1000, 3),
            "is_optimal": False,
        }


def _resolve_profile(profile: CostProfile | str) -> CostProfile:
    if isinstance(profile, CostProfile):
        return profile
    if profile not in COST_PROFILES:
        raise ValueError(f"Unknown cost profile: {profile}")
    return COST_PROFILES[profile]


def _read_search_result(result: Any) -> tuple[list[str], float, float, float]:
    if isinstance(result, dict):
        return (
            result.get("path", []),
            result.get("total_cost", float("inf")),
            result.get("total_distance", 0.0),
            result.get("total_time", 0.0),
        )
    return (
        result.path if result.found else [],
        result.total_cost if result.found else float("inf"),
        result.total_distance if result.found else 0.0,
        result.total_time if result.found else 0.0,
    )
