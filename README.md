# Traffic Route Optimization

Ứng dụng mô phỏng tối ưu tuyến giao thông trên bản đồ Goong, kết hợp đồ thị
đường đi, hoạt ảnh tìm kiếm và dữ liệu địa điểm ăn uống trong một vùng giới hạn.

## Thành phần chính

- Backend Flask cung cấp graph core, tìm đường BFS/DFS/UCS/A*/Greedy, multi-location/TSP và danh sách địa điểm.
- Frontend HTML/CSS/JavaScript dùng Goong GL JS.
- Bộ thu thập dữ liệu Goong Places API hỗ trợ 8 chunk, giới hạn số địa điểm,
  retry khi bị giới hạn tốc độ và ghi checkpoint sau từng chunk.
- API dùng `TrafficGraph` làm nguồn graph duy nhất cho BFS/DFS/UCS/A*/Greedy Best-First/IDA*.
  TSP dùng cùng graph này để tính ma trận chặng trước khi chạy Nearest Neighbor.

## Cấu trúc thư mục

```text
backend/
├── main.py                         # Điểm vào tương thích: python main.py
├── app/
│   ├── api/main.py                 # Flask routes và cấu hình công khai
│   ├── algorithms/                 # Các thuật toán graph core và heuristic
│   ├── core/                       # Mô hình, chi phí, vùng dữ liệu
│   ├── repositories/               # Dữ liệu đồ thị và JSON repository
│   └── services/                   # Route search và Goong Places collector
├── data/
│   ├── nodes_clean.js              # 98 node, gồm giao lộ, access và food node
│   └── edges_clean.js              # 176 cạnh có hướng
└── tests/                          # Test tự động
frontend/
├── index.html
├── app.js
└── styles.css
```

## Cấu hình an toàn

Tạo `.env` ở thư mục gốc dự án, cạnh `README.md`, từ `.env.example`:

```env
GOONG_MAP_TILES_KEY=điền_map_tiles_key
GOONG_REST_API_KEY=điền_rest_api_key
```

Hai khóa có mục đích khác nhau. `GOONG_REST_API_KEY` chỉ được dùng ở backend và
không được đưa vào frontend. Frontend lấy `GOONG_MAP_TILES_KEY` qua
`GET /api/config`; file `.env`, khóa thật và dữ liệu thu thập được đã nằm trong
`.gitignore`.

Không ghi API key vào source code, log, ảnh chụp màn hình hoặc commit. Khi đưa
ứng dụng lên môi trường thật, nên giới hạn domain/IP và hạn mức key trên Goong.

## Cài đặt

Từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r backend\requirements.txt
```

## Chạy ứng dụng

Cửa sổ 1 — backend:

```powershell
cd backend
python main.py
```

Cửa sổ 2 — frontend:

```powershell
cd frontend
python -m http.server 8080
```

Mở `http://localhost:8080`. Backend chạy tại `http://localhost:8000`.

## API chính

- `GET /api/graph` — đồ thị nodes và edges.
- `GET /api/nodes` — danh sách node cho bộ chọn.
- `GET /api/algorithms` — danh sách thuật toán cho selection.
- `GET /api/cost-profiles` — danh sách profile chi phí cho selection.
- `GET /api/food-places` — 39 food node từ dataset, kèm cờ `within_food_area`.
- `GET /api/config` — chỉ trả về map tiles key cho frontend.
- `POST /api/search` — tìm đường với `bfs`, `dfs`, `ucs`, `astar`, `greedy_best_first` hoặc `ida_star`.
- `POST /api/metrics` — so sánh BFS, DFS, Dijkstra, UCS, A*, IDA* và Greedy Best-First.
- `POST /api/tsp` — A* dựng ma trận chi phí, sau đó Nearest Neighbor tối ưu tuyến qua nhiều node.

Graph runtime đọc trực tiếp `backend/data/nodes_clean.js` và
`backend/data/edges_clean.js`. Đây là file JavaScript chứa JSON array, không phải
JSON thuần; loader trong `backend/app/repositories/clean_dataset_repository.py`
đọc array và giữ lại metadata như `address`, `source`, `on_edge`.

## Thu thập địa điểm Goong

Chạy từ thư mục `backend`:

```powershell
python -m app.services.food_places --step 0.004 --radius 0.7 --limit 20 --delay 5 --chunks 8 --max-per-chunk 10 --max-detail-per-chunk 40
```

Kết quả collector được ghi sau mỗi chunk vào `backend/data/food_places.json`. Chạy lại sẽ
tiếp tục từ checkpoint nếu các tham số vùng và số chunk khớp. Muốn quét lại từ
đầu, thêm `--no-resume`. Dữ liệu này là artifact cục bộ, không commit lên Git.

Vùng lọc là tứ giác cố định trong `backend/app/core/food_area.py`:

```text
(10.79185, 106.69584)
(10.78495, 106.68911)
(10.77959, 106.69498)
(10.78659, 106.70156)
```

Collector vẫn kiểm tra tọa độ chi tiết bằng phép kiểm tra điểm-trong-đa-giác;
việc một địa điểm xuất hiện trong kết quả tìm kiếm không đồng nghĩa nó được giữ
lại nếu nằm ngoài tứ giác. Runtime graph và endpoint `/api/food-places` vẫn giữ
đủ 39 food node trong `nodes_clean.js`; trường `within_food_area` cho biết kết
quả có nằm trong vùng cũ hay không.

Frontend lấy danh sách thuật toán và tiêu chí tối ưu từ `/api/algorithms` và
`/api/cost-profiles`, nên selection không cần sửa HTML khi thêm lựa chọn tương
thích ở backend. `POST /api/search` nhận `cost_profile` với các giá trị
`balanced`, `shortest_distance`, `fastest_route` hoặc `avoid_congestion`.

Với TSP/multi-location, payload có dạng:

```json
{
  "start": "1",
  "waypoints": ["1", "5", "10"],
  "cost_profile": "balanced",
  "return_to_start": false
}
```

## Kiểm tra trước khi push

```powershell
python -m py_compile backend\main.py backend\app\api\main.py backend\app\services\food_places.py
node --check frontend\app.js
python -m pytest backend\tests -q
```

Kiểm tra thủ công thêm `GET /api/graph`, `GET /api/config` và `GET
/api/food-places` khi backend đang chạy. Không đưa `.env`, thư mục virtualenv,
`__pycache__`, file tạm hoặc `food_places.json` vào commit.

## Tài liệu tham khảo

- [Goong API key](https://docs.goong.io/rest/api-key/)
- [Goong JavaScript SDK](https://docs.goong.io/javascript/)
- [Goong Map](https://docs.goong.io/javascript/map/)
- [Goong REST API](https://docs.goong.io/rest/)
