"""Kiểm tra contract API giữa graph core và frontend."""

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
        "greedy",
        "tsp",
    }
    assert profiles.status_code == 200
    assert {item["id"] for item in profiles.get_json()} == {
        "balanced",
        "shortest_distance",
        "fastest_route",
        "avoid_congestion",
    }


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
