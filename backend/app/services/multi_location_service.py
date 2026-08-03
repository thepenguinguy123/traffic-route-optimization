"""
Module: multi_location_service.py
Path: backend/app/services/multi_location_service.py
Description: Bộ điều phối dịch vụ giao hàng nhiều điểm (Multi-location Service).
             Chịu trách nhiệm gọi thuật toán tìm đường điểm-đến-điểm (như A* của Thành viên A)
             để dựng ma trận chi phí (Cost Matrix) và ma trận đường đi (Path Matrix),
             sau đó gọi thuật toán Nearest Neighbor (Thành viên B) để tối ưu lộ trình.
Author: Thành viên B (Multi-location Delivery Logic Owner)
"""

import time
from typing import List, Dict, Any, Callable, Union, Optional, Tuple

# Import thuật toán Nearest Neighbor của Thành viên B
try:
    from app.algorithms.nearest_neighbor import nearest_neighbor_tsp
except ImportError:
    from nearest_neighbor import nearest_neighbor_tsp


class MultiLocationService:
    """
    Service quản lý và điều phối logic tối ưu hóa lộ trình giao hàng nhiều địa điểm.
    """

    def __init__(self, search_fn: Optional[Callable] = None):
        """
        Khởi tạo Service.

        Parameters:
        -----------
        search_fn : Optional[Callable]
            Hàm tìm đường ngắn nhất giữa 2 điểm do Thành viên A cung cấp (ví dụ: astar_search).
            Hàm này có dạng: search_fn(graph, start, goal, profile) -> Dict / SearchResult
        """
        self.search_fn = search_fn

    def set_search_function(self, search_fn: Callable) -> None:
        """Cập nhật hàm tìm đường ngắn nhất từ Thành viên A."""
        self.search_fn = search_fn

    def build_matrices(
        self,
        graph: Any,
        nodes: List[Union[str, int]],
        profile: str = "normal",
        search_fn: Optional[Callable] = None
    ) -> Tuple[Dict, Dict, Dict, Dict]:
        """
        Dựng ma trận chi phí (cost), đường đi (path), khoảng cách (distance) và thời gian (time)
        giữa tất cả các cặp điểm trong danh sách nodes.

        Sử dụng thuật toán tìm đường điểm-đến-điểm (A*) của Thành viên A.
        """
        fn = search_fn or self.search_fn
        if fn is None:
            raise ValueError("Chưa cung cấp hàm tìm đường điểm-đến-điểm (search_fn / A*).")

        cost_matrix: Dict[Any, Dict[Any, float]] = {}
        path_matrix: Dict[Any, Dict[Any, List]] = {}
        distance_matrix: Dict[Any, Dict[Any, float]] = {}
        time_matrix: Dict[Any, Dict[Any, float]] = {}

        for u in nodes:
            cost_matrix[u] = {}
            path_matrix[u] = {}
            distance_matrix[u] = {}
            time_matrix[u] = {}

            for v in nodes:
                if u == v:
                    cost_matrix[u][v] = 0.0
                    path_matrix[u][v] = [u]
                    distance_matrix[u][v] = 0.0
                    time_matrix[u][v] = 0.0
                else:
                    # Gọi thuật toán A* của Thành viên A
                    res = fn(graph, start=u, goal=v, profile=profile)

                    # Xử lý linh hoạt dữ liệu trả về từ A* (dù là object hay dict)
                    if isinstance(res, dict):
                        c = res.get("total_cost", float("inf"))
                        p = res.get("path", [])
                        d = res.get("total_distance", 0.0)
                        t = res.get("total_time", 0.0)
                    else:
                        c = getattr(res, "total_cost", float("inf"))
                        p = getattr(res, "path", [])
                        d = getattr(res, "total_distance", 0.0)
                        t = getattr(res, "total_time", 0.0)

                    cost_matrix[u][v] = c
                    path_matrix[u][v] = p
                    distance_matrix[u][v] = d
                    time_matrix[u][v] = t

        return cost_matrix, path_matrix, distance_matrix, time_matrix

    def optimize_delivery_route(
        self,
        start_node: Union[str, int],
        waypoints: List[Union[str, int]],
        graph: Any = None,
        profile: str = "normal",
        return_to_start: bool = False,
        search_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Quy trình điều phối tối ưu lộ trình giao hàng nhiều điểm:
        1. Chuẩn hóa danh sách các điểm.
        2. Dựng Ma trận chi phí & Ma trận đường đi (gọi A* của Thành viên A).
        3. Gọi Thuật toán Nearest Neighbor của Thành viên B sắp xếp thứ tự ghé thăm.
        4. Ghép các đoạn đường đi chi tiết và tính tổng các chỉ số metric.
        5. Đóng gói kết quả trả về đúng chuẩn SearchResult.
        """
        service_start_time = time.perf_counter()

        # 1. Chuẩn hóa danh sách điểm (loại bỏ trùng lặp)
        clean_waypoints = []
        for wp in waypoints:
            if wp != start_node and wp not in clean_waypoints:
                clean_waypoints.append(wp)

        all_locations = [start_node] + clean_waypoints

        if not clean_waypoints:
            return {
                "algorithm": "nearest_neighbor",
                "found": True,
                "visiting_order": [start_node],
                "path": [start_node],
                "total_cost": 0.0,
                "total_distance": 0.0,
                "total_time": 0.0,
                "execution_time_ms": 0.0,
                "is_optimal": True,
                "message": "Không có điểm giao hàng bổ sung nào."
            }

        # 2. Dựng ma trận chi phí & ma trận đường đi (gọi hàm A*)
        cost_matrix, path_matrix, distance_matrix, time_matrix = self.build_matrices(
            graph=graph,
            nodes=all_locations,
            profile=profile,
            search_fn=search_fn
        )

        # 3. Chạy thuật toán Nearest Neighbor của BẠN
        nn_result = nearest_neighbor_tsp(
            start_node=start_node,
            waypoints=clean_waypoints,
            cost_matrix=cost_matrix,
            return_to_start=return_to_start
        )

        visiting_order = nn_result["visiting_order"]

        # 4. Ghép lộ trình chi tiết và cộng dồn các giá trị khoảng cách, thời gian
        full_path: List[Union[str, int]] = []
        total_distance = 0.0
        total_time = 0.0

        for i in range(len(visiting_order) - 1):
            u = visiting_order[i]
            v = visiting_order[i + 1]

            segment_path = path_matrix.get(u, {}).get(v, [])
            total_distance += distance_matrix.get(u, {}).get(v, 0.0)
            total_time += time_matrix.get(u, {}).get(v, 0.0)

            # Ghép chuỗi nút (xử lý khử trùng lặp nút giao kề nhau)
            if not full_path:
                full_path.extend(segment_path)
            else:
                if segment_path and segment_path[0] == full_path[-1]:
                    full_path.extend(segment_path[1:])
                else:
                    full_path.extend(segment_path)

        total_service_time_ms = (time.perf_counter() - service_start_time) * 1000

        # 5. Đóng gói kết quả đầu ra theo chuẩn SearchResult
        return {
            "algorithm": "nearest_neighbor",
            "found": len(visiting_order) > 1,
            "visiting_order": visiting_order,           # Thứ tự ghé các điểm giao [N01, N08, N03...]
            "path": full_path,                           # Lộ trình nút chi tiết để vẽ lên bản đồ Web
            "total_cost": nn_result["total_cost"],       # Tổng chi phí đường đi
            "total_distance": round(total_distance, 3), # Tổng khoảng cách (km)
            "total_time": round(total_time, 2),         # Tổng thời gian dự kiến (phút)
            "algorithm_execution_time_ms": nn_result["execution_time_ms"], # Thời gian chạy riêng NN
            "total_service_execution_time_ms": round(total_service_time_ms, 3), # Tổng thời gian (A* + NN)
            "nodes_explored": nn_result["nodes_explored"],
            "unvisited_left": nn_result["unvisited_left"],
            "is_optimal": False                          # Thuật toán xấp xỉ
        }


# =====================================================================
# BLOCK KIỂM THỬ ĐỘC LẬP (Mô phỏng sự kết hợp giữa A* và Nearest Neighbor)
# =====================================================================
if __name__ == "__main__":
    print("=== TEST KIỂM THỬ CHI TIẾT MULTI_LOCATION_SERVICE ===")

    # 1. Giả lập hàm A* của Thành viên A
    def mock_astar_search(graph, start, goal, profile="normal"):
        mock_paths = {
            ("N01", "N03"): (["N01", "N02", "N03"], 2.5, 2.5, 5.0),
            ("N01", "N08"): (["N01", "N08"], 1.2, 1.2, 2.4),
            ("N01", "N12"): (["N01", "N06", "N12"], 4.0, 4.0, 8.0),
            ("N03", "N01"): (["N03", "N02", "N01"], 2.5, 2.5, 5.0),
            ("N03", "N08"): (["N03", "N07", "N08"], 1.8, 1.8, 3.6),
            ("N03", "N12"): (["N03", "N12"], 1.5, 1.5, 3.0),
            ("N08", "N01"): (["N08", "N01"], 1.2, 1.2, 2.4),
            ("N08", "N03"): (["N08", "N07", "N03"], 1.8, 1.8, 3.6),
            ("N08", "N12"): (["N08", "N10", "N12"], 3.0, 3.0, 6.0),
            ("N12", "N01"): (["N12", "N06", "N01"], 4.0, 4.0, 8.0),
            ("N12", "N03"): (["N12", "N03"], 1.5, 1.5, 3.0),
            ("N12", "N08"): (["N12", "N10", "N08"], 3.0, 3.0, 6.0),
        }
        
        path, cost, dist, time_val = mock_paths.get(
            (start, goal), 
            ([start, goal], float("inf"), float("inf"), float("inf"))
        )
        return {
            "total_cost": cost,
            "path": path,
            "total_distance": dist,
            "total_time": time_val
        }

    # 2. Khởi tạo Service của Thành viên B
    service = MultiLocationService(search_fn=mock_astar_search)

    # 3. Chạy thử nghiệm giao hàng với Kho = N01, Các đơn hàng = [N03, N08, N12]
    start_point = "N01"
    delivery_points = ["N03", "N08", "N12"]

    result = service.optimize_delivery_route(
        start_node=start_point,
        waypoints=delivery_points,
        profile="normal",
        return_to_start=False
    )

    print("\n--- KẾT QUẢ XỬ LÝ LỘ TRÌNH ĐA ĐIỂM ---")
    print(f"Thứ tự ghé thăm tối ưu (Order) : {result['visiting_order']}")
    print(f"Lộ trình nút chi tiết (Full Path): {result['path']}")
    print(f"Tổng chi phí (Cost)              : {result['total_cost']}")
    print(f"Tổng khoảng cách (Km)           : {result['total_distance']} km")
    print(f"Tổng thời gian (Phút)           : {result['total_time']} phút")
    print(f"Thời gian tính toán Service      : {result['total_service_execution_time_ms']} ms")