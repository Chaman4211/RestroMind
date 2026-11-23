from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.alert import Alert
from app.models.camera_source import CameraSource
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from tests.auth_helpers import create_test_user, delete_test_user

client = TestClient(app)


def test_restaurant_table_crud():
    unique_id = uuid4().hex[:8]
    camera_name = f"Test Camera {unique_id}"
    table_number = f"T-{unique_id}"

    camera_id = None
    table_id = None
    user_id, headers = create_test_user("OWNER")

    try:
        camera_response = client.post(
            "/api/v1/camera-sources",
            json={
                "name": camera_name,
                "source_type": "LIVE",
            },
        )

        assert camera_response.status_code == 201
        camera_id = camera_response.json()["id"]

        payload = {
            "table_number": table_number,
            "name": "Test Table",
            "zone_coordinates": {
                "points": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]
            },
            "camera_source_id": camera_id,
        }

        create_response = client.post(
            "/api/v1/restaurant-tables",
            json=payload,
            headers=headers,
        )

        assert create_response.status_code == 201
        created_table = create_response.json()
        table_id = created_table["id"]

        assert created_table["table_number"] == table_number
        assert created_table["status"] == "FREE"
        assert created_table["camera_source_id"] == camera_id

        duplicate_response = client.post(
            "/api/v1/restaurant-tables",
            json=payload,
            headers=headers,
        )
        assert duplicate_response.status_code == 409

        missing_camera_response = client.post(
            "/api/v1/restaurant-tables",
            json={
                "table_number": f"INVALID-{unique_id}",
                "name": "Invalid Camera Table",
                "camera_source_id": 999999999,
            },
            headers=headers,
        )
        assert missing_camera_response.status_code == 404

        list_response = client.get("/api/v1/restaurant-tables", headers=headers)
        assert list_response.status_code == 200
        assert any(
            table["id"] == table_id
            for table in list_response.json()
        )

        get_response = client.get(
            f"/api/v1/restaurant-tables/{table_id}",
            headers=headers,
        )
        assert get_response.status_code == 200

        update_response = client.patch(
            f"/api/v1/restaurant-tables/{table_id}",
            json={
                "name": "Updated Test Table",
                "camera_source_id": None,
            },
            headers=headers,
        )

        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Test Table"
        assert update_response.json()["camera_source_id"] is None

        delete_response = client.delete(
            f"/api/v1/restaurant-tables/{table_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204
        table_id = None

        missing_table_response = client.get(
            f"/api/v1/restaurant-tables/{created_table['id']}",
            headers=headers,
        )
        assert missing_table_response.status_code == 404

    finally:
        db = SessionLocal()
        try:
            if table_id is not None:
                table = db.get(RestaurantTable, table_id)
                if table is not None:
                    db.delete(table)

            camera = db.scalar(
                select(CameraSource).where(
                    CameraSource.name == camera_name
                )
            )
            if camera is not None:
                db.delete(camera)

            db.commit()
        finally:
            db.close()
        delete_test_user(user_id)


def test_table_with_history_cannot_be_deleted():
    unique_id = uuid4().hex[:8]
    table_id = None
    user_id, headers = create_test_user("OWNER")

    db = SessionLocal()

    try:
        table = RestaurantTable(
            table_number=f"H-{unique_id}",
            name="History Protection Test",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        event = OccupancyEvent(
            table_id=table_id,
            previous_status="FREE",
            new_status="OCCUPIED",
            description="Test occupancy event",
        )

        db.add(event)
        db.commit()

        response = client.delete(
            f"/api/v1/restaurant-tables/{table_id}",
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "Cannot delete a table with occupancy history or alerts"
        )

    finally:
        if table_id is not None:
            db.query(OccupancyEvent).filter(
                OccupancyEvent.table_id == table_id
            ).delete(synchronize_session=False)

            db.query(Alert).filter(
                Alert.table_id == table_id
            ).delete(synchronize_session=False)

            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)

            db.commit()

        db.close()
