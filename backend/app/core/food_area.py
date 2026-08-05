"""Hình học vùng tìm kiếm quán ăn."""

from typing import Iterable, List, Sequence, Tuple


# Thứ tự dữ liệu đầu vào: (lat, lng), đi theo chu vi tứ giác.
FOOD_AREA_POLYGON: Tuple[Tuple[float, float], ...] = (
    (10.79185, 106.69584),
    (10.78495, 106.68911),
    (10.77959, 106.69498),
    (10.78659, 106.70156),
)


def point_in_polygon(
    latitude: float,
    longitude: float,
    polygon: Sequence[Tuple[float, float]] = FOOD_AREA_POLYGON,
) -> bool:
    """Kiểm tra điểm có nằm trong đa giác bằng thuật toán ray casting."""
    inside = False
    point_count = len(polygon)
    previous_index = point_count - 1

    for current_index in range(point_count):
        current_lat, current_lng = polygon[current_index]
        previous_lat, previous_lng = polygon[previous_index]
        crosses_latitude = (current_lat > latitude) != (previous_lat > latitude)

        if crosses_latitude:
            intersection_lng = (
                (previous_lng - current_lng)
                * (latitude - current_lat)
                / (previous_lat - current_lat)
                + current_lng
            )
            if longitude < intersection_lng:
                inside = not inside
        previous_index = current_index

    return inside


def polygon_bounds(
    polygon: Iterable[Tuple[float, float]] = FOOD_AREA_POLYGON,
) -> Tuple[float, float, float, float]:
    """Trả về bounds bao ngoài theo dạng west,south,east,north."""
    points = list(polygon)
    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)
