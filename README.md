# 🚗 Vietnamese Traffic Route Optimization

Hệ thống tìm đường giao thông tối ưu tại Quận 1, TP.HCM với giao diện web hiện đại, bản đồ Goong Maps, và animation trực quan hóa quá trình tìm kiếm.

## 🎯 Tính năng

- **3 Thuật toán tìm kiếm:**
  - **DFS** (Depth-First Search) — Tìm kiếm theo chiều sâu
  - **Greedy Best-First Search** — Tìm kiếm tham lam dựa trên heuristic
  - **TSP** (Traveling Salesman Problem) — Tối ưu lộ trình đa điểm

- **Trực quan hóa Animation:**
  - ⚪ Trắng: Node chưa khám phá
  - 🔴 Đỏ: Node đang trong hàng đợi (Frontier)
  - 🟢 Xanh: Node đã duyệt (Visited)
  - 🟡 Vàng: Đường đi tối ưu

- **3 Tiêu chí tối ưu:** Quãng đường, Thời gian, Tổng chi phí (có tính kẹt xe)

## 🛠️ Cài đặt

### 1. Chuẩn bị API Key Goong Maps
- Đăng ký tại [account.goong.io](https://account.goong.io/)
- Lấy **Map Tiles Key**

### 2. Cấu hình API Key
- Mở file `.env` ở thư mục gốc, thay `your_map_tiles_key_here` bằng key thực
- Mở file `frontend/app.js`, thay `YOUR_GOONG_MAP_TILES_KEY` ở dòng 5 bằng key thực

### 3. Cài đặt Backend
```bash
cd backend
pip install -r requirements.txt
```

### 4. Chạy Backend Server
```bash
cd backend
python main.py
# Hoặc chạy module API: python -m app.api.main
# Hoặc: uvicorn main:app --reload --port 8000
```

### 5. Mở Frontend
- Mở file `frontend/index.html` trực tiếp trong trình duyệt
- Hoặc dùng VS Code Live Server extension

## 📁 Cấu trúc Thư mục

```
Lab1-CSAI/
├── .env                    # API keys (không commit lên Git)
├── .env.example            # Template cho .env
├── README.md
├── backend/
│   ├── main.py             # Điểm vào tương thích
│   ├── app/
│   │   ├── api/main.py     # Flask API routes
│   │   ├── algorithms/     # DFS, Greedy, TSP
│   │   ├── repositories/   # Dữ liệu graph
│   │   ├── core/           # Logic hình học vùng
│   │   └── services/       # Goong Places collector
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── index.html           # Trang chính
    ├── styles.css           # Dark glassmorphism theme
    └── app.js               # Map, Animation, Logic
```

## 📊 Dữ liệu Đồ thị

- **54 nodes** — Các ngã tư, địa điểm thực ở Quận 1, TP.HCM
- **Tọa độ thực** (lat/lng) trên bản đồ Goong
- **Edges** tự động tạo dựa trên khoảng cách giữa các node
- **Mức kẹt xe** giả lập: khu du lịch (7-10), khu dân cư (1-6)
