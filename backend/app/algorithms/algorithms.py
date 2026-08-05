import time
import heapq
from typing import Dict, List, Any, Tuple, Optional
from app.repositories.graph_data import NODES, EDGES, calculate_cost, haversine_distance

# Build adjacency list for faster lookup
def get_adj_list() -> Dict[str, List[Dict[str, Any]]]:
    """
    Xây dựng adjacency list từ danh sách edges.
    
    Returns:
        Dict[str, List[Dict]]: Adjacency list với key là node ID
    """
    adj: Dict[str, List[Dict[str, Any]]] = {n: [] for n in NODES}
    for e in EDGES:
        adj[e["from"]].append(e)
    return adj

ADJ: Dict[str, List[Dict[str, Any]]] = get_adj_list()


def format_result(path: List[str], animation_log: List[Dict[str, Any]], 
                 stats: Dict[str, Any], explanation: str) -> Dict[str, Any]:
    """
    Format kết quả tìm kiếm.
    
    Args:
        path: Đường đi tìm được
        animation_log: Log các bước animation
        stats: Thống kê đường đi
        explanation: Giải thích kết quả
        
    Returns:
        Dict: Kết quả đã format
    """
    return {
        "path": path,
        "animation_log": animation_log,
        "stats": stats,
        "explanation": explanation
    }


def calculate_path_stats(path: List[str], start_time: float) -> Dict[str, Any]:
    """
    Tính toán thống kê của một đường đi cho trước.
    
    Args:
        path: Danh sách node IDs trong đường đi
        start_time: Thời gian bắt đầu tính toán
        
    Returns:
        Dict: Thống kê bao gồm total_distance, total_time, total_cost, processing_time_ms
    """
    total_dist: float = 0.0
    total_time: float = 0.0
    total_cost: float = 0.0
    
    if len(path) > 1:
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            for e in ADJ[u]:
                if e["to"] == v:
                    total_dist += e["distance_km"]
                    total_time += e["time_min"]
                    total_cost += calculate_cost(e, "combined")
                    break
                    
    end_time = time.perf_counter()
    return {
        "total_distance": round(total_dist, 2),
        "total_time": round(total_time, 2),
        "total_cost": round(total_cost, 2),
        "processing_time_ms": round((end_time - start_time) * 1000, 2)
    }


def dfs_search(start: str, end: str, cost_type: str = "distance") -> Dict[str, Any]:
    """
    Thuật toán Depth-First Search (Tìm kiếm theo chiều sâu).
    Mở rộng nhánh càng sâu càng tốt trước khi quay lui.
    
    Args:
        start: Node bắt đầu
        end: Node kết thúc
        cost_type: Loại chi phí ('distance', 'time', 'combined')
        
    Returns:
        Dict: Kết quả tìm kiếm bao gồm path, animation_log, stats, explanation
    """
    start_time: float = time.perf_counter()
    stack: List[Tuple[str, List[str]]] = [(start, [start])]
    visited: set = set()
    animation_log: List[Dict[str, Any]] = []
    step: int = 1
    
    nodes_explored: int = 0
    
    while stack:
        curr, path = stack.pop()
        
        if curr not in visited:
            animation_log.append({
                "step": step,
                "node": curr,
                "status": "frontier",
                "parent": path[-2] if len(path) > 1 else None
            })
            step += 1
            
            visited.add(curr)
            nodes_explored += 1
            
            animation_log.append({
                "step": step,
                "node": curr,
                "status": "visited",
                "parent": path[-2] if len(path) > 1 else None
            })
            step += 1
            
            if curr == end:
                stats: Dict[str, Any] = calculate_path_stats(path, start_time)
                stats["nodes_explored"] = nodes_explored
                explanation: str = (f"Thuật toán DFS tìm thấy đường đi từ {NODES[start]['name']} "
                                   f"đến {NODES[end]['name']} qua {len(path)} điểm. "
                                   f"Đây là đường đầu tiên tìm được theo chiều sâu, "
                                   f"không nhất thiết là đường tối ưu nhất.")
                return format_result(path, animation_log, stats, explanation)
                
            # Đảo ngược thứ tự thêm vào stack để đi theo thứ tự nhất định
            for edge in reversed(ADJ[curr]):
                neighbor: str = edge["to"]
                if neighbor not in visited:
                    stack.append((neighbor, path + [neighbor]))
                    
    return format_result([], animation_log, 
                         {"nodes_explored": nodes_explored, 
                          "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)}, 
                         "Không tìm thấy đường đi.")


def greedy_search(start: str, end: str, cost_type: str = "distance") -> Dict[str, Any]:
    """
    Thuật toán Greedy Best-First Search.
    Sử dụng heuristic là khoảng cách Haversine (đường chim bay) đến đích.
    
    Args:
        start: Node bắt đầu
        end: Node kết thúc
        cost_type: Loại chi phí ('distance', 'time', 'combined')
        
    Returns:
        Dict: Kết quả tìm kiếm bao gồm path, animation_log, stats, explanation
    """
    start_time: float = time.perf_counter()
    # Priority Queue elements: (heuristic, current_node, path)
    pq: List[Tuple[float, str, List[str]]] = [(haversine_distance(start, end), start, [start])]
    visited: set = set()
    animation_log: List[Dict[str, Any]] = []
    step: int = 1
    nodes_explored: int = 0
    
    while pq:
        _, curr, path = heapq.heappop(pq)
        
        if curr in visited:
            continue
            
        animation_log.append({
            "step": step,
            "node": curr,
            "status": "frontier",
            "parent": path[-2] if len(path) > 1 else None
        })
        step += 1
        
        visited.add(curr)
        nodes_explored += 1
        
        animation_log.append({
            "step": step,
            "node": curr,
            "status": "visited",
            "parent": path[-2] if len(path) > 1 else None
        })
        step += 1
        
        if curr == end:
            stats: Dict[str, Any] = calculate_path_stats(path, start_time)
            stats["nodes_explored"] = nodes_explored
            explanation: str = (f"Thuật toán Greedy Best-First Search đã tìm đường từ "
                               f"{NODES[start]['name']} đến {NODES[end]['name']}. "
                               f"Thuật toán ưu tiên mở rộng các nút có khoảng cách đường chim bay "
                               f"gần đích nhất ở mỗi bước. Nó thường nhanh hơn nhưng không đảm bảo "
                               f"đường đi là tối ưu hoàn toàn (shortest path).")
            return format_result(path, animation_log, stats, explanation)
            
        for edge in ADJ[curr]:
            neighbor: str = edge["to"]
            if neighbor not in visited:
                h: float = haversine_distance(neighbor, end)
                heapq.heappush(pq, (h, neighbor, path + [neighbor]))
                
    return format_result([], animation_log, 
                         {"nodes_explored": nodes_explored, 
                          "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)}, 
                         "Không tìm thấy đường đi.")


def dijkstra_path(start: str, end: str, cost_type: str = "distance") -> Tuple[List[str], float]:
    """
    Hàm phụ trợ cho TSP: Tìm đường đi ngắn nhất giữa 2 điểm cụ thể sử dụng Dijkstra.
    
    Args:
        start: Node bắt đầu
        end: Node kết thúc
        cost_type: Loại chi phí ('distance', 'time', 'combined')
        
    Returns:
        Tuple[List[str], float]: (Đường đi, tổng chi phí)
    """
    pq: List[Tuple[float, str, List[str]]] = [(0, start, [start])]
    visited: set = set()
    while pq:
        cost, curr, path = heapq.heappop(pq)
        
        if curr in visited: 
            continue
        visited.add(curr)
        
        if curr == end: 
            return path, cost
            
        for e in ADJ[curr]:
            if e["to"] not in visited:
                next_cost: float = cost + calculate_cost(e, cost_type)
                heapq.heappush(pq, (next_cost, e["to"], path + [e["to"]]))
    return [], float('inf')


def tsp_search(waypoints: List[str], cost_type: str = "distance") -> Dict[str, Any]:
    """
    Giải bài toán Traveling Salesman Problem (TSP).
    Phương pháp: Láng giềng gần nhất (Nearest Neighbor).
    Lần lượt chọn trạm tiếp theo gần nhất chưa được ghé thăm.
    
    Args:
        waypoints: Danh sách các điểm cần ghé thăm
        cost_type: Loại chi phí ('distance', 'time', 'combined')
        
    Returns:
        Dict: Kết quả tìm kiếm bao gồm path, animation_log, stats, explanation
    """
    start_time: float = time.perf_counter()
    if not waypoints or len(waypoints) < 2:
        return format_result([], [], {}, "Cần ít nhất 2 điểm để tính toán TSP.")
    
    current: str = waypoints[0]
    unvisited: set = set(waypoints[1:])
    tour: List[str] = [current]
    
    animation_log: List[Dict[str, Any]] = []
    step: int = 1
    
    full_path: List[str] = [current]
    
    while unvisited:
        best_next: Optional[str] = None
        best_cost: float = float('inf')
        best_subpath: List[str] = []
        
        for nxt in unvisited:
            # Tìm đường đi và chi phí ngắn nhất từ hiện tại đến nxt
            subpath, cost = dijkstra_path(current, nxt, cost_type)
            if cost < best_cost:
                best_cost = cost
                best_next = nxt
                best_subpath = subpath
                
        if best_next:
            animation_log.append({
                "step": step, 
                "node": best_next, 
                "status": "frontier", 
                "parent": current
            })
            step += 1
            
            tour.append(best_next)
            unvisited.remove(best_next)
            
            # Ghép nối đường đi (tránh duplicate đỉnh bắt đầu của đoạn nối)
            if len(best_subpath) > 1:
                full_path.extend(best_subpath[1:])
                
            current = best_next
            
            animation_log.append({
                "step": step, 
                "node": best_next, 
                "status": "visited", 
                "parent": current
            })
            step += 1
        else:
            # Đồ thị bị chia cắt
            break
            
    stats: Dict[str, Any] = calculate_path_stats(full_path, start_time)
    stats["nodes_explored"] = len(tour)
    
    tour_names: str = " → ".join([NODES[n]['name'] for n in tour])
    explanation: str = (f"Thuật toán TSP (Nearest Neighbor) tìm được thứ tự ghé thăm tối ưu cục bộ: "
                       f"{tour_names}. Ở mỗi bước, thuật toán luôn chọn điểm đến chưa được thăm "
                       f"có chi phí di chuyển thấp nhất từ vị trí hiện tại.")
    
    return format_result(full_path, animation_log, stats, explanation)
