"""Typed registry for the approved route-search algorithms."""

from collections.abc import Callable

from .astar import search as astar_search
from .bfs import search as bfs_search
from .dfs import search as dfs_search
from .greedy_best_first_search import search as greedy_best_first_search
from .ida_star import search as ida_star_search
from .ucs import search as ucs_search
from ..core.graph import TrafficGraph
from ..core.models import CostProfile
from ..core.search_models import SearchResult


SearchFunction = Callable[
    [TrafficGraph, str, str, CostProfile],
    SearchResult,
]

ALGORITHM_REGISTRY: dict[str, SearchFunction] = {
    "bfs": bfs_search,
    "dfs": dfs_search,
    "greedy_best_first": greedy_best_first_search,
    "ida_star": ida_star_search,
    "ucs": ucs_search,
    "astar": astar_search,
}


__all__ = ["SearchFunction", "ALGORITHM_REGISTRY"]
