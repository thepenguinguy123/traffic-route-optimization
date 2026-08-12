"""Audit runtime data and recommend normalization limits for route costs.

Run from the project root:
    python backend/scripts/calibrate_normalization.py

This development tool only prints recommendations. It never updates production
constants or modifies the runtime dataset.
"""

from __future__ import annotations

import math
import statistics
import sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.cost import CONGESTION_MULTIPLIERS  # noqa: E402
from backend.app.core.graph import TrafficGraph  # noqa: E402
from backend.app.core.models import RoadEdge  # noqa: E402
from backend.app.repositories.clean_dataset_repository import (  # noqa: E402
    load_clean_graph,
)


DISTANCE_ROUNDING_STEP_KM = 0.01
TIME_ROUNDING_STEP_MIN = 0.1


def percentile(values: list[float], percentage: float) -> float:
    """Return a linearly interpolated percentile for non-empty values."""

    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 <= percentage <= 100:
        raise ValueError("percentage must be between 0 and 100")

    ordered_values = sorted(values)
    position = (len(ordered_values) - 1) * percentage / 100
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered_values[lower_index]

    fraction = position - lower_index
    lower_value = ordered_values[lower_index]
    upper_value = ordered_values[upper_index]
    return lower_value + fraction * (upper_value - lower_value)


def round_up_to_step(value: float, step: float) -> float:
    """Round upward to a practical step so the result never falls below P95."""

    if value < 0:
        raise ValueError("value must be non-negative")
    if step <= 0:
        raise ValueError("step must be greater than zero")

    decimal_value = Decimal(str(value))
    decimal_step = Decimal(str(step))
    units = (decimal_value / decimal_step).to_integral_value(
        rounding=ROUND_CEILING
    )
    return float(units * decimal_step)


def get_traversable_edges(graph: TrafficGraph) -> list[RoadEdge]:
    """Return motorbike-traversable directed edges through public graph APIs."""

    edges = []
    for node in graph.get_all_nodes():
        for neighbor_id in graph.get_traversable_neighbors(node.id):
            edges.append(graph.get_edge(node.id, neighbor_id))
    return edges


def calculate_statistics(values: list[float]) -> dict[str, float]:
    """Calculate the descriptive statistics used by this calibration audit."""

    if not values:
        raise ValueError("statistics require at least one value")

    return {
        "min": min(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p75": percentile(values, 75),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "max": max(values),
    }


def print_statistics(title: str, statistics_by_name: dict[str, float]) -> None:
    """Print one readable statistics section."""

    print(title)
    print("-" * len(title))
    for label, key in (
        ("Min", "min"),
        ("Mean", "mean"),
        ("Median", "median"),
        ("P75", "p75"),
        ("P90", "p90"),
        ("P95", "p95"),
        ("Max", "max"),
    ):
        print(f"{label}: {statistics_by_name[key]:.5f}")


def main() -> None:
    """Load the default Flask runtime graph and print calibration guidance."""

    graph = load_clean_graph()
    edges = get_traversable_edges(graph)
    if not edges:
        raise SystemExit("The runtime graph has no traversable edges to calibrate.")

    distances = [edge.distance_km for edge in edges]
    actual_times = [
        edge.base_time_min * CONGESTION_MULTIPLIERS[edge.congestion_level]
        for edge in edges
    ]

    distance_statistics = calculate_statistics(distances)
    time_statistics = calculate_statistics(actual_times)
    recommended_distance = round_up_to_step(
        distance_statistics["p95"],
        DISTANCE_ROUNDING_STEP_KM,
    )
    recommended_time = round_up_to_step(
        time_statistics["p95"],
        TIME_ROUNDING_STEP_MIN,
    )

    print("Normalization Calibration")
    print("=========================")
    print()
    print(f"Traversable edges: {len(edges)}")
    print()
    print_statistics("Distance (km)", distance_statistics)
    print()
    print(f"Recommended MAX_DISTANCE_KM: {recommended_distance:.2f}")
    print(
        "Edges above recommended distance limit: "
        f"{sum(value > recommended_distance for value in distances)}/{len(edges)}"
    )
    print()
    print_statistics("Actual time (min)", time_statistics)
    print()
    print(f"Recommended MAX_TIME_MIN: {recommended_time:.1f}")
    print(
        "Edges above recommended time limit: "
        f"{sum(value > recommended_time for value in actual_times)}/{len(edges)}"
    )
    print()
    print("Suggested values for backend/app/core/cost.py:")
    print()
    print(f"MAX_DISTANCE_KM = {recommended_distance:.2f}")
    print(f"MAX_TIME_MIN = {recommended_time:.1f}")


if __name__ == "__main__":
    main()
