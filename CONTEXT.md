# Bối cảnh dự án

Traffic Route Optimization minh họa cách mô hình hóa mạng lưới giao thông thành đồ thị có trọng số và trực quan hóa quá trình tìm đường trên Goong Maps.

## Thành phần

- Flask cung cấp API graph, search, metrics và TSP.
- Animation log của graph search phản ánh frontier snapshot trước khi đánh dấu node hiện tại là visited.
- Route explanation service tạo explanation có cấu trúc cho search, metrics và multi-location để UI giải thích tiêu chí, guarantee, route thay thế và visiting order.
- Graph runtime đọc dataset sạch trong `backend/data/` qua repository.
- Frontend thuần HTML/CSS/JavaScript hiển thị bản đồ, marker, edge, animation và kết quả.
- Collector Goong Places chạy độc lập, hỗ trợ retry, checkpoint theo chunk, resume và bộ từ khóa địa phương hóa trong `backend/data/food_search_terms.json`.

## Luồng tìm kiếm

1. Frontend tải graph và cấu hình map từ backend.
2. Người dùng chọn thuật toán, cost profile, Start/End hoặc queue TSP.
3. Backend chạy thuật toán và trả về path, animation log, thống kê và giải thích.
4. Frontend animate node/edge, vẽ tuyến primary và hiển thị Route Review.
5. Compare gọi `/api/metrics`, chuyển bảng so sánh vào Bottom Panel và thu gọn Right Panel.

## Quy ước panel

Right Panel chỉ dùng cho kết quả tìm kiếm và Route Review. Bottom Panel chỉ dùng cho Compare Algorithms. Hai panel là hai drawer độc lập; mở một panel sẽ tự động thu gọn panel còn lại. Nút mũi tên cho phép mở lại panel đang thu gọn.

## Dữ liệu và bảo mật

API key chỉ nằm trong `.env`. `GOONG_REST_API_KEY` chỉ dùng ở backend; frontend chỉ nhận map tiles key qua `/api/config`. Không commit `.env`, checkpoint collector, virtualenv, cache hoặc file tạm.

## Bất biến kỹ thuật

- Edge là có hướng; thuật toán chỉ duyệt neighbor hợp lệ và không tự suy diễn cạnh ngược cho đường một chiều.
- Edge traffic baseline dùng congestion/risk deterministic theo road type; các scenario `normal`, `rush_hour` và `rainy_day` được khai báo riêng trong `backend/data/traffic_scenarios.json` để tái lập thí nghiệm.
- UCS, A* và từng segment TSP dùng cùng `CostCalculator` và cost profile runtime.
- `risk_factor` số thực được chuẩn hóa trực tiếp; dữ liệu cũ thiếu trường này mới fallback sang `risk_level`.
- Queue TSP không chứa Start. Mode `auto` dùng Nearest Neighbor trên ma trận chi phí A*; mode `ordered` giữ nguyên thứ tự queue và tối ưu từng segment bằng A*.
- Source thực thi dùng tiếng Anh/ASCII; Unicode tiếng Việt chỉ nằm trong tài liệu và dữ liệu miền.

## Kiểm tra

Chạy các lệnh trong README trước khi push. Với frontend, mở DevTools để kiểm tra không có lỗi Console, request graph trả về `200` và các thao tác search/compare không để lại panel trắng.
- Runtime hỗ trợ scenario `normal`, `rush_hour` và `rainy_day`; graph variant được cache và dữ liệu baseline không bị mutate.

- Frontend có scenario selector; thay đổi scenario sẽ clear kết quả và gửi scenario vào Search, Metrics và TSP.
- Normalization ?? ch?t: `MAX_DISTANCE_KM = 0.25` v? `MAX_TIME_MIN = 0.6` l?y t? P95 c?a distance v? `base_time_min`, sau khi l?m tr?n l?n b??c th?c d?ng; congestion kh?ng thay ??i reference scale m? ?i v?o cost qua `congestion_delay`.
