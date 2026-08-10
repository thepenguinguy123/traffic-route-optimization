# Bối cảnh dự án

Traffic Route Optimization minh họa cách mô hình hóa mạng lưới giao thông thành đồ thị có trọng số và trực quan hóa quá trình tìm đường trên Goong Maps.

## Thành phần

- Flask cung cấp API graph, search, metrics và TSP.
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
- UCS, A* và từng segment TSP dùng cùng `CostCalculator` và cost profile runtime.
- `risk_factor` số thực được chuẩn hóa trực tiếp; dữ liệu cũ thiếu trường này mới fallback sang `risk_level`.
- Queue TSP không chứa Start. Mode `auto` dùng Nearest Neighbor trên ma trận chi phí A*; mode `ordered` giữ nguyên thứ tự queue và tối ưu từng segment bằng A*.
- Source thực thi dùng tiếng Anh/ASCII; Unicode tiếng Việt chỉ nằm trong tài liệu và dữ liệu miền.

## Kiểm tra

Chạy các lệnh trong README trước khi push. Với frontend, mở DevTools để kiểm tra không có lỗi Console, request graph trả về `200` và các thao tác search/compare không để lại panel trắng.