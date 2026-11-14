import pytest

from app.services.vision.geometry import (
    normalize_point,
    normalize_polygon,
    point_in_polygon,
)

SQUARE = [
    (0.1, 0.1),
    (0.5, 0.1),
    (0.5, 0.5),
    (0.1, 0.5),
]


def test_point_inside_polygon():
    assert point_in_polygon((0.3, 0.3), SQUARE) is True


def test_point_outside_polygon():
    assert point_in_polygon((0.8, 0.8), SQUARE) is False


def test_point_outside_near_polygon():
    assert point_in_polygon((0.05, 0.3), SQUARE) is False


def test_polygon_requires_three_points():
    with pytest.raises(ValueError):
        point_in_polygon((0.3, 0.3), [(0, 0), (1, 1)])


def test_normalize_pixel_point():
    result = normalize_point((640, 360), 1280, 720)
    assert result == (0.5, 0.5)


def test_normalize_polygon():
    polygon = [
        (128, 72),
        (640, 72),
        (640, 360),
        (128, 360),
    ]

    result = normalize_polygon(polygon, 1280, 720)

    assert result == SQUARE


def test_invalid_frame_dimensions():
    with pytest.raises(ValueError):
        normalize_point((10, 10), 0, 720)


def test_pixel_point_outside_frame():
    with pytest.raises(ValueError):
        normalize_point((1300, 100), 1280, 720)
