from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.staff_user import StaffUser

client = TestClient(app)


def test_login_and_current_user():
    email = f"auth-test-{uuid4().hex[:12]}@example.com"
    password = "TestPassword123!"
    user_id = None

    db = SessionLocal()

    try:
        user = StaffUser(
            name="Authentication Test User",
            email=email,
            password_hash=hash_password(password),
            role="CLEANING_STAFF",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

        assert login_response.status_code == 200

        token_data = login_response.json()

        assert token_data["access_token"]
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0
        assert token_data["user"]["email"] == email
        assert "password_hash" not in token_data["user"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {token_data['access_token']}"
            },
        )

        assert me_response.status_code == 200
        assert me_response.json()["id"] == user_id
        assert me_response.json()["email"] == email
        assert me_response.json()["role"] == "CLEANING_STAFF"

    finally:
        if user_id is not None:
            user = db.get(StaffUser, user_id)
            if user is not None:
                db.delete(user)
                db.commit()

        db.close()


def test_password_login_rejects_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"test-{uuid4().hex[:12]}@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401


def test_owner_setup_rejects_invalid_setup_key():
    response = client.post(
        "/api/v1/auth/setup-owner",
        json={
            "name": "Test Owner",
            "email": f"owner-{uuid4().hex[:12]}@example.com",
            "password": "StrongTestPassword123!",
            "setup_key": "incorrect-test-key",
        },
    )

    assert response.status_code == 403


def test_current_user_requires_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
