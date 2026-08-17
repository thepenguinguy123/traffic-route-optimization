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
    assert graph["nodes"]["1039"]["on_edge"]["u"] == 33
    assert food_response.status_code == 200
    assert food["count"] == 39


def test_graph_endpoint_uses_requested_traffic_scenario():
    client = app.test_client()

    normal = client.get("/api/graph?scenario=normal")
    rush = client.get("/api/graph?scenario=rush_hour")
    invalid = client.get("/api/graph?scenario=unknown")

    assert normal.status_code == 200
    assert rush.status_code == 200
    assert invalid.status_code == 400
    normal_edges = normal.get_json()["edges"]
    rush_edges = rush.get_json()["edges"]
    assert any(
        normal_edge["congestion"] != rush_edge["congestion"]
        for normal_edge, rush_edge in zip(normal_edges, rush_edges)
    )


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
    assert any(item["status"] == "frontier" for item in payload["animation_log"])
    assert any(item["status"] == "visited" for item in payload["animation_log"])
    animation_log = payload["animation_log"]
    assert animation_log[0]["status"] == "processing"
    processing_indices = [
        index
        for index, item in enumerate(animation_log)
        if item["status"] == "processing"
    ]
    for index, processing_index in enumerate(processing_indices):
        next_processing_index = (
            processing_indices[index + 1]
            if index + 1 < len(processing_indices)
            else len(animation_log)
        )
        current_node = animation_log[processing_index]["node"]
        assert any(
            item["status"] == "visited" and item["node"] == current_node
            for item in animation_log[processing_index + 1 : next_processing_index]
        )
    assert payload["trace"]
    assert payload["explanation_details"]["status"] == "found"
    assert payload["explanation_details"]["criterion"]
    assert "guarantee" in payload["explanation_details"]
    for segment in payload["explanation_details"]["high_impact_segments"]:
        assert segment["source_name"]
        assert segment["target_name"]


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
    assert payload["explanation_details"]["visiting_order_names"]
    assert payload["is_optimal"] is False


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

    assert all(
        item["explanation_details"]["status"] == "found" for item in payload["metrics"]
    )


def test_traffic_scenarios_are_runtime_selectable():
    client = app.test_client()

    scenarios = client.get("/api/traffic-scenarios")
    normal = client.post(
        "/api/search",
        json={
            "start": "1",
            "end": "10",
            "algorithm": "ucs",
            "cost_profile": "balanced",
            "scenario": "normal",
        },
    )
    rainy = client.post(
        "/api/search",
        json={
            "start": "1",
            "end": "10",
            "algorithm": "ucs",
            "cost_profile": "balanced",
            "scenario": "rainy_day",
        },
    )
    invalid = client.post(
        "/api/search",
        json={
            "start": "1",
            "end": "10",
            "algorithm": "ucs",
            "scenario": "unknown",
        },
    )

    assert scenarios.status_code == 200
    assert {item["id"] for item in scenarios.get_json()} == {
        "normal",
        "rush_hour",
        "rainy_day",
    }
    assert normal.status_code == 200
    assert rainy.status_code == 200
    assert normal.get_json()["scenario"] == "normal"
    assert rainy.get_json()["scenario"] == "rainy_day"
    assert invalid.status_code == 400
    metrics = client.post(
        "/api/metrics",
        json={
            "start": "1",
            "end": "10",
            "algorithms": ["ucs"],
            "scenario": "rush_hour",
        },
    )
    assert metrics.get_json()["scenario"] == "rush_hour"
    assert (
        normal.get_json()["stats"]["total_cost"]
        != rainy.get_json()["stats"]["total_cost"]
    )
    assert invalid.status_code == 400
