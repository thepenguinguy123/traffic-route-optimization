"""Calibrate robust normalization references from the cleaned traffic dataset.

Usage:
    python -m scripts.calibrate_cost_scales
    python -m scripts.calibrate_cost_scales --scenario pooled
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from app.core.cost import CONGESTION_MULTIPLIERS
from app.repositories.clean_dataset_repository import (
    load_clean_edges,
    load_traffic_scenarios,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def percentile(values: list[float], probability: float) -> float:
    """Return a linearly interpolated percentile from a non-empty list."""

    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def round_up(value: float, step: float) -> float:
    """Round a positive value up to a stable reporting increment."""

    return math.ceil(value / step) * step


def validate_edges(edges: list[Any]) -> None:
    """Reject values that would make normalization or routing invalid."""

    for index, edge in enumerate(edges):
        values = (edge.distance_km, edge.base_time_min, edge.risk_factor)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"Edge {index} contains a non-finite traffic value")
        if edge.distance_km <= 0 or edge.base_time_min <= 0:
            raise ValueError(
                f"Edge {index} must have positive distance and base_time_min"
            )
        if not 0 <= edge.risk_factor <= 5:
            raise ValueError(f"Edge {index} risk_factor must be between 0 and 5")


def scenario_times(edges: list[Any], scenario: dict[str, Any]) -> list[float]:
    """Return congestion-adjusted edge times for one scenario."""

    offsets = scenario.get("congestion_offset_by_road_type", {})
    return [
        edge.base_time_min
        * CONGESTION_MULTIPLIERS[
            max(1, min(5, edge.congestion_level + int(offsets.get(edge.road_type, 0))))
        ]
        for edge in edges
    ]


def build_report(
    edges: list[Any], scenarios: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Build percentile and recommended reference-scale statistics."""

    distance_values = [edge.distance_km for edge in edges]
    base_time_values = [edge.base_time_min for edge in edges]
    per_scenario = {
        name: {
            "actual_time_p95_min": percentile(scenario_times(edges, config), 0.95),
            "actual_time_p99_min": percentile(scenario_times(edges, config), 0.99),
        }
        for name, config in scenarios.items()
    }
    pooled_times = [
        value
        for config in scenarios.values()
        for value in scenario_times(edges, config)
    ]
    return {
        "edge_count": len(edges),
        "distance_km": {
            "p50": percentile(distance_values, 0.50),
            "p90": percentile(distance_values, 0.90),
            "p95": percentile(distance_values, 0.95),
            "p99": percentile(distance_values, 0.99),
            "recommended_reference": round_up(percentile(distance_values, 0.95), 0.01),
        },
        "base_time_min": {
            "p50": percentile(base_time_values, 0.50),
            "p90": percentile(base_time_values, 0.90),
            "p95": percentile(base_time_values, 0.95),
            "p99": percentile(base_time_values, 0.99),
            "recommended_reference": round_up(percentile(base_time_values, 0.95), 0.05),
        },
        "actual_time_by_scenario": per_scenario,
        "pooled_actual_time_p95_min": percentile(pooled_times, 0.95),
        "pooled_actual_time_reference_min": round_up(
            percentile(pooled_times, 0.95), 0.05
        ),
    }


def main() -> None:
    """Validate the dataset and print a calibration report as JSON."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    edges = load_clean_edges()
    validate_edges(edges)
    report = build_report(edges, load_traffic_scenarios())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
