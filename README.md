# Traffic Route Optimization

## 1. Giới thiệu

Dự án mô phỏng bài toán tìm đường cho shipper xe máy tại Quận 1, TP.HCM.
Backend dùng một graph chung, một cách tính traffic cost chung và một định dạng
kết quả chung cho bốn thuật toán hiện có:

```text
bfs
dfs
ucs
astar
```

README này dành cho hai nhóm thành viên:

1. Người muốn dùng backend đã có để tích hợp với Flask, frontend hoặc
   multi-location.
2. Người muốn viết thêm thuật toán tìm kiếm mà vẫn tuân theo contract chung.

Nếu bạn mới làm quen với Python project, hãy đọc từ trên xuống. Nếu đã quen với
project, có thể chuyển thẳng đến [Public API reference](#8-public-api-reference).

## 2. Cài đặt project

### 2.1. Clone project lần đầu

Mở terminal tại thư mục bạn muốn chứa project, sau đó chạy:

```bash
git clone https://github.com/thepenguinguy123/traffic-route-optimization.git
cd traffic-route-optimization
git switch feature/traffic-graph-core
```

Implementation được mô tả trong README này nằm trên branch
`feature/traffic-graph-core`, đang track `origin/feature/traffic-graph-core`.

Nếu đã clone project trước đó, cập nhật đúng branch bằng:

```bash
git switch feature/traffic-graph-core
git pull --ff-only origin feature/traffic-graph-core
```

### 2.2. Tạo virtual environment

Chạy các lệnh sau từ thư mục gốc, tức thư mục có `README.md` và
`requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Trên Windows, dùng lệnh kích hoạt:

```powershell
.venv\Scripts\activate
```

Sau khi kích hoạt thành công, terminal thường hiển thị `(.venv)` ở đầu dòng.

## 3. Chạy test

### 3.1. Chạy search tests

Từ thư mục gốc của project, chạy:

```bash
python -m pytest backend/tests/test_search.py -q
```

Kết quả đúng hiện tại:

```text
3 passed
```

Ba behavior tests kiểm tra:

- Tìm thấy một unique route.
- Trả no-route đúng cách.
- Kết thúc khi graph có cycle.

Mỗi test chạy lần lượt các function trong `SEARCH_FUNCTIONS`, hiện gồm `bfs`,
`dfs`, `ucs` và `astar`.

### 3.2. Chạy toàn bộ test suite

```bash
python -m pytest backend/tests -q
```

Kết quả đúng hiện tại:

```text
7 passed
```

Bộ test tối giản có hai graph tests, hai cost tests và ba search tests. Không tự
thêm test function mới nếu implementation plan vẫn giới hạn đúng bảy behavior
tests.

## 4. Quick start từng bước

Mục này giúp kiểm tra toàn bộ luồng backend trước khi viết phần tích hợp khác:

```text
Load dataset
    ↓
Tạo base graph
    ↓
Áp dụng traffic profile
    ↓
Tạo RouteSearchService
    ↓
Chạy thuật toán
    ↓
Đọc SearchResult
```

### Bước 1 — Tạo file chạy thử

Đứng tại thư mục gốc của project và tạo file `integration_check.py` ngay cạnh
`README.md`:

```bash
touch integration_check.py
```

Có thể tạo file bằng VS Code thay cho lệnh `touch`. Cấu trúc cần có dạng:

```text
traffic-route-optimization/
├── backend/
├── README.md
├── requirements.txt
└── integration_check.py
```

Đây chỉ là file kiểm tra cục bộ. Không cần commit file này.

### Bước 2 — Dán code vào `integration_check.py`

```python
from pathlib import Path

from backend.app.core.cost import CostCalculator
from backend.app.core.search_models import SearchResult
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
base_graph_before = base_graph.to_dict()

profiles = load_traffic_profiles(
    str(data_dir / "traffic_profiles.json")
)
graph = materialize_traffic_profile(
    base_graph,
    profiles,
    "rush_hour",
    cost_calculator,
)

base_graph_unchanged = base_graph.to_dict() == base_graph_before
assert base_graph_unchanged

service = RouteSearchService(graph)
result = service.search(
    start="N01",
    goal="N07",
    algorithm="astar",
    optimization_profile="balanced",
)
assert isinstance(result, SearchResult)

print("Base graph unchanged:", base_graph_unchanged)
print("Result type:", type(result).__name__)
print("Found:", result.found)
print("Path:", result.path)
print("Distance:", round(result.total_distance, 3))
print("Time:", round(result.total_time, 3))
print("Cost:", round(result.total_cost, 3))
print("Explored:", result.explored_nodes)
print("Trace steps:", len(result.frontier_steps))
```

### Bước 3 — Chạy file

Đảm bảo virtual environment đã được kích hoạt, sau đó chạy:

```bash
python integration_check.py
```

Phải chạy từ thư mục gốc. Không chuyển vào `backend/`, vì các import bắt đầu bằng
`backend.app...`.

### Bước 4 — Kiểm tra output

Với prototype hiện tại, output phải có dạng:

```text
Base graph unchanged: True
Result type: SearchResult
Found: True
Path: ['N01', 'N03', 'N04', 'N05', 'N06', 'N07']
Distance: 2.8
Time: 8.9
Cost: 0.547
Explored: 6
Trace steps: 6
```

Kết quả trên xác nhận:

- Ba file prototype được load thành công.
- `rush_hour` tạo một graph mới và không sửa `base_graph`.
- `RouteSearchService` gọi được A*.
- Service trả đúng Python object `SearchResult`.

Khi kiểm tra xong, có thể xóa `integration_check.py`. Không đưa file tạm này vào
commit trừ khi nhóm chủ động muốn giữ lại.

## 5. Hiểu luồng tích hợp

### 5.1. `CostCalculator`

```python
cost_calculator = CostCalculator()
```

Object này chứa logic tính congestion-adjusted time và traffic-aware cost. Phần
tích hợp không tự viết lại công thức hoặc tự cộng các trọng số.

### 5.2. `load_graph()`

```python
base_graph = load_graph(
    str(data_dir / "nodes.json"),
    str(data_dir / "edges.json"),
    cost_calculator,
)
```

Hàm module-level này đọc node/edge JSON và trả một `TrafficGraph`. Phần tích hợp
không cần tự đọc JSON, tạo NetworkX graph hoặc thêm từng node/edge.

### 5.3. `load_traffic_profiles()`

```python
profiles = load_traffic_profiles(
    str(data_dir / "traffic_profiles.json")
)
```

Hàm này đọc traffic-profile JSON đúng một lần và trả dữ liệu profiles đã
validate. Prototype hiện có `normal`, `rush_hour` và `incident`.

### 5.4. `materialize_traffic_profile()`

```python
graph = materialize_traffic_profile(
    base_graph,
    profiles,
    "rush_hour",
    cost_calculator,
)
```

Hàm này nhận dữ liệu profiles đã load và tạo một `TrafficGraph` mới gồm các trạng thái giao thông:

```text
base_graph
├── normal graph
├── rush_hour graph
└── incident graph
```

`base_graph` không bị mutate. Không truyền đường dẫn file vào
`materialize_traffic_profile()`.

### 5.5. `RouteSearchService`

```python
service = RouteSearchService(graph)
```

Đây là interface chính dành cho lớp tích hợp. Service resolve algorithm và
optimization profile từ registry, gọi common search function rồi trả
`SearchResult`.

Flask, frontend integration và multi-location không import riêng từng thuật toán.

### 5.6. `service.search()`

```python
result = service.search(
    start="N01",
    goal="N07",
    algorithm="astar",
    optimization_profile="balanced",
)
```

Đầu vào gồm start node ID, goal node ID, algorithm key và optimization-profile
key. Traffic profile đã được áp dụng trước đó khi tạo `graph`.

Hàm này trả về một Python object thuộc class `SearchResult`. Object đó cho biết
có tìm thấy route hay không, route gồm những node nào, các metrics của route và
trace từng bước của thuật toán:

```python
result = service.search(...)

print(result.found)
print(result.path)
print(result.total_cost)
print(result.frontier_steps)
```

Danh sách đầy đủ các field và cách đọc `SearchResult` được giải thích tại
[phần 7 — `SearchResult` và animation trace](#7-searchresult-và-animation-trace).

### 5.7. Chạy thử cả bốn thuật toán

Trong `integration_check.py`, có thể thay lần gọi search bằng:

```python
for algorithm in ("bfs", "dfs", "ucs", "astar"):
    result = service.search(
        start="N01",
        goal="N07",
        algorithm=algorithm,
        optimization_profile="balanced",
    )

    print()
    print("Algorithm:", result.algorithm)
    print("Found:", result.found)
    print("Path:", result.path)
    print("Cost:", result.total_cost)
```

Chạy lại:

```bash
python integration_check.py
```

Mục đích là xác nhận bốn thuật toán dùng cùng một service interface và cùng trả
`SearchResult`.

## 6. Hướng dẫn theo vai trò

### 6.1. Người làm Flask

Project hiện chưa có Flask route hoặc serializer. Khi phần Flask được triển khai,
nó chỉ nên đảm nhận:

```text
Validate request
Chọn materialized graph
Gọi RouteSearchService
Serialize SearchResult và nested trace objects
Map errors
Trả JSON response
```

Flask không chứa search algorithm, không tự tính cost và không dựng lại path hoặc
frontier.

### 6.2. Người làm frontend

`RouteSearchService` trả Python `SearchResult`; JavaScript không đọc trực tiếp
object này. Luồng đúng là:

```text
RouteSearchService
        ↓
Python SearchResult
        ↓
Serializer của lớp tích hợp/Flask
        ↓
JSON response
        ↓
Frontend JavaScript
```

Project hiện chưa có JSON serializer hoặc frontend implementation. Sau này,
frontend chỉ đọc `path`, metrics và `frontier_steps` từ JSON response để hiển thị.
Frontend không tự chạy thuật toán hoặc dựng lại frontier.

### 6.3. Người làm multi-location

Project hiện chưa có multi-location implementation. Khi được triển khai, phần này
phải:

- Chọn visiting order.
- Gọi `RouteSearchService` cho từng route leg.
- Xử lý leg không tìm thấy đường.
- Ghép các path và tổng hợp metrics đã có.

Multi-location không tự viết lại point-to-point search hoặc công thức cost.

### 6.4. Người viết thêm thuật toán

#### Bước 1 — Tạo module

Tạo một file mới trong `backend/app/algorithms/`. Ví dụ, nếu thuật toán của bạn có
tên `my_search`, tạo:

```text
backend/app/algorithms/my_search.py
```

#### Bước 2 — Giữ common signature

Trong file vừa tạo (`backend/app/algorithms/my_search.py`), import các contract
dùng chung và khai báo function `search()` như sau:

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

Các import và object trong đoạn trên đến từ những file sau:

- `TrafficGraph` được định nghĩa trong `backend/app/core/graph.py`. Tham số
  `graph` là object graph mà `RouteSearchService` truyền cho thuật toán.
- `CostProfile` được định nghĩa trong `backend/app/core/models.py`. Tham số
  `profile` chứa các trọng số mà weighted algorithm dùng để tính cost.
- `FrontierItem`, `SearchTraceStep` và `SearchResult` được định nghĩa trong
  `backend/app/core/search_models.py`.
- `reconstruct_path()` và `build_search_result()` được định nghĩa trong
  `backend/app/algorithms/common.py`.

Trong phần thân của `search()`, dùng các API chung như sau:

- `graph.get_traversable_neighbors(node_id)` lấy danh sách ID của các node có
  outgoing edge đang đi được từ `node_id`. Method này loại đường đóng và đường
  không dành cho motorbike; danh sách được sắp theo node ID tăng dần.
- Với weighted algorithm, `graph.get_edge_cost(source, target, profile)` lấy
  traffic cost của directed edge `source -> target` theo `profile`. Không tự
  chép lại công thức cost trong thuật toán.
- `reconstruct_path(parents, node_id)` lần theo dictionary `parents` rồi dựng
  path từ start đến `node_id`.
- `build_search_result(...)` tạo `SearchResult`, tính final path metrics qua
  public API của graph và hoàn thành thời gian xử lý.
- `FrontierItem` biểu diễn một node trong frontier. `SearchTraceStep` lưu một
  snapshot sau mỗi lần expand; `visited`, `frontier` và `path_so_far` phải là
  các list snapshot độc lập.

`search()` phải trả một `SearchResult` trong cả trường hợp tìm thấy route và
không tìm thấy route. Dấu `...` trong ví dụ chỉ là vị trí bạn viết logic của
thuật toán, không phải implementation hoàn chỉnh.

Không tạo abstract base class hoặc tự truy cập NetworkX.

#### Bước 3 — Đăng ký vào registry

Mở `backend/app/algorithms/registry.py`. Ở phần import, thêm function mới bằng
alias để tên không bị trùng với các function `search` khác:

```python
from backend.app.algorithms.my_search import search as my_search
```

Sau đó thêm key dùng để gọi thuật toán vào `ALGORITHM_REGISTRY`:

```python
ALGORITHM_REGISTRY: dict[str, SearchFunction] = {
    "bfs": bfs_search,
    "dfs": dfs_search,
    "ucs": ucs_search,
    "astar": astar_search,
    "my_search": my_search,
}
```

Sau thay đổi này, lớp tích hợp có thể gọi thuật toán bằng
`algorithm="my_search"`. Tên key phải là duy nhất và phải trỏ đến function có
đúng common signature. Không tạo registry mới, không dùng reflection hoặc
dynamic plugin registration.

#### Bước 4 — Dùng test chung

Mở `backend/tests/test_search.py`. Thêm import alias:

```python
from backend.app.algorithms.my_search import search as my_search
```

Sau đó thêm alias đó vào tuple hiện có:

```python
SEARCH_FUNCTIONS = (
    bfs_search,
    dfs_search,
    ucs_search,
    astar_search,
    my_search,
)
```

Ba test hiện có sẽ tự chạy cùng các tình huống successful route, no-route và
cycle cho function mới. Không tạo bản sao của ba behavior tests và không tạo
test function riêng cho thuật toán.

Dùng `backend/data/prototype/` để chạy thử và so sánh. Có thể dùng graph nhỏ để
debug, nhưng không thay prototype hoặc tạo dataset format mới.

Trước khi bàn giao, chạy:

```bash
python -m pytest backend/tests/test_search.py -q
python -m pytest backend/tests -q
```

## 7. `SearchResult` và animation trace

Mỗi lần gọi `service.search()`, backend trả về một Python object `SearchResult`.
Trong object này, `frontier_steps` chứa nhiều `SearchTraceStep`; mỗi step lại sử
dụng các `FrontierItem` để mô tả node hiện tại và các node đang chờ xử lý:

```text
SearchResult
└── frontier_steps: list[SearchTraceStep]
    ├── current: FrontierItem
    └── frontier: list[FrontierItem]
```

Ba model được định nghĩa trong `backend/app/core/search_models.py`. Flask hoặc
lớp tích hợp sẽ serialize chúng thành JSON trước khi frontend sử dụng.

### 7.1. Các field của `SearchResult`

Mọi thuật toán trả cùng một Python dataclass với các field sau:

| Field | Ý nghĩa | Mục đích sử dụng |
| --- | --- | --- |
| `algorithm` | Key của thuật toán vừa chạy, ví dụ `bfs`, `dfs`, `ucs` hoặc `astar`. | Cho lớp tích hợp và giao diện biết kết quả thuộc thuật toán nào. |
| `found` | `True` nếu tìm được route từ start đến goal; ngược lại là `False`. | Kiểm tra thành công trước khi đọc hoặc hiển thị `path`. |
| `path` | Danh sách node ID của route theo thứ tự từ start đến goal. Nếu không có route, danh sách này rỗng. | Vẽ route trên bản đồ hoặc chuyển route cho bước tích hợp tiếp theo. |
| `visited_order` | Thứ tự tất cả các lần node thực sự được expand. Nếu weighted algorithm reopen và expand lại một node, ID đó có thể xuất hiện nhiều lần. | Hiển thị thứ tự tìm kiếm cuối cùng và giải thích thuật toán đã khảo sát những node nào. |
| `frontier_steps` | Danh sách các snapshot `SearchTraceStep`, mỗi snapshot tương ứng với một lần expansion. | Phát animation từng bước; chi tiết xem phần 7.2. |
| `total_distance` | Tổng `distance_km` của các directed edges trên final path, đơn vị kilomet. | Thông báo tổng độ dài route. |
| `total_time` | Tổng thời gian ước tính thực tế của final path, đơn vị phút; mỗi edge đã được điều chỉnh bằng congestion multiplier. | Thông báo thời gian giao hàng ước tính trong traffic profile đang dùng. |
| `total_cost` | Tổng traffic-aware cost của final path theo `CostProfile` đã chọn. Đây là normalized weighted cost, không phải kilomet hoặc phút. | So sánh và xếp hạng các route chạy trên cùng graph và cùng optimization profile. |
| `explored_nodes` | Tổng số lần expansion, luôn bằng `len(visited_order)`. | Hiển thị lượng công việc tìm kiếm của thuật toán. |
| `processing_time_ms` | Thời gian chạy thuật toán tính bằng millisecond, gồm search, dựng path, trace và final metrics; không gồm load dataset, Flask serialization hoặc frontend. | Báo cáo và so sánh thời gian xử lý backend. |
| `message` | Thông báo ngắn: `"Route found."` hoặc `"No route found."`. | Hiển thị trạng thái dễ đọc hoặc hỗ trợ lớp tích hợp xử lý kết quả. |

Kiểm tra route:

```python
if result.found:
    print(result.path)
else:
    print(result.message)
```

No-route contract:

```text
found = False
path = []
message = "No route found."
```

Khi không tìm thấy route, `total_distance`, `total_time` và `total_cost` bằng
`0.0`; `visited_order` và `frontier_steps` vẫn có thể chứa quá trình thuật toán
đã tìm kiếm. Không tự đo lại metrics trong Flask, frontend hoặc module tích hợp
khác.

### 7.2. Các field của `SearchTraceStep`

Một `SearchTraceStep` là snapshot được tạo **sau khi** `current` đã được expand
và các successors của nó đã được xử lý. Các field có ý nghĩa như sau:

| Field | Ý nghĩa | Mục đích sử dụng |
| --- | --- | --- |
| `step` | Số thứ tự snapshot, bắt đầu từ `1` và tăng sau mỗi lần expansion. | Sắp xếp và hiển thị số bước animation. |
| `current` | `FrontierItem` của node vừa được lấy khỏi frontier và expand ở bước này. | Highlight node đang được thuật toán xử lý và hiển thị các giá trị `depth`, `g`, `h`, `f` phù hợp. |
| `visited` | Snapshot tích lũy của expansion order tính đến bước hiện tại, bao gồm `current`. | Đánh dấu các node đã được expand tại chính frame animation đó. |
| `frontier` | Snapshot logical frontier sau khi successors của `current` đã được xử lý, theo thứ tự node sẽ được lấy ra tiếp theo. Weighted algorithms loại stale/duplicate heap entries khỏi snapshot này. | Hiển thị queue, stack hoặc priority frontier còn chờ xử lý. |
| `path_so_far` | Parent chain từ start đến `current` tại thời điểm snapshot. Đây là đường dẫn tạm thời, không nhất thiết là final path. | Highlight quá trình thuật toán đi tới node hiện tại. |

`visited`, `frontier` và `path_so_far` là các list snapshot độc lập. Khi thuật
toán thay đổi internal queue/stack/heap ở bước sau, nội dung của step cũ không
bị thay đổi.

Đọc trace trong Python:

```python
for step in result.frontier_steps:
    current_node_id = step.current.node_id
    frontier_node_ids = [
        item.node_id
        for item in step.frontier
    ]

    print("Step:", step.step)
    print("Current:", current_node_id)
    print("Visited:", step.visited)
    print("Frontier:", frontier_node_ids)
    print("Path so far:", step.path_so_far)
```

### 7.3. Các field của `FrontierItem`

`FrontierItem` là frozen dataclass: sau khi được tạo, các field của item không bị
thay đổi. Điều này giúp mỗi trace snapshot giữ nguyên trạng thái tại thời điểm
được ghi.

| Field | Ý nghĩa | Mục đích sử dụng |
| --- | --- | --- |
| `node_id` | ID của node mà item đại diện. | Xác định node cần highlight trên graph. |
| `parent_id` | ID của parent đang được ghi nhận cho node tại thời điểm snapshot; với UCS/A* đây là parent của route có `g_cost` tốt nhất hiện biết. Start node có giá trị `None`. | Vẽ quan hệ parent hoặc giải thích cách `path_so_far` được hình thành. |
| `depth` | Số directed edges từ start đến node theo parent chain; start có depth `0`. | Hiển thị mức/hop của BFS, DFS hoặc các thuật toán khác; đây không phải route cost. |
| `g_cost` | Cumulative traffic cost từ start đến node. UCS và A* cung cấp giá trị này; BFS và DFS dùng `None`. | Hiển thị chi phí đã đi và priority của UCS. |
| `h_cost` | Heuristic cost ước lượng từ node đến goal, cùng scale với `g_cost`. A* cung cấp giá trị này; BFS, DFS và UCS dùng `None`. | Giải thích phần ước lượng còn lại mà A* dùng để ưu tiên frontier. |
| `f_cost` | Tổng `g_cost + h_cost`. Chỉ A* cung cấp; BFS, DFS và UCS dùng `None`. | Hiển thị priority cuối cùng mà A* dùng để chọn node tiếp theo. |

Tóm tắt các cost field theo thuật toán hiện có:

| Thuật toán | `g_cost` | `h_cost` | `f_cost` |
| --- | --- | --- | --- |
| BFS | `None` | `None` | `None` |
| DFS | `None` | `None` | `None` |
| UCS | Cumulative cost | `None` | `None` |
| A* | Cumulative cost | Heuristic cost | `g_cost + h_cost` |

## 8. Public API reference

### 8.1. Dataset paths

```text
backend/data/prototype/nodes.json
backend/data/prototype/edges.json
backend/data/prototype/traffic_profiles.json
```

Prototype chứa node `N01`, `N07` dùng trong quick start.

### 8.2. Repository API

Các function dưới đây nằm trong
`backend/app/repositories/json_graph_repository.py`. Repository dùng
module-level functions, không dùng repository class:

```python
load_graph(
    nodes_path: str,
    edges_path: str,
    cost_calculator: CostCalculator,
) -> TrafficGraph

load_traffic_profiles(
    file_path: str,
) -> dict[str, dict]

materialize_traffic_profile(
    base_graph: TrafficGraph,
    profiles: dict[str, dict],
    profile_name: str,
    cost_calculator: CostCalculator,
) -> TrafficGraph
```

- `load_graph()` đọc `nodes.json` và `edges.json`, tạo các domain objects rồi
  thêm chúng vào một `TrafficGraph` mới. Truyền đường dẫn vào function; không
  hard-code prototype hoặc final dataset trong repository.
- `load_traffic_profiles()` đọc `traffic_profiles.json` một lần và lấy mapping
  các traffic profile đã được khai báo. Dữ liệu trả về được truyền tiếp cho
  `materialize_traffic_profile()`.
- `materialize_traffic_profile()` tạo một `TrafficGraph` độc lập từ
  `base_graph`, sau đó áp dụng các edge overrides của `profile_name`. Function
  không đọc JSON và không mutate `base_graph`.

### 8.3. Service API

`RouteSearchService` nằm trong
`backend/app/services/route_search_service.py`:

```python
RouteSearchService(graph: TrafficGraph)

service.search(
    start: str,
    goal: str,
    algorithm: str,
    optimization_profile: str = "balanced",
) -> SearchResult
```

- `RouteSearchService(graph)` giữ materialized graph sẽ được dùng cho các lần
  tìm đường. Traffic profile phải được materialize trước khi khởi tạo service.
- `service.search()` nhận start, goal, algorithm key và optimization-profile
  key; resolve function/profile trong registry, chạy thuật toán rồi trả một
  `SearchResult`. Chi tiết object kết quả nằm ở phần 7.
- Algorithm/profile key không tồn tại hiện raise `KeyError` từ registry.

### 8.4. Registry values

- **Algorithm registry:** `ALGORITHM_REGISTRY` trong
  `backend/app/algorithms/registry.py` ánh xạ algorithm key sang search function
  tương ứng. Các key hiện có là `bfs`, `dfs`, `ucs` và `astar`.
- **Optimization-profile registry:** `COST_PROFILES` trong
  `backend/app/core/cost_profiles.py` ánh xạ optimization-profile key sang bộ
  trọng số dùng để tính route cost. Các key hiện có là `balanced`,
  `shortest_distance`, `fastest_route` và `avoid_congestion`.
- **Traffic profiles:** `normal`, `rush_hour` và `incident` nằm trong
  `backend/data/prototype/traffic_profiles.json`. Chúng mô tả trạng thái giao
  thông được áp dụng khi materialize graph; đây không phải cost profiles.
- **Shared search-test list:** `SEARCH_FUNCTIONS` trong
  `backend/tests/test_search.py` tập hợp bốn search functions để cả bốn cùng
  chạy qua ba behavior tests hiện có. Đây là test helper, không phải registry mà
  `RouteSearchService` sử dụng.

### 8.5. Public `TrafficGraph` methods thường dùng

Class `TrafficGraph` nằm trong `backend/app/core/graph.py`. Repository dùng các
method thêm dữ liệu; algorithms và services chỉ làm việc qua các public methods
của object này.

Các method quản lý và tra cứu node:

- `add_node(node)` thêm một `TrafficNode`; duplicate node ID bị từ chối.
- `has_node(node_id)` kiểm tra node ID có tồn tại hay không.
- `get_node(node_id)` lấy `TrafficNode` tương ứng với một ID.
- `get_all_nodes()` lấy toàn bộ `TrafficNode` đang được lưu trong graph.

Các method quản lý và tra cứu directed edge:

- `add_edge(edge)` thêm một `RoadEdge` có hướng giữa hai node đã tồn tại.
- `has_edge(source, target)` kiểm tra directed edge `source -> target`.
- `get_edge(source, target)` lấy `RoadEdge` theo source và target.
- `get_all_edges()` lấy toàn bộ directed edges đang được lưu.

Các method dùng khi duyệt graph:

- `get_neighbors(node_id)` lấy tất cả outgoing neighbor IDs theo thứ tự tăng
  dần, kể cả neighbor nối qua edge hiện không đi được.
- `get_traversable_neighbors(node_id)` lấy outgoing neighbor IDs mà motorbike
  được phép đi qua, đồng thời loại closed/restricted edges.
- `get_predecessors(node_id)` lấy các node IDs có directed edge đi vào
  `node_id`.

Các method dùng để tính cost và metrics:

- `get_edge_cost(source, target, profile)` tính traffic cost của một directed
  edge qua `CostCalculator` dùng chung.
- `calculate_path_distance(path)` cộng tổng `distance_km` trên path.
- `calculate_path_time(path)` cộng thời gian thực tế đã điều chỉnh congestion.
- `calculate_path_cost(path, profile)` cộng traffic cost của toàn bộ path theo
  optimization profile.
- `estimate_straight_line_distance(source, target)` tính khoảng cách Haversine
  giữa tọa độ hai node; A* dùng method này trong heuristic.
- `to_dict()` chuyển graph thành dữ liệu nodes/edges tương thích JSON và có thứ
  tự deterministic để lớp tích hợp có thể serialize sau này.

Không gọi các private helpers và không truy cập `graph._graph` từ algorithm hoặc
service.

## 9. Quy tắc bắt buộc và troubleshooting

### 9.1. Quy tắc bắt buộc

- Không truy cập `graph._graph`; chỉ dùng public API của `TrafficGraph`.
- Không import NetworkX trong algorithms hoặc services.
- Không tự viết lại cost; dùng `get_edge_cost()` và graph path metrics.
- Không đọc JSON trong thuật toán; file I/O thuộc repository.
- Không để GUI hoặc Flask tự chạy lại search logic.
- Mọi thuật toán phải trả `SearchResult`.
- Không mutate `base_graph` khi materialize traffic profile.
- Không tự tạo dataset schema hoặc result format riêng.

### 9.2. Lỗi `ModuleNotFoundError: No module named 'backend'`

Nguyên nhân thường gặp là chạy script từ sai thư mục. Chuyển về thư mục có
`README.md`, sau đó chạy:

```bash
python integration_check.py
```

### 9.3. Lỗi thiếu dependency

Kích hoạt virtual environment và cài lại:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 9.4. Lỗi không tìm thấy dataset

Kiểm tra đang đứng tại project root và ba file sau tồn tại:

```bash
ls backend/data/prototype
```

Kết quả phải có `nodes.json`, `edges.json`, `traffic_profiles.json`.

### 9.5. Lỗi `KeyError` khi gọi service

Kiểm tra `algorithm` và `optimization_profile` có nằm trong danh sách ở mục
[Registry values](#84-registry-values). Không tự thêm key chỉ để bỏ qua lỗi.

### 9.6. Không tìm thấy route

No-route không phải lỗi Python. Kiểm tra:

```python
if not result.found:
    print(result.message)
```

Kết quả hợp lệ là `path=[]` và `message="No route found."`.
