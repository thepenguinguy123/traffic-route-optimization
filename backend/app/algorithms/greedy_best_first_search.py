"""Greedy best-first graph search."""

from heapq import heappop, heappush
from itertools import count
from time import perf_counter

from .common import build_search_result, reconstruct_path
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import FrontierItem, SearchResult, SearchTraceStep


def search(
    graph: TrafficGraph,
    start: str,
    goal: str,
    profile: CostProfile,
) -> SearchResult:
    """Search by expanding the node with the smallest distance heuristic."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)
    insertion_order = count()
    frontier = [
        (
            graph.estimate_straight_line_distance(start, goal),
            next(insertion_order),
            start,
        )
    ]
    parents: dict[str, str | None] = {start: None}
    depths = {start: 0}
    discovered = {start}
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    path: list[str] = []

    while frontier:
        _, _, current = heappop(frontier)
        visited_order.append(current)
        if current == goal:
            path = reconstruct_path(parents, current)
        else:
            for neighbor in graph.get_traversable_neighbors(current):
                if neighbor in discovered:
                    continue
                discovered.add(neighbor)
                parents[neighbor] = current
                depths[neighbor] = depths[current] + 1
                heuristic = graph.estimate_straight_line_distance(
                    neighbor,
                    goal,
                )
                heappush(frontier, (heuristic, next(insertion_order), neighbor))

        frontier_steps.append(
            SearchTraceStep(
                step=len(frontier_steps) + 1,
                current=FrontierItem(
                    node_id=current,
                    parent_id=parents[current],
                    depth=depths[current],
                    h_cost=graph.estimate_straight_line_distance(
                        current,
                        goal,
                    ),
                ),
                visited=list(visited_order),
                frontier=[
                    FrontierItem(
                        node_id=node_id,
                        parent_id=parents[node_id],
                        depth=depths[node_id],
                        h_cost=heuristic,
                    )
                    for heuristic, _, node_id in sorted(frontier)
                ],
                path_so_far=reconstruct_path(parents, current),
            )
        )
        if path:
            break

    return build_search_result(
        algorithm="greedy_best_first",
        graph=graph,
        profile=profile,
        path=path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


__all__ = ["search"]
