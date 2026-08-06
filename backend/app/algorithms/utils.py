import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

# ==========================================
# 1. CẤU TRÚC DỮ LIỆU DÙNG CHUNG
# ==========================================

@dataclass
class SearchResult:
    """
    Data class định nghĩa cấu trúc dữ liệu chuẩn trả về cho mọi thuật toán tìm kiếm.
    Điều này giúp GUI, metrics, report và các module khác xử lý kết quả một cách đồng nhất.
    """
    algorithm: str              # Tên thuật toán (vd: "Dijkstra", "IDA*")
    found: bool                 # Trạng thái: True nếu tìm thấy đường, False nếu không
    path: List[str]             # Danh sách ID các node trên tuyến đường cuối cùng (vd: ["N01", "N02", "N05"])
    visited_order: List[str]    # Thứ tự ID các node đã được duyệt (dùng để mô phỏng animation trên GUI)
    frontier_steps: List[List[str]] # Trạng thái của tập biên (frontier) qua từng bước (dùng cho GUI)
    total_distance: float       # Tổng chiều dài tuyến đường (đơn vị: km)
    total_time: float           # Tổng thời gian di chuyển thực tế (đã tính ùn tắc, đơn vị: phút)
    total_cost: float           # Tổng chi phí (cost) của tuyến đường dựa trên hàm cost function
    explored_nodes: int         # Tổng số node đã được mở rộng (để đánh giá hiệu suất thuật toán)
    processing_time_ms: float   # Thời gian thực thi thuật toán (đơn vị: milliseconds)
    message: str                # Thông báo kết quả hoặc lỗi (vd: "Route found successfully.")

@dataclass
class Weights:
    """Cấu trúc lưu trữ trọng số (weights) cho hàm tính chi phí dựa trên các Profile"""
    distance: float
    time: float
    congestion: float
    risk: float

@dataclass
class Limits:
    """Cấu trúc lưu trữ giới hạn dùng để chuẩn hóa (normalize) giá trị khoảng cách và thời gian"""
    max_distance_km: float = 3.0  # Giới hạn khoảng cách tối đa mặc định
    max_time_min: float = 15.0    # Giới hạn thời gian tối đa mặc định


# ==========================================
# 2. CÁC HẰNG SỐ (CONSTANTS)
# ==========================================

# Hệ số nhân thời gian di chuyển dựa trên mức độ ùn tắc (Từ 1: rất thông thoáng đến 5: ùn tắc nghiêm trọng)
CONGESTION_MULTIPLIERS = {
    1: 1.00,
    2: 1.15,
    3: 1.35,
    4: 1.70,
    5: 2.20,
}


# ==========================================
# 3. CÁC HÀM HỖ TRỢ (HELPER FUNCTIONS)
# ==========================================

def get_heuristic(node, goal, minimum_cost_per_km: float = 1.0) -> float:
    """
    Hàm tính giá trị Heuristic h(n) cho thuật toán Greedy Best-First Search và IDA*.
    Trong phiên bản đầu, hàm không xét đến mức độ ùn tắc để đảm bảo tính Admissible và Consistent.
    
    Args:
        node: Node hiện tại đang xét (cần có thuộc tính latitude, longitude).
        goal: Node đích (cần có thuộc tính latitude, longitude).
        minimum_cost_per_km: Hệ số quy đổi khoảng cách thành cost (mặc định là 1.0).
        
    Returns:
        float: Giá trị heuristic h(n) ước tính chi phí thấp nhất từ node hiện tại đến đích.
    """
    # Tính chênh lệch vĩ độ (latitude) và kinh độ (longitude)
    dx = node.longitude - goal.longitude
    dy = node.latitude - goal.latitude
    
    # Tính khoảng cách đường chim bay (Straight-line distance).
    # Nhân với 111.0 để quy đổi xấp xỉ từ độ (degrees) sang kilomet (km) trên Trái Đất.
    straight_line_distance = math.sqrt(dx**2 + dy**2) * 111.0 
    
    # h(n) = khoảng cách đường chim bay * minimum_cost_per_km
    return straight_line_distance * minimum_cost_per_km


def calculate_edge_cost(edge, weights: Weights, limits: Limits) -> float:
    """
    Hàm tính chi phí (cost) cho một đoạn đường (edge) dựa trên công thức hàm mục tiêu.
    Cost càng nhỏ thì tuyến đường càng tốt.
    
    Args:
        edge: Đoạn đường đang xét (chứa thông tin base_time_min, distance_km, congestion_level...).
        weights: Trọng số của profile đang chọn (vd: Balanced, Fastest route...).
        limits: Các giá trị giới hạn để chuẩn hóa.
        
    Returns:
        float: Giá trị cost đã được tính toán. Trả về vô cùng (float("inf")) nếu đường bị đóng.
    """
    # Nếu đường bị đóng hoàn toàn, trả về chi phí vô cực (inf) để thuật toán không bao giờ đi vào.
    if edge.is_closed:
        return float("inf")
        
    # Tính thời gian thực tế = thời gian gốc * hệ số ùn tắc
    actual_time = edge.base_time_min * CONGESTION_MULTIPLIERS.get(edge.congestion_level, 1.0)
    
    # Chuẩn hóa khoảng cách về dải 0.0 -> 1.0. Dùng hàm min() để đảm bảo không vượt quá 1.0
    normalized_distance = min(edge.distance_km / limits.max_distance_km, 1.0)
    
    # Chuẩn hóa thời gian thực tế về dải 0.0 -> 1.0
    normalized_time = min(actual_time / limits.max_time_min, 1.0)
    
    # Chuẩn hóa mức độ ùn tắc (thang 1-5) về dải 0.0 -> 1.0
    normalized_congestion = (edge.congestion_level - 1) / 4
    
    # Chuẩn hóa mức độ rủi ro (thang 0-5) về dải 0.0 -> 1.0
    normalized_risk = edge.risk_level / 5
    
    # Tính tổng cost dựa trên trọng số phân bổ của thuật toán
    total_edge_cost = (
        weights.distance * normalized_distance
        + weights.time * normalized_time
        + weights.congestion * normalized_congestion
        + weights.risk * normalized_risk
    )
    
    return total_edge_cost