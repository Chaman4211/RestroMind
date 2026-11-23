from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from app.models.restaurant_order import RestaurantOrder
from app.services.occupancy.occupancy_service import OccupancyService
from app.services.occupancy.state_machine import (
    OccupancyConfig,
    OccupancyStateMachine,
)


def test_occupancy_lifecycle_is_saved_in_database():
    db = SessionLocal()
    table_id = None

    start = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)

    service = OccupancyService(
        OccupancyStateMachine(
            OccupancyConfig(
                enter_threshold_seconds=5,
                exit_threshold_seconds=10,
                service_reminder_seconds=1800,
            )
        )
    )

    try:
        table = RestaurantTable(
            table_number=f"TEST-{uuid4().hex[:8]}",
            name="Occupancy Integration Test",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        service.process_detection(db, table_id, True, start)

        result = service.process_detection(
            db, table_id, True, start + timedelta(seconds=5)
        )

        assert result["status"] == "OCCUPIED"

        db.refresh(table)
        assert table.status == "OCCUPIED"

        events = db.scalars(
            select(OccupancyEvent).where(
                OccupancyEvent.table_id == table_id
            )
        ).all()

        assert len(events) == 1
        assert events[0].previous_status == "FREE"
        assert events[0].new_status == "OCCUPIED"

        service.process_detection(
            db, table_id, False, start + timedelta(seconds=10)
        )

        result = service.process_detection(
            db, table_id, False, start + timedelta(seconds=20)
        )

        assert result["status"] == "FREE"

        db.refresh(table)
        assert table.status == "FREE"

        cleaning_alerts = db.scalars(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        ).all()

        assert cleaning_alerts == []

        events = db.scalars(
            select(OccupancyEvent).where(
                OccupancyEvent.table_id == table_id
            )
        ).all()

        assert len(events) == 2
        assert events[-1].previous_status == "OCCUPIED"
        assert events[-1].new_status == "FREE"

    finally:
        if table_id is not None:
            db.query(Alert).filter(
                Alert.table_id == table_id
            ).delete(synchronize_session=False)

            db.query(OccupancyEvent).filter(
                OccupancyEvent.table_id == table_id
            ).delete(synchronize_session=False)

            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)

            db.commit()

        db.close()


def test_occupancy_service_rejects_unknown_table():
    db = SessionLocal()
    service = OccupancyService()

    try:
        with pytest.raises(ValueError, match="Restaurant table not found"):
            service.process_detection(
                db,
                999999999,
                True,
                datetime.now(UTC),
            )
    finally:
        db.close()


def test_paid_order_departure_requires_cleaning_and_confirmation():
    db = SessionLocal()
    table_id = None

    start = datetime(2026, 11, 13, 11, 0, tzinfo=UTC)

    service = OccupancyService(
        OccupancyStateMachine(
            OccupancyConfig(
                enter_threshold_seconds=5,
                exit_threshold_seconds=10,
                service_reminder_seconds=1800,
            )
        )
    )

    try:
        table = RestaurantTable(
            table_number=f"TEST-{uuid4().hex[:8]}",
            name="Paid Order Cleaning Test",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        service.process_detection(db, table_id, True, start)
        service.process_detection(
            db, table_id, True, start + timedelta(seconds=5)
        )

        order = RestaurantOrder(
            order_number=f"TEST-{uuid4().hex[:12]}",
            public_token=uuid4().hex,
            table_id=table_id,
            total_amount=Decimal("1500.00"),
            payment_status="PAID",
            created_at=start + timedelta(seconds=6),
        )
        db.add(order)
        db.commit()

        service.process_detection(
            db, table_id, False, start + timedelta(seconds=10)
        )
        result = service.process_detection(
            db, table_id, False, start + timedelta(seconds=20)
        )

        assert result["status"] == "NEEDS_CLEANING"

        db.refresh(table)
        assert table.status == "NEEDS_CLEANING"

        alerts = db.scalars(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        ).all()

        assert len(alerts) == 1

        result = service.confirm_cleaning(
            db, table_id, start + timedelta(seconds=30)
        )

        assert result["status"] == "FREE"

        db.refresh(table)
        db.refresh(alerts[0])

        assert table.status == "FREE"
        assert alerts[0].status == "RESOLVED"
        assert alerts[0].resolved_at is not None

        events = db.scalars(
            select(OccupancyEvent)
            .where(OccupancyEvent.table_id == table_id)
            .order_by(OccupancyEvent.id)
        ).all()

        assert [event.new_status for event in events] == [
            "OCCUPIED",
            "NEEDS_CLEANING",
            "FREE",
        ]

    finally:
        if table_id is not None:
            db.query(RestaurantOrder).filter(
                RestaurantOrder.table_id == table_id
            ).delete(synchronize_session=False)

            db.query(Alert).filter(
                Alert.table_id == table_id
            ).delete(synchronize_session=False)

            db.query(OccupancyEvent).filter(
                OccupancyEvent.table_id == table_id
            ).delete(synchronize_session=False)

            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)

            db.commit()

        db.close()


def test_unpaid_order_keeps_table_occupied_after_customer_departure():
    db = SessionLocal()
    table_id = None

    start = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)

    service = OccupancyService(
        OccupancyStateMachine(
            OccupancyConfig(
                enter_threshold_seconds=5,
                exit_threshold_seconds=10,
                service_reminder_seconds=1800,
            )
        )
    )

    try:
        table = RestaurantTable(
            table_number=f"TEST-{uuid4().hex[:8]}",
            name="Unpaid Bill Protection Test",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        table_id = table.id

        service.process_detection(db, table_id, True, start)
        service.process_detection(
            db, table_id, True, start + timedelta(seconds=5)
        )

        order = RestaurantOrder(
            order_number=f"TEST-{uuid4().hex[:12]}",
            public_token=uuid4().hex,
            table_id=table_id,
            total_amount=Decimal("2000.00"),
            payment_status="UNPAID",
            created_at=start + timedelta(seconds=6),
        )
        db.add(order)
        db.commit()

        service.process_detection(
            db, table_id, False, start + timedelta(seconds=10)
        )

        result = service.process_detection(
            db, table_id, False, start + timedelta(seconds=20)
        )

        assert result["status"] == "OCCUPIED"

        db.refresh(table)
        assert table.status == "OCCUPIED"

        unpaid_alerts = db.scalars(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "UNPAID_BILL",
                Alert.status == "OPEN",
            )
        ).all()

        assert len(unpaid_alerts) == 1

        cleaning_alerts = db.scalars(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        ).all()

        assert cleaning_alerts == []

    finally:
        if table_id is not None:
            db.query(RestaurantOrder).filter(
                RestaurantOrder.table_id == table_id
            ).delete(synchronize_session=False)

            db.query(Alert).filter(
                Alert.table_id == table_id
            ).delete(synchronize_session=False)

            db.query(OccupancyEvent).filter(
                OccupancyEvent.table_id == table_id
            ).delete(synchronize_session=False)

            table = db.get(RestaurantTable, table_id)
            if table is not None:
                db.delete(table)

            db.commit()

        db.close()
