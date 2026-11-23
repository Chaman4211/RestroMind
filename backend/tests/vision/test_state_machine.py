from datetime import UTC, datetime, timedelta

import pytest

from app.services.occupancy.state_machine import (
    OccupancyConfig,
    OccupancyStateMachine,
    TableStatus,
)

START = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)


def create_machine():
    return OccupancyStateMachine(
        OccupancyConfig(
            enter_threshold_seconds=5,
            exit_threshold_seconds=10,
            service_reminder_seconds=1800,
        )
    )


def test_table_starts_free():
    machine = create_machine()

    result = machine.update(1, occupied=False, timestamp=START)

    assert result["status"] == "FREE"


def test_table_becomes_occupied_after_threshold():
    machine = create_machine()

    machine.update(1, True, START)
    result = machine.update(1, True, START + timedelta(seconds=5))

    assert result["status"] == "OCCUPIED"
    assert result["events"][0]["event_type"] == "STATUS_CHANGED"


def test_short_presence_does_not_change_status():
    machine = create_machine()

    machine.update(1, True, START)
    result = machine.update(1, False, START + timedelta(seconds=3))

    assert result["status"] == "FREE"


def test_short_absence_does_not_change_occupied_status():
    machine = create_machine()

    machine.update(1, True, START)
    machine.update(1, True, START + timedelta(seconds=5))

    result = machine.update(1, False, START + timedelta(seconds=8))

    assert result["status"] == "OCCUPIED"


def test_table_becomes_free_after_confirmed_absence():
    machine = create_machine()

    machine.update(1, True, START)
    machine.update(1, True, START + timedelta(seconds=5))

    result = machine.update(1, False, START + timedelta(seconds=20))
    result = machine.update(1, False, START + timedelta(seconds=30))

    assert result["status"] == "NEEDS_CLEANING"
    assert result["events"][-1]["status"] == "NEEDS_CLEANING"


def test_presence_resets_absence_timer():
    machine = create_machine()

    machine.update(1, True, START)
    machine.update(1, True, START + timedelta(seconds=5))
    machine.update(1, False, START + timedelta(seconds=10))

    result = machine.update(1, True, START + timedelta(seconds=18))

    assert result["status"] == "OCCUPIED"


def test_cleaning_confirmation_returns_table_to_free():
    machine = create_machine()

    machine.update(1, True, START)
    machine.update(1, True, START + timedelta(seconds=5))
    machine.update(1, False, START + timedelta(seconds=20))
    machine.update(1, False, START + timedelta(seconds=30))

    machine.tables[1].status = TableStatus.NEEDS_CLEANING

    result = machine.confirm_cleaning(1, START + timedelta(seconds=40))

    assert result["status"] == "FREE"
    assert result["event_type"] == "CLEANING_CONFIRMED"


def test_cleaning_confirmation_requires_cleaning_status():
    machine = create_machine()
    machine.register_table(1)

    with pytest.raises(ValueError):
        machine.confirm_cleaning(1, START)


def test_service_reminder_is_generated_once():
    machine = create_machine()

    machine.update(1, True, START)
    machine.update(1, True, START + timedelta(seconds=5))

    result = machine.update(1, True, START + timedelta(seconds=1805))

    reminders = [
        event for event in result["events"] if event["event_type"] == "SERVICE_REMINDER"
    ]

    assert len(reminders) == 1

    result = machine.update(1, True, START + timedelta(seconds=1810))

    assert not any(
        event["event_type"] == "SERVICE_REMINDER" for event in result["events"]
    )


def test_naive_timestamp_is_rejected():
    machine = create_machine()

    with pytest.raises(ValueError):
        machine.update(
            1,
            True,
            datetime(2026, 11, 13, 10, 0),
        )


def test_presence_timer_restarts_after_interruption():
    machine = create_machine()

    machine.update(1, True, START)
    machine.update(1, False, START + timedelta(seconds=3))

    result = machine.update(1, True, START + timedelta(seconds=10))

    assert result["status"] == "FREE"

    result = machine.update(1, True, START + timedelta(seconds=15))

    assert result["status"] == "OCCUPIED"


def test_older_timestamp_is_rejected():
    machine = create_machine()
    machine.update(1, True, START + timedelta(seconds=10))

    with pytest.raises(ValueError, match="earlier than the previous update"):
        machine.update(1, True, START + timedelta(seconds=5))
