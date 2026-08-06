import time
import heapq
from .utils import SearchResult, get_heuristic, CONGESTION_MULTIPLIERS

def greedy_best_first_search(graph, start_id: str, goal_id: str) -> SearchResult:
    """
    Thuật toán Greedy Best-First Search.
    Thuật toán này định hướng tìm kiếm dựa hoàn toàn vào hàm ước lượng Heuristic h(n)
    (khoảng cách đường chim bay từ node hiện tại đến đích).
    Nó luôn ưu tiên mở rộng node có vẻ "gần đích nhất" mà không quan tâm đến 
    chi phí quãng đường đã đi qua (g_cost).
    
    Args:
        graph: Đối tượng đồ thị chứa các node và edge.
        start_id: ID của điểm xuất phát.
        goal_id: ID của điểm đích.
        
    Returns:
        SearchResult: Đối tượng chứa toàn bộ thông tin về kết quả tìm kiếm.
    """
    start_time_proc = time.time()
    
    # Lấy đối tượng node đích để tính heuristic cho các node khác
    goal_node = graph.get_node(goal_id)
    start_node = graph.get_node(start_id)
    
    # Tính heuristic ban đầu từ điểm xuất phát
    h_start = get_heuristic(start_node, goal_node)
    
    # Hàng đợi ưu tiên. Cấu trúc tuple:
    # (h_cost, node_id, path_so_far, total_dist, total_actual_time, dummy_g_cost)
    # Vì heapq sắp xếp theo phần tử đầu tiên, thuật toán sẽ luôn ưu tiên h_cost nhỏ nhất
    frontier = []
    heapq.heappush(frontier, (h_start, start_id, [start_id], 0.0, 0.0, 0.0))
    
    # Tập hợp các node đã duyệt để tránh vòng lặp (chu trình)
    explored = set()
    visited_order = []
    frontier_steps = []
    
    while frontier:
        # Ghi nhận trạng thái tập biên hiện tại để hiển thị lên GUI
        frontier_steps.append([item[1] for item in frontier])
        
        # Lấy node có giá trị heuristic (h_cost) nhỏ nhất ra khỏi tập biên
        h_cost, current_id, path, current_dist, current_time, current_g_cost = heapq.heappop(frontier)
        
        # Bỏ qua nếu node này đã được duyệt trước đó
        if current_id in explored:
            continue
            
        # Đánh dấu node đã duyệt
        explored.add(current_id)
        visited_order.append(current_id)
        
        # Nếu đã tìm thấy đích đến
        if current_id == goal_id:
            proc_time = (time.time() - start_time_proc) * 1000
            return SearchResult(
                algorithm="Greedy Best-First Search", 
                found=True, 
                path=path,
                visited_order=visited_order, 
                frontier_steps=frontier_steps,
                total_distance=current_dist, 
                total_time=current_time, 
                total_cost=current_g_cost,
                explored_nodes=len(explored), 
                processing_time_ms=proc_time, 
                message="Route found successfully."
            )
            
        # Khám phá các node hàng xóm
        for edge in graph.get_edges(current_id):
            # Chỉ xét các node kề chưa được duyệt và đoạn đường không bị đóng
            if edge.target not in explored and not edge.is_closed:
                target_node = graph.get_node(edge.target)
                
                # Tính Heuristic h(n) từ node hàng xóm đến đích
                h_next = get_heuristic(target_node, goal_node)
                new_path = path + [edge.target]
                
                # Tính thời gian thực tế để cộng dồn vào tổng thời gian
                multiplier = CONGESTION_MULTIPLIERS.get(edge.congestion_level, 1.0)
                actual_time = edge.base_time_min * multiplier
                
                # Đưa node hàng xóm vào hàng đợi ưu tiên.
                # Lưu ý: Greedy Best-First Search chỉ dùng h_next để quyết định ưu tiên.
                heapq.heappush(frontier, (
                    h_next, 
                    edge.target, 
                    new_path,
                    current_dist + edge.distance_km,
                    current_time + actual_time,
                    current_g_cost + 1  # Chi phí giả định (dummy cost) do thuật toán không tối ưu g(n)
                ))
                
    # Trường hợp đã duyệt hết đồ thị nhưng không thể đến đích
    proc_time = (time.time() - start_time_proc) * 1000
    return SearchResult(
        algorithm="Greedy Best-First Search", 
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