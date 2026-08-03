"""Uniform-cost search using the approved traffic-aware edge cost."""

from heapq import heappop, heappush
from itertools import count
from time import perf_counter

from backend.app.algorithms.common import build_search_result, reconstruct_path
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import CostProfile
from backend.app.core.search_models import (
    FrontierItem,
    SearchResult,
    SearchTraceStep,
)


def search(
    graph: TrafficGraph,
    start: str,
    goal: str,
    profile: CostProfile,
) -> SearchResult:
    """Find a minimum-cost route using deterministic uniform-cost search."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)

    insertion_order = count()
    frontier = [(0.0, next(insertion_order), start)]
    best_g = {start: 0.0}
    parents: dict[str, str | None] = {start: None}
    depths = {start: 0}
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    path: list[str] = []

    while frontier:
        g_cost, _, current = heappop(frontier)
        if g_cost > best_g[current]:
            continue

        visited_order.append(current)
        if current == goal:
            path = reconstruct_path(parents, current)
        else:
            for neighbor in graph.get_traversable_neighbors(current):
                candidate_g = g_cost + graph.get_edge_cost(
                    current,
                    neighbor,
                    profile,
                )
                if candidate_g >= best_g.get(neighbor, float("inf")):
                    continue

                best_g[neighbor] = candidate_g
                parents[neighbor] = current
                depths[neighbor] = depths[current] + 1
                heappush(
                    frontier,
                    (candidate_g, next(insertion_order), neighbor),
                )

        frontier_steps.append(
            SearchTraceStep(
                step=len(frontier_steps) + 1,
                current=FrontierItem(
                    node_id=current,
                    parent_id=parents[current],
                    depth=depths[current],
                    g_cost=g_cost,
                ),
                visited=list(visited_order),
                frontier=_build_logical_frontier(
                    frontier,
                    best_g,
                    parents,
                    depths,
                ),
                path_so_far=reconstruct_path(parents, current),
            )
        )

        if path:
            break

    return build_search_result(
        algorithm="ucs",
        graph=graph,
        profile=profile,
        path=path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


def _build_logical_frontier(
    frontier: list[tuple[float, int, str]],
    best_g: dict[str, float],
    parents: dict[str, str | None],
    depths: dict[str, int],
) -> list[FrontierItem]:
    best_entries: dict[str, tuple[float, int, str]] = {}
    for entry in frontier:
        g_cost, _, node_id = entry
        if g_cost != best_g.get(node_id):
            continue
        if node_id not in best_entries or entry < best_entries[node_id]:
            best_entries[node_id] = entry

    return [
        FrontierItem(
            node_id=node_id,
            parent_id=parents[node_id],
            depth=depths[node_id],
            g_cost=g_cost,
        )
        for g_cost, _, node_id in sorted(best_entries.values())
    ]


__all__ = ["search"]
