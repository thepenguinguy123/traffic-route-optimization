# 📋 CONTEXT.md: Bối Cảnh Dự Án

## 🎯 Tổng Quan Dự Án

**Tên Dự Án:** Vietnamese Traffic Route Optimization  
**Mục Đích:** Hệ thống trực quan hóa thuật toán tìm đường giao thông tối ưu tại Quận 1, TP.HCM  
**Công Nghệ:** FastAPI (Backend) + Leaflet (Frontend) + Goong.io (Map Tiles)  
**Ngôn Ngữ:** Python (Backend), JavaScript (Frontend), Tiếng Việt (Tài liệu)  

---

## 🏗️ Kiến Trúc Hệ Thống

### Sơ Đồ Kiến Trúc
```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                                 │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐ │
│  │   LEAFLET MAP    │  │         CONTROL PANEL                    │ │
│  │  • 56 Nodes      │  │  • Algorithm Selection (DFS/Greedy/TSP)  │ │
│  │  • Edges         │  │  • Start/End Node Selection              │ │
│  │  • Animation     │  │  • Cost Criteria (Distance/Time/Cost)    │ │
│  │  • Path Highlight│  │  • Animation Speed Slider                │ │
│  └──────────────────┘  │  • Start Search Button                   │ │
│                        │  • Results Display                       │ │
│                        └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND SERVER (FastAPI)                         │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  API Endpoints:                                                │  │
│  │  • GET  /api/graph      → Trả về toàn bộ đồ thị (nodes + edges)│  │
│  │  • GET  /api/nodes      → Danh sách nodes cho dropdown         │  │
│  │  • POST /api/search     → Tìm đường (DFS/Greedy)               │  │
│  │  • POST /api/tsp        → Tối ưu lộ trình đa điểm              │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│                     GOONG.IO API (Map Tiles)                      │
│  • Cung cấp tile bản đồ Việt Nam (Quận 1, TP.HCM)                 │
│  • URL: https://tiles.goong.io/map/{z}/{x}/{y}.png?api_key=...    │
└───────────────────────────────────────────────────────────────────┘
```

### Luồng Dữ Liệu
```
1. User chọn thuật toán + điểm bắt đầu/kết thúc
2. Frontend gửi request → Backend (POST /api/search)
3. Backend tính toán đường đi → Trả về path + animation_log
4. Frontend hiển thị animation từng bước trên bản đồ
```

---

## 🔧 Công Nghệ Sử Dụng

### Backend Stack
| Công Nghệ | Phiên Bản | Mục Đích |
|-----------|-----------|----------|
| Python | 3.8+ | Ngôn ngữ chính |
| FastAPI | 0.95+ | Web framework |
| Uvicorn | latest | ASGI server |
| Pydantic | latest | Data validation |
| Python-dotenv | latest | Load environment variables |

### Frontend Stack
| Công Nghệ | Phiên Bản | Mục Đích |
|-----------|-----------|----------|
| HTML5 | - | Cấu trúc trang |
| CSS3 | - | Styling (Minimalism) |
| JavaScript (ES6+) | - | Logic + Animation |
| Leaflet | 1.9.4 | Map rendering |
| Goong.io Tiles | - | Vietnamese map provider |

---

## 📊 Dữ Liệu Dự Án

### Nguồn Dữ Liệu
- **Nguồn:** Tọa độ thực tế các ngã tư, địa điểm ở Quận 1, TP.HCM
- **Định Dạng:** CSV (id, name, lat, lng)
- **Số Lượng:** 56 nodes
- **Kết Nối:** Edges tự động sinh dựa trên khoảng cách Haversine

### Cấu Trúc Dữ Liệu

#### Nodes
```json
{
  "1": {
    "name": "Point 1",
    "lat": 10.7918511,
    "lng": 106.6958498
  },
  "2": {
    "name": "Point 2",
    "lat": 10.7902602,
    "lng": 106.694281
  },
  
}
```

#### Edges
```json
{
  "from": "1",
  "to": "2",
  "distance_km": 0.456,
  "time_min": 2,
  "congestion": 5
}
```

### Chi Tiết Thuộc Tính
| Thuộc Tính | Mô Tả | Giá Trị |
|------------|-------|--------|
| `name` | Tên điểm | String |
| `lat` | Vĩ độ | Float |
| `lng` | Kinh độ | Float |
| `distance_km` | Khoảng cách | Float (km) |
| `time_min` | Thời gian di chuyển | Integer (phút) |
| `congestion` | Mức độ kẹt xe | Integer (1-10) |

---

## 🎓 Mục Đích Giáo Dục

Dự án được thiết kế để:

### 1. Học Thuật Toán Đồ Thị
- **DFS (Depth-First Search):** Tìm kiếm theo chiều sâu
- **Greedy Best-First Search:** Tìm kiếm tham lam dựa trên heuristic
- **TSP (Traveling Salesman Problem):** Tối ưu lộ trình đa điểm

### 2. Học Lập Trình Web
- **Backend:** FastAPI + Python
- **Frontend:** HTML/CSS/JavaScript
- **Kết Nối:** Fetch API + RESTful API

### 3. Học Trực Quan Hóa
- Animation từng bước của thuật toán
- Hiển thị trạng thái nodes (frontier, visited, optimal)
- Đánh dấu đường đi tối ưu

### 4. Học Làm Việc Với Bản Đồ
- Sử dụng Leaflet cho bản đồ web
- Tích hợp Goong.io (bản đồ Việt Nam)
- Hiển thị markers, polylines

---

## 🔗 Tài Nguyên Liên Quan

### Tài Liệu Chính Thức
- [Leaflet Documentation](https://leafletjs.com/reference-1.9.4.html)
- [Goong.io API Docs](https://help.goong.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Tham Khảo Thuật Toán
- [DFS Algorithm](https://en.wikipedia.org/wiki/Depth-first_search)
- [Greedy Best-First Search](https://en.wikipedia.org/wiki/Best-first_search)
- [Traveling Salesman Problem](https://en.wikipedia.org/wiki/Travelling_salesman_problem)

### Công Cụ Phát Triển
- [VS Code](https://code.visualstudio.com/)
- [Postman](https://www.postman.com/) (Test API)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/) (Debug)

---

## 📝 Lịch Sử Phát Triển

| Ngày | Phiên Bản | Thay Đổi |
|------|-----------|----------|
| 2026-07-25 | v1.0 | Khởi tạo dự án |
| 2026-07-31 | v1.1 | Thêm 56 nodes từ CSV |
| 2026-08-01 | v1.2 | Chuyển từ Goong JS SDK sang Leaflet |

---

## 🤝 Đóng Góp

### Cách Đóng Góp
1. Fork repository
2. Tạo branch mới (`git checkout -b feature/your-feature`)
3. Commit thay đổi (`git commit -m "Thêm tính năng X"`)
4. Push lên branch (`git push origin feature/your-feature`)
5. Tạo Pull Request

### Quy Tắc Đóng Góp
- Code phải format đúng (PEP 8 / Standard JS)
- Có comments giải thích cho hàm phức tạp
- Cập nhật tài liệu khi thay đổi API
- Không commit file `.env`

---

## 📜 Giấy Phép

MIT License - Xem file [LICENSE](LICENSE) để biết chi tiết.
