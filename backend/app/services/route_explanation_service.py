"""Generate human-readable explanations for traffic-aware route results."""

from collections.abc import Iterable
from typing import Any

from ..algorithms.registry import ALGORITHM_REGISTRY
from ..core.cost_profiles import COST_PROFILES
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import SearchResult


ALGORITHM_GUARANTEES: dict[str, str] = {
    "bfs": "Complete on a finite graph and optimal for the fewest number of hops, not weighted traffic cost.",
    "dfs": "Complete on this finite graph with cycle protection, but it does not guarantee a minimum-cost route.",
    "ucs": "Complete and optimal when every traversable edge has a non-negative traffic cost.",
    "astar": "Complete and optimal because the cost-scaled Haversine heuristic is admissible and consistent.",
    "ida_star": "Optimal with the current non-negative edge costs and the exact reverse-cost lower bound used by this implementation.",
    "greedy_best_first": "Complete on this finite graph with cycle protection, but it does not guarantee an optimal weighted route.",
}

PROFILE_LABELS = {
    "balanced": "balanced total cost",
    "shortest_distance": "distance-prioritized traffic cost",
    "fastest_route": "time-prioritized traffic cost",
    "avoid_congestion": "lowest congestion-weighted cost",
}


class RouteExplanationService:
    """Build structured and human-readable route explanations."""

    @staticmethod
    def explain_search(
        graph: TrafficGraph,
        result: SearchResult,
        start: str,
        goal: str,
        profile: CostProfile,
        include_alternative: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        """Explain why a two-location result was selected."""

        if not result.found:
            details = {
                "status": "not_found",
                "criterion": PROFILE_LABELS.get(profile.name, profile.name),
                "guarantee": ALGORITHM_GUARANTEES.get(
                    result.algorithm,
                    "Guarantee not documented.",
                ),
                "high_impact_segments": [],
                "alternative": None,
            }
            return (
                f"No route was found from {graph.get_node(start).name} to "
                f"{graph.get_node(goal).name} under the "
                f"{PROFILE_LABELS.get(profile.name, profile.name)} profile.",
                details,
            )

        segments = RouteExplanationService._impact_segments(graph, result.path)
        alternative = (
            RouteExplanationService._find_alternative(
                graph,
                result,
                start,
                goal,
                profile,
            )
            if include_alternative
            else None
        )
        criterion = PROFILE_LABELS.get(profile.name, profile.name)
        guarantee = ALGORITHM_GUARANTEES.get(
            result.algorithm,
            "Guarantee not documented.",
        )

        sentence = (
            f"The route was selected as the {criterion} route from "
            f"{graph.get_node(start).name} to {graph.get_node(goal).name}. "
            f"{guarantee}"
        )
        if segments:
            sentence += (
                f" It contains {len(segments)} high-impact segment(s) "
                "with elevated congestion or risk; review the highlighted "
                "edge metrics for details."
            )
        else:
            sentence += (
                " No segment exceeds the current congestion/risk review thresholds."
            )
        if alternative is not None:
            sentence += (
                f" A different candidate route has cost "
                f"{alternative['total_cost']:.4f} compared with "
                f"{result.total_cost:.4f} for the selected route."
            )

        details = {
            "status": "found",
            "criterion": criterion,
            "guarantee": guarantee,
            "high_impact_segments": segments,
            "alternative": alternative,
        }
        return sentence, details

    @staticmethod
    def explain_multi_location(
        graph: TrafficGraph,
        result: dict[str, Any],
        profile: CostProfile,
        order_mode: str,
    ) -> tuple[str, dict[str, Any]]:
        """Explain an automatic or explicitly ordered multi-stop result."""

        visiting_order = [str(node_id) for node_id in result.get("visiting_order", [])]
        order_names = [graph.get_node(node_id).name for node_id in visiting_order]
        is_ordered = order_mode == "ordered"
        if is_ordered:
            guarantee = (
                "The requested waypoint order is guaranteed; each segment is "
                "optimized with A*, but the global order is not changed."
            )
        else:
            guarantee = (
                "Nearest Neighbor provides an approximate visiting order and "
                "does not guarantee the globally optimal TSP tour."
            )

        details = {
            "status": "found" if result.get("found") else "partial",
            "criterion": PROFILE_LABELS.get(profile.name, profile.name),
            "guarantee": guarantee,
            "visiting_order": visiting_order,
            "visiting_order_names": order_names,
            "unvisited": [str(node_id) for node_id in result.get("unvisited_left", [])],
            "is_optimal": False,
            "order_preserved": bool(is_ordered and result.get("found")),
            "segments_optimized": bool(result.get("found")),
        }
        if not result.get("found"):
            sentence = "The multi-location route is partial because one or more waypoints are unreachable."
        elif is_ordered:
            sentence = "The route preserves the requested waypoint order and optimizes each segment with A*."
        else:
            sentence = "The route uses Nearest Neighbor to choose the next waypoint by the lowest pairwise route cost."
        return f"{sentence} {guarantee}", details

    @staticmethod
    def _impact_segments(
        graph: TrafficGraph,
        path: list[str],
    ) -> list[dict[str, Any]]:
        """Return path segments with congestion or risk requiring attention."""

        segments = []
        for source, target in zip(path, path[1:]):
            edge = graph.get_edge(source, target)
            if edge.congestion_level < 4 and edge.risk_factor < 3.0:
                continue
            segments.append(
                {
                    "source": source,
                    "target": target,
                    "source_name": graph.get_node(source).name,
                    "target_name": graph.get_node(target).name,
                    "congestion": edge.congestion_level,
                    "risk": edge.risk_factor,
                    "road_type": edge.road_type,
                }
            )
        return segments

    @staticmethod
    def _find_alternative(
        graph: TrafficGraph,
        result: SearchResult,
        start: str,
        goal: str,
        profile: CostProfile,
    ) -> dict[str, Any] | None:
        """Find one different candidate route for comparison when available."""

        candidates: Iterable[str] = ("ucs", "astar", "bfs", "greedy_best_first")
        for algorithm_name in candidates:
            if algorithm_name == result.algorithm:
                continue
            candidate = ALGORITHM_REGISTRY[algorithm_name](graph, start, goal, profile)
            if candidate.found and candidate.path != result.path:
                return {
                    "algorithm": algorithm_name,
                    "path": candidate.path,
                    "total_cost": candidate.total_cost,
                    "total_distance": candidate.total_distance,
                    "total_time": candidate.total_time,
                }
        return None


__all__ = ["ALGORITHM_GUARANTEES", "RouteExplanationService"]
