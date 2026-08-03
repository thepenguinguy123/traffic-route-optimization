"""Framework-independent orchestration for route-search algorithms."""

from backend.app.algorithms.registry import ALGORITHM_REGISTRY
from backend.app.core.cost_profiles import COST_PROFILES
from backend.app.core.graph import TrafficGraph
from backend.app.core.search_models import SearchResult


class RouteSearchService:
    """Resolve approved registries and execute a route-search algorithm."""

    def __init__(self, graph: TrafficGraph) -> None:
        self._traffic_graph = graph

    def search(
        self,
        start: str,
        goal: str,
        algorithm: str,
        optimization_profile: str = "balanced",
    ) -> SearchResult:
        """Run one registered algorithm with one registered cost profile."""

        search_function = ALGORITHM_REGISTRY[algorithm]
        profile = COST_PROFILES[optimization_profile]
        return search_function(
            self._traffic_graph,
            start,
            goal,
            profile,
        )


__all__ = ["RouteSearchService"]
