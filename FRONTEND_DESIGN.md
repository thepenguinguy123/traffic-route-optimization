# Thiết kế frontend và bản đồ

## Định hướng

Giao diện dùng phong cách vuông, tương phản cao và palette thống nhất:

- Primary: `#1769f9`
- Secondary: `#e7e7e7`
- Black: `#000000`
- White: `#ffffff`
- Route step: `#22d3ee`
- Visited node: xanh lá

## Quy tắc hiển thị

Node thông thường có kích thước đồng nhất. Start/End có marker nhiều vòng và nhãn phía trên. Waypoint TSP dùng số thứ tự phía trên node. Edge một chiều và hai chiều được phân biệt bằng metadata và hướng hiển thị.

## Panel kết quả

Route Review nằm ở Right Panel, có resizer theo chiều ngang. Compare nằm ở Bottom Panel, có resizer theo chiều dọc, vùng content cuộn được và bố cục hai cột. JavaScript điều phối trạng thái loại trừ giữa hai drawer để không chồng lấn hoặc tạo vùng trắng. Right Panel thu gọn bằng dịch chuyển ngang; Bottom Panel thu gọn bằng dịch chuyển dọc, trong khi nút toggle vẫn nằm ngoài mép panel.

## Tính tương thích

Frontend không yêu cầu React hoặc Tailwind; HTML/CSS/JavaScript thuần phù hợp với cấu trúc hiện tại và không cần thêm pipeline build.

## Bất biến tương tác

- Thay đổi thuật toán, Start, End, waypoint, thứ tự queue, route mode hoặc cost profile phải hủy animation và xóa kết quả cũ.
- Search thành công mở Right Panel và đóng Bottom Panel.
- Compare thành công mở Bottom Panel và thu gọn Right Panel; mở lại Right Panel sẽ thu gọn Bottom Panel.
- HTML ID là duy nhất và mọi ID tĩnh được JavaScript truy cập phải tồn tại trong markup.
## Chi tiết từng bước

Mỗi bước tuyến được trình bày theo ba lớp: cặp điểm `FROM`/`TO`, lưới bốn thông số khoảng cách/thời gian/ùn tắc/rủi ro, và dòng mô tả hướng cạnh. Cấu trúc này giữ tên địa điểm dài trong vùng giới hạn, giúp người dùng quét nhanh thông tin mà không phải đọc chuỗi dấu gạch chéo.
