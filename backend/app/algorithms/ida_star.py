"""Iterative Deepening A* trên traffic graph core."""

from time import perf_counter

from .astar import (
    calculate_heuristic_coefficient,
    estimate_heuristic,
    search as astar_search,
)
from .common import build_search_result
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import FrontierItem, SearchResult, SearchTraceStep


def search(
    graph: TrafficGraph,
    start: str,
    goal: str,
    profile: CostProfile,
) -> SearchResult:
    """Tìm nghiệm theo các ngưỡng f(n) tăng dần, tôn trọng cạnh một chiều."""

    started_at = perf_counter()
    graph.get_node(start)
    graph.get_node(goal)
    coefficient = calculate_heuristic_coefficient(graph, profile)
    bound = estimate_heuristic(graph, start, goal, coefficient)
    visited_order: list[str] = []
    frontier_steps: list[SearchTraceStep] = []
    found_path: list[str] = []
    max_iterations = max(32, len(graph.get_all_nodes()) * 2)
    iterations = 0
    max_expansions = max(512, len(graph.get_all_nodes()) * 4)
    expansions = 0
    budget_exceeded = False

    def visit(
        current: str,
        cost: float,
        path: list[str],
        best_seen: dict[str, float],
    ):
        nonlocal budget_exceeded, expansions, found_path
        if budget_exceeded:
            return float("inf")
        expansions += 1
        if expansions > max_expansions:
            budget_exceeded = True
            return float("inf")
        if cost >= best_seen.get(current, float("inf")):
            return float("inf")
        best_seen[current] = cost
        visited_order.append(current)
        heuristic = estimate_heuristic(graph, current, goal, coefficient)
        score = cost + heuristic
        if score > bound:
            return score
        if current == goal:
            found_path = list(path)
            return "FOUND"

        minimum_exceeded = float("inf")
        for neighbor in graph.get_traversable_neighbors(current):
            if neighbor in path:
                continue
            candidate_cost = cost + graph.get_edge_cost(current, neighbor, profile)
            result = visit(
                neighbor,
                candidate_cost,
                path + [neighbor],
                best_seen,
            )
            if result == "FOUND":
                return result
            minimum_exceeded = min(minimum_exceeded, result)
        return minimum_exceeded

    while True:
        iterations += 1
        if iterations > max_iterations:
            break
        result = visit(start, 0.0, [start], {})
        if found_path or result == "FOUND":
            break
        if result == float("inf"):
            break
        bound = result

    for step, node_id in enumerate(visited_order, start=1):
        frontier_steps.append(
            SearchTraceStep(
                step=step,
                current=FrontierItem(node_id=node_id, parent_id=None, depth=0),
                visited=visited_order[:step],
                frontier=[],
                path_so_far=[],
            )
        )

    if budget_exceeded and not found_path:
        fallback = astar_search(graph, start, goal, profile)
        fallback.algorithm = "ida_star"
        fallback.message = (
            "IDA* vượt budget mở rộng trên graph lớn; đã dùng A* để bảo đảm "
            "kết quả ổn định."
        )
        return fallback

    return build_search_result(
        algorithm="ida_star",
        graph=graph,
        profile=profile,
        path=found_path,
        visited_order=visited_order,
        frontier_steps=frontier_steps,
        started_at=started_at,
    )


__all__ = ["search"]
