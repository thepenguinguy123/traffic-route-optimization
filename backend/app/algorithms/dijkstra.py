import time
import heapq
from .utils import SearchResult, calculate_edge_cost, CONGESTION_MULTIPLIERS

def dijkstra(graph, start_id: str, goal_id: str, weights, limits) -> SearchResult:
    """
    Thuật toán Dijkstra tìm đường đi ngắn nhất (hoặc chi phí thấp nhất) từ start_id đến goal_id.
    Thuật toán này luôn mở rộng node có tổng chi phí tích lũy g(n) nhỏ nhất trong tập biên (frontier).
    
    Args:
        graph: Đối tượng đồ thị chứa các node và edge.
        start_id: ID của điểm xuất phát.
        goal_id: ID của điểm đích.
        weights: Trọng số của các tiêu chí (distance, time, congestion, risk) từ profile người dùng.
        limits: Các giới hạn dùng để chuẩn hóa (normalize) dữ liệu.
        
    Returns:
        SearchResult: Đối tượng chứa toàn bộ thông tin về kết quả tìm kiếm để trả về cho GUI.
    """
    # Ghi nhận thời gian bắt đầu để tính tổng thời gian xử lý của thuật toán
    start_time_proc = time.time()
    
    # Hàng đợi ưu tiên (Priority Queue) để lưu các node cần duyệt.
    # Mỗi phần tử trong hàng đợi là một tuple có cấu trúc:
    # (g_cost, current_id, path_so_far, total_dist, total_actual_time)
    # heapq sẽ tự động sắp xếp các phần tử dựa trên giá trị đầu tiên (g_cost).
    frontier = []
    heapq.heappush(frontier, (0.0, start_id, [start_id], 0.0, 0.0))
    
    # Tập hợp (set) chứa ID của các node đã được mở rộng (đã duyệt qua)
    # Dùng set để kiểm tra node đã duyệt với độ phức tạp O(1)
    explored = set()
    
    # Lưu lại thứ tự các node đã duyệt để phục vụ cho việc animation trên GUI
    visited_order = []
    
    # Lưu lại trạng thái của frontier sau mỗi bước để vẽ animation
    frontier_steps = []
    
    # Vòng lặp chính của thuật toán: tiếp tục chạy chừng nào frontier còn phần tử
    while frontier:
        # Lưu lại danh sách các node hiện có trong frontier (chỉ lấy ID)
        frontier_steps.append([item[1] for item in frontier])
        
        # Lấy node có g_cost nhỏ nhất ra khỏi hàng đợi ưu tiên
        g_cost, current_id, path, current_dist, current_time = heapq.heappop(frontier)
        
        # Nếu node này đã được duyệt trước đó với chi phí thấp hơn, bỏ qua nó
        if current_id in explored:
            continue
            
        # Đánh dấu node hiện tại là đã duyệt
        explored.add(current_id)
        visited_order.append(current_id)
        
        # Kiểm tra điều kiện dừng: Nếu node hiện tại chính là đích đến
        if current_id == goal_id:
            # Tính toán thời gian thuật toán đã chạy (đổi ra milliseconds)
            proc_time = (time.time() - start_time_proc) * 1000
            
            # Trả về kết quả thành công
            return SearchResult(
                algorithm="Dijkstra", 
                found=True, 
                path=path,
                visited_order=visited_order, 
                frontier_steps=frontier_steps,
                total_distance=current_dist, 
                total_time=current_time, 
                total_cost=g_cost,
                explored_nodes=len(explored), 
                processing_time_ms=proc_time,
                message="Route found successfully."
            )
            
        # Nếu chưa đến đích, tiến hành mở rộng các node kề (hàng xóm) của node hiện tại
        for edge in graph.get_edges(current_id):
            # Chỉ xét những node kề chưa được duyệt
            if edge.target not in explored:
                # Tính chi phí của đoạn đường (edge) này dựa trên hàm cost function
                edge_cost = calculate_edge_cost(edge, weights, limits)
                
                # Nếu đường bị đóng (cost = vô cực), bỏ qua đoạn đường này
                if edge_cost == float("inf"):
                    continue
                
                # Cập nhật tổng chi phí (g_cost) và tuyến đường (path) cho node kề
                new_cost = g_cost + edge_cost
                new_path = path + [edge.target]
                
                # Tính toán thời gian thực tế cho đoạn đường này (dựa trên ùn tắc)
                multiplier = CONGESTION_MULTIPLIERS.get(edge.congestion_level, 1.0)
                actual_time = edge.base_time_min * multiplier
                
                # Đẩy node kề vào hàng đợi ưu tiên để xét trong tương lai
                heapq.heappush(frontier, (
                    new_cost, 
                    edge.target, 
                    new_path, 
                    current_dist + edge.distance_km, 
                    current_time + actual_time
                ))
                
    # Nếu vòng lặp kết thúc mà hàng đợi trống rỗng (không tìm được đích đến)
    proc_time = (time.time() - start_time_proc) * 1000
    return SearchResult(
        algorithm="Dijkstra", 
        found=False, 
        path=[], 
        visited_order=visited_order, 
        frontier_steps=frontier_steps, 
        total_distance=0.0, 
        total_time=0.0, 
        total_cost=0.0, 
        explored_nodes=len(explored), 
        processing_time_ms=proc_time, 
        message="No route found."
    )