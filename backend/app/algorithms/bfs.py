"""Breadth-first search over the public traffic graph interface."""

from collections import deque
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
    """Find a minimum-hop route using deterministic breadth-first search."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)

    frontier = deque([start])
    discovered = {start}
    parents: dict[str, str | None] = {start: None}
    depths = {start: 0}
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    path: list[str] = []

    while frontier:
        current = frontier.popleft()
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
                    for node_id in frontier
                ],
                path_so_far=reconstruct_path(parents, current),
            )
        )

        if path:
            break

    return build_search_result(
        algorithm="bfs",
        graph=graph,
        profile=profile,
        path=path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


__all__ = ["search"]
