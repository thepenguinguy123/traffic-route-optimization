"""Điểm vào tương thích để chạy backend bằng `python main.py`."""

import sys
from pathlib import Path


# Cho phép chạy từ thư mục backend nhưng vẫn dùng package `backend.app` thống nhất.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.main import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
