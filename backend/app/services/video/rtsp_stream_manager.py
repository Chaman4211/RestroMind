from dataclasses import dataclass, field
from threading import Event, Lock, Thread

import cv2

OPEN_TIMEOUT_MS = 5000
READ_TIMEOUT_MS = 5000
STOP_TIMEOUT_SECONDS = 7

from app.db.session import SessionLocal
from app.services.camera.rtsp_encryption import decrypt_rtsp_url
from app.services.vision.runtime import camera_sessions, vision_pipeline


@dataclass
class RTSPWorker:
    camera_source_id: int
    stop_event: Event = field(default_factory=Event)
    thread: Thread | None = None
    status: str = "STARTING"
    error: str | None = None
    processed_frames: int = 0


class RTSPStreamManager:
    def __init__(self, frame_interval: int = 5):
        if frame_interval < 1:
            raise ValueError("Frame interval must be at least 1")

        self.frame_interval = frame_interval
        self._lock = Lock()
        self._workers: dict[int, RTSPWorker] = {}

    def start(self, camera_source_id: int, encrypted_url: str) -> bool:
        with self._lock:
            existing = self._workers.get(camera_source_id)

            if existing and existing.thread and existing.thread.is_alive():
                return False

            if not camera_sessions.acquire(camera_source_id):
                return False

            worker = RTSPWorker(camera_source_id=camera_source_id)
            self._workers[camera_source_id] = worker

            try:
                rtsp_url = decrypt_rtsp_url(encrypted_url)
                worker.thread = Thread(
                    target=self._run,
                    args=(worker, rtsp_url),
                    name=f"restromind-rtsp-{camera_source_id}",
                    daemon=True,
                )
                worker.thread.start()
            except Exception:
                camera_sessions.release(camera_source_id)
                self._workers.pop(camera_source_id, None)
                raise

            return True

    def stop(self, camera_source_id: int) -> dict | None:
        with self._lock:
            worker = self._workers.get(camera_source_id)

            if worker is None:
                return None

            worker.stop_event.set()
            if worker.status in {"STARTING", "RUNNING"}:
                worker.status = "STOPPING"

            thread = worker.thread

        if thread:
            thread.join(timeout=STOP_TIMEOUT_SECONDS)

        return self.get_status(camera_source_id)

    def get_status(self, camera_source_id: int) -> dict | None:
        with self._lock:
            worker = self._workers.get(camera_source_id)

            if worker is None:
                return None

            return {
                "camera_source_id": worker.camera_source_id,
                "status": worker.status,
                "processed_frames": worker.processed_frames,
                "error": worker.error,
            }

    def _run(self, worker: RTSPWorker, rtsp_url: str) -> None:
        capture = None
        db = None
        frame_index = 0

        try:
            capture = cv2.VideoCapture(
                rtsp_url,
                cv2.CAP_FFMPEG,
                [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                    OPEN_TIMEOUT_MS,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                    READ_TIMEOUT_MS,
                ],
            )

            if not capture.isOpened():
                self._update_worker(
                    worker,
                    status="ERROR",
                    error="Could not connect to the RTSP camera.",
                )
                return

            db = SessionLocal()
            self._update_worker(worker, status="RUNNING")

            while not worker.stop_event.is_set():
                success, frame = capture.read()

                if not success:
                    if not worker.stop_event.is_set():
                        self._update_worker(
                            worker,
                            status="ERROR",
                            error="RTSP stream disconnected or stopped sending frames.",
                        )
                    break

                if frame_index % self.frame_interval == 0:
                    vision_pipeline.process_frame(
                        db=db,
                        camera_source_id=worker.camera_source_id,
                        frame=frame,
                    )

                    with self._lock:
                        worker.processed_frames += 1

                frame_index += 1

        except Exception:
            if not worker.stop_event.is_set():
                self._update_worker(
                    worker,
                    status="ERROR",
                    error="An error occurred while processing the RTSP stream.",
                )

        finally:
            if capture is not None:
                capture.release()

            if db is not None:
                db.close()

            vision_pipeline.reset_tracker(worker.camera_source_id)
            camera_sessions.release(worker.camera_source_id)

            if worker.stop_event.is_set():
                self._update_worker(worker, status="STOPPED")

    def _update_worker(
        self,
        worker: RTSPWorker,
        status: str,
        error: str | None = None,
    ) -> None:
        with self._lock:
            worker.status = status
            worker.error = error


rtsp_stream_manager = RTSPStreamManager()
