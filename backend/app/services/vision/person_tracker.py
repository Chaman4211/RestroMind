from pathlib import Path

from ultralytics import YOLO

from app.services.vision.person_detector import MODEL_PATH


class PersonTracker:
    """
    Track detected people across consecutive video frames.

    Create one tracker instance per video or live-camera stream.
    """

    def __init__(self, model_path: Path = MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found: {model_path}"
            )

        self.model = YOLO(str(model_path))

    def update(self, frame):
        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=0.35,
            verbose=False,
            device="cpu",
        )

        tracked_people = []

        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes

            if boxes.id is None:
                continue

            for box, track_id in zip(boxes, boxes.id, strict=True):
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                tracked_people.append({
                    "track_id": int(track_id),
                    "bbox": [
                        float(x1),
                        float(y1),
                        float(x2),
                        float(y2),
                    ],
                    "confidence": float(box.conf[0]),
                })

        return tracked_people
