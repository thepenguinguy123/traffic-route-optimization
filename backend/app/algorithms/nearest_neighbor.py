"""
Module: nearest_neighbor.py
Path: backend/app/algorithms/nearest_neighbor.py
Description: Cài đặt thuật toán Tham lam Nearest Neighbor (Hàng xóm gần nhất)
             cho bài toán tối ưu lộ trình giao hàng nhiều điểm (Multi-location / TSP).
Author: Thành viên B (AI & TSP Optimization Logic)
"""

import time
from typing import List, Dict, Any, Union


def nearest_neighbor_tsp(
    start_node: Union[str, int],
    waypoints: List[Union[str, int]],
    cost_matrix: Dict[Union[str, int], Dict[Union[str, int], float]],
    return_to_start: bool = False
) -> Dict[str, Any]:
    """
    Thuật toán Tham lam Nearest Neighbor sắp xếp thứ tự ghé thăm các điểm giao hàng.

    Parameters:
    -----------
    start_node : Union[str, int]
        ID của điểm xuất phát (ví dụ: Kho hàng "N01").
    waypoints : List[Union[str, int]]
        Danh sách ID các điểm cần giao hàng (ví dụ: ["N03", "N08", "N12"]).
    cost_matrix : Dict[str, Dict[str, float]]
        Ma trận chi phí 2 chiều giữa các cặp điểm: cost_matrix[u][v] = chi phí từ u tới v.
        Được tính toán trước thông qua thuật toán A* (hoặc UCS).
    return_to_start : bool, optional
        Nếu True, shipper sẽ quay lại điểm xuất phát sau khi hoàn thành các đơn (Closed TSP).
        Nếu False, kết thúc tại điểm giao cuối cùng (Open TSP - mặc định).

    Returns:
    --------
    Dict[str, Any]
        Kết quả sắp xếp lộ trình gồm thứ tự ghé thăm, tổng chi phí, thời gian xử lý và các metrics.
    """
    start_time = time.perf_counter()

    # 1. Chuẩn hóa tập các điểm cần ghé (loại bỏ trùng lặp và loại bỏ start_node nếu nằm trong waypoints)
    unvisited = set(waypoints)
    if start_node in unvisited:
        unvisited.remove(start_node)

    current_node = start_node
    visiting_order = [current_node]
    total_cost = 0.0
    nodes_explored_count = 0

    # 2. Vòng lặp Tham lam (Greedy Loop): Chọn điểm chưa đi có chi phí nhỏ nhất từ current_node
    while unvisited:
        next_node = None
        min_cost = float('inf')

        # Duyệt qua từng điểm chưa ghé thăm để tìm điểm gần nhất theo cost_matrix
        for candidate in unvisited:
            nodes_explored_count += 1
            
            # Lấy chi phí từ current_node tới candidate (mặc định inf nếu không tìm thấy đường)
            cost = cost_matrix.get(current_node, {}).get(candidate, float('inf'))
            
            if cost < min_cost:
                min_cost = cost
                next_node = candidate

        # Trường hợp không thể đến bất kỳ điểm còn lại nào (đường bị chặn hoàn toàn)
        if next_node is None or min_cost == float('inf'):
            break

        # Cập nhật trạng thái lộ trình
        total_cost += min_cost
        current_node = next_node
        visiting_order.append(current_node)
        unvisited.remove(current_node)

    # 3. Tùy chọn quay về điểm bắt đầu (nếu shipper cần về kho)
    if return_to_start and current_node != start_node:
        return_cost = cost_matrix.get(current_node, {}).get(start_node, float('inf'))
        if return_cost != float('inf'):
            total_cost += return_cost
            visiting_order.append(start_node)

    execution_time_ms = (time.perf_counter() - start_time) * 1000  # Đổi sang mili-giây (ms)

    # 4. Trả về kết quả đóng gói chuẩn xác
    return {
        "algorithm": "nearest_neighbor",
        "visiting_order": visiting_order,       # Thứ tự các điểm lớn ghé thăm [start, p1, p2...]
        "total_cost": round(total_cost, 4),      # Tổng chi phí đường đi
        "nodes_explored": nodes_explored_count,  # Số lần so sánh chi phí
        "execution_time_ms": round(execution_time_ms, 3), # Thời gian tính toán (ms)
        "unvisited_left": list(unvisited),      # Danh sách điểm không thể đến (nếu có lỗi kết nối)
        "is_optimal": False                     # Thuật toán xấp xỉ (Greedy heuristic)
    }


if __name__ == "__main__":
    # === TEST CASE MÔ PHỎNG ĐỂ BẠN KIỂM THỬ ĐỘC LẬP ===
    # Giả sử có 4 điểm: N01 (Kho), N03, N08, N12
    sample_cost_matrix = {
        "N01": {"N03": 2.5, "N08": 1.2, "N12": 4.0},
        "N03": {"N01": 2.5, "N08": 1.8, "N12": 1.5},
        "N08": {"N01": 1.2, "N03": 1.8, "N12": 3.0},
        "N12": {"N01": 4.0, "N03": 1.5, "N08": 3.0}
    }

    test_start = "N01"
    test_waypoints = ["N03", "N08", "N12"]

    res = nearest_neighbor_tsp(test_start, test_waypoints, sample_cost_matrix)
    print("--- KẾT QUẢ KIỂM THỬ NEAREST NEIGHBOR ---")
    print(f"Thứ tự ghé thăm: {res['visiting_order']}")
    print(f"Tổng chi phí:    {res['total_cost']}")
    print(f"Thời gian chạy:  {res['execution_time_ms']} ms")
    print(f"Tính tối ưu:     {res['is_optimal']}")