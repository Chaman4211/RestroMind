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
            raise FileNotFoundError(f"YOLO model not found: {model_path}")

        self.model = YOLO(str(model_path))

    def update(
        self,
        frame,
        confidence: float = 0.35,
        image_size: int = 640,
    ):
        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=confidence,
            imgsz=image_size,
            verbose=False,
            device="cpu",
        )

        tracked_people = []

        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes
            track_ids = boxes.id

            for index, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # Keep detections even when YOLO cannot provide track IDs.
                # Negative IDs are temporary and are not real tracker IDs.
                track_id = (
                    int(track_ids[index]) if track_ids is not None else -(index + 1)
                )

                tracked_people.append(
                    {
                        "track_id": track_id,
                        "bbox": [
                            float(x1),
                            float(y1),
                            float(x2),
                            float(y2),
                        ],
                        "confidence": float(box.conf[0]),
                    }
                )

        return tracked_people
