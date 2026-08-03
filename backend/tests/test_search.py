"""Minimal behavior tests shared by route-search algorithms."""

from backend.app.algorithms.bfs import search as bfs_search
from backend.app.algorithms.dfs import search as dfs_search
from backend.app.core.cost import CostCalculator
from backend.app.core.cost_profiles import COST_PROFILES
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import RoadEdge, TrafficNode


SEARCH_FUNCTIONS = (bfs_search, dfs_search)


def _build_graph(
    node_ids: list[str],
    edge_pairs: list[tuple[str, str]],
) -> TrafficGraph:
    graph = TrafficGraph(CostCalculator())
    for index, node_id in enumerate(node_ids):
        graph.add_node(
            TrafficNode(
                id=node_id,
                name=node_id,
                node_type="intersection",
                latitude=10.77 + index * 0.001,
                longitude=106.69 + index * 0.001,
            )
        )
    for source, target in edge_pairs:
        graph.add_edge(
            RoadEdge(
                source=source,
                target=target,
                distance_km=1.0,
                base_time_min=4.0,
                congestion_level=1,
                road_type="main_road",
                risk_level=0,
                restriction="none",
            )
        )
    return graph


def test_search_finds_unique_route():
    graph = _build_graph(["A", "B", "C"], [("A", "B"), ("B", "C")])

    for search_function in SEARCH_FUNCTIONS:
        result = search_function(
            graph,
            "A",
            "C",
            COST_PROFILES["balanced"],
        )

        assert result.found
        assert result.path == ["A", "B", "C"]


def test_search_returns_no_route():
    graph = _build_graph(["A", "B"], [])

    for search_function in SEARCH_FUNCTIONS:
        result = search_function(
            graph,
            "A",
            "B",
            COST_PROFILES["balanced"],
        )

        assert not result.found
        assert result.path == []


def test_search_handles_cycle():
    graph = _build_graph(
        ["A", "B", "C"],
        [("A", "B"), ("B", "A"), ("B", "C")],
    )

    for search_function in SEARCH_FUNCTIONS:
        result = search_function(
            graph,
            "A",
            "C",
            COST_PROFILES["balanced"],
        )

        assert result.found
        assert result.path == ["A", "B", "C"]
