"""Load validated graph entities from the cleaned JavaScript datasets."""

import json
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..core.cost import CostCalculator
from ..core.graph import TrafficGraph
from ..core.models import RoadEdge, TrafficNode


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
NODES_DATA_PATH = DATA_DIR / "nodes_clean.js"
EDGES_DATA_PATH = DATA_DIR / "edges_clean.js"
SCENARIOS_DATA_PATH = DATA_DIR / "traffic_scenarios.json"


def load_js_array(file_path: Path) -> list[dict[str, Any]]:
    """Extract and validate an object array from a JavaScript data file."""

    text = file_path.read_text(encoding="utf-8")
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < start:
        raise ValueError(f"No JSON array was found in {file_path}")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, list) or not all(
        isinstance(item, dict) for item in payload
    ):
        raise ValueError(f"Dataset {file_path} must be an array of objects")
    return payload


def load_clean_nodes(file_path: Path = NODES_DATA_PATH) -> list[TrafficNode]:
    """Load cleaned node records as validated traffic nodes."""

    nodes = []
    for record in load_js_array(file_path):
        required = {"id", "name", "lat", "lng", "type"}
        missing = required.difference(record)
        if missing:
            raise ValueError(f"Node is missing fields: {sorted(missing)}")
        metadata = {key: value for key, value in record.items() if key not in required}
        nodes.append(
            TrafficNode(
                id=str(record["id"]),
                name=str(record["name"]),
                node_type="food" if record["type"] == "food" else record["type"],
                latitude=float(record["lat"]),
                longitude=float(record["lng"]),
                metadata=metadata,
            )
        )
    return nodes


def load_clean_edges(file_path: Path = EDGES_DATA_PATH) -> list[RoadEdge]:
    """Load cleaned edge records as validated road edges."""

    edges = []
    for record in load_js_array(file_path):
        required = {
            "source",
            "target",
            "distance_km",
            "base_time_min",
            "congestion_level",
            "road_type",
            "risk_factor",
        }
        missing = required.difference(record)
        if missing:
            raise ValueError(f"Edge is missing fields: {sorted(missing)}")
        risk_factor = float(record["risk_factor"])
        edges.append(
            RoadEdge(
                source=str(record["source"]),
                target=str(record["target"]),
                distance_km=float(record["distance_km"]),
                base_time_min=float(record["base_time_min"]),
                congestion_level=max(1, min(5, int(record["congestion_level"]))),
                road_type=str(record["road_type"]),
                risk_level=max(0, min(5, round(risk_factor))),
                restriction="none",
                is_closed=False,
                risk_factor=risk_factor,
            )
        )
    return edges


def load_traffic_scenarios(
    file_path: Path = SCENARIOS_DATA_PATH,
) -> dict[str, dict]:
    """Load the reproducible runtime traffic scenario configuration."""

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("Traffic scenario configuration must define scenarios")
    return scenarios


def _apply_scenario(edge: RoadEdge, scenario: dict) -> RoadEdge:
    """Return an edge adjusted by a validated scenario definition."""

    offsets = scenario.get("congestion_offset_by_road_type", {})
    offset = int(offsets.get(edge.road_type, 0))
    congestion = max(1, min(5, edge.congestion_level + offset))
    risk_factor = min(
        5.0, max(0.0, edge.risk_factor * float(scenario.get("risk_multiplier", 1.0)))
    )
    return replace(
        edge,
        congestion_level=congestion,
        risk_level=max(0, min(5, round(risk_factor))),
        risk_factor=risk_factor,
    )


@lru_cache(maxsize=8)
def load_clean_graph(
    nodes_path: Path = NODES_DATA_PATH,
    edges_path: Path = EDGES_DATA_PATH,
    scenario: str = "normal",
) -> TrafficGraph:
    """Build a traffic graph with an optional reproducible traffic scenario."""

    scenarios = load_traffic_scenarios()
    if scenario not in scenarios:
        raise ValueError(f"Unknown traffic scenario: {scenario}")

    graph = TrafficGraph(CostCalculator())
    for node in load_clean_nodes(nodes_path):
        graph.add_node(node)
    for edge in load_clean_edges(edges_path):
        graph.add_edge(_apply_scenario(edge, scenarios[scenario]))
    return graph


__all__ = [
    "DATA_DIR",
    "NODES_DATA_PATH",
    "EDGES_DATA_PATH",
    "SCENARIOS_DATA_PATH",
    "load_traffic_scenarios",
    "load_js_array",
    "load_clean_nodes",
    "load_clean_edges",
    "load_clean_graph",
]
