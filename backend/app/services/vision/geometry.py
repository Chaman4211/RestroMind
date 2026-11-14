from collections.abc import Sequence

Point = tuple[float, float]
Polygon = Sequence[Point]


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """
    Return True when a point is inside a polygon.

    Uses the ray-casting algorithm.
    Coordinates can be normalized or pixel-based, but both
    the point and polygon must use the same coordinate system.
    """
    if len(polygon) < 3:
        raise ValueError("A polygon must contain at least three points")

    x, y = point
    inside = False

    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if (yi > y) != (yj > y):
            intersection_x = (
                (xj - xi) * (y - yi) / (yj - yi) + xi
            )

            if x < intersection_x:
                inside = not inside

        j = i

    return inside


def normalize_point(
    pixel_point: Point,
    frame_width: int,
    frame_height: int,
) -> Point:
    """
    Convert pixel coordinates into normalized 0–1 coordinates.
    """
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")

    x, y = pixel_point

    if not 0 <= x <= frame_width or not 0 <= y <= frame_height:
        raise ValueError("Pixel coordinates are outside the frame")

    return x / frame_width, y / frame_height


def normalize_polygon(
    polygon: Polygon,
    frame_width: int,
    frame_height: int,
) -> list[Point]:
    """
    Convert a polygon from pixel coordinates to normalized coordinates.
    """
    if len(polygon) < 3:
        raise ValueError("A polygon must contain at least three points")

    return [
        normalize_point(point, frame_width, frame_height)
        for point in polygon
    ]
