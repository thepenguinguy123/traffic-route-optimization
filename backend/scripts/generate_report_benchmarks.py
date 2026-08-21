"""Tạo số liệu và biểu đồ tái lập cho phần so sánh thuật toán của báo cáo.

Chạy từ thư mục gốc dự án:
python backend/scripts/generate_report_benchmarks.py
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.algorithms.registry import ALGORITHM_REGISTRY
from backend.app.core.cost import CostCalculator
from backend.app.core.cost_profiles import COST_PROFILES
from backend.app.core.graph import TrafficGraph
from backend.app.repositories.clean_dataset_repository import load_clean_graph


OUTPUT_DIRECTORY = PROJECT_ROOT / "output/report_assets"
ALGORITHMS = (
    "bfs",
    "dfs",
    "ucs",
    "astar",
    "greedy_best_first",
    "ida_star",
)
ALGORITHM_LABELS = {
    "bfs": "BFS",
    "dfs": "DFS",
    "ucs": "UCS",
    "astar": "A*",
    "greedy_best_first": "GBFS",
    "ida_star": "IDA*",
}
REPETITIONS = 101
EXPERIMENT_NODE_COUNT = 30


@dataclass(frozen=True)
class ExperimentCase:
    """Giữ nguyên đồ thị con và cặp điểm dùng xuyên suốt thí nghiệm."""

    node_ids: tuple[str, ...]
    start: str
    goal: str


def build_local_node_ids(
    graph: TrafficGraph,
    seed: str,
    node_limit: int,
) -> tuple[str, ...] | None:
    """Lấy một vùng liên thông cục bộ có đúng số node cần cho thí nghiệm."""

    queue = deque([seed])
    discovered = {seed}
    selected: list[str] = []

    while queue and len(selected) < node_limit:
        current = queue.popleft()
        selected.append(current)
        adjacent_nodes = sorted(
            set(graph.get_neighbors(current)) | set(graph.get_predecessors(current))
        )
        for neighbor in adjacent_nodes:
            if neighbor in discovered:
                continue
            discovered.add(neighbor)
            queue.append(neighbor)

    if len(selected) != node_limit:
        return None
    return tuple(sorted(selected))


def build_induced_graph(
    source_graph: TrafficGraph,
    node_ids: tuple[str, ...],
) -> TrafficGraph:
    """Sao chép đồ thị cảm sinh, chỉ giữ các node của ca thực nghiệm."""

    node_id_set = set(node_ids)
    graph = TrafficGraph(CostCalculator())
    for node in source_graph.get_all_nodes():
        if node.id in node_id_set:
            graph.add_node(node)
    for edge in source_graph.get_all_edges():
        if edge.source in node_id_set and edge.target in node_id_set:
            graph.add_edge(edge)
    return graph


def find_congestion_case() -> ExperimentCase:
    """Chọn đồ thị con 30 node có đường vòng dài hơn khi kẹt xe tăng."""

    full_normal_graph = load_clean_graph(scenario="normal")
    full_rush_graph = load_clean_graph(scenario="rush_hour")
    profile = COST_PROFILES["balanced"]
    candidate: tuple[float, ExperimentCase] | None = None

    for seed in sorted(node.id for node in full_normal_graph.get_all_nodes()):
        node_ids = build_local_node_ids(
            full_normal_graph,
            seed,
            EXPERIMENT_NODE_COUNT,
        )
        if node_ids is None:
            continue

        normal_graph = build_induced_graph(full_normal_graph, node_ids)
        rush_graph = build_induced_graph(full_rush_graph, node_ids)
        for start in node_ids:
            for goal in node_ids:
                if start == goal:
                    continue
                normal = ALGORITHM_REGISTRY["ucs"](
                    normal_graph,
                    start,
                    goal,
                    profile,
                )
                rush = ALGORITHM_REGISTRY["ucs"](
                    rush_graph,
                    start,
                    goal,
                    profile,
                )
                if not normal.found or not rush.found or normal.path == rush.path:
                    continue

                distance_increase = rush.total_distance - normal.total_distance
                old_route_rush_cost = rush_graph.calculate_path_cost(
                    normal.path,
                    profile,
                )
                if (
                    distance_increase <= 0
                    or rush.total_cost >= old_route_rush_cost
                ):
                    continue

                score = distance_increase + 0.01 * (
                    len(rush.path) - len(normal.path)
                )
                experiment_case = ExperimentCase(
                    node_ids=node_ids,
                    start=start,
                    goal=goal,
                )
                if candidate is None or score > candidate[0]:
                    candidate = (score, experiment_case)

    if candidate is None:
        raise RuntimeError(
            "Không tìm thấy đồ thị con 30 node có đường vòng do kẹt xe."
        )
    return candidate[1]


def measure_algorithms(
    graph: TrafficGraph,
    start: str,
    goal: str,
) -> list[dict[str, float | int | str]]:
    """Đo median thời gian thực thi trên cùng graph và cùng profile."""

    profile = COST_PROFILES["balanced"]
    rows: list[dict[str, float | int | str]] = []
    for algorithm in ALGORITHMS:
        results = [
            ALGORITHM_REGISTRY[algorithm](graph, start, goal, profile)
            for _ in range(REPETITIONS)
        ]
        result = results[0]
        if not result.found:
            raise RuntimeError(f"{algorithm} không tìm được tuyến thử nghiệm.")
        rows.append(
            {
                "algorithm": ALGORITHM_LABELS[algorithm],
                "explored_nodes": result.explored_nodes,
                "total_distance_km": round(result.total_distance, 3),
                "total_time_min": round(result.total_time, 3),
                "total_cost": round(result.total_cost, 4),
                "processing_time_ms_median": round(
                    statistics.median(item.processing_time_ms for item in results), 4
                ),
                "path": " -> ".join(result.path),
            }
        )
    return rows


def route_summary(
    normal_graph: TrafficGraph,
    rush_graph: TrafficGraph,
    start: str,
    goal: str,
) -> list[dict[str, float | str]]:
    """So sánh tuyến tối ưu trước và trong giờ cao điểm bằng UCS."""

    profile = COST_PROFILES["balanced"]
    normal = ALGORITHM_REGISTRY["ucs"](normal_graph, start, goal, profile)
    rush = ALGORITHM_REGISTRY["ucs"](rush_graph, start, goal, profile)
    old_route_in_rush_cost = rush_graph.calculate_path_cost(normal.path, profile)
    old_route_in_rush_time = rush_graph.calculate_path_time(normal.path)
    return [
        {
            "scenario": "Bình thường - tuyến tối ưu",
            "path": " -> ".join(normal.path),
            "distance_km": round(normal.total_distance, 3),
            "time_min": round(normal.total_time, 3),
            "cost": round(normal.total_cost, 4),
        },
        {
            "scenario": "Giờ cao điểm - giữ tuyến cũ",
            "path": " -> ".join(normal.path),
            "distance_km": round(normal.total_distance, 3),
            "time_min": round(old_route_in_rush_time, 3),
            "cost": round(old_route_in_rush_cost, 4),
        },
        {
            "scenario": "Giờ cao điểm - tuyến tối ưu mới",
            "path": " -> ".join(rush.path),
            "distance_km": round(rush.total_distance, 3),
            "time_min": round(rush.total_time, 3),
            "cost": round(rush.total_cost, 4),
        },
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    """Ghi bảng dữ liệu có thể nhập trực tiếp vào Word hoặc Excel."""

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def create_chart(rows: list[dict[str, float | int | str]], path: Path) -> None:
    """Tạo ba biểu đồ cột: chất lượng tuyến, node duyệt và thời gian xử lý."""

    labels = [str(row["algorithm"]) for row in rows]
    measures = [
        ("Tổng chi phí (thấp hơn tốt hơn)", "total_cost"),
        ("Số node đã duyệt", "explored_nodes"),
        ("Thời gian xử lý trung vị (ms)", "processing_time_ms_median"),
    ]
    colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#af7aa1"]
    chart_width = 430
    chart_height = 320
    bar_width = 42
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1290" height="360" '
        'viewBox="0 0 1290 360" role="img" '
        'aria-label="Biểu đồ so sánh các thuật toán">',
        '<rect width="1290" height="360" fill="white"/>',
    ]
    for index, (title, key) in enumerate(measures):
        offset_x = index * chart_width
        values = [float(row[key]) for row in rows]
        maximum = max(values) or 1.0
        baseline = 275
        plot_height = 205
        parts.extend(
            [
                f'<text x="{offset_x + 215}" y="28" text-anchor="middle" '
                'font-family="Arial" font-size="15" font-weight="bold">'
                f'{title}</text>',
                f'<line x1="{offset_x + 48}" y1="{baseline}" '
                f'x2="{offset_x + 410}" y2="{baseline}" stroke="#333"/>',
                f'<line x1="{offset_x + 48}" y1="55" '
                f'x2="{offset_x + 48}" y2="{baseline}" stroke="#333"/>',
            ]
        )
        for tick in range(5):
            value = maximum * tick / 4
            y = baseline - plot_height * tick / 4
            parts.extend(
                [
                    f'<line x1="{offset_x + 48}" y1="{y:.1f}" '
                    f'x2="{offset_x + 410}" y2="{y:.1f}" stroke="#ddd"/>',
                    f'<text x="{offset_x + 42}" y="{y + 4:.1f}" '
                    'text-anchor="end" font-family="Arial" font-size="10">'
                    f'{value:.4g}</text>',
                ]
            )
        for bar_index, (label, value, color) in enumerate(zip(labels, values, colors)):
            x = offset_x + 64 + bar_index * 57
            height = plot_height * value / maximum
            y = baseline - height
            parts.extend(
                [
                    f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" '
                    f'height="{height:.1f}" fill="{color}"/>',
                    f'<text x="{x + bar_width / 2}" y="{y - 5:.1f}" '
                    'text-anchor="middle" font-family="Arial" font-size="10">'
                    f'{value:.4g}</text>',
                    f'<text x="{x + bar_width / 2}" y="{baseline + 15}" '
                    'text-anchor="end" transform="rotate(-35 '
                    f'{x + bar_width / 2} {baseline + 15})" font-family="Arial" '
                    f'font-size="10">{label}</text>',
                ]
            )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def create_markdown(
    experiment_case: ExperimentCase,
    edge_count: int,
    rows: list[dict],
    traffic: list[dict],
) -> str:
    """Tạo đoạn Markdown tiếng Việt để chèn trực tiếp vào báo cáo."""

    table_rows = "\n".join(
        "| {algorithm} | {explored_nodes} | {total_distance_km:.3f} | "
        "{total_time_min:.3f} | {total_cost:.4f} | "
        "{processing_time_ms_median:.4f} |".format(**row)
        for row in rows
    )
    traffic_rows = "\n".join(
        "| {scenario} | `{path}` | {distance_km:.3f} | {time_min:.3f} | {cost:.4f} |".format(
            **row
        )
        for row in traffic
    )
    start = experiment_case.start
    goal = experiment_case.goal
    return f"""# Kết quả thực nghiệm so sánh thuật toán

## Thiết lập

Thí nghiệm dùng **đồ thị con cảm sinh gồm đúng {len(experiment_case.node_ids)} node và {edge_count} cạnh** từ dataset giao thông hybrid của dự án (các địa điểm thực tế, điều kiện giao thông mô phỏng tái lập). Cặp điểm đầu-cuối là `{start}` -> `{goal}`, profile chi phí là `balanced`. Như vậy toàn bộ phần thực nghiệm tuân theo yêu cầu kiểm thử trong khoảng 30 node. Mỗi thuật toán chạy {REPETITIONS} lần trên cùng tiến trình; thời gian trong bảng là trung vị của trường `processing_time_ms`, do đó giảm ảnh hưởng của dao động hệ điều hành. Chi phí tuyến là tổng chi phí chuẩn hoá theo hàm: khoảng cách 0,30; thời gian cơ sở 0,45; độ trễ do kẹt xe 0,15; rủi ro 0,10.

## Bảng so sánh lý thuyết

Ký hiệu: `V` là số node, `E` là số cạnh, `b` là hệ số phân nhánh và `d` là độ sâu nghiệm. Bộ nhớ trong bảng là bộ nhớ phụ của thuật toán, không tính graph đầu vào.

| Thuật toán | Độ phức tạp thời gian | Bộ nhớ | Tính hoàn chỉnh | Tính tối ưu với chi phí giao thông không âm |
|---|---|---|---|---|
| BFS | O(V + E) | O(V) | Có, trên graph hữu hạn | Không; chỉ tối ưu số chặng khi mọi cạnh có cùng chi phí |
| DFS | O(V + E) | O(V) | Có, trên graph hữu hạn với tập visited | Không |
| UCS | O((V + E) log V) với binary heap | O(V) | Có | Có |
| A* | O((V + E) log V) trong hiện thực graph-search; phụ thuộc chất lượng heuristic | O(V) | Có | Có khi heuristic admissible và consistent |
| GBFS | O(b^d) trong trường hợp xấu nhất | O(b^d) | Có trên graph hữu hạn của chương trình; không bảo đảm trong không gian vô hạn | Không |
| IDA* | O(b^d) trong trường hợp xấu nhất | O(d) theo IDA* chuẩn | Có | Có khi heuristic admissible |

Các độ phức tạp trên mô tả phiên bản lý thuyết, không tính dữ liệu đầu vào và trace phục vụ animation của GUI. Trong mã nguồn này, heuristic A* là Haversine được nhân hệ số lower bound nên admissible/consistent. IDA* tiền xử lý chi phí còn lại trên đồ thị đảo để tạo lower bound chính xác; bước này tốn O((V + E) log V) thời gian và O(V + E) bộ nhớ, vì vậy lợi thế bộ nhớ O(d) của IDA* chuẩn không còn hoàn toàn đúng cho hiện thực này.

## Hiệu suất thực tế

| Thuật toán | Node đã duyệt | Quãng đường (km) | Thời gian đi (phút) | Tổng chi phí | Thời gian xử lý trung vị (ms) |
|---|---:|---:|---:|---:|---:|
{table_rows}

![Biểu đồ cột so sánh chất lượng tuyến, node đã duyệt và thời gian xử lý](algorithm_comparison.svg)

**Bàn luận.** Tuyến có `tổng chi phí` thấp nhất là tuyến phù hợp nhất với profile đã chọn; không nên chỉ nhìn quãng đường vì hàm mục tiêu còn tính thời gian, kẹt xe và rủi ro. UCS, A* và IDA* phải cho cùng chi phí tối ưu trên đồ thị này. GBFS thường duyệt ít node do chỉ bám heuristic khoảng cách, nhưng không bảo đảm tối ưu nên cần đối chiếu tổng chi phí trước khi dùng. BFS tối ưu số chặng, còn DFS phụ thuộc thứ tự cạnh; vì vậy cả hai có thể tạo tuyến có chi phí giao thông cao hơn. Số node đã duyệt phản ánh lượng không gian tìm kiếm: ít node hơn thường nhanh hơn, nhưng không tự nó chứng minh tuyến tốt hơn. Thời gian xử lý ở cỡ mili-giây và phụ thuộc cấu hình máy; so sánh hợp lệ khi chạy cùng máy, cùng graph, cùng profile và cùng số lần lặp như trên. Vì các thuật toán chạy rất nhanh ở đồ thị 30 node, phần chênh lệch mili-giây chủ yếu phản ánh chi phí quản lý hàng đợi ưu tiên và heuristic, không phải thời gian di chuyển ngoài thực tế.

## Tác động của kẹt xe

Để kiểm tra độ nhạy với kẹt xe, giữ nguyên cặp điểm `{start}` -> `{goal}` và profile `balanced`. Kịch bản `rush_hour` cộng một mức congestion cho mọi loại đường (giới hạn mức 5). Bảng dưới dùng UCS; A* và IDA* cũng chọn cùng nghiệm tối ưu do cùng hàm chi phí.

| Trạng thái | Tuyến | Quãng đường (km) | Thời gian đi (phút) | Tổng chi phí |
|---|---|---:|---:|---:|
{traffic_rows}

Khi giờ cao điểm làm tuyến cũ bị phạt congestion, thuật toán tối ưu đánh giá lại tổng chi phí thay vì giữ đường ngắn theo hình học. Nếu tuyến tối ưu mới dài hơn nhưng có tổng chi phí thấp hơn tuyến cũ trong cùng kịch bản giờ cao điểm, kết quả xác nhận hệ thống đã né đoạn kẹt xe đúng theo hàm mục tiêu. A* và IDA* dùng hàm chi phí giống UCS nên phải cho cùng tuyến tối ưu sau khi thay đổi congestion. Không diễn giải đây là “đường ngắn nhất tuyệt đối”; đây là tuyến có chi phí tổng hợp nhỏ nhất theo trọng số đã công bố.
"""


def main() -> None:
    """Sinh toàn bộ tài sản dùng cho báo cáo."""

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    experiment_case = find_congestion_case()
    normal_graph = build_induced_graph(
        load_clean_graph(scenario="normal"),
        experiment_case.node_ids,
    )
    rush_graph = build_induced_graph(
        load_clean_graph(scenario="rush_hour"),
        experiment_case.node_ids,
    )
    performance = measure_algorithms(
        normal_graph,
        experiment_case.start,
        experiment_case.goal,
    )
    traffic = route_summary(
        normal_graph,
        rush_graph,
        experiment_case.start,
        experiment_case.goal,
    )
    write_csv(OUTPUT_DIRECTORY / "algorithm_performance.csv", performance)
    write_csv(OUTPUT_DIRECTORY / "congestion_route_change.csv", traffic)
    create_chart(performance, OUTPUT_DIRECTORY / "algorithm_comparison.svg")
    (OUTPUT_DIRECTORY / "report_comparison_section.md").write_text(
        create_markdown(
            experiment_case,
            len(normal_graph.get_all_edges()),
            performance,
            traffic,
        ),
        encoding="utf-8",
    )
    print(f"Report assets created at {OUTPUT_DIRECTORY.resolve()}")
    print(
        "Test case: "
        f"{experiment_case.start} -> {experiment_case.goal} "
        f"on {len(experiment_case.node_ids)} nodes"
    )


if __name__ == "__main__":
    main()
