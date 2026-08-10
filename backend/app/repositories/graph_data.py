"""Compatibility views and helpers backed by the cleaned graph dataset."""

import math
from typing import Any

from .clean_dataset_repository import load_clean_edges, load_clean_nodes


_CLEAN_NODES = load_clean_nodes()
_CLEAN_EDGES = load_clean_edges()

NODES: dict[str, dict[str, Any]] = {
    node.id: {
        "name": node.name,
        "lat": node.latitude,
        "lng": node.longitude,
        "type": node.node_type,
        **node.metadata,
    }
    for node in _CLEAN_NODES
}

EDGES: list[dict[str, Any]] = [
    {
        "from": edge.source,
        "to": edge.target,
        "source": edge.source,
        "target": edge.target,
        "distance_km": edge.distance_km,
        "time_min": edge.base_time_min,
        "base_time_min": edge.base_time_min,
        "congestion": edge.congestion_level,
        "congestion_level": edge.congestion_level,
        "road_type": edge.road_type,
        "risk_factor": edge.risk_factor,
    }
    for edge in _CLEAN_EDGES
]


def haversine_distance(node1: str, node2: str) -> float:
    """Return the great-circle distance between two graph nodes in kilometers."""

    if node1 not in NODES or node2 not in NODES:
        return float("inf")
    latitude_delta = math.radians(NODES[node2]["lat"] - NODES[node1]["lat"])
    longitude_delta = math.radians(NODES[node2]["lng"] - NODES[node1]["lng"])
    latitude_1 = math.radians(NODES[node1]["lat"])
    latitude_2 = math.radians(NODES[node2]["lat"])
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 6371.0088 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def calculate_cost(edge: dict[str, Any], cost_type: str = "distance") -> float:
    """Calculate a legacy edge cost for the requested cost type."""

    if cost_type == "distance":
        return edge["distance_km"]
    if cost_type == "time":
        return edge["time_min"]
    if cost_type == "combined":
        return edge["distance_km"] + edge["time_min"] / 10.0 + edge["congestion"] * 0.4
    return edge["distance_km"]


__all__ = ["NODES", "EDGES", "calculate_cost", "haversine_distance"]
