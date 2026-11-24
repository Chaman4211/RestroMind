from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.restaurant_table import RestaurantTable

client = TestClient(app)


def test_public_tables_returns_real_table_numbers():
    unique_id = uuid4().hex[:8]
    table_number = f"PUBLIC-{unique_id}"
    table_id = None

    try:
        with SessionLocal() as db:
            table = RestaurantTable(
                table_number=table_number,
                name="Public Table Test",
                status="FREE",
            )
            db.add(table)
            db.commit()
            db.refresh(table)
            table_id = table.id

        response = client.get("/api/v1/public/tables")

        assert response.status_code == 200
        tables = response.json()

        matching_table = next(
            (item for item in tables if item["id"] == table_id),
            None,
        )

        assert matching_table is not None
        assert matching_table["table_number"] == table_number
        assert matching_table["name"] == "Public Table Test"

        detail_response = client.get(
            f"/api/v1/public/tables/{table_id}"
        )

        assert detail_response.status_code == 200
    finally:
        if table_id is not None:
            with SessionLocal() as db:
                table = db.get(RestaurantTable, table_id)
                if table is not None:
                    db.delete(table)
                    db.commit()
