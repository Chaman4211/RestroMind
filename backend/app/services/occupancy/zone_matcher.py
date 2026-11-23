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
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")

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
        table["id"]: [] for table in tables if table.get("zone_coordinates") is not None
    }

    table_polygons = {
        table["id"]: get_table_polygon(table["zone_coordinates"])
        for table in tables
        if table.get("zone_coordinates") is not None
    }

    for person in people:
        x1, y1, x2, y2 = person["bbox"]
        center_x = (x1 + x2) / 2
        box_height = y2 - y1

        # Seated customers may have their feet outside the table zone.
        # Check the feet, lower body, and centre of the detected person.
        sample_points = [
            (center_x, y2),
            (center_x, y1 + box_height * 0.75),
            (center_x, y1 + box_height * 0.50),
        ]

        table_scores = {}

        for table_id, polygon in table_polygons.items():
            score = 0

            for point in sample_points:
                normalized_point = normalize_point(
                    point,
                    frame_width,
                    frame_height,
                )

                if point_in_polygon(normalized_point, polygon):
                    score += 1

            if score:
                table_scores[table_id] = score

        if table_scores:
            best_table_id = max(
                table_scores,
                key=table_scores.get,
            )
            assignments[best_table_id].append(person["track_id"])

    return assignments
