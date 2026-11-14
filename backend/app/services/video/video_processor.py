from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
from sqlalchemy.orm import Session

from app.services.vision.vision_pipeline import VisionPipeline


class VideoProcessor:
    def __init__(
        self,
        pipeline: VisionPipeline,
        frame_interval: int = 5,
    ):
        if frame_interval < 1:
            raise ValueError("Frame interval must be at least 1")

        self.pipeline = pipeline
        self.frame_interval = frame_interval

    def process_video(
        self,
        db: Session,
        camera_source_id: int,
        video_path: str | Path,
    ):
        video_path = Path(video_path)

        if not video_path.is_file():
            raise ValueError("Video file does not exist")

        capture = cv2.VideoCapture(str(video_path))

        if not capture.isOpened():
            capture.release()
            raise ValueError("Could not open video file")

        fps = capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0 or total_frames <= 0:
            capture.release()
            raise ValueError("Video has invalid FPS or frame count")

        start_time = datetime.now(UTC)
        processed_frames = 0
        people_detected = 0
        frame_index = 0
        latest_tables = []

        self.pipeline.reset_tracker(camera_source_id)

        try:
            while True:
                success, frame = capture.read()

                if not success:
                    break

                if frame_index % self.frame_interval == 0:
                    timestamp = start_time + timedelta(
                        seconds=frame_index / fps
                    )

                    result = self.pipeline.process_frame(
                        db=db,
                        camera_source_id=camera_source_id,
                        frame=frame,
                        timestamp=timestamp,
                    )

                    processed_frames += 1
                    people_detected = max(
                        people_detected,
                        result["people_detected"],
                    )
                    latest_tables = result["tables"]

                frame_index += 1

        finally:
            capture.release()
            self.pipeline.reset_tracker(camera_source_id)

        if frame_index == 0:
            raise ValueError("Video contains no readable frames")

        return {
            "camera_source_id": camera_source_id,
            "total_frames": frame_index,
            "processed_frames": processed_frames,
            "frame_interval": self.frame_interval,
            "fps": fps,
            "duration_seconds": round(frame_index / fps, 2),
            "max_people_detected": people_detected,
            "tables": latest_tables,
        }
