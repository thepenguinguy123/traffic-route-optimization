"""Kiểm tra tính toàn vẹn của dataset nodes/edges được dùng runtime."""

from backend.app.repositories.clean_dataset_repository import (
    load_clean_edges,
    load_clean_nodes,
)


def test_clean_dataset_has_expected_shape_and_references():
    nodes = load_clean_nodes()
    edges = load_clean_edges()
    node_ids = {node.id for node in nodes}

    assert len(nodes) == 98
    assert len(edges) == 176
    assert len(node_ids) == len(nodes)
    assert all(edge.source in node_ids and edge.target in node_ids for edge in edges)
    assert len({(edge.source, edge.target) for edge in edges}) == len(edges)
    assert sum(node.node_type == "food" for node in nodes) == 39
    assert sum(node.node_type == "access" for node in nodes) == 3
    assert all(node.id != "9001" for node in nodes)
    assert {(edge.source, edge.target) for edge in edges} >= {
        ("1005", "20"),
        ("20", "1005"),
        ("7", "8"),
        ("3", "19"),
        ("19", "3"),
        ("1035", "1005"),
        ("1005", "1035"),
    }
    assert ("8", "1") not in {(edge.source, edge.target) for edge in edges}
    assert ("1005", "19") not in {(edge.source, edge.target) for edge in edges}


def test_food_metadata_and_directed_edges_are_preserved():
    nodes = load_clean_nodes()
    edges = load_clean_edges()
    food_node = next(node for node in nodes if node.id == "1039")

    assert food_node.node_type == "food"
    assert food_node.metadata["source"] == "goong_places"
    assert food_node.metadata["on_edge"]["u"] == 23
    assert any(edge.road_type == "one_way" for edge in edges)
    assert any(edge.source == "2" and edge.target == "10" for edge in edges)
