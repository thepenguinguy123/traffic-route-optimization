"""Typed registry for the approved route-search algorithms."""

from collections.abc import Callable

from backend.app.algorithms.astar import search as astar_search
from backend.app.algorithms.bfs import search as bfs_search
from backend.app.algorithms.dfs import search as dfs_search
from backend.app.algorithms.ucs import search as ucs_search
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import CostProfile
from backend.app.core.search_models import SearchResult


SearchFunction = Callable[
    [TrafficGraph, str, str, CostProfile],
    SearchResult,
]

ALGORITHM_REGISTRY: dict[str, SearchFunction] = {
    "bfs": bfs_search,
    "dfs": dfs_search,
    "ucs": ucs_search,
    "astar": astar_search,
}


__all__ = ["SearchFunction", "ALGORITHM_REGISTRY"]
