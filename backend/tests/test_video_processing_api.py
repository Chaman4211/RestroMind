from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import video_processing
from app.db.session import SessionLocal
from app.main import app
from app.models.camera_source import CameraSource

client = TestClient(app)


def create_camera(source_type="UPLOAD", is_active=True):
    db = SessionLocal()
    try:
        camera = CameraSource(
            name=f"video-api-{uuid4().hex[:8]}",
            source_type=source_type,
            is_active=is_active,
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
        return camera.id
    finally:
        db.close()


def delete_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.get(CameraSource, camera_id)
        if camera is not None:
            db.delete(camera)
            db.commit()
    finally:
        db.close()


def test_video_upload_success(monkeypatch):
    camera_id = create_camera()
    processed_path = None

    def fake_process_video(db, camera_source_id, video_path):
        nonlocal processed_path
        processed_path = Path(video_path)

        assert processed_path.is_file()
        assert processed_path.read_bytes() == b"fake-video-content"
        assert camera_source_id == camera_id

        return {
            "camera_source_id": camera_source_id,
            "total_frames": 10,
            "processed_frames": 2,
            "frame_interval": 5,
            "fps": 10.0,
            "duration_seconds": 1.0,
            "max_people_detected": 2,
            "tables": [],
        }

    processor = Mock()
    processor.process_video.side_effect = fake_process_video
    monkeypatch.setattr(video_processing, "video_processor", processor)

    try:
        response = client.post(
            f"/api/v1/camera-sources/{camera_id}/process-video",
            files={"file": ("sample.mp4", b"fake-video-content", "video/mp4")},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Video processed successfully"
        assert response.json()["file_name"] == "sample.mp4"
        assert response.json()["processed_frames"] == 2
        processor.process_video.assert_called_once()
        assert processed_path is not None
        assert not processed_path.exists()
    finally:
        delete_camera(camera_id)


def test_video_upload_rejects_unsupported_extension():
    camera_id = create_camera()

    try:
        response = client.post(
            f"/api/v1/camera-sources/{camera_id}/process-video",
            files={"file": ("sample.txt", b"not a video", "text/plain")},
        )

        assert response.status_code == 415
        assert response.json()["detail"] == "Unsupported video format"
    finally:
        delete_camera(camera_id)


def test_video_upload_rejects_empty_file():
    camera_id = create_camera()

    try:
        response = client.post(
            f"/api/v1/camera-sources/{camera_id}/process-video",
            files={"file": ("sample.mp4", b"", "video/mp4")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Uploaded video is empty"
    finally:
        delete_camera(camera_id)


def test_video_upload_rejects_file_over_size_limit(monkeypatch):
    camera_id = create_camera()
    monkeypatch.setattr(video_processing, "MAX_VIDEO_SIZE_BYTES", 3)

    try:
        response = client.post(
            f"/api/v1/camera-sources/{camera_id}/process-video",
            files={"file": ("sample.mp4", b"1234", "video/mp4")},
        )

        assert response.status_code == 413
        assert response.json()["detail"] == (
            "Video exceeds the 100 MB upload limit"
        )
    finally:
        delete_camera(camera_id)


def test_video_upload_rejects_inactive_camera():
    camera_id = create_camera(is_active=False)

    try:
        response = client.post(
            f"/api/v1/camera-sources/{camera_id}/process-video",
            files={"file": ("sample.mp4", b"video", "video/mp4")},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Camera source is inactive"
    finally:
        delete_camera(camera_id)


def test_video_upload_rejects_non_upload_camera():
    camera_id = create_camera(source_type="LIVE")

    try:
        response = client.post(
            f"/api/v1/camera-sources/{camera_id}/process-video",
            files={"file": ("sample.mp4", b"video", "video/mp4")},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "This camera source does not support video uploads"
        )
    finally:
        delete_camera(camera_id)


def test_video_upload_returns_404_for_missing_camera():
    response = client.post(
        "/api/v1/camera-sources/999999999/process-video",
        files={"file": ("sample.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Camera source not found"
