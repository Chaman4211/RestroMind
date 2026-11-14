from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.video.video_processor import VideoProcessor


class FakeCapture:
    def __init__(self, frames, fps=10):
        self.frames = frames
        self.fps = fps
        self.index = 0
        self.released = False

    def isOpened(self):
        return True

    def get(self, property_id):
        if property_id == 5:
            return self.fps
        if property_id == 7:
            return len(self.frames)
        return 0

    def read(self):
        if self.index >= len(self.frames):
            return False, None

        frame = self.frames[self.index]
        self.index += 1
        return True, frame

    def release(self):
        self.released = True



class EmptyFrameCapture(FakeCapture):
    def get(self, property_id):
        if property_id == 5:
            return self.fps
        if property_id == 7:
            return 1
        return 0

def test_video_processor_samples_frames_and_resets_tracker(tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    frames = [
        np.zeros((100, 100, 3), dtype=np.uint8)
        for _ in range(10)
    ]

    capture = FakeCapture(frames)
    pipeline = MagicMock()

    pipeline.process_frame.return_value = {
        "people_detected": 2,
        "tables": [{"table_id": 1, "status": "OCCUPIED"}],
    }

    processor = VideoProcessor(
        pipeline=pipeline,
        frame_interval=2,
    )

    with patch(
        "app.services.video.video_processor.cv2.VideoCapture",
        return_value=capture,
    ):
        result = processor.process_video(
            db=MagicMock(),
            camera_source_id=5,
            video_path=video_path,
        )

    assert result["total_frames"] == 10
    assert result["processed_frames"] == 5
    assert result["frame_interval"] == 2
    assert result["fps"] == 10
    assert result["duration_seconds"] == 1.0
    assert result["max_people_detected"] == 2
    assert len(result["tables"]) == 1

    assert pipeline.process_frame.call_count == 5
    assert pipeline.reset_tracker.call_count == 2
    assert capture.released is True


def test_video_processor_rejects_missing_file():
    processor = VideoProcessor(pipeline=MagicMock())

    with pytest.raises(ValueError, match="Video file does not exist"):
        processor.process_video(
            db=MagicMock(),
            camera_source_id=1,
            video_path=Path("missing-video.mp4"),
        )


def test_video_processor_rejects_invalid_frame_interval():
    with pytest.raises(ValueError, match="Frame interval must be at least 1"):
        VideoProcessor(
            pipeline=MagicMock(),
            frame_interval=0,
        )


def test_video_processor_rejects_unreadable_video(tmp_path):
    video_path = tmp_path / "invalid.mp4"
    video_path.touch()

    capture = MagicMock()
    capture.isOpened.return_value = False

    processor = VideoProcessor(pipeline=MagicMock())

    with patch(
        "app.services.video.video_processor.cv2.VideoCapture",
        return_value=capture,
    ):
        with pytest.raises(ValueError, match="Could not open video file"):
            processor.process_video(
                db=MagicMock(),
                camera_source_id=1,
                video_path=video_path,
            )

    capture.release.assert_called_once()


def test_video_processor_rejects_invalid_video_metadata(tmp_path):
    video_path = tmp_path / "invalid-metadata.mp4"
    video_path.touch()

    capture = FakeCapture([], fps=0)

    processor = VideoProcessor(pipeline=MagicMock())

    with patch(
        "app.services.video.video_processor.cv2.VideoCapture",
        return_value=capture,
    ):
        with pytest.raises(ValueError, match="Video has invalid FPS or frame count"):
            processor.process_video(
                db=MagicMock(),
                camera_source_id=1,
                video_path=video_path,
            )

    assert capture.released is True


def test_video_processor_rejects_video_without_readable_frames(tmp_path):
    video_path = tmp_path / "empty.mp4"
    video_path.touch()

    capture = EmptyFrameCapture([], fps=10)
    processor = VideoProcessor(pipeline=MagicMock())

    with patch(
        "app.services.video.video_processor.cv2.VideoCapture",
        return_value=capture,
    ):
        with pytest.raises(ValueError, match="Video contains no readable frames"):
            processor.process_video(
                db=MagicMock(),
                camera_source_id=1,
                video_path=video_path,
            )

    assert capture.released is True
