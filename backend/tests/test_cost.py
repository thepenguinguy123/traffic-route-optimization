"""Behavior tests for traffic-aware cost calculation."""

import pytest

from backend.app.core.cost import CostCalculator
from backend.app.core.cost_profiles import COST_PROFILES
from backend.app.core.models import RoadEdge


def test_congestion_adjusted_time():
    edge = RoadEdge(
        source="A",
        target="B",
        distance_km=1.0,
        base_time_min=10.0,
        congestion_level=4,
        road_type="main_road",
        risk_level=1,
        restriction="none",
    )

    actual_time = CostCalculator().calculate_actual_time(edge)

    assert actual_time == 17.0


def test_route_cost():
    edges = [
        RoadEdge(
            source="A",
            target="B",
            distance_km=1.5,
            base_time_min=5.0,
            congestion_level=1,
            road_type="main_road",
            risk_level=0,
            restriction="none",
        ),
        RoadEdge(
            source="B",
            target="C",
            distance_km=1.5,
            base_time_min=5.0,
            congestion_level=1,
            road_type="secondary_road",
            risk_level=0,
            restriction="none",
        ),
    ]

    route_cost = CostCalculator().calculate_path_cost(
        edges,
        COST_PROFILES["balanced"],
    )

    assert route_cost == pytest.approx(1.50)
