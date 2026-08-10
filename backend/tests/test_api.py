"""Integration tests for the public HTTP API contract."""

from backend.app.api.main import app


def test_route_options_are_available():
    client = app.test_client()

    algorithms = client.get("/api/algorithms")
    profiles = client.get("/api/cost-profiles")

    assert algorithms.status_code == 200
    assert {item["id"] for item in algorithms.get_json()} >= {
        "bfs",
        "dfs",
        "ucs",
        "astar",
        "greedy_best_first",
        "ida_star",
        "tsp",
    }
    assert profiles.status_code == 200
    assert {item["id"] for item in profiles.get_json()} == {
        "balanced",
        "shortest_distance",
        "fastest_route",
        "avoid_congestion",
    }


def test_graph_and_food_endpoints_use_clean_dataset():
    client = app.test_client()

    graph_response = client.get("/api/graph")
    food_response = client.get("/api/food-places")
    graph = graph_response.get_json()
    food = food_response.get_json()

    assert graph_response.status_code == 200
    assert len(graph["nodes"]) == 98
    assert len(graph["edges"]) == 176
    assert graph["nodes"]["1039"]["address"]
    assert graph["nodes"]["1039"]["on_edge"]["u"] == 23
    assert food_response.status_code == 200
    assert food["count"] == 39


def test_graph_core_search_uses_new_profile_contract():
    client = app.test_client()

    response = client.post(
        "/api/search",
        json={
            "start": "1",
            "end": "10",
            "algorithm": "astar",
            "cost_profile": "avoid_congestion",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["algorithm"] == "astar"
    assert payload["found"] is True
    assert len(payload["path"]) >= 2
    assert payload["animation_log"]
    assert payload["trace"]


def test_multi_location_route_uses_nearest_neighbor_service():
    client = app.test_client()

    response = client.post(
        "/api/tsp",
        json={
            "start": "1",
            "waypoints": ["1", "5", "10"],
            "cost_profile": "balanced",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["algorithm"] == "nearest_neighbor"
    assert payload["visiting_order"][0] == "1"
    assert len(payload["path"]) >= 2


def test_metrics_endpoint_compares_selected_algorithms():
    client = app.test_client()

    response = client.post(
        "/api/metrics",
        json={
            "start": "1",
            "end": "10",
            "cost_profile": "balanced",
            "algorithms": ["ucs", "ida_star", "greedy_best_first"],
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert [item["algorithm"] for item in payload["metrics"]] == [
        "ucs",
        "ida_star",
        "greedy_best_first",
    ]
    assert all(item["found"] for item in payload["metrics"])
    assert all(
        "path" in item and "visited_order" in item and "animation_log" in item
        for item in payload["metrics"]
    )
