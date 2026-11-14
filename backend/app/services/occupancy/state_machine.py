from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class TableStatus(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    NEEDS_CLEANING = "NEEDS_CLEANING"


@dataclass
class OccupancyConfig:
    enter_threshold_seconds: float = 5.0
    exit_threshold_seconds: float = 10.0
    service_reminder_seconds: float = 1800.0


@dataclass
class TableOccupancy:
    table_id: int
    status: TableStatus = TableStatus.FREE
    occupied_since: datetime | None = None
    last_detected_at: datetime | None = None
    absence_started_at: datetime | None = None
    presence_started_at: datetime | None = None
    service_reminder_sent: bool = False
    last_update_at: datetime | None = None


class OccupancyStateMachine:
    def __init__(self, config: OccupancyConfig | None = None):
        self.config = config or OccupancyConfig()
        self.tables: dict[int, TableOccupancy] = {}

    def register_table(self, table_id: int):
        if table_id in self.tables:
            return self.tables[table_id]

        state = TableOccupancy(table_id=table_id)
        self.tables[table_id] = state
        return state

    def update(
        self,
        table_id: int,
        occupied: bool,
        timestamp: datetime | None = None,
    ):
        now = timestamp or datetime.now(UTC)

        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware")

        state = self.register_table(table_id)

        if state.last_update_at is not None and now < state.last_update_at:
            raise ValueError("Timestamp cannot be earlier than the previous update")

        state.last_update_at = now
        events = []

        if occupied:
            state.last_detected_at = now
            state.absence_started_at = None

            if state.status == TableStatus.FREE:
                if state.presence_started_at is None:
                    state.presence_started_at = now

                elapsed = (
                    now - state.presence_started_at
                ).total_seconds()

                if elapsed >= self.config.enter_threshold_seconds:
                    state.status = TableStatus.OCCUPIED
                    state.occupied_since = state.presence_started_at
                    state.service_reminder_sent = False

                    events.append({
                        "event_type": "STATUS_CHANGED",
                        "table_id": table_id,
                        "status": state.status.value,
                        "timestamp": now,
                    })

            elif state.status == TableStatus.OCCUPIED:
                state.presence_started_at = None

        else:
            state.presence_started_at = None

            if state.status == TableStatus.OCCUPIED:
                if state.absence_started_at is None:
                    state.absence_started_at = now

                elapsed = (
                    now - state.absence_started_at
                ).total_seconds()

                if elapsed >= self.config.exit_threshold_seconds:
                    state.status = TableStatus.NEEDS_CLEANING

                    events.append({
                        "event_type": "STATUS_CHANGED",
                        "table_id": table_id,
                        "status": state.status.value,
                        "timestamp": now,
                    })

        if (
            state.status == TableStatus.OCCUPIED
            and state.occupied_since is not None
            and not state.service_reminder_sent
        ):
            elapsed = (
                now - state.occupied_since
            ).total_seconds()

            if elapsed >= self.config.service_reminder_seconds:
                state.service_reminder_sent = True

                events.append({
                    "event_type": "SERVICE_REMINDER",
                    "table_id": table_id,
                    "status": state.status.value,
                    "timestamp": now,
                })

        return {
            "table_id": table_id,
            "status": state.status.value,
            "events": events,
        }

    def confirm_cleaning(self, table_id: int, timestamp: datetime | None = None):
        now = timestamp or datetime.now(UTC)

        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware")

        state = self.tables.get(table_id)

        if state is None:
            raise ValueError("Table is not registered")

        if state.status != TableStatus.NEEDS_CLEANING:
            raise ValueError("Table does not need cleaning")

        state.status = TableStatus.FREE
        state.occupied_since = None
        state.last_detected_at = None
        state.absence_started_at = None
        state.presence_started_at = None
        state.service_reminder_sent = False

        return {
            "table_id": table_id,
            "status": state.status.value,
            "event_type": "CLEANING_CONFIRMED",
            "timestamp": now,
        }
