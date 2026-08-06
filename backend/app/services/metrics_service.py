from typing import List, Dict, Any
from app.algorithms.utils import SearchResult, Weights, Limits

class MetricsService:
    """
    Service đảm nhận việc chạy thử nghiệm, đo lường và trích xuất các metrics 
    hiệu năng của các thuật toán tìm kiếm để phục vụ cho API, GUI và Báo cáo.
    """

    @staticmethod
    def compare_algorithms(
        graph, 
        start_id: str, 
        goal_id: str, 
        weights: Weights, 
        limits: Limits, 
        algorithms: List[Dict[str, Any]]
    ) -> List[SearchResult]:
        """
        Nhận vào danh sách các thuật toán, thực thi từng thuật toán trên đồ thị 
        và thu thập danh sách kết quả SearchResult.
        """
        results = []
        
        for algo in algorithms:
            algo_func = algo["func"]
            requires_weights = algo.get("requires_weights", False)
            
            if requires_weights:
                result = algo_func(graph, start_id, goal_id, weights, limits)
            else:
                result = algo_func(graph, start_id, goal_id)
                
            results.append(result)
            
        return results

    @staticmethod
    def format_summary_metrics(results: List[SearchResult]) -> List[Dict[str, Any]]:
        """
        Chuyển đổi danh sách SearchResult thành dạng Dictionary đơn giản, 
        giúp dễ dàng trả về JSON Response cho API hoặc lưu ra báo cáo.
        """
        summary = []
        for res in results:
            summary.append({
                "algorithm": res.algorithm,
                "found": res.found,
                "explored_nodes": res.explored_nodes,
                "processing_time_ms": round(res.processing_time_ms, 4),
                "total_distance_km": round(res.total_distance, 2) if res.found else None,
                "total_time_min": round(res.total_time, 2) if res.found else None,
                "total_cost": round(res.total_cost, 4) if res.found else None,
                "path_length": len(res.path) if res.found else 0
            })
        return summary

    @staticmethod
    def print_metrics_table(results: List[SearchResult]):
        """In ra bảng so sánh metrics đẹp mắt ngay tại console để debug/kiểm tra"""
        print("-" * 110)
        print(f"{'Thuật toán':<25} | {'Trạng thái':<10} | {'Node mở rộng':<15} | {'Thời gian (ms)':<15} | {'Quãng đường (km)':<15} | {'Cost':<10}")
        print("-" * 110)
        
        for res in results:
            status = "Thành công" if res.found else "Thất bại"
            nodes = res.explored_nodes
            time_ms = f"{res.processing_time_ms:.4f}"
            dist = f"{res.total_distance:.2f}" if res.found else "N/A"
            cost = f"{res.total_cost:.4f}" if res.found else "N/A"
            
            print(f"{res.algorithm:<25} | {status:<10} | {nodes:<15} | {time_ms:<15} | {dist:<15} | {cost:<10}")
        
        print("-" * 110)