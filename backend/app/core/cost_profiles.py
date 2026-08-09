"""Approved optimization profiles for traffic-aware route cost."""

from .models import CostProfile


COST_PROFILES = {
    "balanced": CostProfile(
        name="balanced",
        distance_weight=0.30,
        time_weight=0.45,
        congestion_weight=0.15,
        risk_weight=0.10,
    ),
    "shortest_distance": CostProfile(
        name="shortest_distance",
        distance_weight=0.65,
        time_weight=0.20,
        congestion_weight=0.10,
        risk_weight=0.05,
    ),
    "fastest_route": CostProfile(
        name="fastest_route",
        distance_weight=0.15,
        time_weight=0.65,
        congestion_weight=0.15,
        risk_weight=0.05,
    ),
    "avoid_congestion": CostProfile(
        name="avoid_congestion",
        distance_weight=0.15,
        time_weight=0.30,
        congestion_weight=0.45,
        risk_weight=0.10,
    ),
}

DEFAULT_COST_PROFILE = COST_PROFILES["balanced"]


__all__ = ["COST_PROFILES", "DEFAULT_COST_PROFILE"]
