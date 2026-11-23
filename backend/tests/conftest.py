import pytest
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.staff_user import StaffUser


def cleanup_permission_test_users():
    with SessionLocal() as db:
        db.execute(
            delete(StaffUser).where(
                StaffUser.name.like("Permission Test %"),
                StaffUser.email.like("permission-%@example.com"),
                StaffUser.id != 21,
            )
        )
        db.commit()


@pytest.fixture(autouse=True)
def cleanup_test_staff_after_each_test():
    yield
    cleanup_permission_test_users()


def pytest_sessionfinish(session, exitstatus):
    cleanup_permission_test_users()
