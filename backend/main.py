"""Điểm vào tương thích để chạy backend bằng `python main.py`."""

from app.api.main import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
