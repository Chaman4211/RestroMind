from uuid import uuid4

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.v1 import camera_stream
from app.db.session import SessionLocal
from app.main import app
from app.models.camera_source import CameraSource

client = TestClient(app)


def create_camera(source_type="LIVE", is_active=True):
    with SessionLocal() as db:
        camera = CameraSource(
            name=f"stream-test-{uuid4().hex[:8]}",
            source_type=source_type,
            is_active=is_active,
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
        return camera.id


def delete_camera(camera_id):
    with SessionLocal() as db:
        camera = db.get(CameraSource, camera_id)
        if camera is not None:
            db.delete(camera)
            db.commit()


def create_jpeg_frame():
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", frame)
    assert success
    return encoded.tobytes()


def test_live_stream_processes_valid_frame_and_cleans_up(monkeypatch):
    camera_id = create_camera()
    processed_frames = []
    reset_cameras = []

    def fake_process(camera_source_id, frame):
        processed_frames.append((camera_source_id, frame.shape))
        return {
            "camera_source_id": camera_source_id,
            "people_detected": 0,
            "table_count": 0,
            "tables": [],
        }

    monkeypatch.setattr(
        camera_stream,
        "process_camera_frame",
        fake_process,
    )
    monkeypatch.setattr(
        camera_stream.vision_pipeline,
        "reset_tracker",
        lambda camera_source_id: reset_cameras.append(camera_source_id),
    )

    try:
        with client.websocket_connect(
            f"/api/v1/camera-sources/{camera_id}/stream"
        ) as websocket:
            connected = websocket.receive_json()
            assert connected["type"] == "connected"
            assert connected["camera_source_id"] == camera_id

            websocket.send_bytes(create_jpeg_frame())
            response = websocket.receive_json()

            assert response["type"] == "frame_processed"
            assert response["result"]["camera_source_id"] == camera_id
            assert response["result"]["people_detected"] == 0

        assert len(processed_frames) == 1
        assert processed_frames[0][0] == camera_id
        assert processed_frames[0][1] == (32, 32, 3)
        assert reset_cameras == [camera_id]
        assert not camera_stream.camera_sessions.is_active(camera_id)

    finally:
        camera_stream.camera_sessions.release(camera_id)
        delete_camera(camera_id)


def test_live_stream_rejects_invalid_jpeg_frame(monkeypatch):
    camera_id = create_camera()

    monkeypatch.setattr(
        camera_stream,
        "process_camera_frame",
        lambda camera_source_id, frame: pytest.fail(
            "Invalid JPEG must not reach frame processing"
        ),
    )

    try:
        with client.websocket_connect(
            f"/api/v1/camera-sources/{camera_id}/stream"
        ) as websocket:
            websocket.receive_json()
            websocket.send_bytes(b"not-a-jpeg")

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert response["message"] == "Invalid JPEG frame"

    finally:
        camera_stream.camera_sessions.release(camera_id)
        delete_camera(camera_id)


def test_live_stream_rejects_oversized_frame(monkeypatch):
    camera_id = create_camera()

    monkeypatch.setattr(
        camera_stream,
        "MAX_FRAME_SIZE_BYTES",
        10,
    )
    monkeypatch.setattr(
        camera_stream,
        "process_camera_frame",
        lambda camera_source_id, frame: pytest.fail(
            "Oversized frame must not reach processing"
        ),
    )

    try:
        with client.websocket_connect(
            f"/api/v1/camera-sources/{camera_id}/stream"
        ) as websocket:
            websocket.receive_json()
            websocket.send_bytes(b"x" * 11)

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert response["message"] == "Frame exceeds the 2 MB limit"

    finally:
        camera_stream.camera_sessions.release(camera_id)
        delete_camera(camera_id)


@pytest.mark.parametrize(
    ("source_type", "is_active", "expected_reason"),
    [
        ("UPLOAD", True, "This camera source does not support live streaming"),
        ("LIVE", False, "Camera source is inactive"),
    ],
)
def test_live_stream_rejects_unsupported_camera(
    source_type,
    is_active,
    expected_reason,
):
    camera_id = create_camera(
        source_type=source_type,
        is_active=is_active,
    )

    try:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f"/api/v1/camera-sources/{camera_id}/stream"):
                pass

        assert error.value.code == 1008

    finally:
        delete_camera(camera_id)


def test_live_stream_rejects_missing_camera():
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/v1/camera-sources/999999999/stream"):
            pass

    assert error.value.code == 1008


def test_live_stream_rejects_second_session_for_same_camera(monkeypatch):
    camera_id = create_camera()

    monkeypatch.setattr(
        camera_stream,
        "process_camera_frame",
        lambda camera_source_id, frame: {},
    )

    try:
        with client.websocket_connect(
            f"/api/v1/camera-sources/{camera_id}/stream"
        ) as first_websocket:
            first_websocket.receive_json()

            with pytest.raises(WebSocketDisconnect) as error:
                with client.websocket_connect(
                    f"/api/v1/camera-sources/{camera_id}/stream"
                ):
                    pass

            assert error.value.code == 1008
            assert camera_stream.camera_sessions.is_active(camera_id)

        assert not camera_stream.camera_sessions.is_active(camera_id)

    finally:
        camera_stream.camera_sessions.release(camera_id)
        delete_camera(camera_id)
