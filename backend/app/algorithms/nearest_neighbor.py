"""Thuật toán Nearest Neighbor cho bài toán nhiều điểm."""

from time import perf_counter
from typing import Any, Hashable


def nearest_neighbor_tsp(
    start_node: Hashable,
    waypoints: list[Hashable],
    cost_matrix: dict[Hashable, dict[Hashable, float]],
    return_to_start: bool = False,
) -> dict[str, Any]:
    """Chọn điểm chưa đi có chi phí thấp nhất ở mỗi bước."""

    started_at = perf_counter()
    unvisited = set(waypoints)
    unvisited.discard(start_node)
    current = start_node
    visiting_order = [current]
    total_cost = 0.0
    comparisons = 0

    while unvisited:
        next_node = None
        next_cost = float("inf")
        for candidate in sorted(unvisited, key=str):
            comparisons += 1
            cost = cost_matrix.get(current, {}).get(candidate, float("inf"))
            if cost < next_cost:
                next_node = candidate
                next_cost = cost
        if next_node is None or next_cost == float("inf"):
            break
        visiting_order.append(next_node)
        unvisited.remove(next_node)
        total_cost += next_cost
        current = next_node

    if return_to_start and current != start_node:
        return_cost = cost_matrix.get(current, {}).get(start_node, float("inf"))
        if return_cost != float("inf"):
            total_cost += return_cost
            visiting_order.append(start_node)

    return {
        "algorithm": "nearest_neighbor",
        "visiting_order": visiting_order,
        "total_cost": round(total_cost, 4),
        "nodes_explored": comparisons,
        "execution_time_ms": round((perf_counter() - started_at) * 1000, 3),
        "unvisited_left": sorted(unvisited, key=str),
        "is_optimal": False,
    }
