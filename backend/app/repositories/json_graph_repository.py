"""Load traffic graph domain data from approved JSON files."""

import json
from dataclasses import replace
from pathlib import Path

from backend.app.core.cost import CostCalculator
from backend.app.core.errors import InvalidTrafficProfileError
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import RoadEdge, TrafficNode


def load_nodes(file_path: str) -> list[TrafficNode]:
    """Load traffic nodes from an approved nodes JSON file."""

    records = _load_records(file_path, "nodes")
    return [TrafficNode(**record) for record in records]


def load_edges(file_path: str) -> list[RoadEdge]:
    """Load directed road edges from an approved edges JSON file."""

    records = _load_records(file_path, "edges")
    return [RoadEdge(**record) for record in records]


def load_graph(
    nodes_path: str,
    edges_path: str,
    cost_calculator: CostCalculator,
) -> TrafficGraph:
    """Build a traffic graph from node and edge JSON file paths."""

    graph = TrafficGraph(cost_calculator)
    for node in load_nodes(nodes_path):
        graph.add_node(node)
    for edge in load_edges(edges_path):
        graph.add_edge(edge)
    return graph


def load_traffic_profiles(file_path: str) -> dict[str, dict]:
    """Load named traffic profiles from an approved profiles JSON file."""

    profiles = _load_mapping(file_path, "profiles")
    for profile_name, profile in profiles.items():
        if not isinstance(profile_name, str) or not isinstance(profile, dict):
            raise ValueError("Every traffic profile must be a named object")
        if set(profile) != {"description", "edge_overrides"}:
            raise ValueError(
                "Every traffic profile must contain only 'description' "
                "and 'edge_overrides'"
            )
        if not isinstance(profile["description"], str):
            raise ValueError("Traffic profile description must be a string")

        overrides = profile["edge_overrides"]
        if not isinstance(overrides, list):
            raise ValueError("Traffic profile edge_overrides must be a list")
        if not all(isinstance(override, dict) for override in overrides):
            raise ValueError("Every traffic profile override must be an object")
    return profiles


def materialize_traffic_profile(
    base_graph: TrafficGraph,
    profiles: dict[str, dict],
    profile_name: str,
    cost_calculator: CostCalculator,
) -> TrafficGraph:
    """Create an independent graph with one traffic profile applied."""

    if profile_name not in profiles:
        raise InvalidTrafficProfileError(
            f"Traffic profile not found: {profile_name}"
        )

    updated_edges = {
        (edge.source, edge.target): replace(edge)
        for edge in base_graph.get_all_edges()
    }
    for override in profiles[profile_name]["edge_overrides"]:
        try:
            source = override["source"]
            target = override["target"]
        except KeyError as error:
            raise InvalidTrafficProfileError(
                "Traffic profile override requires source and target"
            ) from error

        edge_key = (source, target)
        if edge_key not in updated_edges:
            raise InvalidTrafficProfileError(
                f"Traffic profile edge not found: {source} -> {target}"
            )

        changes = {
            field_name: value
            for field_name, value in override.items()
            if field_name not in {"source", "target"}
        }
        updated_edges[edge_key] = replace(
            updated_edges[edge_key],
            **changes,
        )

    materialized_graph = TrafficGraph(cost_calculator)
    for node in base_graph.get_all_nodes():
        materialized_graph.add_node(node)
    for edge in updated_edges.values():
        materialized_graph.add_edge(edge)
    return materialized_graph


def _load_records(file_path: str, collection_name: str) -> list[dict]:
    with Path(file_path).open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict) or set(payload) != {collection_name}:
        raise ValueError(
            f"JSON must contain only the '{collection_name}' collection"
        )

    records = payload[collection_name]
    if not isinstance(records, list):
        raise ValueError(f"'{collection_name}' must be a list")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"Every '{collection_name}' record must be an object")
    return records


def _load_mapping(file_path: str, collection_name: str) -> dict:
    with Path(file_path).open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict) or set(payload) != {collection_name}:
        raise ValueError(
            f"JSON must contain only the '{collection_name}' collection"
        )

    mapping = payload[collection_name]
    if not isinstance(mapping, dict):
        raise ValueError(f"'{collection_name}' must be an object")
    return mapping


__all__ = [
    "load_nodes",
    "load_edges",
    "load_graph",
    "load_traffic_profiles",
    "materialize_traffic_profile",
]
