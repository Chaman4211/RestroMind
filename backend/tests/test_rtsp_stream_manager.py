from threading import Event

from app.services.video import rtsp_stream_manager as rtsp_module
from app.services.video.rtsp_stream_manager import (
    RTSPStreamManager,
    RTSPWorker,
)


class FakeCapture:
    def __init__(self, opened=True):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return True, object()

    def release(self):
        self.released = True


class FakeDatabase:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_rtsp_worker_processes_frames_and_cleans_up(monkeypatch):
    capture = FakeCapture()
    database = FakeDatabase()
    cleanup = []
    worker = RTSPWorker(camera_source_id=90001)

    monkeypatch.setattr(
        rtsp_module.cv2,
        "VideoCapture",
        lambda *args: capture,
    )
    monkeypatch.setattr(
        rtsp_module,
        "SessionLocal",
        lambda: database,
    )

    def process_frame(**kwargs):
        worker.stop_event.set()

    monkeypatch.setattr(
        rtsp_module.vision_pipeline,
        "process_frame",
        process_frame,
    )
    monkeypatch.setattr(
        rtsp_module.vision_pipeline,
        "reset_tracker",
        lambda camera_id: cleanup.append(("tracker", camera_id)),
    )
    monkeypatch.setattr(
        rtsp_module.camera_sessions,
        "release",
        lambda camera_id: cleanup.append(("session", camera_id)),
    )

    manager = RTSPStreamManager(frame_interval=1)
    manager._run(worker, "rtsp://example.invalid/stream")

    assert worker.status == "STOPPED"
    assert worker.processed_frames == 1
    assert capture.released is True
    assert database.closed is True
    assert ("tracker", 90001) in cleanup
    assert ("session", 90001) in cleanup


def test_rtsp_worker_handles_connection_failure(monkeypatch):
    capture = FakeCapture(opened=False)
    cleanup = []
    worker = RTSPWorker(camera_source_id=90002)

    monkeypatch.setattr(
        rtsp_module.cv2,
        "VideoCapture",
        lambda *args: capture,
    )
    monkeypatch.setattr(
        rtsp_module,
        "SessionLocal",
        lambda: None,
    )
    monkeypatch.setattr(
        rtsp_module.vision_pipeline,
        "reset_tracker",
        lambda camera_id: cleanup.append(("tracker", camera_id)),
    )
    monkeypatch.setattr(
        rtsp_module.camera_sessions,
        "release",
        lambda camera_id: cleanup.append(("session", camera_id)),
    )

    manager = RTSPStreamManager()
    manager._run(worker, "rtsp://example.invalid/stream")

    assert worker.status == "ERROR"
    assert worker.error == "Could not connect to the RTSP camera."
    assert capture.released is True
    assert ("tracker", 90002) in cleanup
    assert ("session", 90002) in cleanup


def test_rtsp_worker_hides_processing_errors(monkeypatch):
    capture = FakeCapture()
    database = FakeDatabase()
    worker = RTSPWorker(camera_source_id=90003)

    monkeypatch.setattr(
        rtsp_module.cv2,
        "VideoCapture",
        lambda *args: capture,
    )
    monkeypatch.setattr(
        rtsp_module,
        "SessionLocal",
        lambda: database,
    )

    def fail_processing(**kwargs):
        raise RuntimeError(
            "Connection failed for rtsp://private:secret@example.invalid"
        )

    monkeypatch.setattr(
        rtsp_module.vision_pipeline,
        "process_frame",
        fail_processing,
    )
    monkeypatch.setattr(
        rtsp_module.vision_pipeline,
        "reset_tracker",
        lambda camera_id: None,
    )
    monkeypatch.setattr(
        rtsp_module.camera_sessions,
        "release",
        lambda camera_id: None,
    )

    manager = RTSPStreamManager(frame_interval=1)
    manager._run(worker, "rtsp://private:secret@example.invalid")

    assert worker.status == "ERROR"
    assert worker.error == (
        "An error occurred while processing the RTSP stream."
    )
    assert "private" not in worker.error
    assert "secret" not in worker.error
    assert capture.released is True
    assert database.closed is True
