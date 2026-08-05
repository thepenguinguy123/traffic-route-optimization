# 🤖 AGENTS.md: Hướng Dẫn cho AI Agents

## 📌 Quy Tắc Chung

### Ngôn Ngữ
- **Tất cả tài liệu** (README, CONTEXT, comments) **phải viết bằng tiếng Việt**
- **Code** có thể dùng tiếng Anh cho tên biến/hàm (tuân thủ convention)
- **Comments kỹ thuật** có thể viết bằng tiếng Anh

### Code Style
- **Python**: Tuân thủ [PEP 8](https://peps.python.org/pep-0008/)
- **JavaScript**: Tuân thủ [Standard JS](https://standardjs.com/)
- **HTML/CSS**: Format nhất quán, thút vào 2 hoặc 4 space

### Commit Messages
- **Format**: `<type>(<scope>): <message>`
- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Example**: `feat(algorithms): thêm thuật toán A*`
- **Language**: Tiếng Việt, rõ ràng, ngắn gọn

---

## 🛠️ Development Workflow

### 1. Setup Environment
```bash
# Clone repository
git clone <repository-url>
cd Lab1-CSAI

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Setup frontend (tùy chọn)
cd ../frontend
# Không cần cài đặt gì thêm (chỉ HTML/CSS/JS)
```

### 2. Chạy Dự Án

#### Backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```
- **Development**: `--reload` (auto-restart khi code thay đổi)
- **Production**: `--workers 4` (4 worker processes)

#### Frontend
- Mở trực tiếp `frontend/index.html` trong trình duyệt
- Hoặc dùng server local:
  ```bash
  cd frontend
  python -m http.server 8080
  ```

### 3. Testing

#### Backend Tests
```bash
# Kiểm tra API endpoints
curl http://localhost:8000/api/graph
curl http://localhost:8000/api/nodes

# Tìm đường với DFS
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"start":"1","end":"2","algorithm":"dfs"}'

# Tìm đường với Greedy
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"start":"1","end":"10","algorithm":"greedy","cost_type":"distance"}'

# TSP với nhiều điểm
curl -X POST http://localhost:8000/api/tsp \
  -H "Content-Type: application/json" \
  -d '{"waypoints":["1","5","10"],"cost_type":"time"}'
```

#### Frontend Tests
1. Mở `frontend/index.html` trong trình duyệt
2. Mở **DevTools (F12)**
3. Kiểm tra:
   - ✅ Không lỗi trong **Console**
   - ✅ Request đến `/api/graph` trả về `200 OK`
   - ✅ Request đến Goong Tiles trả về `200 OK`
   - ✅ Animation chạy khi nhấn "Start Search"

---

## 📁 Cấu Trúc Thư Mục

```
Lab1-CSAI/
├── .env                    # ❌ KHÔNG COMMIT (chứa API keys)
├── .env.example            # ✅ Template cho .env
├── README.md               # ✅ Tài liệu chính
├── CONTEXT.md              # ✅ Bối cảnh dự án
├── AGENTS.md               # ✅ Hướng dẫn cho AI agents
├── backend/
│   ├── main.py             # FastAPI app + routes
│   ├── graph_data.py       # 56 nodes + edges + helpers
│   ├── algorithms.py       # DFS, Greedy, TSP implementations
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── index.html          # Main HTML (Leaflet + Goong Tiles)
    ├── styles.css          # Minimalism CSS
    └── app.js              # Map logic + animation
```

### Quy Tắc File
| File | Quyền | Mô Tả |
|------|-------|-------|
| `.env` | **Không commit** | Chứa API keys |
| `*.py` | `644` | Python source code |
| `*.js` | `644` | JavaScript source code |
| `*.html` | `644` | HTML files |
| `*.css` | `644` | CSS files |
| `*.md` | `644` | Documentation |

---

## ⚠️ Prohibited Actions (Cấm Kị)

| Hành Động | Lý Do | Giải Pháp |
|-----------|-------|-----------|
| Commit `.env` | Lộ API keys | Thêm `.env` vào `.gitignore` |
| Dùng `goongjs` | Xung đột với Leaflet | Dùng `L.*` (Leaflet) |
| Xóa comments | Mất tài liệu | Giữ nguyên comments |
| Thay đổi cấu trúc nodes/edges | Phá vỡ backend | Giữ nguyên format |
| Hardcode values | Khó bảo trì | Dùng constants/variables |
| Sửa trực tiếp `main` branch | Gây xung đột | Luôn dùng feature branch |

---

## ✅ Best Practices

### Backend (Python)
- ✅ **Sử dụng Pydantic models** cho request/response validation
- ✅ **Type hints** cho tất cả hàm và biến
- ✅ **Docstrings** cho tất cả hàm public
- ✅ **Error handling** với HTTPException
- ✅ **Logging** cho debug (sử dụng `logging` module)

**Ví dụ:**
```python
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    """Request model cho API tìm đường."""
    start: str
    end: str
    algorithm: str
    cost_type: Optional[str] = "distance"

@app.post("/api/search")
def search_route(req: SearchRequest):
    """Tìm đường giữa 2 điểm sử dụng thuật toán chọn."""
    try:
        # Logic tìm đường
        return {"path": [...], "animation_log": [...]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Frontend (JavaScript)
- ✅ **Sử dụng Leaflet** cho bản đồ (`L.map`, `L.marker`)
- ✅ **Async/Await** cho fetch requests
- ✅ **Error handling** với try-catch
- ✅ **Modular code** (chia nhỏ hàm)
- ✅ **Comments** cho logic phức tạp

**Ví dụ:**
```javascript
async function loadGraph() {
    try {
        const response = await fetch(`${API_BASE}/api/graph`);
        if (!response.ok) throw new Error("Failed to load graph");
        const data = await response.json();
        renderNodes(data.nodes);
        renderEdges(data.edges, data.nodes);
    } catch (err) {
        console.error("Error:", err);
        alert("Không thể tải dữ liệu đồ thị");
    }
}
```

### CSS
- ✅ **BEM methodology** (Block__Element--Modifier)
- ✅ **CSS Variables** cho màu sắc
- ✅ **Responsive design** (media queries)
- ✅ **Minimalism** (không bo tròn, viền đen, nền trắng/xám)

**Ví dụ:**
```css
:root {
    --bg-primary: #ffffff;
    --border-color: #000000;
    --text-primary: #333333;
}

.map-container {
    height: 100vh;
}

#map {
    width: 100%;
    height: 100%;
    border: 1px solid var(--border-color);
}
```

---

## 🔍 Debugging Guide

### Common Issues & Fixes

| Lỗi | Nguyên Nhân | Debug Steps | Giải Pháp |
|-----|-------------|-------------|-----------|
| `403 Forbidden` (Goong Tiles) | API Key không hợp lệ | Kiểm tra `.env` + `app.js` | Lấy key mới từ Goong.io |
| `L is not defined` | Leaflet không tải | Kiểm tra `<script src="...leaflet.js">` | Thêm Leaflet CDN |
| `Map container has 0 height` | CSS sai | Inspect `#map` trong DevTools | Sửa CSS: `#map { height: 100% }` |
| `Cannot connect to backend` | Backend không chạy | `curl http://localhost:8000` | Chạy `uvicorn main:app --reload` |
| `CORS error` | CORS không cấu hình | Kiểm tra response headers | Thêm `CORSMiddleware` trong `main.py` |
| `onboarding.js error` | Goong JS SDK vẫn tải | Kiểm tra `<script>` tags | Xóa Goong JS SDK, dùng Leaflet |

### Debug Commands
```bash
# Kiểm tra backend
curl -v http://localhost:8000/api/graph

# Kiểm tra Goong Tiles (thay YOUR_KEY)
curl -v "https://tiles.goong.io/map/14/8512/5678.png?api_key=YOUR_KEY"

# Kiểm tra cổng backend
netstat -ano | findstr 8000  # Windows
lsof -i :8000               # Linux/Mac
```

---

## 📝 Code Review Checklist

### Backend Checklist
- [ ] Tất cả endpoints có **docstrings**
- [ ] Tất cả request/response dùng **Pydantic models**
- [ ] Có **error handling** (try-except + HTTPException)
- [ ] Có **type hints** cho hàm và biến
- [ ] **CORS** được cấu hình đúng
- [ ] **Logging** cho debug (nếu cần)

### Frontend Checklist
- [ ] Chỉ dùng **Leaflet** (không Goong JS SDK)
- [ ] Có **error handling** cho fetch requests
- [ ] **Animation** chạy mượt mà
- [ ] **Responsive** trên mobile/desktop
- [ ] **Console** không có lỗi

### General Checklist
- [ ] **Code format** đúng (PEP 8 / Standard JS)
- [ ] **Comments** giải thích logic phức tạp
- [ ] **No hardcoded values** (dùng constants)
- [ ] **Tài liệu** được cập nhật
- [ ] **Tests** chạy thành công

---

## 🤝 Collaboration Rules

### Pull Request Template
```markdown
## [Feat/Fix/Docs] <Tên tính năng>

### Mô Tả
- [ ] Thêm tính năng X
- [ ] Sửa lỗi Y
- [ ] Cập nhật tài liệu Z

### Thay Đổi
- `backend/algorithms.py`: Thêm thuật toán A*
- `frontend/app.js`: Cập nhật animation logic

### Kiểm Tra
- [ ] Code format đúng
- [ ] Không lỗi khi chạy
- [ ] Tài liệu được cập nhật

### Screenshots (nếu có)
![Description](image.png)
```

### Review Process
1. **Self-review**: Kiểm tra theo checklist trên
2. **Create PR**: Điền đầy đủ template
3. **Wait for review**: Chờ ít nhất 1 approval
4. **Merge**: Sau khi tất cả comments được giải quyết

---

## 📚 Learning Resources

### Python/FastAPI
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### JavaScript/Leaflet
- [Leaflet Documentation](https://leafletjs.com/reference-1.9.4.html)
- [MDN JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [Async/Await Guide](https://javascript.info/async-await)

### Goong.io
- [Goong.io API Docs](https://help.goong.io/)
- [Static Map API](https://help.goong.io/kb/rest-api/static-map-static-map/staticmap-ban-do-tinh/)

---

## 📜 License

MIT License - Xem [LICENSE](LICENSE) để biết chi tiết.
