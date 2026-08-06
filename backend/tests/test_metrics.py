import sys
import os
import json

# Thêm đường dẫn root của dự án vào sys.path để import các module trong backend/app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.metrics_service import MetricsService
from app.algorithms.utils import Weights, Limits
from app.algorithms.dijkstra import dijkstra
from app.algorithms.ida_star import ida_star
from app.algorithms.greedy_best_first_search import greedy_best_first_search


# ==========================================
# 1. MÔ PHỎNG DỮ LIỆU ĐỒ THỊ (MOCK GRAPH)
# ==========================================

class MockNode:
    def __init__(self, id, name, latitude, longitude):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

class MockEdge:
    def __init__(self, source, target, distance_km, base_time_min, congestion_level, risk_level=0, is_closed=False):
        self.source = source
        self.target = target
        self.distance_km = distance_km
        self.base_time_min = base_time_min
        self.congestion_level = congestion_level
        self.risk_level = risk_level
        self.is_closed = is_closed

class MockGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def add_node(self, node):
        self.nodes[node.id] = node
        self.edges[node.id] = []

    def add_edge(self, edge):
        self.edges[edge.source].append(edge)

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_edges(self, node_id):
        return self.edges.get(node_id, [])


def build_test_graph():
    """Khởi tạo một đồ thị kiểm thử nhỏ đại diện cho khu vực Quận 1"""
    graph = MockGraph()
    
    # Thêm các Node (Địa danh & Giao lộ)
    graph.add_node(MockNode("N01", "Dinh Doc Lap", 10.7769, 106.6951))
    graph.add_node(MockNode("N02", "Nha Tho Duc Ba", 10.7798, 106.6990))
    graph.add_node(MockNode("N03", "Cho Ben Thanh", 10.7725, 106.6980))
    graph.add_node(MockNode("N04", "Pho Di Bo Nguyen Hue", 10.7743, 106.7031))
    
    # Thêm các Edge (Đoạn đường)
    # Tuyến N01 -> N02: Ngắn hơn nhưng ùn tắc nặng (congestion = 5)
    graph.add_edge(MockEdge("N01", "N02", distance_km=0.5, base_time_min=2.0, congestion_level=5))
    
    # Tuyến N01 -> N03: Thông thoáng (congestion = 2)
    graph.add_edge(MockEdge("N01", "N03", distance_km=0.8, base_time_min=3.0, congestion_level=2))
    
    # Tuyến N03 -> N02: Dài hơn nhưng thông thoáng (congestion = 1)
    graph.add_edge(MockEdge("N03", "N02", distance_km=1.0, base_time_min=3.5, congestion_level=1))
    
    # Tuyến N02 -> N04: Đường đi tới đích
    graph.add_edge(MockEdge("N02", "N04", distance_km=0.6, base_time_min=2.5, congestion_level=3))
    
    # Tuyến N03 -> N04: Bị đóng hoàn toàn (is_closed = True)
    graph.add_edge(MockEdge("N03", "N04", distance_km=0.7, base_time_min=2.0, congestion_level=1, is_closed=True))
    
    return graph


# ==========================================
# 2. CHẠY TEST METRICS SERVICE
# ==========================================

def test_metrics_service():
    graph = build_test_graph()
    
    start_id = "N01"
    goal_id = "N04"
    
    # Cấu hình trọng số thử nghiệm (Profile: Balanced)
    weights = Weights(distance=0.30, time=0.45, congestion=0.15, risk=0.10)
    limits = Limits(max_distance_km=3.0, max_time_min=15.0)
    
    # Danh sách cấu hình các thuật toán cần đo lường
    algorithms_config = [
        {
            "name": "Dijkstra",
            "func": dijkstra,
            "requires_weights": True
        },
        {
            "name": "Greedy Best-First Search",
            "func": greedy_best_first_search,
            "requires_weights": False
        },
        {
            "name": "IDA*",
            "func": ida_star,
            "requires_weights": True
        }
    ]
    
    print("=" * 60)
    print(f"CHẠY KIỂM THỬ METRICS SERVICE: TÌM ĐƯỜNG TỪ {start_id} ĐẾN {goal_id}")
    print("=" * 60)
    
    # 1. Chạy đo lường tất cả thuật toán qua MetricsService
    results = MetricsService.compare_algorithms(
        graph, start_id, goal_id, weights, limits, algorithms_config
    )
    
    # 2. In bảng kết quả so sánh ra console
    print("\n1. BẢNG TỔNG HỢP METRICS:")
    MetricsService.print_metrics_table(results)
    
    # 3. Trích xuất dạng định dạng JSON Response (chuẩn bị dữ liệu gửi về API)
    print("\n2. DỮ LIỆU ĐỊNH DẠNG JSON (TRẢ VỀ CHO API/FRONTEND):")
    summary_data = MetricsService.format_summary_metrics(results)
    print(json.dumps(summary_data, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    test_metrics_service()