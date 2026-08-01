"""Behavior tests for the public traffic graph interface."""

from backend.app.core.cost import CostCalculator
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import RoadEdge, TrafficNode


def test_directed_edge_requires_reverse_record():
    graph = TrafficGraph(CostCalculator())
    graph.add_node(TrafficNode("A", "Start", "intersection", 10.77, 106.69))
    graph.add_node(TrafficNode("B", "Destination", "poi", 10.78, 106.70))
    graph.add_edge(
        RoadEdge(
            source="A",
            target="B",
            distance_km=1.0,
            base_time_min=4.0,
            congestion_level=2,
            road_type="main_road",
            risk_level=1,
            restriction="none",
        )
    )

    assert graph.has_edge("A", "B")
    assert not graph.has_edge("B", "A")


def test_closed_edge_is_not_traversable():
    graph = TrafficGraph(CostCalculator())
    graph.add_node(TrafficNode("A", "Start", "intersection", 10.77, 106.69))
    graph.add_node(TrafficNode("B", "Closed road", "poi", 10.78, 106.70))
    graph.add_node(TrafficNode("C", "Open road", "poi", 10.79, 106.71))
    graph.add_edge(
        RoadEdge(
            source="A",
            target="B",
            distance_km=1.0,
            base_time_min=4.0,
            congestion_level=2,
            road_type="main_road",
            risk_level=1,
            restriction="none",
            is_closed=True,
        )
    )
    graph.add_edge(
        RoadEdge(
            source="A",
            target="C",
            distance_km=1.2,
            base_time_min=5.0,
            congestion_level=2,
            road_type="secondary_road",
            risk_level=1,
            restriction="none",
        )
    )

    assert graph.get_neighbors("A") == ["B", "C"]
    assert graph.get_traversable_neighbors("A") == ["C"]
