from uuid import uuid4

import numpy as np
import pytest

from app.db.session import SessionLocal
from app.models.camera_source import CameraSource
from app.models.restaurant_table import RestaurantTable
from app.services.vision.vision_pipeline import VisionPipeline


class FakeTracker:
    def __init__(self, people=None):
        self.people = people or []

    def update(self, frame, **kwargs):
        return self.people


class FakeTrackerFactory:
    def __init__(self, people=None):
        self.people = people or []
        self.created_trackers = []

    def __call__(self):
        tracker = FakeTracker(self.people)
        self.created_trackers.append(tracker)
        return tracker


class FakeOccupancyService:
    def __init__(self):
        self.calls = []

    def process_detection(self, db, table_id, occupied, timestamp=None):
        self.calls.append({
            "table_id": table_id,
            "occupied": occupied,
            "timestamp": timestamp,
        })

        return {
            "status": "OCCUPIED" if occupied else "FREE",
            "events": [],
        }



class SequenceTracker:
    def __init__(self, frames):
        self.frames = iter(frames)

    def update(self, frame, **kwargs):
        return next(self.frames)


class SequenceTrackerFactory:
    def __init__(self, frames):
        self.frames = frames

    def __call__(self):
        return SequenceTracker(self.frames)


def test_person_moving_between_tables_updates_both_occupancies():
    db = SessionLocal()
    camera_ids = []
    table_ids = []

    table_one_zone = [
        [0.05, 0.1],
        [0.45, 0.1],
        [0.45, 0.9],
        [0.05, 0.9],
    ]
    table_two_zone = [
        [0.55, 0.1],
        [0.95, 0.1],
        [0.95, 0.9],
        [0.55, 0.9],
    ]

    person_at_table_one = {
        "track_id": 7,
        "bbox": [15, 20, 25, 40],
        "confidence": 0.95,
    }
    person_at_table_two = {
        "track_id": 7,
        "bbox": [75, 20, 85, 40],
        "confidence": 0.95,
    }

    frames = [
        [person_at_table_one],
        [person_at_table_two],
    ]

    occupancy_service = FakeOccupancyService()
    pipeline = VisionPipeline(
        occupancy_service=occupancy_service,
        tracker_factory=SequenceTrackerFactory(frames),
    )

    try:
        camera = create_camera(
            db,
            f"test-transfer-{uuid4().hex[:8]}",
        )
        camera_ids.append(camera.id)

        table_one = create_table(db, camera.id, table_one_zone)
        table_ids.append(table_one.id)

        table_two = create_table(db, camera.id, table_two_zone)
        table_ids.append(table_two.id)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        first_result = pipeline.process_frame(db, camera.id, frame)
        second_result = pipeline.process_frame(db, camera.id, frame)

        assert first_result["assignments"][table_one.id] == [7]
        assert first_result["assignments"][table_two.id] == []

        assert second_result["assignments"][table_one.id] == []
        assert second_result["assignments"][table_two.id] == [7]

        assert occupancy_service.calls[0]["occupied"] is True
        assert occupancy_service.calls[1]["occupied"] is False
        assert occupancy_service.calls[2]["occupied"] is False
        assert occupancy_service.calls[3]["occupied"] is True

    finally:
        cleanup_records(db, table_ids, camera_ids)
        db.close()


def create_camera(db, name, is_active=True, source_type="LIVE"):
    camera = CameraSource(
        name=name,
        source_type=source_type,
        is_active=is_active,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


def create_table(db, camera_id, zone_coordinates):
    table = RestaurantTable(
        table_number=f"TEST-{uuid4().hex[:8]}",
        name="Vision Pipeline Test",
        camera_source_id=camera_id,
        zone_coordinates=zone_coordinates,
        upload_zone_coordinates=zone_coordinates,
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def cleanup_records(db, table_ids, camera_ids):
    for table_id in table_ids:
        table = db.get(RestaurantTable, table_id)
        if table is not None:
            db.delete(table)

    db.commit()

    for camera_id in camera_ids:
        camera = db.get(CameraSource, camera_id)
        if camera is not None:
            db.delete(camera)

    db.commit()


def test_pipeline_matches_people_to_table_zones():
    db = SessionLocal()
    camera_ids = []
    table_ids = []

    people = [
        {
            "track_id": 1,
            "bbox": [40, 20, 60, 60],
            "confidence": 0.95,
        },
        {
            "track_id": 2,
            "bbox": [0, 0, 10, 10],
            "confidence": 0.90,
        },
    ]

    factory = FakeTrackerFactory(people)
    occupancy_service = FakeOccupancyService()

    pipeline = VisionPipeline(
        occupancy_service=occupancy_service,
        tracker_factory=factory,
    )

    try:
        camera = create_camera(
            db,
            f"test-pipeline-{uuid4().hex[:8]}",
        )
        camera_ids.append(camera.id)

        table = create_table(
            db,
            camera.id,
            [
                [0.2, 0.2],
                [0.8, 0.2],
                [0.8, 0.8],
                [0.2, 0.8],
            ],
        )
        table_ids.append(table.id)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        result = pipeline.process_frame(
            db,
            camera.id,
            frame,
        )

        assert result["camera_source_id"] == camera.id
        assert result["people_detected"] == 2
        assert result["table_count"] == 1
        assert result["assignments"][table.id] == [1]

        assert result["tables"][0]["table_id"] == table.id
        assert result["tables"][0]["occupied"] is True
        assert result["tables"][0]["person_count"] == 1
        assert result["tables"][0]["track_ids"] == [1]

        assert occupancy_service.calls[0]["table_id"] == table.id
        assert occupancy_service.calls[0]["occupied"] is True

    finally:
        cleanup_records(db, table_ids, camera_ids)
        db.close()



def test_new_track_id_keeps_table_occupied_after_temporary_detection_loss():
    db = SessionLocal()
    camera_ids = []
    table_ids = []

    frames = [
        [{
            "track_id": 7,
            "bbox": [40, 20, 60, 60],
            "confidence": 0.95,
        }],
        [],
        [{
            "track_id": 19,
            "bbox": [40, 20, 60, 60],
            "confidence": 0.92,
        }],
    ]

    occupancy_service = FakeOccupancyService()
    pipeline = VisionPipeline(
        occupancy_service=occupancy_service,
        tracker_factory=SequenceTrackerFactory(frames),
    )

    try:
        camera = create_camera(
            db,
            f"test-track-change-{uuid4().hex[:8]}",
        )
        camera_ids.append(camera.id)

        table = create_table(
            db,
            camera.id,
            [
                [0.2, 0.2],
                [0.8, 0.2],
                [0.8, 0.8],
                [0.2, 0.8],
            ],
        )
        table_ids.append(table.id)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        first = pipeline.process_frame(db, camera.id, frame)
        missing = pipeline.process_frame(db, camera.id, frame)
        returned = pipeline.process_frame(db, camera.id, frame)

        assert first["tables"][0]["occupied"] is True
        assert missing["tables"][0]["occupied"] is False
        assert returned["tables"][0]["occupied"] is True
        assert returned["assignments"][table.id] == [19]

        assert [call["occupied"] for call in occupancy_service.calls] == [
            True,
            False,
            True,
        ]

    finally:
        cleanup_records(db, table_ids, camera_ids)
        db.close()


def test_pipeline_creates_separate_trackers_for_each_camera():
    db = SessionLocal()
    camera_ids = []
    table_ids = []

    factory = FakeTrackerFactory()
    occupancy_service = FakeOccupancyService()

    pipeline = VisionPipeline(
        occupancy_service=occupancy_service,
        tracker_factory=factory,
    )

    try:
        camera_one = create_camera(
            db,
            f"test-camera-one-{uuid4().hex[:8]}",
        )
        camera_ids.append(camera_one.id)

        camera_two = create_camera(
            db,
            f"test-camera-two-{uuid4().hex[:8]}",
        )
        camera_ids.append(camera_two.id)

        zone = [
            [0.2, 0.2],
            [0.8, 0.2],
            [0.8, 0.8],
            [0.2, 0.8],
        ]

        table_one = create_table(db, camera_one.id, zone)
        table_ids.append(table_one.id)

        table_two = create_table(db, camera_two.id, zone)
        table_ids.append(table_two.id)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        pipeline.process_frame(db, camera_one.id, frame)
        pipeline.process_frame(db, camera_two.id, frame)

        assert len(factory.created_trackers) == 2
        assert factory.created_trackers[0] is not factory.created_trackers[1]

        assert camera_one.id in pipeline.trackers
        assert camera_two.id in pipeline.trackers

    finally:
        cleanup_records(db, table_ids, camera_ids)
        db.close()


def test_pipeline_rejects_missing_camera():
    db = SessionLocal()
    pipeline = VisionPipeline(
        occupancy_service=FakeOccupancyService(),
        tracker_factory=FakeTrackerFactory(),
    )

    try:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        with pytest.raises(ValueError, match="Camera source not found"):
            pipeline.process_frame(db, 999999999, frame)

    finally:
        db.close()


def test_pipeline_rejects_inactive_camera():
    db = SessionLocal()
    camera_ids = []

    pipeline = VisionPipeline(
        occupancy_service=FakeOccupancyService(),
        tracker_factory=FakeTrackerFactory(),
    )

    try:
        camera = create_camera(
            db,
            f"test-inactive-{uuid4().hex[:8]}",
            is_active=False,
        )
        camera_ids.append(camera.id)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        with pytest.raises(ValueError, match="Camera source is inactive"):
            pipeline.process_frame(db, camera.id, frame)

    finally:
        cleanup_records(db, [], camera_ids)
        db.close()


def test_pipeline_rejects_invalid_frame():
    db = SessionLocal()
    pipeline = VisionPipeline(
        occupancy_service=FakeOccupancyService(),
        tracker_factory=FakeTrackerFactory(),
    )

    try:
        with pytest.raises(ValueError, match="A valid video frame is required"):
            pipeline.process_frame(db, 1, None)

    finally:
        db.close()


def test_upload_pipeline_uses_upload_zones_and_matches_seated_people():
    db = SessionLocal()
    camera_ids = []
    table_ids = []

    occupancy_service = FakeOccupancyService()

    seated_person = {
        "track_id": 44,
        # Feet are below the upload zone; the person's body overlaps it.
        "bbox": [40, 20, 60, 90],
        "confidence": 0.90,
    }

    pipeline = VisionPipeline(
        occupancy_service=occupancy_service,
        tracker_factory=FakeTrackerFactory([seated_person]),
    )

    try:
        camera = create_camera(
            db,
            f"test-upload-zones-{uuid4().hex[:8]}",
            source_type="UPLOAD",
        )
        camera_ids.append(camera.id)

        table = RestaurantTable(
            table_number=f"TEST-{uuid4().hex[:8]}",
            name="Upload Zone Test",
            camera_source_id=None,
            upload_camera_source_id=camera.id,
            zone_coordinates=[
                [0.05, 0.05],
                [0.25, 0.05],
                [0.25, 0.25],
                [0.05, 0.25],
            ],
            upload_zone_coordinates=[
                [0.30, 0.20],
                [0.70, 0.20],
                [0.70, 0.65],
                [0.30, 0.65],
            ],
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_ids.append(table.id)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        result = pipeline.process_frame(db, camera.id, frame)

        assert result["table_count"] == 1
        assert result["people_detected"] == 1
        assert result["assignments"][table.id] == [44]
        assert result["tables"][0]["occupied"] is True
        assert result["tables"][0]["person_count"] == 1

    finally:
        cleanup_records(db, table_ids, camera_ids)
        db.close()
