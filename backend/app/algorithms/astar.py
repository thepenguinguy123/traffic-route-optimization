"""Approved Haversine lower-bound helpers for A-star search."""

from heapq import heappop, heappush
from itertools import count
from time import perf_counter

from .common import build_search_result, reconstruct_path
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import (
    FrontierItem,
    SearchResult,
    SearchTraceStep,
)


def calculate_heuristic_coefficient(
    graph: TrafficGraph,
    profile: CostProfile,
) -> float:
    """Return the minimum traversable edge cost per Haversine kilometre."""

    minimum_ratio: float | None = None
    for node in graph.get_all_nodes():
        for neighbor in graph.get_traversable_neighbors(node.id):
            distance = graph.estimate_straight_line_distance(
                node.id,
                neighbor,
            )
            if distance <= 0:
                continue

            ratio = graph.get_edge_cost(node.id, neighbor, profile) / distance
            if minimum_ratio is None or ratio < minimum_ratio:
                minimum_ratio = ratio

    return 0.0 if minimum_ratio is None else minimum_ratio


def estimate_heuristic(
    graph: TrafficGraph,
    node: str,
    goal: str,
    k: float,
) -> float:
    """Return the approved cost-scaled Haversine estimate to the goal."""

    return k * graph.estimate_straight_line_distance(node, goal)


def search(
    graph: TrafficGraph,
    start: str,
    goal: str,
    profile: CostProfile,
) -> SearchResult:
    """Find a minimum-cost route using the approved A-star heuristic."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)

    k = calculate_heuristic_coefficient(graph, profile)
    insertion_order = count()
    start_h = estimate_heuristic(graph, start, goal, k)
    frontier = [((start_h, next(insertion_order), start), 0.0)]
    best_g = {start: 0.0}
    parents: dict[str, str | None] = {start: None}
    depths = {start: 0}
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    path: list[str] = []

    while frontier:
        (f_cost, _, current), g_cost = heappop(frontier)
        if g_cost > best_g[current]:
            continue

        visited_order.append(current)
        h_cost = estimate_heuristic(graph, current, goal, k)
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
                candidate_h = estimate_heuristic(graph, neighbor, goal, k)
                heappush(
                    frontier,
                    (
                        (
                            candidate_g + candidate_h,
                            next(insertion_order),
                            neighbor,
                        ),
                        candidate_g,
                    ),
                )

        frontier_steps.append(
            SearchTraceStep(
                step=len(frontier_steps) + 1,
                current=FrontierItem(
                    node_id=current,
                    parent_id=parents[current],
                    depth=depths[current],
                    g_cost=g_cost,
                    h_cost=h_cost,
                    f_cost=f_cost,
                ),
                visited=list(visited_order),
                frontier=_build_logical_frontier(
                    frontier,
                    best_g,
                    parents,
                    depths,
                    graph,
                    goal,
                    k,
                ),
                path_so_far=reconstruct_path(parents, current),
            )
        )

        if path:
            break

    return build_search_result(
        algorithm="astar",
        graph=graph,
        profile=profile,
        path=path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


def _build_logical_frontier(
    frontier: list[tuple[tuple[float, int, str], float]],
    best_g: dict[str, float],
    parents: dict[str, str | None],
    depths: dict[str, int],
    graph: TrafficGraph,
    goal: str,
    k: float,
) -> list[FrontierItem]:
    best_entries: dict[
        str,
        tuple[tuple[float, int, str], float],
    ] = {}
    for entry in frontier:
        (_, _, node_id), g_cost = entry
        if g_cost != best_g.get(node_id):
            continue
        if node_id not in best_entries or entry < best_entries[node_id]:
            best_entries[node_id] = entry

    logical_frontier = []
    for (f_cost, _, node_id), g_cost in sorted(best_entries.values()):
        logical_frontier.append(
            FrontierItem(
                node_id=node_id,
                parent_id=parents[node_id],
                depth=depths[node_id],
                g_cost=g_cost,
                h_cost=estimate_heuristic(graph, node_id, goal, k),
                f_cost=f_cost,
            )
        )
    return logical_frontier


__all__ = [
    "calculate_heuristic_coefficient",
    "estimate_heuristic",
    "search",
]
