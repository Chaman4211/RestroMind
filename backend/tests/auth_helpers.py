from uuid import uuid4

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.staff_user import StaffUser


def create_test_user(role="OWNER", is_active=True):
    user_id = None

    with SessionLocal() as db:
        user = StaffUser(
            name=f"Permission Test {uuid4().hex[:8]}",
            email=f"permission-{uuid4().hex}@example.com",
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    token = create_access_token(str(user_id))

    return user_id, {
        "Authorization": f"Bearer {token}"
    }


def delete_test_user(user_id):
    with SessionLocal() as db:
        user = db.get(StaffUser, user_id)

        if user is not None:
            db.delete(user)
            db.commit()
