"""Iterative-deepening A* search with an exact directed-graph lower bound."""

from heapq import heappop, heappush
from itertools import count
from time import perf_counter

from .common import build_search_result
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import FrontierItem, SearchResult, SearchTraceStep


_EPSILON = 1e-9


def search(
    graph: TrafficGraph,
    start: str,
    goal: str,
    profile: CostProfile,
) -> SearchResult:
    """Find a minimum-cost route with iterative-deepening A*."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)

    neighbors, edge_costs = _build_traversable_costs(graph, profile)
    heuristic = _calculate_remaining_costs(graph, goal, neighbors, edge_costs)
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    found_path: list[str] = []

    if start not in heuristic:
        return build_search_result(
            algorithm="ida_star",
            graph=graph,
            profile=profile,
            path=found_path,
            visited_order=visited_order,
            frontier_steps=frontier_steps,
            started_at=started_at,
        )

    bound = heuristic[start]

    def visit(
        current: str,
        cost: float,
        path: list[str],
        path_nodes: set[str],
        best_cost_in_iteration: dict[str, float],
    ) -> float | None:
        """Visit one IDA* branch and return the next threshold."""

        nonlocal found_path

        remaining_cost = heuristic.get(current)
        if remaining_cost is None:
            return float("inf")

        score = cost + remaining_cost
        if score > bound + _EPSILON:
            return score

        previous_cost = best_cost_in_iteration.get(current)
        if previous_cost is not None and cost >= previous_cost - _EPSILON:
            return float("inf")
        best_cost_in_iteration[current] = cost

        visited_order.append(current)
        frontier_steps.append(
            SearchTraceStep(
                step=len(frontier_steps) + 1,
                current=FrontierItem(
                    node_id=current,
                    parent_id=path[-2] if len(path) > 1 else None,
                    depth=len(path) - 1,
                    g_cost=cost,
                    h_cost=remaining_cost,
                    f_cost=score,
                ),
                visited=list(visited_order),
                frontier=[],
                path_so_far=list(path),
            )
        )

        if current == goal:
            found_path = list(path)
            return None

        next_bound = float("inf")
        for neighbor in neighbors[current]:
            if neighbor in path_nodes:
                continue

            candidate_cost = cost + edge_costs[(current, neighbor)]
            result = visit(
                neighbor,
                candidate_cost,
                path + [neighbor],
                path_nodes | {neighbor},
                best_cost_in_iteration,
            )
            if result is None:
                return None
            next_bound = min(next_bound, result)

        return next_bound

    while True:
        result = visit(start, 0.0, [start], {start}, {})
        if result is None or result == float("inf"):
            break
        bound = result

    return build_search_result(
        algorithm="ida_star",
        graph=graph,
        profile=profile,
        path=found_path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


def _build_traversable_costs(
    graph: TrafficGraph,
    profile: CostProfile,
) -> tuple[dict[str, list[str]], dict[tuple[str, str], float]]:
    """Precompute traversable neighbors and their edge costs."""

    neighbors: dict[str, list[str]] = {}
    edge_costs: dict[tuple[str, str], float] = {}
    for node in graph.get_all_nodes():
        node_neighbors = graph.get_traversable_neighbors(node.id)
        neighbors[node.id] = node_neighbors
        for neighbor in node_neighbors:
            edge_costs[(node.id, neighbor)] = graph.get_edge_cost(
                node.id,
                neighbor,
                profile,
            )
    return neighbors, edge_costs


def _calculate_remaining_costs(
    graph: TrafficGraph,
    goal: str,
    neighbors: dict[str, list[str]],
    edge_costs: dict[tuple[str, str], float],
) -> dict[str, float]:
    """Compute exact remaining-cost lower bounds with reverse Dijkstra."""

    reverse_edges: dict[str, list[tuple[str, float]]] = {
        node.id: [] for node in graph.get_all_nodes()
    }
    for source, node_neighbors in neighbors.items():
        for target in node_neighbors:
            reverse_edges[target].append((source, edge_costs[(source, target)]))

    insertion_order = count()
    remaining_costs = {goal: 0.0}
    frontier = [(0.0, next(insertion_order), goal)]
    while frontier:
        cost, _, current = heappop(frontier)
        if cost > remaining_costs[current] + _EPSILON:
            continue

        for predecessor, edge_cost in reverse_edges[current]:
            candidate_cost = cost + edge_cost
            if (
                candidate_cost
                >= remaining_costs.get(
                    predecessor,
                    float("inf"),
                )
                - _EPSILON
            ):
                continue
            remaining_costs[predecessor] = candidate_cost
            heappush(
                frontier,
                (candidate_cost, next(insertion_order), predecessor),
            )

    return remaining_costs


__all__ = ["search"]
