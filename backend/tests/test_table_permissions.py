from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.alert import Alert
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from tests.auth_helpers import create_test_user, delete_test_user

client = TestClient(app)


def create_cleaning_table(db):
    table = RestaurantTable(
        table_number=f"PERM-{uuid4().hex[:8]}",
        name="Permission Test Table",
        status="NEEDS_CLEANING",
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def cleanup_table(db, table_id):
    db.query(Alert).filter(Alert.table_id == table_id).delete(synchronize_session=False)

    db.query(OccupancyEvent).filter(OccupancyEvent.table_id == table_id).delete(
        synchronize_session=False
    )

    table = db.get(RestaurantTable, table_id)
    if table is not None:
        db.delete(table)
        db.commit()


def test_unauthenticated_user_cannot_view_tables():
    response = client.get("/api/v1/restaurant-tables")
    assert response.status_code == 401


def test_cleaning_staff_cannot_view_all_tables():
    user_id, headers = create_test_user("CLEANING_STAFF")

    try:
        response = client.get(
            "/api/v1/restaurant-tables",
            headers=headers,
        )
        assert response.status_code == 403
    finally:
        delete_test_user(user_id)


def test_waiter_cannot_confirm_table_cleaning():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("WAITER")

    try:
        table = create_cleaning_table(db)
        table_id = table.id

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/confirm-cleaning",
            headers=headers,
        )

        assert response.status_code == 403
    finally:
        if table_id is not None:
            cleanup_table(db, table_id)
        db.close()
        delete_test_user(user_id)


def test_cleaner_can_confirm_own_assigned_cleaning_task():
    db = SessionLocal()
    table_id = None
    cleaner_id, headers = create_test_user("CLEANING_STAFF")

    try:
        table = create_cleaning_table(db)
        table_id = table.id

        alert = Alert(
            table_id=table_id,
            assigned_staff_id=cleaner_id,
            alert_type="CLEANING_REQUIRED",
            message="Clean this table.",
            status="OPEN",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/confirm-cleaning",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "FREE"

        db.refresh(alert)
        assert alert.status == "RESOLVED"
        assert alert.resolved_at is not None
    finally:
        if table_id is not None:
            cleanup_table(db, table_id)
        db.close()
        delete_test_user(cleaner_id)


def test_cleaner_cannot_confirm_unassigned_cleaning_task():
    db = SessionLocal()
    table_id = None
    cleaner_id, headers = create_test_user("CLEANING_STAFF")

    try:
        table = create_cleaning_table(db)
        table_id = table.id

        alert = Alert(
            table_id=table_id,
            assigned_staff_id=None,
            alert_type="CLEANING_REQUIRED",
            message="This task has not been assigned.",
            status="OPEN",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        response = client.post(
            f"/api/v1/restaurant-tables/{table_id}/confirm-cleaning",
            headers=headers,
        )

        assert response.status_code == 403

        db.refresh(table)
        db.refresh(alert)
        assert table.status == "NEEDS_CLEANING"
        assert alert.status == "OPEN"
    finally:
        if table_id is not None:
            cleanup_table(db, table_id)
        db.close()
        delete_test_user(cleaner_id)
