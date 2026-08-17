"""Goong Places collector with chunking, retries, polygon filtering, and checkpoints."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from ..core.food_area import FOOD_AREA_POLYGON, point_in_polygon, polygon_bounds
from ..repositories.graph_data import NODES


GOONG_PLACES_URL = "https://rsapi.goong.io/Place/AutoComplete"
GOONG_DETAILS_URL = "https://rsapi.goong.io/Place/Detail"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_OUTPUT = DATA_DIR / "food_places.json"
SEARCH_TERMS_PATH = DATA_DIR / "food_search_terms.json"
DEFAULT_SEARCH_TERMS = (
    "restaurant",
    "food",
    "coffee",
    "cafe",
    "juice",
    "tea",
    "milk tea",
    "bakery",
    "cake",
    "dessert",
)


def load_search_terms(path: Path = SEARCH_TERMS_PATH) -> Tuple[str, ...]:
    """Load and deduplicate localized search terms from a UTF-8 JSON array."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SEARCH_TERMS
    if not isinstance(payload, list):
        return DEFAULT_SEARCH_TERMS
    terms = tuple(
        dict.fromkeys(
            term.strip() for term in payload if isinstance(term, str) and term.strip()
        )
    )
    return terms or DEFAULT_SEARCH_TERMS


SEARCH_TERMS = load_search_terms()


def parse_bounds(value: str) -> Tuple[float, float, float, float]:
    """Parse west,south,east,north into validated rectangular bounds."""
    try:
        west, south, east, north = (float(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Bounds must use west,south,east,north format."
        ) from error

    if west >= east or south >= north:
        raise argparse.ArgumentTypeError("Bounds must define a valid rectangle.")
    return west, south, east, north


def graph_bounds(padding: float) -> Tuple[float, float, float, float]:
    """Return graph bounds expanded by coordinate padding."""
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
    """Yield search centers that fall inside the configured polygon."""
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
    """Call a Goong endpoint with retry handling for throttling and network errors."""
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
            print(f"Goong rate limit reached (429); waiting {wait_seconds:g}s...")
            time.sleep(wait_seconds)
        except URLError as error:
            if attempt == 4:
                raise
            wait_seconds = 2**attempt
            print(
                f"Network error while calling Goong ({error.reason}); "
                f"retrying in {wait_seconds:g}s..."
            )
            time.sleep(wait_seconds)

    if payload is None:
        raise RuntimeError("Goong API returned no payload after all retries.")
    if payload.get("status") not in (None, "OK"):
        raise RuntimeError(
            f"Goong API returned status={payload.get('status')}: {payload}"
        )
    return payload


def in_search_area(
    location: Dict[str, Any],
    polygon: Tuple[Tuple[float, float], ...] = FOOD_AREA_POLYGON,
) -> bool:
    """Return whether a Goong location lies inside the search polygon."""
    return point_in_polygon(
        float(location["lat"]),
        float(location["lng"]),
        polygon,
    )


def split_bounds(
    bounds: Tuple[float, float, float, float],
    chunks: int,
) -> List[Tuple[float, float, float, float]]:
    """Split bounds into an evenly sized chunk grid."""
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


def write_checkpoint(
    output_path: Path,
    bounds: Tuple[float, float, float, float],
    places: List[Dict[str, Any]],
    completed_chunks: Set[int],
    chunks: int,
    complete: bool,
) -> None:
    """Atomically persist collector progress after a chunk completes."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "polygon": FOOD_AREA_POLYGON,
        "bounds": bounds,
        "chunks": chunks,
        "completed_chunks": sorted(completed_chunks),
        "complete": complete,
        "count": len(places),
        "places": sorted(places, key=lambda place: place["name"].lower()),
    }
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)


def collect_places(
    api_key: str,
    bounds: Tuple[float, float, float, float],
    step: float,
    radius_km: float,
    limit: int,
    delay: float,
    polygon: Tuple[Tuple[float, float], ...] = FOOD_AREA_POLYGON,
    chunks: int = 8,
    max_per_chunk: int = 10,
    max_detail_per_chunk: int = 40,
    output_path: Optional[Path] = None,
    resume: bool = True,
) -> List[Dict[str, Any]]:
    """Collect, filter, deduplicate, and checkpoint places by search chunk."""
    places: List[Dict[str, Any]] = []
    used_place_ids: Set[str] = set()
    checked_place_ids: Set[str] = set()
    area_chunks = split_bounds(bounds, chunks)
    completed_chunks: Set[int] = set()

    if resume and output_path and output_path.exists():
        try:
            previous = json.loads(output_path.read_text(encoding="utf-8"))
            if previous.get("chunks") == chunks and previous.get("bounds") == list(
                bounds
            ):
                places = previous.get("places", [])
                used_place_ids = {place["id"] for place in places}
                completed_chunks = set(previous.get("completed_chunks", []))
                print(
                    f"Resuming from checkpoint; completed chunks: {sorted(completed_chunks)}."
                )
        except (OSError, json.JSONDecodeError, KeyError):
            print("Checkpoint is invalid; restarting from the first chunk.")

    for index, chunk in enumerate(area_chunks, start=1):
        if index in completed_chunks:
            continue
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
            f"Scanned chunk {index}/{len(area_chunks)}; "
            f"found {len(predictions)} IDs."
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
                if place_id in used_place_ids:
                    time.sleep(delay)
                    continue
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
            f"Chunk {index}: retained {detail_count}/{max_per_chunk} places; "
            f"checked {detail_attempts}/{max_detail_per_chunk} IDs."
        )
        completed_chunks.add(index)
        if output_path:
            write_checkpoint(
                output_path,
                bounds,
                places,
                completed_chunks,
                chunks,
                complete=len(completed_chunks) == len(area_chunks),
            )

    unique_places = {place["id"]: place for place in places}
    return sorted(unique_places.values(), key=lambda place: place["name"].lower())


def main() -> None:
    """Parse command-line options and run the Goong Places collector."""
    reconfigure_stdout = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure_stdout):
        reconfigure_stdout(encoding="utf-8")

    project_env = Path(__file__).resolve().parents[3] / ".env"
    backend_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(backend_env)
    load_dotenv(project_env, override=True)
    parser = argparse.ArgumentParser(
        description="Collect food places within bounds using the Goong Places API."
    )
    parser.add_argument(
        "--bounds",
        type=parse_bounds,
        help="west,south,east,north; defaults to the configured polygon bounds.",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.004,
        help="Coordinate padding when deriving bounds (default: 0.004).",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.008,
        help="Grid spacing in degrees (default: 0.008).",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=1.0,
        help="Search radius in kilometers (default: 1.0).",
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Results requested per query."
    )
    parser.add_argument(
        "--delay", type=float, default=0.15, help="Delay between requests."
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=8,
        help="Number of search chunks (default: 8, arranged as a 2x4 grid).",
    )
    parser.add_argument(
        "--max-per-chunk",
        type=int,
        default=10,
        help="Maximum places retained per chunk (default: 10).",
    )
    parser.add_argument(
        "--max-detail-per-chunk",
        type=int,
        default=40,
        help="Maximum Place Detail requests per chunk (default: 40).",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore the checkpoint and scan from the beginning.",
    )
    args = parser.parse_args()

    api_key = os.getenv("GOONG_REST_API_KEY")
    if not api_key:
        raise SystemExit("GOONG_REST_API_KEY is missing from the .env file.")
    if (
        args.step <= 0
        or args.radius <= 0
        or args.limit <= 0
        or args.chunks <= 0
        or args.max_per_chunk <= 0
        or args.max_detail_per_chunk <= 0
    ):
        raise SystemExit("Count, step, and radius arguments must be greater than zero.")

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
        args.output,
        not args.no_resume,
    )
    print(f"Wrote {len(places)} food places to {args.output}")


if __name__ == "__main__":
    main()
