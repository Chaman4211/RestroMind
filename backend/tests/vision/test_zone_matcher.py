import pytest

from app.services.occupancy.zone_matcher import (
    get_person_footpoint,
    get_table_polygon,
    match_people_to_tables,
)


def test_person_footpoint():
    bbox = [100, 100, 200, 300]

    assert get_person_footpoint(bbox) == (150, 300)


def test_invalid_bounding_box():
    with pytest.raises(ValueError):
        get_person_footpoint([100, 100, 200])


def test_invalid_bounding_box_order():
    with pytest.raises(ValueError):
        get_person_footpoint([200, 100, 100, 300])


def test_table_polygon_from_list():
    polygon = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]

    assert len(get_table_polygon(polygon)) == 4


def test_table_polygon_from_dictionary():
    zone = {
        "points": [
            [0.1, 0.1],
            [0.5, 0.1],
            [0.5, 0.5],
        ]
    }

    assert len(get_table_polygon(zone)) == 3


def test_invalid_table_polygon():
    with pytest.raises(ValueError):
        get_table_polygon([[0.1, 0.1], [0.5, 0.5]])


def test_polygon_requires_normalized_coordinates():
    with pytest.raises(ValueError):
        get_table_polygon([[10, 10], [20, 10], [20, 20]])


def test_person_assigned_to_table():
    people = [
        {"track_id": 1, "bbox": [400, 200, 600, 900]},
        {"track_id": 2, "bbox": [800, 200, 900, 500]},
    ]

    tables = [
        {
            "id": 10,
            "zone_coordinates": {
                "points": [
                    [0.4, 0.7],
                    [0.6, 0.7],
                    [0.6, 0.95],
                    [0.4, 0.95],
                ]
            },
        }
    ]

    result = match_people_to_tables(
        people,
        tables,
        frame_width=1000,
        frame_height=1000,
    )

    assert result == {10: [1]}


def test_tables_without_zones_are_ignored():
    tables = [{"id": 10, "zone_coordinates": None}]

    result = match_people_to_tables(
        [],
        tables,
        frame_width=1000,
        frame_height=1000,
    )

    assert result == {}


def test_invalid_frame_dimensions():
    with pytest.raises(ValueError):
        match_people_to_tables(
            [{"track_id": 1, "bbox": [10, 10, 20, 20]}],
            [],
            frame_width=0,
            frame_height=100,
        )
