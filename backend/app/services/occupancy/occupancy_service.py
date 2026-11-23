from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_order import RestaurantOrder
from app.models.restaurant_table import RestaurantTable
from app.services.occupancy.state_machine import (
    OccupancyStateMachine,
    TableStatus,
)


class OccupancyService:
    def __init__(self, state_machine: OccupancyStateMachine | None = None):
        self.state_machine = state_machine or OccupancyStateMachine()

    def _restore_state(self, table: RestaurantTable, sync: bool = False):
        state = self.state_machine.tables.get(table.id)

        if state is not None and not sync and state.status.value == table.status:
            return state

        if state is None:
            state = self.state_machine.register_table(table.id)

        state.status = TableStatus(table.status)

        if state.status == TableStatus.OCCUPIED:
            state.occupied_since = table.last_status_changed_at
        else:
            state.occupied_since = None
            state.last_detected_at = None
            state.absence_started_at = None
            state.presence_started_at = None
            state.service_reminder_sent = False

        return state

    def _current_visit_orders(self, table):
        """Return non-cancelled orders created during the current table visit.

        An order can be created milliseconds before mark_occupied records
        the OCCUPIED transition. Allow a small timestamp tolerance so that
        the first order is not incorrectly excluded from its own visit.
        """
        from datetime import timedelta

        visit_started_at = table.last_status_changed_at or table.created_at
        visit_started_at -= timedelta(seconds=5)

        return select(RestaurantOrder.id).where(
            RestaurantOrder.table_id == table.id,
            RestaurantOrder.status != "CANCELLED",
            RestaurantOrder.created_at >= visit_started_at,
        )

    def mark_occupied(
        self,
        db: Session,
        table_id: int,
        timestamp: datetime | None = None,
    ):
        """Mark a table occupied, including when a customer places an order."""
        table = db.scalar(
            select(RestaurantTable)
            .where(RestaurantTable.id == table_id)
            .with_for_update()
        )

        if table is None:
            raise ValueError("Restaurant table not found")

        now = timestamp or datetime.now().astimezone()
        previous_status = table.status

        state = self._restore_state(table, sync=True)
        state.status = TableStatus.OCCUPIED
        state.occupied_since = (
            table.last_status_changed_at
            if previous_status == TableStatus.OCCUPIED
            else now
        )
        state.last_detected_at = now
        state.absence_started_at = None
        state.presence_started_at = None
        state.service_reminder_sent = False
        state.last_update_at = now

        if previous_status != TableStatus.OCCUPIED:
            table.status = TableStatus.OCCUPIED
            table.last_status_changed_at = now
            db.add(
                OccupancyEvent(
                    table_id=table_id,
                    previous_status=previous_status,
                    new_status=TableStatus.OCCUPIED.value,
                    description=(
                        "Customer placed an order or was detected at the table."
                    ),
                    created_at=now,
                )
            )

        return {
            "table_id": table_id,
            "status": TableStatus.OCCUPIED.value,
        }

    def mark_customer_left(
        self,
        db: Session,
        table_id: int,
        timestamp: datetime | None = None,
    ):
        """Record a confirmed departure, protecting unpaid orders."""
        table = db.scalar(
            select(RestaurantTable)
            .where(RestaurantTable.id == table_id)
            .with_for_update()
        )

        if table is None:
            raise ValueError("Restaurant table not found")

        now = timestamp or datetime.now().astimezone()

        if table.status == TableStatus.NEEDS_CLEANING.value:
            return self.mark_needs_cleaning(
                db,
                table_id,
                description=(
                    "Staff confirmed the customer has left. Table requires cleaning."
                ),
                timestamp=now,
            )

        if table.status != TableStatus.OCCUPIED.value:
            raise ValueError("Only occupied tables can be marked as customer left")

        current_visit_orders = self._current_visit_orders(table)
        has_orders = db.scalar(current_visit_orders.limit(1)) is not None

        unpaid_order_id = db.scalar(
            self._current_visit_orders(table)
            .where(RestaurantOrder.payment_status != "PAID")
            .limit(1)
        )

        if unpaid_order_id is not None:
            alert = db.scalar(
                select(Alert).where(
                    Alert.table_id == table_id,
                    Alert.alert_type == "UNPAID_BILL",
                    Alert.status == "OPEN",
                )
            )
            if alert is None:
                db.add(
                    Alert(
                        table_id=table_id,
                        alert_type="UNPAID_BILL",
                        message=(
                            "Customer has left while an order payment "
                            "is still outstanding."
                        ),
                        created_at=now,
                    )
                )
            db.commit()
            return {
                "table_id": table_id,
                "status": TableStatus.OCCUPIED.value,
                "unpaid_bill": True,
            }

        if not has_orders:
            state = self._restore_state(table, sync=True)
            previous_status = table.status
            state.status = TableStatus.FREE
            state.last_update_at = now
            state.occupied_since = None
            state.last_detected_at = None
            state.absence_started_at = None
            state.presence_started_at = None
            state.service_reminder_sent = False

            table.status = TableStatus.FREE.value
            table.last_status_changed_at = now
            db.add(
                OccupancyEvent(
                    table_id=table_id,
                    previous_status=previous_status,
                    new_status=TableStatus.FREE.value,
                    description="Customer left without placing an order.",
                    created_at=now,
                )
            )
            db.commit()
            return {
                "table_id": table_id,
                "status": TableStatus.FREE.value,
                "unpaid_bill": False,
            }

        return self.mark_needs_cleaning(
            db,
            table_id,
            description=(
                "Staff confirmed the customer has left. Table requires cleaning."
            ),
            timestamp=now,
        )

    def mark_needs_cleaning(
        self,
        db: Session,
        table_id: int,
        description: str = "Customer has left. Table requires cleaning.",
        timestamp: datetime | None = None,
    ):
        """Move a table to cleaning and create at most one open cleaning alert."""
        table = db.scalar(
            select(RestaurantTable)
            .where(RestaurantTable.id == table_id)
            .with_for_update()
        )

        if table is None:
            raise ValueError("Restaurant table not found")

        now = timestamp or datetime.now().astimezone()

        existing_alert = db.scalar(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        )

        if table.status == TableStatus.NEEDS_CLEANING.value:
            self._restore_state(table, sync=True)

            if existing_alert is None:
                existing_alert = Alert(
                    table_id=table_id,
                    alert_type="CLEANING_REQUIRED",
                    message=description,
                    created_at=now,
                )
                db.add(existing_alert)
                db.flush()

                return {
                    "table_id": table_id,
                    "status": table.status,
                    "alert_id": existing_alert.id,
                    "created": True,
                }

            return {
                "table_id": table_id,
                "status": table.status,
                "alert_id": existing_alert.id,
                "created": False,
            }

        previous_status = table.status
        self._restore_state(table, sync=True)

        result = self.state_machine.mark_needs_cleaning(
            table_id=table_id,
            timestamp=now,
        )

        table.status = TableStatus.NEEDS_CLEANING.value
        table.last_status_changed_at = result["timestamp"]

        db.add(
            OccupancyEvent(
                table_id=table_id,
                previous_status=previous_status,
                new_status=TableStatus.NEEDS_CLEANING.value,
                description=description,
                created_at=result["timestamp"],
            )
        )

        alert = existing_alert
        if alert is None:
            alert = Alert(
                table_id=table_id,
                alert_type="CLEANING_REQUIRED",
                message=description,
                created_at=result["timestamp"],
            )
            db.add(alert)

        # Assign the new alert its database ID before returning.
        db.flush()

        return {
            "table_id": table_id,
            "status": TableStatus.NEEDS_CLEANING.value,
            "alert_id": alert.id,
            "created": True,
        }

    def process_detection(
        self,
        db: Session,
        table_id: int,
        occupied: bool,
        timestamp: datetime | None = None,
    ):
        table = db.scalar(select(RestaurantTable).where(RestaurantTable.id == table_id))

        if table is None:
            raise ValueError("Restaurant table not found")

        now = timestamp or datetime.now().astimezone()
        self._restore_state(table)

        has_orders = db.scalar(self._current_visit_orders(table).limit(1)) is not None

        has_unpaid_order = (
            db.scalar(
                self._current_visit_orders(table)
                .where(RestaurantOrder.payment_status != "PAID")
                .limit(1)
            )
            is not None
        )

        # An unpaid departure is recorded as an alert, never as cleaning.
        if not occupied and has_unpaid_order:
            result = self.state_machine.update(
                table_id=table_id,
                occupied=False,
                timestamp=now,
                allow_exit_transition=False,
            )
            state = self.state_machine.tables[table_id]
            departure_confirmed = (
                state.absence_started_at is not None
                and (now - state.absence_started_at).total_seconds()
                >= self.state_machine.config.exit_threshold_seconds
            )

            if departure_confirmed:
                existing_alert = db.scalar(
                    select(Alert).where(
                        Alert.table_id == table_id,
                        Alert.alert_type == "UNPAID_BILL",
                        Alert.status == "OPEN",
                    )
                )
                if existing_alert is None:
                    db.add(
                        Alert(
                            table_id=table_id,
                            alert_type="UNPAID_BILL",
                            message=(
                                "Camera detected customer departure while "
                                "an order payment is outstanding."
                            ),
                            created_at=now,
                        )
                    )
                    db.commit()

                # Keep the table occupied in the state machine until payment.
                result = self.state_machine.update(
                    table_id=table_id,
                    occupied=True,
                    timestamp=now,
                )
                result["status"] = TableStatus.OCCUPIED.value

            return result

        result = self.state_machine.update(
            table_id=table_id,
            occupied=occupied,
            timestamp=now,
            requires_cleaning=has_orders,
        )

        for event in result["events"]:
            if event["event_type"] == "STATUS_CHANGED":
                previous_status = table.status
                new_status = event["status"]

                table.status = new_status
                table.last_status_changed_at = event["timestamp"]

                db.add(
                    OccupancyEvent(
                        table_id=table_id,
                        previous_status=previous_status,
                        new_status=new_status,
                        description=(
                            "Customer left. Table requires cleaning."
                            if new_status == TableStatus.NEEDS_CLEANING.value
                            else (
                                "Customer left without placing an order. "
                                "Table is available."
                            )
                            if new_status == TableStatus.FREE.value
                            else "Table occupancy status changed."
                        ),
                        created_at=event["timestamp"],
                    )
                )

                if new_status == TableStatus.NEEDS_CLEANING.value:
                    existing_alert = db.scalar(
                        select(Alert).where(
                            Alert.table_id == table_id,
                            Alert.alert_type == "CLEANING_REQUIRED",
                            Alert.status == "OPEN",
                        )
                    )
                    if existing_alert is None:
                        db.add(
                            Alert(
                                table_id=table_id,
                                alert_type="CLEANING_REQUIRED",
                                message="Customer has left. Table requires cleaning.",
                                created_at=event["timestamp"],
                            )
                        )

            elif event["event_type"] == "SERVICE_REMINDER":
                db.add(
                    Alert(
                        table_id=table_id,
                        alert_type="SERVICE_REMINDER",
                        message="Table has been occupied for an extended period.",
                        created_at=event["timestamp"],
                    )
                )

        if result["events"]:
            db.commit()

        return result

    def report_cleaning_required(
        self,
        db: Session,
        table_id: int,
        reported_by: str,
        reason: str | None = None,
        timestamp: datetime | None = None,
    ):
        table = db.scalar(
            select(RestaurantTable)
            .where(RestaurantTable.id == table_id)
            .with_for_update()
        )

        if table is None:
            raise ValueError("Restaurant table not found")

        self._restore_state(table, sync=True)

        existing_alert = db.scalar(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        )

        if table.status == TableStatus.NEEDS_CLEANING.value:
            if existing_alert is not None:
                return {
                    "table_id": table_id,
                    "status": table.status,
                    "alert_id": existing_alert.id,
                    "created": False,
                }
            raise ValueError("Table already needs cleaning")

        if table.status != TableStatus.FREE.value:
            raise ValueError("Only vacant tables can be marked for cleaning")

        result = self.state_machine.mark_needs_cleaning(
            table_id=table_id,
            timestamp=timestamp,
        )

        previous_status = table.status
        table.status = TableStatus.NEEDS_CLEANING.value
        table.last_status_changed_at = result["timestamp"]

        message = reason or "Staff reported that this table needs cleaning."

        alert = Alert(
            table_id=table_id,
            alert_type="CLEANING_REQUIRED",
            message=f"{message} Reported by {reported_by}.",
            created_at=result["timestamp"],
        )

        db.add(
            OccupancyEvent(
                table_id=table_id,
                previous_status=previous_status,
                new_status=TableStatus.NEEDS_CLEANING.value,
                description="Staff reported that the table needs cleaning.",
                created_at=result["timestamp"],
            )
        )
        db.add(alert)

        try:
            db.commit()
            db.refresh(alert)
        except Exception:
            db.rollback()
            self.state_machine.tables.pop(table_id, None)
            raise

        return {
            "table_id": table_id,
            "status": TableStatus.NEEDS_CLEANING.value,
            "alert_id": alert.id,
            "created": True,
        }

    def confirm_cleaning(
        self,
        db: Session,
        table_id: int,
        timestamp: datetime | None = None,
    ):
        table = db.scalar(select(RestaurantTable).where(RestaurantTable.id == table_id))

        if table is None:
            raise ValueError("Restaurant table not found")

        unpaid_order_id = db.scalar(
            self._current_visit_orders(table)
            .where(RestaurantOrder.payment_status != "PAID")
            .limit(1)
        )
        if unpaid_order_id is not None:
            raise ValueError("Cannot confirm cleaning while an order is unpaid")

        self._restore_state(table, sync=True)

        result = self.state_machine.confirm_cleaning(
            table_id=table_id,
            timestamp=timestamp,
        )

        previous_status = table.status
        table.status = TableStatus.FREE.value
        table.last_status_changed_at = result["timestamp"]

        db.add(
            OccupancyEvent(
                table_id=table_id,
                previous_status=previous_status,
                new_status=TableStatus.FREE.value,
                description="Staff confirmed table cleaning.",
                created_at=result["timestamp"],
            )
        )

        open_alerts = db.scalars(
            select(Alert).where(
                Alert.table_id == table_id,
                Alert.alert_type == "CLEANING_REQUIRED",
                Alert.status == "OPEN",
            )
        ).all()

        for alert in open_alerts:
            alert.status = "RESOLVED"
            alert.resolved_at = result["timestamp"]

        db.commit()

        return result
