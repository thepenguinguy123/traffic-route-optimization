import sys
import os

# Thêm đường dẫn để có thể import từ backend/app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

# Import các cấu trúc và thuật toán (Giả sử bạn đã lưu các file thuật toán trong backend/app/algorithms/)
from algorithms.utils import Weights, Limits
from algorithms.dijkstra import dijkstra
from algorithms.ida_star import ida_star
from algorithms.greedy_best_first_search import greedy_best_first_search

# ==========================================
# 1. CÁC CLASS MÔ PHỎNG ĐỒ THỊ
# ==========================================

class Node:
    def __init__(self, id, name, node_type, latitude, longitude):
        self.id = id
        self.name = name
        self.node_type = node_type
        self.latitude = latitude
        self.longitude = longitude

class Edge:
    def __init__(self, source, target, distance_km, base_time_min, congestion_level, road_type, direction, risk_level, restriction, is_closed):
        self.source = source
        self.target = target
        self.distance_km = distance_km
        self.base_time_min = base_time_min
        self.congestion_level = congestion_level
        self.road_type = road_type
        self.direction = direction
        self.risk_level = risk_level
        self.restriction = restriction
        self.is_closed = is_closed

class Graph:
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

# ==========================================
# 2. KHỞI TẠO ĐỒ THỊ MẪU (PROTOTYPE GRAPH)
# ==========================================

def create_mock_graph():
    graph = Graph()
    
    # Tạo các node (Tọa độ giả lập để tính Heuristic)
    graph.add_node(Node("A", "Dinh Doc Lap", "landmark", 10.7769, 106.6951))
    graph.add_node(Node("B", "Nha Tho Duc Ba", "landmark", 10.7798, 106.6990))
    graph.add_node(Node("C", "Cho Ben Thanh", "landmark", 10.7725, 106.6980))
    graph.add_node(Node("D", "Pho di bo Nguyen Hue", "landmark", 10.7743, 106.7031))

    # Tạo các đoạn đường (edges)
    # Tuyến A -> B: Ngắn nhưng kẹt xe nặng (congestion = 5)
    graph.add_edge(Edge("A", "B", distance_km=0.5, base_time_min=2.0, congestion_level=5, road_type="main_road", direction="one_way", risk_level=1, restriction="none", is_closed=False))
    
    # Tuyến A -> C: Đường bình thường
    graph.add_edge(Edge("A", "C", distance_km=0.8, base_time_min=3.0, congestion_level=2, road_type="main_road", direction="two_way", risk_level=0, restriction="none", is_closed=False))
    
    # Tuyến C -> B: Đường vòng dài hơn nhưng thông thoáng
    graph.add_edge(Edge("C", "B", distance_km=1.0, base_time_min=3.5, congestion_level=1, road_type="secondary_road", direction="two_way", risk_level=0, restriction="none", is_closed=False))
    
    # Tuyến B -> D: Đường một chiều
    graph.add_edge(Edge("B", "D", distance_km=0.6, base_time_min=2.5, congestion_level=3, road_type="main_road", direction="one_way", risk_level=2, restriction="none", is_closed=False))
    
    # Tuyến C -> D: Bị đóng (is_closed = True)
    graph.add_edge(Edge("C", "D", distance_km=0.7, base_time_min=2.0, congestion_level=1, road_type="residential_road", direction="two_way", risk_level=0, restriction="none", is_closed=True))

    return graph

# ==========================================
# 3. CHẠY THỬ NGHIỆM CÁC THUẬT TOÁN
# ==========================================

def run_tests():
    graph = create_mock_graph()
    
    # Thiết lập profile Balanced mặc định
    weights = Weights(distance=0.30, time=0.45, congestion=0.15, risk=0.10)
    limits = Limits(max_distance_km=3.0, max_time_min=15.0)
    
    start_node = "A"
    goal_node = "D"
    
    print(f"--- TÌM ĐƯỜNG TỪ {start_node} ĐẾN {goal_node} ---")
    print("Profile: Balanced (Distance=0.3, Time=0.45, Congestion=0.15, Risk=0.10)\n")

    # 1. Dijkstra
    print(">> Đang chạy Dijkstra...")
    res_dijkstra = dijkstra(graph, start_node, goal_node, weights, limits)
    print_result(res_dijkstra)

    # 2. Greedy Best-First Search
    print("\n>> Đang chạy Greedy Best-First Search...")
    res_greedy = greedy_best_first_search(graph, start_node, goal_node)
    print_result(res_greedy)

    # 3. IDA*
    print("\n>> Đang chạy IDA*...")
    res_ida = ida_star(graph, start_node, goal_node, weights, limits)
    print_result(res_ida)


def print_result(result):
    if result.found:
        print(f"Thuật toán: {result.algorithm}")
        print(f"Lộ trình tìm được: {' -> '.join(result.path)}")
        print(f"Tổng khoảng cách: {result.total_distance:.2f} km")
        print(f"Tổng thời gian (có xét ùn tắc): {result.total_time:.2f} phút")
        print(f"Tổng Cost: {result.total_cost:.4f}")
        print(f"Số node đã mở rộng: {result.explored_nodes}")
        print(f"Thời gian xử lý: {result.processing_time_ms:.2f} ms")
    else:
        print(f"Thuật toán: {result.algorithm} - Không tìm thấy đường đi!")


if __name__ == "__main__":
    run_tests()