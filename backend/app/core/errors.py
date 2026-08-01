"""Shared exceptions for the traffic route optimization backend."""


class TrafficGraphError(Exception):
    """Base exception for traffic graph domain and integration errors."""


class InvalidNodeError(TrafficGraphError):
    """Raised when node data violates the approved node contract."""


class InvalidEdgeError(TrafficGraphError):
    """Raised when edge data violates the approved edge contract."""


class NodeNotFoundError(TrafficGraphError):
    """Raised when a requested node does not exist."""


class EdgeNotFoundError(TrafficGraphError):
    """Raised when a requested directed edge does not exist."""


class DuplicateNodeError(TrafficGraphError):
    """Raised when a node ID already exists."""


class DuplicateEdgeError(TrafficGraphError):
    """Raised when a directed edge already exists."""


class UnsupportedVehicleError(TrafficGraphError):
    """Raised when a vehicle outside the version 1 contract is requested."""


class InvalidPathError(TrafficGraphError):
    """Raised when a path contains an invalid graph transition."""


class InvalidTrafficProfileError(TrafficGraphError):
    """Raised when a traffic profile or override is invalid."""


__all__ = [
    "TrafficGraphError",
    "InvalidNodeError",
    "InvalidEdgeError",
    "NodeNotFoundError",
    "EdgeNotFoundError",
    "DuplicateNodeError",
    "DuplicateEdgeError",
    "UnsupportedVehicleError",
    "InvalidPathError",
    "InvalidTrafficProfileError",
]
