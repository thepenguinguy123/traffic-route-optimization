# Bối cảnh dự án

## Mục tiêu

Traffic Route Optimization minh họa cách mô hình hóa mạng lưới giao thông thành
đồ thị và so sánh các cách tìm tuyến. Người dùng chọn node đầu/cuối, tiêu chí
chi phí và quan sát tuyến được hoạt ảnh trên bản đồ Goong.

## Kiến trúc hiện tại

- `backend/app/api/main.py`: Flask app, CORS và các HTTP endpoint.
- `backend/app/repositories/clean_dataset_repository.py`: loader đọc trực tiếp
  `backend/data/nodes_clean.js` và `backend/data/edges_clean.js`.
- `backend/app/repositories/graph_data.py`: adapter tương thích cho legacy,
  nhưng dữ liệu runtime vẫn là 98 node và 176 cạnh sạch.
- `backend/app/algorithms/`: BFS, DFS, UCS, A*, Greedy Best-First và
  IDA* dùng registry chung; Nearest Neighbor xử lý nhiều waypoint.
- `backend/app/core/`: mô hình đồ thị, chi phí và vùng địa điểm.
- `backend/app/services/multi_location_service.py`: dựng ma trận cost/path bằng
  A* và tối ưu thứ tự waypoint bằng Nearest Neighbor.
- `backend/app/services/metrics_service.py`: chạy và tổng hợp metrics của nhiều
  thuật toán trên cùng graph/profile.
- `backend/app/services/food_places.py`: collector Goong Places API có retry,
  giới hạn chunk và checkpoint.
- `frontend/app.js`: khởi tạo Goong GL JS, tải graph đầy đủ và hoạt ảnh.

API đã dùng `TrafficGraph` làm graph runtime cho BFS, DFS, UCS, A*,
Greedy Best-First và IDA*.
Response được chuyển về format animation cũ để frontend có thể hiển thị frontier,
visited và tuyến cuối mà không cần hai hệ thống dữ liệu song song.

## Luồng chạy

1. Backend nạp `.env` ở thư mục gốc (hoặc `backend/.env` để thuận tiện local).
2. Frontend gọi `/api/config` để nhận duy nhất map tiles key.
3. Frontend gọi `/api/algorithms`, `/api/cost-profiles`, `/api/nodes` và
   `/api/graph` để dựng selection và bản đồ. Graph đã bao gồm cả food node.
4. Khi tìm kiếm, frontend gọi `/api/search` hoặc `/api/tsp` và phát hoạt ảnh.
   `/api/tsp` dùng pipeline A* + Nearest Neighbor cho nhiều điểm.
5. Nút Compare Algorithms gọi `/api/metrics` để hiển thị bảng so sánh hiệu năng.

## Dữ liệu graph và địa điểm

Dataset chính gồm 98 node và 176 cạnh có hướng. Trong đó có 56 node giao lộ,
3 node access và 39 node food. Các file nguồn có wrapper JavaScript `const ... = [...]`, vì vậy
không được đọc bằng JSON loader thông thường. `clean_dataset_repository.py`
parse phần array, chuẩn hóa ID thành string ở domain layer và giữ metadata gốc.

Các cạnh mới dùng `source/target`, `road_type`, `risk_factor` và có thể là một
chiều. Graph core tôn trọng hướng cạnh; không tự sinh thêm cạnh ngược.

Vùng thu thập được định nghĩa bằng tứ giác trong `backend/app/core/food_area.py`.
Collector lọc lại tọa độ từ Place Detail bằng phép kiểm tra điểm-trong-đa-giác,
do đó dữ liệu collector runtime không giữ kết quả ngoài vùng. Dataset clean mới
giữ đủ 39 food node và API đánh dấu `within_food_area` cho các node ngoài vùng.
Kết quả runtime
được lưu tại `backend/data/food_places.json`, bị Git bỏ qua để tránh đưa dữ liệu
phụ thuộc API vào repository.

Mặc định collector chia vùng thành 8 chunk (lưới 2x4), giữ tối đa 10 địa điểm
mỗi chunk và kiểm tra tối đa 40 ID chi tiết mỗi chunk. Sau mỗi chunk, file JSON
được ghi atomically để có thể tiếp tục sau lỗi mạng hoặc HTTP 429.

## Selection và profile chi phí

Frontend không hardcode danh sách thuật toán. Các lựa chọn graph core gồm BFS,
DFS, UCS, A*, Greedy Best-First và IDA*; TSP được hiển thị trong nhóm
multi-stop. Cost profile
gồm `balanced`, `shortest_distance`, `fastest_route` và `avoid_congestion`.

## Bảo mật

- `.env` không được commit.
- REST API key chỉ tồn tại trong collector/backend.
- Không log giá trị key và không hardcode key trong JavaScript.
- Map key nên được giới hạn domain; REST key nên được giới hạn theo IP/quota trên
  Goong khi môi trường triển khai hỗ trợ.
- Dữ liệu Places cần được xem là dữ liệu cache có thể thay đổi, không phải nguồn
  dữ liệu chính thức lâu dài.

## Kiểm tra tối thiểu

```powershell
python -m py_compile backend\main.py backend\app\api\main.py backend\app\services\food_places.py
node --check frontend\app.js
python -m pytest backend\tests -q
```
