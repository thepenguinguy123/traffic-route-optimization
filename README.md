# Traffic Route Optimization

Dự án mô phỏng bài toán tìm đường cho shipper xe máy tại Quận 1, TP.HCM.
Backend hiện có bốn thuật toán `bfs`, `dfs`, `ucs`, `astar` và dùng chung
`TrafficGraph`, cách tính cost, định dạng kết quả và animation trace.

README này dành cho hai nhóm:

1. Thành viên muốn dùng backend đã có để tích hợp Flask, frontend hoặc bài toán
   multi-location.
2. Thành viên muốn viết thêm thuật toán tìm kiếm.

## 1. Cài đặt và chạy test

Clone project lần đầu:

```bash
git clone https://github.com/thepenguinguy123/traffic-route-optimization.git
cd traffic-route-optimization
git switch feature/traffic-graph-core
```

Implementation hiện tại nằm trên branch `feature/traffic-graph-core`, đang track
`origin/feature/traffic-graph-core`. Nếu đã có project, cập nhật đúng branch này:

```bash
git switch feature/traffic-graph-core
git pull --ff-only origin feature/traffic-graph-core
```

Tạo virtual environment, kích hoạt và cài dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Trên Windows, lệnh kích hoạt là:

```powershell
.venv\Scripts\activate
```

Chạy test:

```bash
python -m pytest backend/tests/test_search.py -q
python -m pytest backend/tests -q
```

Bộ test tối giản có đúng bảy behavior tests: hai graph tests, hai cost tests và
ba search tests.

## 2. Các file và thư mục chính

```text
backend/
├── app/
│   ├── algorithms/    # BFS, DFS, UCS, A*, common helpers và registry
│   ├── core/          # Models, TrafficGraph, cost, profiles, result và errors
│   ├── repositories/  # Đọc JSON và materialize traffic profile
│   └── services/      # RouteSearchService
├── data/prototype/    # Dataset nhỏ dùng chung để phát triển và debug
└── tests/             # Bảy behavior tests dùng chung
```

Prototype gồm ba file dùng cùng schema với dataset cuối:

```text
backend/data/prototype/nodes.json
backend/data/prototype/edges.json
backend/data/prototype/traffic_profiles.json
```

## 3. Nhóm tích hợp backend vào Flask, frontend, multi-location

### 3.1. Load graph, áp dụng traffic profile và tìm route

Chạy snippet này từ thư mục gốc của project:

```python
from pathlib import Path

from backend.app.core.cost import CostCalculator
from backend.app.repositories.json_graph_repository import (
    load_graph,
    load_traffic_profiles,
    materialize_traffic_profile,
)
from backend.app.services.route_search_service import RouteSearchService


data_dir = Path("backend/data/prototype")
cost_calculator = CostCalculator()

base_graph = load_graph(
    str(data_dir / "nodes.json"),
    str(data_dir / "edges.json"),
    cost_calculator,
)
profiles = load_traffic_profiles(str(data_dir / "traffic_profiles.json"))
graph = materialize_traffic_profile(
    base_graph,
    profiles,
    "rush_hour",
    cost_calculator,
)

service = RouteSearchService(graph)
result = service.search(
    start="N01",
    goal="N07",
    algorithm="astar",
    optimization_profile="balanced",
)

print(result.found)
print(result.path)
print(result.total_cost)
```

`load_traffic_profiles()` đọc JSON một lần. `materialize_traffic_profile()` nhận
dữ liệu đã load và tạo `TrafficGraph` mới; `base_graph` không bị sửa.

Các giá trị hiện có:

- Algorithms: `bfs`, `dfs`, `ucs`, `astar`.
- Optimization profiles: `balanced`, `shortest_distance`, `fastest_route`,
  `avoid_congestion`.
- Traffic profiles: `normal`, `rush_hour`, `incident`.

### 3.2. Đọc `SearchResult`

Mọi thuật toán trả cùng một `SearchResult` với các field:

- `algorithm`: tên thuật toán đã chạy.
- `found`: có tìm thấy route hay không.
- `path`: danh sách node ID của route; rỗng nếu không tìm thấy.
- `visited_order`: thứ tự các node thực sự được expand.
- `frontier_steps`: các snapshot dùng cho animation.
- `total_distance`: tổng khoảng cách theo kilomet.
- `total_time`: tổng thời gian ước tính đã điều chỉnh congestion.
- `total_cost`: tổng traffic-aware cost.
- `explored_nodes`: số lần expansion.
- `processing_time_ms`: thời gian xử lý của thuật toán.
- `message`: thông báo kết quả.

Trong Python, service hoặc lớp tích hợp đọc `result.path` trước khi serialize:

```python
if result.found:
    route_node_ids = result.path
else:
    route_node_ids = []
```

### 3.3. Dùng trace cho animation

Mỗi phần tử trong `result.frontier_steps` là một `SearchTraceStep` chứa
`current`, `visited`, `frontier` và `path_so_far`:

```python
for step in result.frontier_steps:
    current_node_id = step.current.node_id
    frontier_node_ids = [item.node_id for item in step.frontier]

    print(step.step, current_node_id)
    print(step.visited)
    print(frontier_node_ids)
    print(step.path_so_far)
```

`FrontierItem` có `node_id`, `parent_id`, `depth`, `g_cost`, `h_cost` và
`f_cost`. Field không áp dụng cho thuật toán có giá trị `None`.

`RouteSearchService` trả Python object `SearchResult`. Flask hoặc lớp tích hợp có
trách nhiệm serialize object này thành JSON; project hiện chưa cung cấp serializer
hoặc Flask route. Frontend đọc `path` và `frontier_steps` từ JSON response rồi chỉ
phát lại các snapshot theo thứ tự. Frontend không truy cập trực tiếp Python
`result`, không tự tìm đường, không dựng lại frontier và không chạy lại thuật toán.

### 3.4. Ranh giới tích hợp

Flask, frontend và multi-location phải gọi `RouteSearchService`, sau đó đọc
`SearchResult`. Các lớp tích hợp không import riêng `bfs`, `dfs`, `ucs` hoặc
`astar`.

Hiện project chưa cung cấp Flask routes, frontend hoặc multi-location
implementation. Khi các phần đó được thêm:

- Flask chỉ validate request, chọn graph đã materialize, gọi service và serialize
  kết quả.
- Frontend chỉ hiển thị graph cùng `path`, metrics và `frontier_steps` nhận từ JSON
  response.
- Multi-location gọi service cho từng route leg và dùng cost đã có trong result.

## 4. Nhóm viết thêm thuật toán

### 4.1. Tạo module và giữ common signature

Tạo một file mới trong `backend/app/algorithms/`. Ví dụ tên minh họa:
`new_algorithm.py`.

Các import và signature nền tảng:

```python
from backend.app.algorithms.common import build_search_result, reconstruct_path
from backend.app.core.graph import TrafficGraph
from backend.app.core.models import CostProfile
from backend.app.core.search_models import (
    FrontierItem,
    SearchResult,
    SearchTraceStep,
)


def search(
    graph: TrafficGraph,
    start: str,
    goal: str,
    profile: CostProfile,
) -> SearchResult:
    ...
```

Trong implementation:

- Dùng `graph.get_traversable_neighbors(node_id)` để lấy đường đi được.
- Thuật toán weighted dùng `graph.get_edge_cost(source, target, profile)`.
- Có thể dùng `reconstruct_path()` để dựng parent chain.
- Có thể dùng `build_search_result()` để tính final metrics và tạo result chung.
- Tạo trace bằng `SearchTraceStep` và `FrontierItem`.
- Mỗi trace step phải dùng các list snapshot riêng, không tái sử dụng list đang
  tiếp tục bị mutate.
- Luôn trả `SearchResult`, kể cả no-route.

Không cần tạo abstract base class. Giữ implementation cụ thể và đơn giản.

### 4.2. Đăng ký thuật toán

Registry hiện tại có dạng:

```python
from backend.app.algorithms.astar import search as astar_search
from backend.app.algorithms.bfs import search as bfs_search
from backend.app.algorithms.dfs import search as dfs_search
from backend.app.algorithms.ucs import search as ucs_search


ALGORITHM_REGISTRY = {
    "bfs": bfs_search,
    "dfs": dfs_search,
    "ucs": ucs_search,
    "astar": astar_search,
}
```

Sau khi module mới tồn tại, thêm một import alias và một key theo đúng mẫu trên.
Không dùng reflection hoặc dynamic plugin registration.

### 4.3. Dữ liệu và test dùng chung

Dùng `backend/data/prototype/` để chạy thử và so sánh với các thuật toán đã có.
Có thể tạo graph nhỏ riêng trong lúc debug, nhưng graph đó không thay thế
prototype và không được tạo một dataset format mới.

`backend/tests/test_search.py` có ba behavior tests chung:

- Tìm thấy một unique route.
- Trả no-route đúng cách.
- Kết thúc đúng khi graph có cycle.

Đưa function mới vào `SEARCH_FUNCTIONS` của ba test hiện có. Không thêm test
function mới nếu implementation plan vẫn giới hạn suite ở đúng bảy behavior
tests. Trước khi bàn giao, chạy:

```bash
python -m pytest backend/tests/test_search.py -q
python -m pytest backend/tests -q
```

Kiểm tra thuật toán tìm được route, xử lý no-route và cycle, đồng thời trả đủ
`SearchResult`.

## 5. Quy tắc bắt buộc

- Không truy cập `graph._graph`; chỉ dùng public API của `TrafficGraph`.
- Không import NetworkX trong algorithms hoặc services.
- Không tự viết lại công thức cost; dùng `get_edge_cost()` và graph path metrics.
- Không đọc JSON trong thuật toán; file I/O thuộc repository.
- Không để GUI hoặc Flask tự chạy lại search logic.
- Mọi thuật toán phải trả `SearchResult`.
- Không sửa trực tiếp base graph khi áp dụng traffic profile.
- Không tự tạo dataset schema hoặc result format riêng.
