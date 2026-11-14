from pathlib import Path

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODEL_PATH = PROJECT_ROOT / "data" / "models" / "yolo11n.pt"


class PersonDetector:
    """Detect people using the pretrained YOLO11n model."""

    def __init__(self, model_path: Path = MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found: {model_path}"
            )

        self.model = YOLO(str(model_path))

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            classes=[0],
            conf=0.35,
            verbose=False,
            device="cpu",
        )

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append({
                    "bbox": [
                        float(x1),
                        float(y1),
                        float(x2),
                        float(y2),
                    ],
                    "confidence": float(box.conf[0]),
                    "class_id": int(box.cls[0]),
                })

        return detections
