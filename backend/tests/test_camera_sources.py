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


def test_rtsp_camera_credentials_are_encrypted_and_hidden():
    from app.services.camera.rtsp_encryption import decrypt_rtsp_url

    name = f"test-rtsp-{uuid4().hex[:8]}"
    rtsp_url = "rtsp://testuser:testpassword@camera.example.com:554/stream"
    source_id = None

    try:
        response = client.post(
            "/api/v1/camera-sources",
            json={
                "name": name,
                "source_type": "RTSP",
                "rtsp_url": rtsp_url,
            },
        )

        assert response.status_code == 201
        created = response.json()
        source_id = created["id"]

        assert created["source_type"] == "RTSP"
        assert "rtsp_url" not in created
        assert "rtsp_url_encrypted" not in created

        response_text = response.text
        assert "testuser" not in response_text
        assert "testpassword" not in response_text

        db = SessionLocal()
        try:
            source = db.get(CameraSource, source_id)
            assert source is not None
            assert source.rtsp_url_encrypted is not None
            assert rtsp_url not in source.rtsp_url_encrypted
            assert decrypt_rtsp_url(source.rtsp_url_encrypted) == rtsp_url
        finally:
            db.close()

        get_response = client.get(
            f"/api/v1/camera-sources/{source_id}"
        )
        assert get_response.status_code == 200
        assert "testpassword" not in get_response.text

        list_response = client.get("/api/v1/camera-sources")
        assert list_response.status_code == 200
        assert "testpassword" not in list_response.text

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


def test_rtsp_camera_update_rules():
    name = f"test-rtsp-update-{uuid4().hex[:8]}"
    source_id = None

    try:
        create_response = client.post(
            "/api/v1/camera-sources",
            json={
                "name": name,
                "source_type": "RTSP",
                "rtsp_url": "rtsp://first:password@camera.example.com/stream",
            },
        )

        assert create_response.status_code == 201
        source_id = create_response.json()["id"]

        missing_url_response = client.patch(
            f"/api/v1/camera-sources/{source_id}",
            json={"source_type": "LIVE"},
        )
        assert missing_url_response.status_code == 200

        db = SessionLocal()
        try:
            source = db.get(CameraSource, source_id)
            assert source is not None
            assert source.source_type == "LIVE"
            assert source.rtsp_url_encrypted is None
        finally:
            db.close()

        missing_rtsp_response = client.patch(
            f"/api/v1/camera-sources/{source_id}",
            json={"source_type": "RTSP"},
        )
        assert missing_rtsp_response.status_code == 422

        restore_response = client.patch(
            f"/api/v1/camera-sources/{source_id}",
            json={
                "source_type": "RTSP",
                "rtsp_url": "rtsps://second:password@camera.example.com/stream",
            },
        )
        assert restore_response.status_code == 200
        assert restore_response.json()["source_type"] == "RTSP"

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


def test_rtsp_start_stop_and_status_endpoints(monkeypatch):
    from app.api.v1 import camera_sources as camera_api

    name = f"test-rtsp-endpoints-{uuid4().hex[:8]}"
    rtsp_url = "rtsp://privateuser:privatepassword@camera.example.com/stream"
    source_id = None
    captured = {}

    try:
        create_response = client.post(
            "/api/v1/camera-sources",
            json={
                "name": name,
                "source_type": "RTSP",
                "rtsp_url": rtsp_url,
            },
        )
        assert create_response.status_code == 201
        source_id = create_response.json()["id"]

        def fake_start(camera_source_id, encrypted_url):
            captured["camera_source_id"] = camera_source_id
            captured["encrypted_url"] = encrypted_url
            return True

        def fake_status(camera_source_id):
            return {
                "camera_source_id": camera_source_id,
                "status": "RUNNING",
                "processed_frames": 15,
                "error": None,
            }

        def fake_stop(camera_source_id):
            return {
                "camera_source_id": camera_source_id,
                "status": "STOPPED",
                "processed_frames": 15,
                "error": None,
            }

        manager = camera_api.rtsp_stream_manager

        monkeypatch.setattr(manager, "start", fake_start)
        monkeypatch.setattr(manager, "get_status", fake_status)
        monkeypatch.setattr(manager, "stop", fake_stop)

        start_response = client.post(
            f"/api/v1/camera-sources/{source_id}/rtsp/start"
        )

        assert start_response.status_code == 200
        assert start_response.json()["status"] == "RUNNING"
        assert start_response.json()["processed_frames"] == 15

        assert captured["camera_source_id"] == source_id
        assert captured["encrypted_url"] != rtsp_url

        status_response = client.get(
            f"/api/v1/camera-sources/{source_id}/rtsp/status"
        )

        assert status_response.status_code == 200
        assert status_response.json()["status"] == "RUNNING"

        stop_response = client.post(
            f"/api/v1/camera-sources/{source_id}/rtsp/stop"
        )

        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "STOPPED"

        for response in (start_response, status_response, stop_response):
            assert "privateuser" not in response.text
            assert "privatepassword" not in response.text
            assert rtsp_url not in response.text

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


def test_rtsp_start_rejects_non_rtsp_and_inactive_cameras():
    name = f"test-rtsp-validation-{uuid4().hex[:8]}"
    source_id = None

    try:
        create_response = client.post(
            "/api/v1/camera-sources",
            json={
                "name": name,
                "source_type": "UPLOAD",
            },
        )

        assert create_response.status_code == 201
        source_id = create_response.json()["id"]

        non_rtsp_response = client.post(
            f"/api/v1/camera-sources/{source_id}/rtsp/start"
        )
        assert non_rtsp_response.status_code == 409

        update_response = client.patch(
            f"/api/v1/camera-sources/{source_id}",
            json={"is_active": False},
        )
        assert update_response.status_code == 200

        inactive_response = client.post(
            f"/api/v1/camera-sources/{source_id}/rtsp/start"
        )
        assert inactive_response.status_code == 409

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
