from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.alert import Alert
from app.models.restaurant_table import RestaurantTable
from tests.auth_helpers import create_test_user, delete_test_user

client = TestClient(app)


def test_list_alerts_and_filter_by_status():
    db = SessionLocal()
    table_id = None
    user_id, headers = create_test_user("OWNER")

    try:
        table = RestaurantTable(
            table_number=f"AL-{uuid4().hex[:8]}",
            name="Alerts API Test",
            status="NEEDS_CLEANING",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        open_alert = Alert(
            table_id=table_id,
            alert_type="CLEANING_REQUIRED",
            message="This table requires cleaning.",
            status="OPEN",
        )
        resolved_alert = Alert(
            table_id=table_id,
            alert_type="CLEANING_REQUIRED",
            message="This alert has been resolved.",
            status="RESOLVED",
        )
        db.add_all([open_alert, resolved_alert])
        db.commit()

        response = client.get("/api/v1/alerts", headers=headers)

        assert response.status_code == 200
        alerts = response.json()

        table_alerts = [
            alert for alert in alerts
            if alert["table_id"] == table_id
        ]

        assert len(table_alerts) == 2
        assert table_alerts[0]["table_number"] == table.table_number
        assert table_alerts[0]["table_name"] == "Alerts API Test"

        open_response = client.get(
            "/api/v1/alerts",
            params={"status": "OPEN"},
            headers=headers,
        )

        assert open_response.status_code == 200
        assert all(
            alert["status"] == "OPEN"
            for alert in open_response.json()
        )
        assert any(
            alert["table_id"] == table_id
            for alert in open_response.json()
        )

        resolved_response = client.get(
            "/api/v1/alerts",
            params={"status": "RESOLVED"},
            headers=headers,
        )

        assert resolved_response.status_code == 200
        assert all(
            alert["status"] == "RESOLVED"
            for alert in resolved_response.json()
        )

    finally:
        if table_id is not None:
            db.query(Alert).filter(
                Alert.table_id == table_id
            ).delete(synchronize_session=False)

            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)

            db.commit()

        db.close()
        delete_test_user(user_id)


def test_list_alerts_rejects_invalid_status():
    user_id, headers = create_test_user("OWNER")

    try:
        response = client.get(
            "/api/v1/alerts",
            params={"status": "INVALID"},
            headers=headers,
        )

        assert response.status_code == 422
    finally:
        delete_test_user(user_id)
