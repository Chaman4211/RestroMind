from app.services.vision.geometry import (
    normalize_point,
    point_in_polygon,
)


def get_person_footpoint(bbox):
    """
    Calculate the bottom-center point of a person bounding box.

    bbox format: [x1, y1, x2, y2]
    """
    if len(bbox) != 4:
        raise ValueError("Bounding box must contain four coordinates")

    x1, y1, x2, y2 = bbox

    if x2 < x1 or y2 < y1:
        raise ValueError("Invalid bounding box coordinates")

    return (x1 + x2) / 2, y2


def get_table_polygon(zone_coordinates):
    """
    Support both stored zone formats:
    - [[x, y], [x, y], [x, y]]
    - {"points": [[x, y], [x, y], [x, y]]}
    """
    if isinstance(zone_coordinates, dict):
        polygon = zone_coordinates.get("points")
    else:
        polygon = zone_coordinates

    if not isinstance(polygon, list) or len(polygon) < 3:
        raise ValueError("Table zone must contain at least three points")

    points = []

    for point in polygon:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("Each polygon point must contain x and y")

        x, y = point

        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise TypeError("Polygon coordinates must be numeric")

        if not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("Table zone coordinates must be normalized")

        points.append((float(x), float(y)))

    return points


def match_people_to_tables(people, tables, frame_width, frame_height):
    """
    Assign tracked people to configured table zones.

    people:
        List of tracked people containing track_id and bbox.

    tables:
        List of tables containing id and zone_coordinates.

    Returns:
        Dictionary mapping table IDs to lists of person track IDs.
    """
    assignments = {
        table["id"]: []
        for table in tables
        if table.get("zone_coordinates") is not None
    }

    table_polygons = {
        table["id"]: get_table_polygon(table["zone_coordinates"])
        for table in tables
        if table.get("zone_coordinates") is not None
    }

    for person in people:
        footpoint = get_person_footpoint(person["bbox"])

        normalized_point = normalize_point(
            footpoint,
            frame_width,
            frame_height,
        )

        matching_tables = [
            table_id
            for table_id, polygon in table_polygons.items()
            if point_in_polygon(normalized_point, polygon)
        ]

        if matching_tables:
            assignments[matching_tables[0]].append(person["track_id"])

    return assignments
