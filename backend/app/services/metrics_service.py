"""Run comparable searches and serialize their benchmark metrics."""

from collections.abc import Iterable
from typing import Any

from ..algorithms.registry import ALGORITHM_REGISTRY
from ..core.cost_profiles import COST_PROFILES
from ..core.graph import TrafficGraph
from ..core.search_models import SearchResult


DEFAULT_COMPARISON_ALGORITHMS = (
    "bfs",
    "dfs",
    "ucs",
    "astar",
    "ida_star",
    "greedy_best_first",
)


class MetricsService:
    """Coordinate algorithm comparisons against one graph."""

    @staticmethod
    def compare_algorithms(
        graph: TrafficGraph,
        start: str,
        goal: str,
        profile_name: str = "balanced",
        algorithm_names: Iterable[str] = DEFAULT_COMPARISON_ALGORITHMS,
    ) -> list[SearchResult]:
        """Coordinate algorithm comparisons against one graph."""

        if profile_name not in COST_PROFILES:
            raise ValueError(f"Unknown cost profile: {profile_name}")
        profile = COST_PROFILES[profile_name]
        results = []
        for algorithm_name in algorithm_names:
            if algorithm_name not in ALGORITHM_REGISTRY:
                raise ValueError(f"Unknown algorithm: {algorithm_name}")
            results.append(
                ALGORITHM_REGISTRY[algorithm_name](graph, start, goal, profile)
            )
        return results

    @staticmethod
    def format_summary_metrics(results: Iterable[SearchResult]) -> list[dict[str, Any]]:
        """Convert search results into stable API-ready metric records."""

        return [
            {
                "algorithm": result.algorithm,
                "found": result.found,
                "explored_nodes": result.explored_nodes,
                "processing_time_ms": round(result.processing_time_ms, 4),
                "total_distance_km": (
                    round(result.total_distance, 3) if result.found else None
                ),
                "total_time_min": round(result.total_time, 3) if result.found else None,
                "total_cost": round(result.total_cost, 4) if result.found else None,
                "path_length": len(result.path) if result.found else 0,
            }
            for result in results
        ]


__all__ = ["DEFAULT_COMPARISON_ALGORITHMS", "MetricsService"]
