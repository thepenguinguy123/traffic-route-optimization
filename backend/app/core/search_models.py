"""Shared result and animation trace models for search algorithms."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FrontierItem:
    """A node and its algorithm-specific values in the logical frontier."""

    node_id: str
    parent_id: str | None
    depth: int
    g_cost: float | None = None
    h_cost: float | None = None
    f_cost: float | None = None


@dataclass
class SearchTraceStep:
    """A snapshot captured after one node expansion."""

    step: int
    current: FrontierItem
    visited: list[str] = field(default_factory=list)
    frontier: list[FrontierItem] = field(default_factory=list)
    path_so_far: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """The common result returned by every search algorithm."""

    algorithm: str
    found: bool
    path: list[str] = field(default_factory=list)
    visited_order: list[str] = field(default_factory=list)
    frontier_steps: list[SearchTraceStep] = field(default_factory=list)
    total_distance: float = 0.0
    total_time: float = 0.0
    total_cost: float = 0.0
    explored_nodes: int = 0
    processing_time_ms: float = 0.0
    message: str = ""


__all__ = ["FrontierItem", "SearchTraceStep", "SearchResult"]
