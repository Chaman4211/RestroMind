from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.occupancy_event import OccupancyEvent
from app.models.restaurant_table import RestaurantTable
from app.services.occupancy.state_machine import (
    OccupancyStateMachine,
    TableStatus,
)


class OccupancyService:
    def __init__(self, state_machine: OccupancyStateMachine | None = None):
        self.state_machine = state_machine or OccupancyStateMachine()

    def _restore_state(self, table: RestaurantTable):
        if table.id in self.state_machine.tables:
            return

        state = self.state_machine.register_table(table.id)
        state.status = TableStatus(table.status)

        if state.status == TableStatus.OCCUPIED:
            state.occupied_since = table.last_status_changed_at

    def process_detection(
        self,
        db: Session,
        table_id: int,
        occupied: bool,
        timestamp: datetime | None = None,
    ):
        table = db.scalar(
            select(RestaurantTable).where(RestaurantTable.id == table_id)
        )

        if table is None:
            raise ValueError("Restaurant table not found")

        self._restore_state(table)

        result = self.state_machine.update(
            table_id=table_id,
            occupied=occupied,
            timestamp=timestamp,
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
                        description="Table occupancy status changed.",
                        created_at=event["timestamp"],
                    )
                )

                if new_status == TableStatus.NEEDS_CLEANING.value:
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

    def confirm_cleaning(
        self,
        db: Session,
        table_id: int,
        timestamp: datetime | None = None,
    ):
        table = db.scalar(
            select(RestaurantTable).where(RestaurantTable.id == table_id)
        )

        if table is None:
            raise ValueError("Restaurant table not found")

        self._restore_state(table)

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
