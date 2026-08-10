# Traffic Route Optimization

Ứng dụng mô phỏng tối ưu tuyến giao thông trên bản đồ Goong, kết hợp graph core, hoạt ảnh tìm kiếm và dữ liệu địa điểm ăn uống trong khu vực giới hạn.

## Kiến trúc

- `backend/`: Flask API, graph core, các thuật toán BFS, DFS, UCS, A*, Greedy Best-First, IDA* và TSP.
- `backend/data/`: dữ liệu node/edge và bộ từ khóa địa phương hóa; graph loader đọc trực tiếp `nodes_clean.js` và `edges_clean.js`.
- `backend/app/repositories/`: lớp đọc và chuẩn hóa dataset.
- `backend/app/services/`: route search, metrics, TSP và collector Goong Places.
- `frontend/`: HTML/CSS/JavaScript thuần, Goong GL JS, không dùng framework build.

## Cài đặt

Từ thư mục gốc trên Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r backend\requirements.txt
```

Tạo file `.env` ở thư mục gốc, dựa trên `.env.example`:

```env
GOONG_MAP_TILES_KEY=your_map_tiles_key
GOONG_REST_API_KEY=your_rest_api_key
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

Không commit `.env` hoặc bất kỳ API key nào.

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

Mở `http://localhost:8080`. Backend mặc định chạy ở `http://localhost:8000`.

## API chính

- `GET /api/graph`, `/api/nodes`, `/api/algorithms`, `/api/cost-profiles`.
- `GET /api/config`, `/api/food-places`.
- `POST /api/search` tìm tuyến hai điểm.
- `POST /api/tsp` tìm tuyến nhiều waypoint.
- `POST /api/metrics` so sánh các thuật toán.

## Collector dữ liệu Goong

Collector chỉ phục vụ cào dữ liệu, không phải runtime bắt buộc của frontend. Chạy từ `backend`:

```powershell
python -m app.services.food_places --step 0.004 --radius 0.7 --limit 20 --delay 5 --chunks 8 --max-per-chunk 10 --max-detail-per-chunk 40
```

Kết quả checkpoint nằm trong `backend/data/food_places.json` và bị loại khỏi Git. Từ khóa truy vấn được cấu hình trong `backend/data/food_search_terms.json`; code collector chỉ chứa logic tiếng Anh. Vùng lọc là tứ giác trong `backend/app/core/food_area.py`:

```text
(10.79185, 106.69584)
(10.78495, 106.68911)
(10.77959, 106.69498)
(10.78659, 106.70156)
```

## Hành vi giao diện

- Start và End được đánh dấu bằng marker nhiều vòng với nhãn `S` và `E`.
- Waypoint TSP nằm trong queue riêng, không bao gồm Start; số thứ tự được hiển thị phía trên node.
- Sau khi thay đổi thuật toán, Start/End, waypoint, queue, mode hoặc cost profile, kết quả cũ được xóa.
- Route Review mở ở Right Panel. Compare Algorithms mở ở Bottom Panel; khi một panel mở, panel còn lại tự động thu gọn.
- Right Panel có thể kéo rộng/hẹp; Bottom Panel có thể kéo thay đổi chiều cao và cuộn nội dung.
- Mỗi step trong Route Review tách tuyến `FROM`/`TO`, khoảng cách, thời gian, congestion, risk và hướng cạnh thành các trường riêng.
- Tuyến kết quả dùng màu primary `#1769f9`; step đang xem dùng cyan sáng `#22d3ee`; node đã duyệt dùng xanh lá.

## Quy ước ngôn ngữ và dữ liệu

- Toàn bộ source thực thi (`.py`, `.js`, `.html`, `.css`) dùng tiếng Anh và ASCII để tránh lỗi encoding.
- Tài liệu dự án viết bằng tiếng Việt theo `AGENTS.md`.
- Tên địa điểm, địa chỉ và từ khóa tìm kiếm được xem là dữ liệu miền nên giữ Unicode tiếng Việt trong `backend/data/`.

## Kiểm tra trước khi push

```powershell
python -m black --check backend
python -m compileall -q backend
node --check frontend\app.js
python -m pytest backend\tests -q -p no:cacheprovider
```

Bộ test hiện có gồm 25 trường hợp. Kiểm tra thêm thủ công các endpoint `/api/graph`, `/api/config`, `/api/food-places` khi backend đang chạy.
