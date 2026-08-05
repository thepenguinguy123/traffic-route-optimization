"""Thu thập dữ liệu quán ăn trong một hình chữ nhật bằng Goong Places API."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.core.food_area import FOOD_AREA_POLYGON, point_in_polygon, polygon_bounds
from app.repositories.graph_data import NODES


GOONG_PLACES_URL = "https://rsapi.goong.io/Place/AutoComplete"
GOONG_DETAILS_URL = "https://rsapi.goong.io/Place/Detail"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "food_places.json"
SEARCH_TERMS = (
    "quán ăn",
    "nhà hàng",
    "cà phê",
    "coffee",
    "juice",
    "nước ép",
    "trà",
    "trà sữa",
    "bánh",
    "tiệm bánh",
    "bakery",
    "dessert",
    "food",
    "restaurant",
)


def parse_bounds(value: str) -> Tuple[float, float, float, float]:
    """Phân tích bounds theo định dạng west,south,east,north."""
    try:
        west, south, east, north = (float(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Bounds phải có dạng west,south,east,north."
        ) from error

    if west >= east or south >= north:
        raise argparse.ArgumentTypeError("Bounds không tạo thành hình chữ nhật hợp lệ.")
    return west, south, east, north


def graph_bounds(padding: float) -> Tuple[float, float, float, float]:
    """Tạo bounds từ danh sách node hiện tại và thêm khoảng đệm theo độ."""
    longitudes = [node["lng"] for node in NODES.values()]
    latitudes = [node["lat"] for node in NODES.values()]
    return (
        min(longitudes) - padding,
        min(latitudes) - padding,
        max(longitudes) + padding,
        max(latitudes) + padding,
    )


def grid_points(
    bounds: Tuple[float, float, float, float],
    step: float,
    polygon: Tuple[Tuple[float, float], ...] = FOOD_AREA_POLYGON,
) -> Iterable[Tuple[float, float]]:
    """Sinh các tâm tìm kiếm nằm trong tứ giác cần quét."""
    west, south, east, north = bounds
    longitude = west
    while longitude <= east:
        latitude = south
        while latitude <= north:
            if point_in_polygon(latitude, longitude, polygon):
                yield longitude, latitude
            latitude += step
        longitude += step


def request_json(url: str, params: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    """Gọi Goong REST API và trả về JSON, có thông báo lỗi rõ ràng."""
    query = urlencode(params)
    request = Request(f"{url}?{query}", headers={"User-Agent": "Lab01-CSAI/1.0"})
    payload: Optional[Dict[str, Any]] = None
    for attempt in range(5):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            if error.code != 429 or attempt == 4:
                raise
            retry_after = error.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after else 2**attempt
            print(f"Goong giới hạn request (429), chờ {wait_seconds:g}s...")
            time.sleep(wait_seconds)

    if payload is None:
        raise RuntimeError("Goong API không trả về payload sau các lần thử lại.")
    if payload.get("status") not in (None, "OK"):
        raise RuntimeError(f"Goong API trả về status={payload.get('status')}: {payload}")
    return payload


def in_search_area(
    location: Dict[str, Any],
    polygon: Tuple[Tuple[float, float], ...] = FOOD_AREA_POLYGON,
) -> bool:
    """Kiểm tra tọa độ có nằm trong đúng tứ giác hay không."""
    return point_in_polygon(
        float(location["lat"]),
        float(location["lng"]),
        polygon,
    )


def split_bounds(
    bounds: Tuple[float, float, float, float],
    chunks: int,
) -> List[Tuple[float, float, float, float]]:
    """Chia bounds thành lưới đều; 8 chunks sẽ thành lưới 2x4."""
    rows = max(1, int(chunks**0.5))
    while rows > 1 and chunks % rows != 0:
        rows -= 1
    columns = (chunks + rows - 1) // rows
    west, south, east, north = bounds
    longitude_step = (east - west) / columns
    latitude_step = (north - south) / rows
    result = []

    for row in range(rows):
        for column in range(columns):
            result.append(
                (
                    west + column * longitude_step,
                    south + row * latitude_step,
                    west + (column + 1) * longitude_step,
                    south + (row + 1) * latitude_step,
                )
            )
    return result


def collect_places(
    api_key: str,
    bounds: Tuple[float, float, float, float],
    step: float,
    radius_km: float,
    limit: int,
    delay: float,
    polygon: Tuple[Tuple[float, float], ...] = FOOD_AREA_POLYGON,
    chunks: int = 16,
    max_per_chunk: int = 10,
    max_detail_per_chunk: int = 40,
) -> List[Dict[str, Any]]:
    """Tìm tối đa max_per_chunk địa điểm trong mỗi ô và lọc theo polygon."""
    places: List[Dict[str, Any]] = []
    used_place_ids: Set[str] = set()
    checked_place_ids: Set[str] = set()
    area_chunks = split_bounds(bounds, chunks)

    for index, chunk in enumerate(area_chunks, start=1):
        chunk_west, chunk_south, chunk_east, chunk_north = chunk
        longitude = (chunk_west + chunk_east) / 2
        latitude = (chunk_south + chunk_north) / 2
        predictions: Dict[str, Dict[str, Any]] = {}
        for term in SEARCH_TERMS:
            response = request_json(
                GOONG_PLACES_URL,
                {
                    "api_key": api_key,
                    "input": term,
                    "location": f"{latitude},{longitude}",
                    "radius": radius_km,
                    "limit": limit,
                },
            )
            for prediction in response.get("predictions", []):
                place_id = prediction.get("place_id")
                if place_id:
                    predictions[place_id] = prediction
            time.sleep(delay)
        print(
            f"Đã quét chunk {index}/{len(area_chunks)}; "
            f"tìm thấy {len(predictions)} ID."
        )

        detail_count = 0
        detail_attempts = 0
        for prediction in predictions.values():
            if detail_count >= max_per_chunk:
                break
            if detail_attempts >= max_detail_per_chunk:
                break
            prediction_id = prediction["place_id"]
            if prediction_id in checked_place_ids:
                continue
            checked_place_ids.add(prediction_id)
            detail_attempts += 1
            details = request_json(
                GOONG_DETAILS_URL,
                {"api_key": api_key, "place_id": prediction_id},
            )
            result = details.get("result", {})
            location = result.get("geometry", {}).get("location")
            if location and in_search_area(location, polygon):
                place_id = result.get("place_id", prediction["place_id"])
                used_place_ids.add(place_id)
                places.append(
                    {
                        "id": place_id,
                        "name": result.get("name") or prediction.get("description"),
                        "address": result.get("formatted_address")
                        or prediction.get("description", ""),
                        "lat": float(location["lat"]),
                        "lng": float(location["lng"]),
                        "type": "food",
                        "source": "goong_places",
                    }
                )
                detail_count += 1
            time.sleep(delay)
        print(
            f"Chunk {index}: giữ {detail_count}/{max_per_chunk} quán, "
            f"đã kiểm tra {detail_attempts}/{max_detail_per_chunk} ID."
        )

    unique_places = {place["id"]: place for place in places}
    return sorted(unique_places.values(), key=lambda place: place["name"].lower())


def main() -> None:
    """Chạy chương trình thu thập và ghi dữ liệu ra JSON."""
    reconfigure_stdout = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure_stdout):
        reconfigure_stdout(encoding="utf-8")
    # Ưu tiên .env ở thư mục gốc; hỗ trợ thêm backend/.env để chạy thuận tiện.
    project_env = Path(__file__).resolve().parents[3] / ".env"
    backend_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(backend_env)
    load_dotenv(project_env, override=True)
    parser = argparse.ArgumentParser(
        description="Thu thập quán ăn trong bounds bằng Goong Places API."
    )
    parser.add_argument(
        "--bounds",
        type=parse_bounds,
        help="west,south,east,north; mặc định lấy theo node list.",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.004,
        help="Khoảng đệm theo độ khi tự tính bounds (mặc định: 0.004).",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.008,
        help="Khoảng cách điểm lưới theo độ (mặc định: 0.008).",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=1.0,
        help="Bán kính mỗi truy vấn, đơn vị km (mặc định: 1.0).",
    )
    parser.add_argument("--limit", type=int, default=20, help="Số kết quả mỗi truy vấn.")
    parser.add_argument("--delay", type=float, default=0.15, help="Độ trễ giữa các request.")
    parser.add_argument(
        "--chunks",
        type=int,
        default=8,
        help="Số ô chia vùng tìm kiếm (mặc định: 8 = lưới 2x4).",
    )
    parser.add_argument(
        "--max-per-chunk",
        type=int,
        default=10,
        help="Số quán tối đa lấy từ mỗi ô (mặc định: 10).",
    )
    parser.add_argument(
        "--max-detail-per-chunk",
        type=int,
        default=40,
        help="Số ID tối đa gọi Place Detail trong mỗi ô (mặc định: 40).",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    api_key = os.getenv("GOONG_REST_API_KEY")
    if not api_key:
        raise SystemExit("Thiếu GOONG_REST_API_KEY trong file .env.")
    if (
        args.step <= 0
        or args.radius <= 0
        or args.limit <= 0
        or args.chunks <= 0
        or args.max_per_chunk <= 0
        or args.max_detail_per_chunk <= 0
    ):
        raise SystemExit("Các thông số số lượng, step và radius phải lớn hơn 0.")

    bounds = args.bounds or polygon_bounds()
    places = collect_places(
        api_key,
        bounds,
        args.step,
        args.radius,
        args.limit,
        args.delay,
        FOOD_AREA_POLYGON,
        args.chunks,
        args.max_per_chunk,
        args.max_detail_per_chunk,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "polygon": FOOD_AREA_POLYGON,
                "bounds": bounds,
                "count": len(places),
                "places": places,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Đã ghi {len(places)} quán ăn vào {args.output}")


if __name__ == "__main__":
    main()
