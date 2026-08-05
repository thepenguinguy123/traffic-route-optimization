"""Immutable domain models for the traffic graph."""

import math
from dataclasses import dataclass

from .errors import InvalidEdgeError, InvalidNodeError


_VALID_NODE_TYPES = frozenset({"intersection", "poi"})
_VALID_ROAD_TYPES = frozenset(
    {"main_road", "secondary_road", "residential_road", "alley"}
)
_VALID_RESTRICTIONS = frozenset(
    {
        "none",
        "delivery_restricted",
        "temporarily_restricted",
        "vehicle_restricted",
    }
)


@dataclass(frozen=True)
class TrafficNode:
    """A location or intersection in the traffic graph."""

    id: str
    name: str
    node_type: str
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not self.id:
            raise InvalidNodeError("id must not be empty")
        if not self.name:
            raise InvalidNodeError("name must not be empty")
        if self.node_type not in _VALID_NODE_TYPES:
            raise InvalidNodeError(
                "node_type must be 'intersection' or 'poi'"
            )
        if not -90 <= self.latitude <= 90:
            raise InvalidNodeError("latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise InvalidNodeError("longitude must be between -180 and 180")


@dataclass(frozen=True)
class RoadEdge:
    """A directed road segment between two traffic nodes."""

    source: str
    target: str
    distance_km: float
    base_time_min: float
    congestion_level: int
    road_type: str
    risk_level: int
    restriction: str
    is_closed: bool = False

    def __post_init__(self) -> None:
        if self.distance_km <= 0:
            raise InvalidEdgeError("distance_km must be greater than 0")
        if self.base_time_min <= 0:
            raise InvalidEdgeError("base_time_min must be greater than 0")
        if not 1 <= self.congestion_level <= 5:
            raise InvalidEdgeError("congestion_level must be between 1 and 5")
        if self.road_type not in _VALID_ROAD_TYPES:
            raise InvalidEdgeError("road_type is not supported")
        if not 0 <= self.risk_level <= 5:
            raise InvalidEdgeError("risk_level must be between 0 and 5")
        if self.restriction not in _VALID_RESTRICTIONS:
            raise InvalidEdgeError("restriction is not supported")


@dataclass(frozen=True)
class CostProfile:
    """Weights used to calculate traffic-aware route cost."""

    name: str
    distance_weight: float
    time_weight: float
    congestion_weight: float
    risk_weight: float

    def __post_init__(self) -> None:
        weights = (
            self.distance_weight,
            self.time_weight,
            self.congestion_weight,
            self.risk_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("cost profile weights must be non-negative")

        total = sum(weights)
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError("cost profile weights must total 1.0")


__all__ = ["TrafficNode", "RoadEdge", "CostProfile"]
