import time
from .utils import SearchResult, calculate_edge_cost, get_heuristic, CONGESTION_MULTIPLIERS

def ida_star(graph, start_id: str, goal_id: str, weights, limits) -> SearchResult:
    """
    Thuật toán Iterative Deepening A* (IDA*).
    Sử dụng tìm kiếm theo chiều sâu (DFS) với một giới hạn chi phí (bound).
    Giới hạn này ban đầu bằng giá trị heuristic từ điểm bắt đầu đến đích.
    Nếu việc tìm kiếm vượt quá giới hạn chi phí này, giới hạn sẽ được tăng lên
    bằng chi phí nhỏ nhất vượt ngưỡng ở bước trước đó.
    
    Args:
        graph: Đối tượng đồ thị chứa các node và edge.
        start_id: ID của điểm xuất phát.
        goal_id: ID của điểm đích.
        weights: Trọng số của các tiêu chí từ profile người dùng.
        limits: Các giới hạn dùng để chuẩn hóa dữ liệu.
        
    Returns:
        SearchResult: Đối tượng chứa toàn bộ thông tin về kết quả tìm kiếm.
    """
    start_time_proc = time.time()
    
    goal_node = graph.get_node(goal_id)
    start_node = graph.get_node(start_id)
    
    # Giới hạn ban đầu (bound) được đặt bằng giá trị ước lượng h(n) từ điểm xuất phát
    bound = get_heuristic(start_node, goal_node)
    
    visited_order = []
    frontier_steps = []
    
    def search(current_id: str, g_cost: float, path: list, current_dist: float, current_time: float, current_bound: float):
        """
        Hàm đệ quy thực hiện tìm kiếm theo chiều sâu (DFS) với giới hạn bound.
        Trả về trạng thái "FOUND" kèm kết quả nếu tìm thấy,
        hoặc trả về chi phí f_cost nhỏ nhất vượt qua bound để làm bound cho lần lặp sau.
        """
        visited_order.append(current_id)
        current_node = graph.get_node(current_id)
        
        # Tính hàm đánh giá f(n) = g(n) + h(n)
        f_cost = g_cost + get_heuristic(current_node, goal_node)
        
        # Nếu tổng chi phí ước tính vượt quá giới hạn cho phép, cắt tỉa nhánh này
        # và trả về f_cost để có thể dùng cập nhật bound cho lần lặp tiếp theo
        if f_cost > current_bound:
            return f_cost, None
            
        # Nếu đã đến đích, trả về trạng thái tìm thấy và các thông tin quãng đường
        if current_id == goal_id:
            return "FOUND", (path, current_dist, current_time, g_cost)
            
        min_cost = float("inf")
        
        # Duyệt qua các node kề (hàng xóm)
        for edge in graph.get_edges(current_id):
            # Bỏ qua nếu đường bị đóng hoặc node kề đã nằm trong đường đi hiện tại (tránh chu trình)
            if edge.is_closed or edge.target in path:
                continue
                
            # Tính chi phí g(n) cho đoạn đường mới
            edge_cost = calculate_edge_cost(edge, weights, limits)
            
            # Tính toán thời gian thực tế dựa trên mức độ ùn tắc
            multiplier = CONGESTION_MULTIPLIERS.get(edge.congestion_level, 1.0)
            actual_time = edge.base_time_min * multiplier
            
            # Gọi đệ quy để đi sâu xuống node kề
            t, result = search(
                edge.target, 
                g_cost + edge_cost, 
                path + [edge.target],
                current_dist + edge.distance_km,
                current_time + actual_time,
                current_bound
            )
            
            # Nếu nhánh này tìm thấy đích, truyền kết quả lên trên
            if t == "FOUND":
                return "FOUND", result
                
            # Cập nhật chi phí nhỏ nhất bị vượt ngưỡng
            if t < min_cost:
                min_cost = t
                
        return min_cost, None

    # Vòng lặp tăng dần giới hạn (Iterative Deepening)
    while True:
        # Mỗi lần lặp sẽ chạy lại DFS từ đầu nhưng với một giới hạn (bound) lớn hơn
        t, result = search(start_id, 0.0, [start_id], 0.0, 0.0, bound)
        
        # Nếu tìm thấy đích, đóng gói và trả về kết quả
        if t == "FOUND":
            path, dist, time_val, cost = result
            proc_time = (time.time() - start_time_proc) * 1000
            
            # Ghi nhận trạng thái frontier giả lập (do bản chất DFS đệ quy không có frontier rõ như BFS/Dijkstra)
            frontier_steps.append([start_id]) 
            
            return SearchResult(
                algorithm="IDA*", 
                found=True, 
                path=path,
                visited_order=visited_order, 
                frontier_steps=frontier_steps,
                total_distance=dist, 
                total_time=time_val, 
                total_cost=cost,
                explored_nodes=len(set(visited_order)), 
                processing_time_ms=proc_time,
                message="Route found successfully."
            )
            
        # Nếu trả về vô cực, nghĩa là đã duyệt hết đồ thị mà không còn đường nào đi được nữa
        if t == float("inf"):
            proc_time = (time.time() - start_time_proc) * 1000
            return SearchResult(
                algorithm="IDA*", 
                found=False, 
                path=[], 
                visited_order=visited_order, 
                frontier_steps=frontier_steps, 
                total_distance=0.0, 
                total_time=0.0, 
                total_cost=0.0, 
                explored_nodes=len(set(visited_order)), 
                processing_time_ms=proc_time, 
                message="No route found."
            )
            
        # Cập nhật giới hạn mới bằng với chi phí nhỏ nhất đã bị cắt tỉa trong lần lặp vừa rồi
        bound = t