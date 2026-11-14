from threading import Lock

from app.services.vision.vision_pipeline import VisionPipeline


class CameraSessionRegistry:
    """Prevent overlapping processing sessions for the same camera."""

    def __init__(self):
        self._lock = Lock()
        self._active_cameras: set[int] = set()

    def acquire(self, camera_source_id: int) -> bool:
        with self._lock:
            if camera_source_id in self._active_cameras:
                return False

            self._active_cameras.add(camera_source_id)
            return True

    def release(self, camera_source_id: int) -> None:
        with self._lock:
            self._active_cameras.discard(camera_source_id)

    def is_active(self, camera_source_id: int) -> bool:
        with self._lock:
            return camera_source_id in self._active_cameras


vision_pipeline = VisionPipeline()
camera_sessions = CameraSessionRegistry()
