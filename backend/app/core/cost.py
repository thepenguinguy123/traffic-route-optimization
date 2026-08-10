"""Traffic-aware cost calculations shared by routing algorithms."""

from .models import CostProfile, RoadEdge

CONGESTION_MULTIPLIERS = {
    1: 1.00,
    2: 1.15,
    3: 1.35,
    4: 1.70,
    5: 2.20,
}

MAX_DISTANCE_KM = 3.0
MAX_TIME_MIN = 15.0


class CostCalculator:
    """Calculate shared traffic costs using approved normalization limits."""

    def __init__(
        self,
        max_distance_km: float = MAX_DISTANCE_KM,
        max_time_min: float = MAX_TIME_MIN,
    ) -> None:
        if max_distance_km <= 0:
            raise ValueError("max_distance_km must be greater than 0")
        if max_time_min <= 0:
            raise ValueError("max_time_min must be greater than 0")

        self.max_distance_km = max_distance_km
        self.max_time_min = max_time_min

    def calculate_actual_time(self, edge: RoadEdge) -> float:
        """Return congestion-adjusted estimated travel time in minutes."""

        return edge.base_time_min * CONGESTION_MULTIPLIERS[edge.congestion_level]

    def calculate_edge_cost(
        self,
        edge: RoadEdge,
        profile: CostProfile,
    ) -> float:
        """Return the normalized traffic-aware cost of one directed edge."""

        if edge.is_closed:
            return float("inf")

        actual_time = self.calculate_actual_time(edge)
        normalized_distance = min(edge.distance_km / self.max_distance_km, 1.0)
        normalized_actual_time = min(actual_time / self.max_time_min, 1.0)
        normalized_congestion = (edge.congestion_level - 1) / 4

        risk_factor = (
            edge.risk_factor if edge.risk_factor is not None else float(edge.risk_level)
        )
        normalized_risk = min(max(risk_factor / 5, 0.0), 1.0)

        return (
            profile.distance_weight * normalized_distance
            + profile.time_weight * normalized_actual_time
            + profile.congestion_weight * normalized_congestion
            + profile.risk_weight * normalized_risk
        )

    def calculate_path_cost(
        self,
        edges: list[RoadEdge],
        profile: CostProfile,
    ) -> float:
        """Return the sum of traffic-aware costs for a sequence of edges."""

        return sum(self.calculate_edge_cost(edge, profile) for edge in edges)


__all__ = [
    "CONGESTION_MULTIPLIERS",
    "MAX_DISTANCE_KM",
    "MAX_TIME_MIN",
    "CostCalculator",
]
