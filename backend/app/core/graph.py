"""Public traffic graph interface backed by a private NetworkX graph."""

from math import asin, cos, radians, sin, sqrt

import networkx as nx

from .cost import CostCalculator
from .errors import (
    DuplicateEdgeError,
    DuplicateNodeError,
    EdgeNotFoundError,
    InvalidPathError,
    NodeNotFoundError,
    UnsupportedVehicleError,
)
from .models import CostProfile, RoadEdge, TrafficNode


_NODE_DATA_KEY = "node"
_EDGE_DATA_KEY = "edge"
_EARTH_RADIUS_KM = 6371.0088


class TrafficGraph:
    """Store traffic data while hiding NetworkX implementation details."""

    def __init__(self, cost_calculator: CostCalculator) -> None:
        self._graph = nx.DiGraph()
        self._cost_calculator = cost_calculator

    def add_node(self, node: TrafficNode) -> None:
        """Add a traffic node, rejecting duplicate node IDs."""

        if self.has_node(node.id):
            raise DuplicateNodeError(f"Node already exists: {node.id}")

        self._graph.add_node(node.id, **{_NODE_DATA_KEY: node})

    def has_node(self, node_id: str) -> bool:
        """Return whether a node ID exists in the graph."""

        return self._graph.has_node(node_id)

    def get_node(self, node_id: str) -> TrafficNode:
        """Return a traffic node by ID."""

        if not self.has_node(node_id):
            raise NodeNotFoundError(f"Node not found: {node_id}")

        return self._graph.nodes[node_id][_NODE_DATA_KEY]

    def get_all_nodes(self) -> list[TrafficNode]:
        """Return every traffic node."""

        return [
            attributes[_NODE_DATA_KEY]
            for _, attributes in self._graph.nodes(data=True)
        ]

    def add_edge(self, edge: RoadEdge) -> None:
        """Add a directed road edge between two existing nodes."""

        self.get_node(edge.source)
        self.get_node(edge.target)

        if self.has_edge(edge.source, edge.target):
            raise DuplicateEdgeError(
                f"Edge already exists: {edge.source} -> {edge.target}"
            )

        self._graph.add_edge(
            edge.source,
            edge.target,
            **{_EDGE_DATA_KEY: edge},
        )

    def has_edge(self, source: str, target: str) -> bool:
        """Return whether a directed edge exists."""

        return self._graph.has_edge(source, target)

    def get_edge(self, source: str, target: str) -> RoadEdge:
        """Return a directed road edge by source and target IDs."""

        if not self.has_edge(source, target):
            raise EdgeNotFoundError(f"Edge not found: {source} -> {target}")

        return self._graph.edges[source, target][_EDGE_DATA_KEY]

    def get_all_edges(self) -> list[RoadEdge]:
        """Return every directed road edge."""

        return [
            attributes[_EDGE_DATA_KEY]
            for _, _, attributes in self._graph.edges(data=True)
        ]

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return all outgoing neighbor IDs in ascending order."""

        self.get_node(node_id)
        return sorted(self._graph.successors(node_id))

    def get_traversable_neighbors(
        self,
        node_id: str,
        vehicle_type: str = "motorbike",
    ) -> list[str]:
        """Return outgoing neighbors traversable by the version 1 vehicle."""

        neighbors = self.get_neighbors(node_id)
        if vehicle_type != "motorbike":
            raise UnsupportedVehicleError(
                f"Unsupported vehicle: {vehicle_type}"
            )

        return [
            neighbor_id
            for neighbor_id in neighbors
            if self._is_traversable_edge(node_id, neighbor_id)
        ]

    def get_predecessors(self, node_id: str) -> list[str]:
        """Return IDs with a directed edge into the requested node."""

        self.get_node(node_id)
        return list(self._graph.predecessors(node_id))

    def get_edge_cost(
        self,
        source: str,
        target: str,
        profile: CostProfile,
    ) -> float:
        """Return the shared traffic cost for one directed edge."""

        return self._cost_calculator.calculate_edge_cost(
            self.get_edge(source, target),
            profile,
        )

    def calculate_path_distance(self, path: list[str]) -> float:
        """Return total road distance for a node-ID path."""

        return sum(edge.distance_km for edge in self._get_path_edges(path))

    def calculate_path_time(self, path: list[str]) -> float:
        """Return congestion-adjusted time for a node-ID path."""

        return sum(
            self._cost_calculator.calculate_actual_time(edge)
            for edge in self._get_path_edges(path)
        )

    def calculate_path_cost(
        self,
        path: list[str],
        profile: CostProfile,
    ) -> float:
        """Return shared traffic cost for a node-ID path."""

        return self._cost_calculator.calculate_path_cost(
            self._get_path_edges(path),
            profile,
        )

    def estimate_straight_line_distance(
        self,
        source: str,
        target: str,
    ) -> float:
        """Return Haversine distance between two nodes in kilometres."""

        source_node = self.get_node(source)
        target_node = self.get_node(target)

        source_latitude = radians(source_node.latitude)
        target_latitude = radians(target_node.latitude)
        latitude_delta = target_latitude - source_latitude
        longitude_delta = radians(target_node.longitude - source_node.longitude)

        haversine_value = (
            sin(latitude_delta / 2) ** 2
            + cos(source_latitude)
            * cos(target_latitude)
            * sin(longitude_delta / 2) ** 2
        )
        central_angle = 2 * asin(
            sqrt(min(1.0, max(0.0, haversine_value)))
        )
        return _EARTH_RADIUS_KM * central_angle

    def to_dict(self) -> dict:
        """Return deterministic graph data with approved JSON-compatible fields."""

        nodes = sorted(self.get_all_nodes(), key=lambda node: node.id)
        edges = sorted(
            self.get_all_edges(),
            key=lambda edge: (edge.source, edge.target),
        )

        return {
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "node_type": node.node_type,
                    "latitude": node.latitude,
                    "longitude": node.longitude,
                }
                for node in nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "distance_km": edge.distance_km,
                    "base_time_min": edge.base_time_min,
                    "congestion_level": edge.congestion_level,
                    "road_type": edge.road_type,
                    "risk_level": edge.risk_level,
                    "restriction": edge.restriction,
                    "is_closed": edge.is_closed,
                }
                for edge in edges
            ],
        }

    def _is_traversable_edge(self, source: str, target: str) -> bool:
        edge = self.get_edge(source, target)
        return not edge.is_closed and edge.restriction == "none"

    def _get_path_edges(self, path: list[str]) -> list[RoadEdge]:
        edges = []
        for source, target in zip(path, path[1:]):
            if not self.has_edge(source, target):
                raise InvalidPathError(
                    f"Invalid path transition: {source} -> {target}"
                )
            edges.append(self.get_edge(source, target))
        return edges


__all__ = ["TrafficGraph"]
