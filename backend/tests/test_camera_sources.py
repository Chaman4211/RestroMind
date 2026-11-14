from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.camera_source import CameraSource

client = TestClient(app)


def test_camera_source_crud():
    name = f"test-camera-{uuid4().hex[:8]}"
    source_id = None

    try:
        invalid_response = client.post(
            "/api/v1/camera-sources",
            json={"name": "A", "source_type": "UPLOAD"},
        )
        assert invalid_response.status_code == 422

        invalid_type_response = client.post(
            "/api/v1/camera-sources",
            json={"name": name, "source_type": "RTSP"},
        )
        assert invalid_type_response.status_code == 422

        create_response = client.post(
            "/api/v1/camera-sources",
            json={"name": name, "source_type": "UPLOAD"},
        )

        assert create_response.status_code == 201
        created = create_response.json()
        source_id = created["id"]

        assert created["name"] == name
        assert created["source_type"] == "UPLOAD"
        assert created["is_active"] is True

        invalid_update_response = client.patch(
            f"/api/v1/camera-sources/{source_id}",
            json={"source_type": "RTSP"},
        )
        assert invalid_update_response.status_code == 422

        unchanged_response = client.get(
            f"/api/v1/camera-sources/{source_id}"
        )
        assert unchanged_response.json()["source_type"] == "UPLOAD"

        list_response = client.get("/api/v1/camera-sources")
        assert list_response.status_code == 200
        assert any(item["id"] == source_id for item in list_response.json())

        get_response = client.get(
            f"/api/v1/camera-sources/{source_id}"
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == source_id

        update_response = client.patch(
            f"/api/v1/camera-sources/{source_id}",
            json={"name": f"{name}-updated", "is_active": False},
        )

        assert update_response.status_code == 200
        assert update_response.json()["name"] == f"{name}-updated"
        assert update_response.json()["is_active"] is False

        delete_response = client.delete(
            f"/api/v1/camera-sources/{source_id}"
        )
        assert delete_response.status_code == 204

        missing_response = client.get(
            f"/api/v1/camera-sources/{source_id}"
        )
        assert missing_response.status_code == 404

        source_id = None

    finally:
        if source_id is not None:
            db = SessionLocal()
            try:
                source = db.get(CameraSource, source_id)
                if source is not None and not source.tables:
                    db.delete(source)
                    db.commit()
            finally:
                db.close()
