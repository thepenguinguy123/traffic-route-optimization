from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from app.repositories.graph_data import NODES, EDGES
from app.algorithms.algorithms import dfs_search, greedy_search, tsp_search
from app.core.food_area import point_in_polygon

# Load environment variables
project_env = Path(__file__).resolve().parents[3] / ".env"
backend_env = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(backend_env)
load_dotenv(project_env, override=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route("/")
def health_check():
    """Kiểm tra trạng thái server."""
    return jsonify({"status": "ok", "message": "API is running"})


@app.route("/api/graph", methods=["GET"])
def get_graph():
    """Trả về toàn bộ đồ thị (nodes + edges)."""
    return jsonify({"nodes": NODES, "edges": EDGES})


@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Trả về danh sách nodes cho dropdown."""
    return jsonify([{"id": k, "name": v["name"]} for k, v in NODES.items()])


@app.route("/api/food-places", methods=["GET"])
def get_food_places():
    """Trả về tối đa 40 quán ăn đã thu thập từ Goong Places API."""
    food_file = Path(__file__).parent / "data" / "food_places.json"
    if not food_file.exists():
        return jsonify({"count": 0, "places": [], "message": "Chưa có dữ liệu quán ăn."})

    try:
        with food_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        places = [
            place
            for place in data.get("places", [])
            if point_in_polygon(float(place["lat"]), float(place["lng"]))
        ][:40]
        return jsonify({"count": len(places), "places": places})
    except (OSError, json.JSONDecodeError) as error:
        return jsonify({"error": f"Không thể đọc dữ liệu quán ăn: {error}"}), 500


@app.route("/api/search", methods=["POST"])
def search_route():
    """Tìm đường giữa 2 điểm sử dụng thuật toán chọn (DFS/Greedy)."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    
    start = data.get("start")
    end = data.get("end")
    algorithm = data.get("algorithm")
    cost_type = data.get("cost_type", "distance")
    
    if not start or not end or not algorithm:
        return jsonify({"error": "Missing required fields: start, end, algorithm"}), 400
    
    if start not in NODES or end not in NODES:
        return jsonify({"error": "Trạm bắt đầu hoặc kết thúc không hợp lệ (Invalid start/end node)."}), 400
    
    algo = algorithm.lower()
    
    if algo == "dfs":
        result = dfs_search(start, end, cost_type)
    elif algo == "greedy":
        result = greedy_search(start, end, cost_type)
    else:
        return jsonify({"error": "Thuật toán không được hỗ trợ (Unsupported algorithm)."}), 400
    
    return jsonify(result)


@app.route("/api/tsp", methods=["POST"])
def tsp_route():
    """Tối ưu lộ trình đa điểm (TSP)."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    
    waypoints = data.get("waypoints")
    cost_type = data.get("cost_type", "distance")
    
    if not waypoints or len(waypoints) < 2:
        return jsonify({"error": "Cần ít nhất 2 điểm để tính toán TSP."}), 400
    
    if any(w not in NODES for w in waypoints):
        return jsonify({"error": "Danh sách trạm đi qua không hợp lệ (Invalid waypoints)."}), 400
    
    result = tsp_search(waypoints, cost_type)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
