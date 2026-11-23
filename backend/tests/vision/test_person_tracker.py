from types import SimpleNamespace

import numpy as np

from app.services.vision.person_tracker import PersonTracker


class FakeBox:
    def __init__(self, x1=10, y1=20, x2=50, y2=100):
        self.xyxy = [np.array([x1, y1, x2, y2])]
        self.conf = [0.91]


class FakeBoxes(list):
    def __init__(self, boxes, ids=None):
        super().__init__(boxes)
        self.id = ids


class FakeModel:
    def __init__(self, boxes):
        self.boxes = boxes

    def track(self, **kwargs):
        return [SimpleNamespace(boxes=self.boxes)]


def make_tracker(boxes):
    tracker = PersonTracker.__new__(PersonTracker)
    tracker.model = FakeModel(boxes)
    return tracker


def test_tracker_keeps_detections_when_tracking_ids_are_missing():
    boxes = FakeBoxes(
        [
            FakeBox(10, 20, 50, 100),
            FakeBox(60, 25, 100, 110),
        ]
    )

    people = make_tracker(boxes).update(np.zeros((120, 120, 3)))

    assert len(people) == 2
    assert [person["track_id"] for person in people] == [-1, -2]
    assert people[0]["bbox"] == [10.0, 20.0, 50.0, 100.0]
    assert people[0]["confidence"] == 0.91


def test_tracker_preserves_real_tracking_ids():
    boxes = FakeBoxes(
        [FakeBox()],
        ids=np.array([27]),
    )

    people = make_tracker(boxes).update(np.zeros((120, 120, 3)))

    assert len(people) == 1
    assert people[0]["track_id"] == 27
