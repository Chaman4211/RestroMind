from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.alert import Alert
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from tests.auth_helpers import create_test_user, delete_test_user

client = TestClient(app)


def test_staff_can_confirm_table_cleaning():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("OWNER")

    try:
        table = RestaurantTable(
            table_number=f"API-{uuid4().hex[:8]}",
            name="Cleaning API Test",
            status="NEEDS_CLEANING",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        alert = Alert(
            table_id=table_id,
            alert_type="CLEANING_REQUIRED",
            message="Table requires cleaning.",
        )
        db.add(alert)
        db.commit()

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/confirm-cleaning",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "FREE"

        db.refresh(table)
        db.refresh(alert)

        assert table.status == "FREE"
        assert alert.status == "RESOLVED"
        assert alert.resolved_at is not None

        events = (
            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).all()
        )

        assert len(events) == 1
        assert events[0].previous_status == "NEEDS_CLEANING"
        assert events[0].new_status == "FREE"

    finally:
        if table_id is not None:
            db.query(Alert).filter(Alert.table_id == table_id).delete(
                synchronize_session=False
            )

            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).delete(
                synchronize_session=False
            )

            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)

            db.commit()

        db.close()
        delete_test_user(user_id)


def test_cleaning_confirmation_rejected_for_free_table():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("OWNER")

    try:
        table = RestaurantTable(
            table_number=f"FREE-{uuid4().hex[:8]}",
            name="Free Table Test",
            status="FREE",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/confirm-cleaning",
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Table does not need cleaning"

    finally:
        if table_id is not None:
            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)
                db.commit()

        db.close()
        delete_test_user(user_id)


def test_cleaning_confirmation_returns_404_for_missing_table():
    user_id, headers = create_test_user("OWNER")
    try:
        response = client.post(
            "/api/v1/restaurant-tables/999999999/confirm-cleaning",
            headers=headers,
        )

        assert response.status_code == 404
    finally:
        delete_test_user(user_id)


def test_waiter_can_report_vacant_table_for_cleaning():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("WAITER")

    try:
        table = RestaurantTable(
            table_number=f"REPORT-{uuid4().hex[:8]}",
            name="Cleaning Report Test",
            status="FREE",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/report-cleaning",
            headers=headers,
            json={"reason": "Food spill on the table"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "NEEDS_CLEANING"
        assert response.json()["created"] is True

        db.refresh(table)
        assert table.status == "NEEDS_CLEANING"

        alerts = (
            db.query(Alert)
            .filter(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
            .all()
        )
        assert len(alerts) == 1
        assert "Food spill on the table" in alerts[0].message

        events = (
            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).all()
        )
        assert len(events) == 1
        assert events[0].previous_status == "FREE"
        assert events[0].new_status == "NEEDS_CLEANING"

    finally:
        if table_id is not None:
            db.query(Alert).filter(Alert.table_id == table_id).delete(
                synchronize_session=False
            )
            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).delete(
                synchronize_session=False
            )
            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)
            db.commit()
        db.close()
        delete_test_user(user_id)


def test_duplicate_cleaning_report_reuses_open_alert():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("OWNER")

    try:
        table = RestaurantTable(
            table_number=f"DUP-{uuid4().hex[:8]}",
            name="Duplicate Report Test",
            status="FREE",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        url = f"/api/v1/restaurant-tables/{table_id}/report-cleaning"
        first = client.post(url, headers=headers, json={})
        second = client.post(url, headers=headers, json={})

        assert first.status_code == 200
        assert first.json()["created"] is True
        assert second.status_code == 200
        assert second.json()["created"] is False
        assert first.json()["alert_id"] == second.json()["alert_id"]

        count = (
            db.query(Alert)
            .filter(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
            .count()
        )
        assert count == 1

    finally:
        if table_id is not None:
            db.query(Alert).filter(Alert.table_id == table_id).delete(
                synchronize_session=False
            )
            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).delete(
                synchronize_session=False
            )
            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)
            db.commit()
        db.close()
        delete_test_user(user_id)


def test_cleaning_report_rejected_for_occupied_table():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("OWNER")

    try:
        table = RestaurantTable(
            table_number=f"OCC-{uuid4().hex[:8]}",
            name="Occupied Report Test",
            status="OCCUPIED",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/report-cleaning",
            headers=headers,
            json={},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "Only vacant tables can be marked for cleaning"
        )

        db.refresh(table)
        assert table.status == "OCCUPIED"

        count = (
            db.query(Alert)
            .filter(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
            )
            .count()
        )
        assert count == 0

    finally:
        if table_id is not None:
            db.query(Alert).filter(Alert.table_id == table_id).delete(
                synchronize_session=False
            )
            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).delete(
                synchronize_session=False
            )
            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)
            db.commit()
        db.close()
        delete_test_user(user_id)


def test_cleaning_staff_cannot_report_cleaning_need():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("CLEANING_STAFF")

    try:
        table = RestaurantTable(
            table_number=f"DENY-{uuid4().hex[:8]}",
            name="Permission Report Test",
            status="FREE",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/report-cleaning",
            headers=headers,
            json={},
        )

        assert response.status_code == 403

        db.refresh(table)
        assert table.status == "FREE"

    finally:
        if table_id is not None:
            db.query(Alert).filter(Alert.table_id == table_id).delete(
                synchronize_session=False
            )
            db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).delete(
                synchronize_session=False
            )
            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)
            db.commit()
        db.close()
        delete_test_user(user_id)
