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
Route Reasoning ch? hi?n th? s? l??ng high-impact segment v? h??ng d?n xem chi ti?t trong Route Steps; kh?ng l?p l?i danh s?ch edge d?i.

## Tương tác bảng so sánh

Mỗi row thuật toán là một control có thể click hoặc chọn bằng `Enter`/`Space`. Khi được chọn, row đổi trạng thái, bản đồ reset trạng thái duyệt trước đó, node đã duyệt chuyển sang xanh lá và final route chuyển sang primary; Bottom Panel vẫn được giữ mở để đối chiếu.

## TSP v? tr?ng th?i animation

- Route Mode v? Route Queue n?m trong c?ng m?t section; h?ng ch?n mode n?m ri?ng ?? kh?ng ch?n ti?u ?? ho?c b? ??m.
- Mode `Automatic` kh?a k?o th? v? thu?t to?n t? t?i ?u th? t? waypoint. Mode `Ordered` cho ph?p k?o th? v? gi? ??ng th? t? queue.
- Start kh?ng n?m trong queue. Waypoint v?n gi? s? th? t? ph?a tr?n marker tr?n b?n ??.
- M?t b??c graph search ???c hi?n th? theo th? t? `Processing ? Frontier updates ? Visited`; m?u ?? c? v?ng n?n v? glow nh?, frontier c? glow v?ng.
- Edge m?t chi?u c? m?t m?i t?n ? gi?a; edge hai chi?u c? k? hi?u `=` m?u xanh l? ? gi?a. C?c k? hi?u l? l?p tr?c quan, kh?ng thay ??i h??ng c?nh trong dataset.
