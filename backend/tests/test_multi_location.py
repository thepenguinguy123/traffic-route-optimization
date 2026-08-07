"""Kiểm tra điều kiện hoàn tất của tuyến nhiều waypoint."""

from backend.app.algorithms.nearest_neighbor import nearest_neighbor_tsp
from backend.app.core.cost import CostCalculator
from backend.app.core.cost_profiles import COST_PROFILES
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import RoadEdge, TrafficNode
from backend.app.services.multi_location_service import MultiLocationService


def test_nearest_neighbor_reports_unreachable_waypoints():
    result = nearest_neighbor_tsp(
        start_node="A",
        waypoints=["A", "B", "C"],
        cost_matrix={
            "A": {"A": 0.0, "B": 1.0, "C": float("inf")},
            "B": {"A": 1.0, "B": 0.0, "C": float("inf")},
            "C": {"A": float("inf"), "B": float("inf"), "C": 0.0},
        },
    )

    assert result["visiting_order"] == ["A", "B"]
    assert result["unvisited_left"] == ["C"]


def test_multi_location_does_not_mark_partial_route_as_found():
    graph = TrafficGraph(CostCalculator())
    for node_id in ("A", "B", "C"):
        graph.add_node(
            TrafficNode(
                id=node_id,
                name=node_id,
                node_type="intersection",
                latitude=10.0,
                longitude=106.0,
            )
        )
    for source, target in (("A", "B"), ("B", "A")):
        graph.add_edge(
            RoadEdge(
                source=source,
                target=target,
                distance_km=1.0,
                base_time_min=1.0,
                congestion_level=1,
                road_type="main_street",
                risk_level=0,
                restriction="none",
            )
        )

    result = MultiLocationService().optimize_delivery_route(
        start_node="A",
        waypoints=["A", "B", "C"],
        graph=graph,
        profile=COST_PROFILES["balanced"],
    )

    assert result["found"] is False
    assert result["unvisited_left"] == ["C"]
