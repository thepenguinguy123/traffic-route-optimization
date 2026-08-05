# Bối cảnh dự án

## Mục tiêu

Traffic Route Optimization minh họa cách mô hình hóa mạng lưới giao thông thành
đồ thị và so sánh các cách tìm tuyến. Người dùng chọn node đầu/cuối, tiêu chí
chi phí và quan sát tuyến được hoạt ảnh trên bản đồ Goong.

## Kiến trúc hiện tại

- `backend/app/api/main.py`: Flask app, CORS và các HTTP endpoint.
- `backend/app/repositories/graph_data.py`: dữ liệu 56 node/edge đang dùng bởi
  giao diện hiện tại.
- `backend/app/algorithms/`: BFS, DFS, UCS, A*, Greedy dùng registry chung và
  TSP legacy cho nhiều waypoint.
- `backend/app/core/`: mô hình đồ thị, chi phí và vùng địa điểm.
- `backend/app/services/multi_location_service.py`: dựng ma trận cost/path bằng
  A* và tối ưu thứ tự waypoint bằng Nearest Neighbor.
- `backend/app/services/food_places.py`: collector Goong Places API có retry,
  giới hạn chunk và checkpoint.
- `frontend/app.js`: khởi tạo Goong GL JS, tải graph/food places và hoạt ảnh.

API đã dùng `TrafficGraph` làm graph runtime cho BFS, DFS, UCS, A* và Greedy.
Response được chuyển về format animation cũ để frontend có thể hiển thị frontier,
visited và tuyến cuối mà không cần hai hệ thống dữ liệu song song.

## Luồng chạy

1. Backend nạp `.env` ở thư mục gốc (hoặc `backend/.env` để thuận tiện local).
2. Frontend gọi `/api/config` để nhận duy nhất map tiles key.
3. Frontend gọi `/api/algorithms`, `/api/cost-profiles`, `/api/nodes`, `/api/graph`
   và `/api/food-places` để dựng selection và bản đồ.
4. Khi tìm kiếm, frontend gọi `/api/search` hoặc `/api/tsp` và phát hoạt ảnh.
   `/api/tsp` dùng pipeline A* + Nearest Neighbor cho nhiều điểm.

## Dữ liệu địa điểm

Vùng thu thập được định nghĩa bằng tứ giác trong `backend/app/core/food_area.py`.
Collector lọc lại tọa độ từ Place Detail bằng phép kiểm tra điểm-trong-đa-giác,
do đó các kết quả ngoài vùng không được ghi vào danh sách cuối. Kết quả runtime
được lưu tại `backend/data/food_places.json`, bị Git bỏ qua để tránh đưa dữ liệu
phụ thuộc API vào repository.

Mặc định collector chia vùng thành 8 chunk (lưới 2x4), giữ tối đa 10 địa điểm
mỗi chunk và kiểm tra tối đa 40 ID chi tiết mỗi chunk. Sau mỗi chunk, file JSON
được ghi atomically để có thể tiếp tục sau lỗi mạng hoặc HTTP 429.

## Selection và profile chi phí

Frontend không hardcode danh sách thuật toán. Các lựa chọn graph core gồm BFS,
DFS, UCS, A* và Greedy; TSP được hiển thị trong nhóm multi-stop. Cost profile
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
