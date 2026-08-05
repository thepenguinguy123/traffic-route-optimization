"""Shared concrete helpers for route-search algorithms."""

from time import perf_counter

from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import SearchResult, SearchTraceStep


def reconstruct_path(
    parents: dict[str, str | None],
    node_id: str,
) -> list[str]:
    """Return the parent chain from the search start to one node."""

    path = []
    current: str | None = node_id
    while current is not None:
        path.append(current)
        current = parents[current]
    path.reverse()
    return path


def build_search_result(
    algorithm: str,
    graph: TrafficGraph,
    profile: CostProfile,
    path: list[str],
    visited_order: list[str],
    frontier_steps: list[SearchTraceStep],
    started_at: float,
) -> SearchResult:
    """Build the common result and calculate final metrics through the graph."""

    found = bool(path)
    total_distance = graph.calculate_path_distance(path) if found else 0.0
    total_time = graph.calculate_path_time(path) if found else 0.0
    total_cost = graph.calculate_path_cost(path, profile) if found else 0.0
    processing_time_ms = (perf_counter() - started_at) * 1000

    return SearchResult(
        algorithm=algorithm,
        found=found,
        path=list(path),
        visited_order=list(visited_order),
        frontier_steps=list(frontier_steps),
        total_distance=total_distance,
        total_time=total_time,
        total_cost=total_cost,
        explored_nodes=len(visited_order),
        processing_time_ms=processing_time_ms,
        message="Route found." if found else "No route found.",
    )


__all__ = ["reconstruct_path", "build_search_result"]
