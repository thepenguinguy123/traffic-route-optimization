"""Iterative depth-first search over the public traffic graph interface."""

from time import perf_counter

from .common import build_search_result, reconstruct_path
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import (
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
    """Find a route using deterministic iterative depth-first search."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)

    frontier = [start]
    discovered = {start}
    parents: dict[str, str | None] = {start: None}
    depths = {start: 0}
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    path: list[str] = []

    while frontier:
        current = frontier.pop()
        visited_order.append(current)

        if current == goal:
            path = reconstruct_path(parents, current)
        else:
            neighbors = graph.get_traversable_neighbors(current)
            for neighbor in reversed(neighbors):
                if neighbor in discovered:
                    continue
                discovered.add(neighbor)
                parents[neighbor] = current
                depths[neighbor] = depths[current] + 1
                frontier.append(neighbor)

        frontier_steps.append(
            SearchTraceStep(
                step=len(frontier_steps) + 1,
                current=FrontierItem(
                    node_id=current,
                    parent_id=parents[current],
                    depth=depths[current],
                ),
                visited=list(visited_order),
                frontier=[
                    FrontierItem(
                        node_id=node_id,
                        parent_id=parents[node_id],
                        depth=depths[node_id],
                    )
                    for node_id in reversed(frontier)
                ],
                path_so_far=reconstruct_path(parents, current),
            )
        )

        if path:
            break

    return build_search_result(
        algorithm="dfs",
        graph=graph,
        profile=profile,
        path=path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


__all__ = ["search"]
