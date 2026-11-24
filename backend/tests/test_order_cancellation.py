from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.restaurant_order import RestaurantOrder
from app.models.restaurant_order_feedback import RestaurantOrderFeedback
from app.models.restaurant_table import RestaurantTable
from tests.auth_helpers import create_test_user, delete_test_user

client = TestClient(app)


def create_test_order(initial_status="NEW", payment_status="UNPAID"):
    db = SessionLocal()

    table = RestaurantTable(
        table_number=f"CANCEL-{uuid4().hex[:8]}",
        name="Cancellation Test Table",
        status="FREE",
    )
    db.add(table)
    db.commit()
    db.refresh(table)

    order = RestaurantOrder(
        order_number=f"TEST-{uuid4().hex[:12]}",
        public_token=uuid4().hex,
        table_id=table.id,
        customer_name="Cancellation Test",
        status=initial_status,
        payment_status=payment_status,
        total_amount=Decimal("10.00"),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return db, table.id, order.id


def cleanup_test_order(db, table_id, order_id):
    try:
        order = db.get(RestaurantOrder, order_id)
        if order is not None:
            db.delete(order)
            db.commit()

        table = db.get(RestaurantTable, table_id)
        if table is not None:
            db.delete(table)
            db.commit()
    finally:
        db.close()


def test_kitchen_staff_can_cancel_new_order():
    db, table_id, order_id = create_test_order("NEW")
    user_id, headers = create_test_user("KITCHEN_ASSISTANT")

    try:
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=headers,
            json={
                "status": "CANCELLED",
                "cancellation_reason": "Customer changed their mind",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"
        assert data["cancellation_reason"] == "Customer changed their mind"
        assert data["cancelled_at"] is not None

        db.expire_all()
        order = db.get(RestaurantOrder, order_id)
        assert order.status == "CANCELLED"
        assert order.cancellation_reason == "Customer changed their mind"
        assert order.cancelled_at is not None
    finally:
        cleanup_test_order(db, table_id, order_id)
        delete_test_user(user_id)


def test_kitchen_staff_can_cancel_preparing_order():
    db, table_id, order_id = create_test_order("PREPARING")
    user_id, headers = create_test_user("CHEF")

    try:
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=headers,
            json={
                "status": "CANCELLED",
                "cancellation_reason": "Item is unavailable",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"
        assert response.json()["cancelled_at"] is not None
    finally:
        cleanup_test_order(db, table_id, order_id)
        delete_test_user(user_id)


def test_cancellation_requires_a_reason():
    db, table_id, order_id = create_test_order("NEW")
    user_id, headers = create_test_user("KITCHEN_ASSISTANT")

    try:
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=headers,
            json={
                "status": "CANCELLED",
                "cancellation_reason": "  ",
            },
        )

        assert response.status_code == 422

        db.expire_all()
        order = db.get(RestaurantOrder, order_id)
        assert order.status == "NEW"
        assert order.cancelled_at is None
    finally:
        cleanup_test_order(db, table_id, order_id)
        delete_test_user(user_id)


def test_kitchen_staff_cannot_cancel_ready_order():
    db, table_id, order_id = create_test_order("READY")
    user_id, headers = create_test_user("KITCHEN_ASSISTANT")

    try:
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=headers,
            json={
                "status": "CANCELLED",
                "cancellation_reason": "Customer requested cancellation",
            },
        )

        assert response.status_code == 403

        db.expire_all()
        order = db.get(RestaurantOrder, order_id)
        assert order.status == "READY"
        assert order.cancelled_at is None
    finally:
        cleanup_test_order(db, table_id, order_id)
        delete_test_user(user_id)


def test_management_can_cancel_ready_order():
    db, table_id, order_id = create_test_order("READY")
    user_id, headers = create_test_user("OWNER")

    try:
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=headers,
            json={
                "status": "CANCELLED",
                "cancellation_reason": "Management approved cancellation",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"
        assert response.json()["cancellation_reason"] == (
            "Management approved cancellation"
        )
        assert response.json()["cancelled_at"] is not None
    finally:
        cleanup_test_order(db, table_id, order_id)
        delete_test_user(user_id)



def test_customer_can_cancel_new_unpaid_order():
    db, table_id, order_id = create_test_order("NEW", "UNPAID")

    try:
        order = db.get(RestaurantOrder, order_id)
        response = client.post(
            f"/api/v1/orders/track/{order.public_token}/cancel"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"
        assert data["cancellation_reason"] == "Cancelled by customer"
        assert data["cancelled_at"] is not None

        db.expire_all()
        saved_order = db.get(RestaurantOrder, order_id)
        saved_table = db.get(RestaurantTable, table_id)

        assert saved_order.status == "CANCELLED"
        assert saved_order.cancelled_at is not None
        assert saved_table.status == "FREE"
    finally:
        cleanup_test_order(db, table_id, order_id)


@pytest.mark.parametrize(
    ("initial_status", "payment_status"),
    [
        ("PREPARING", "UNPAID"),
        ("READY", "UNPAID"),
        ("NEW", "PENDING"),
        ("NEW", "PAID"),
    ],
)
def test_customer_cannot_cancel_after_preparation_or_payment(
    initial_status,
    payment_status,
):
    db, table_id, order_id = create_test_order(
        initial_status,
        payment_status,
    )

    try:
        order = db.get(RestaurantOrder, order_id)
        response = client.post(
            f"/api/v1/orders/track/{order.public_token}/cancel"
        )

        assert response.status_code == 409

        db.expire_all()
        saved_order = db.get(RestaurantOrder, order_id)
        assert saved_order.status == initial_status
        assert saved_order.cancelled_at is None
    finally:
        cleanup_test_order(db, table_id, order_id)



def test_customer_can_submit_review_and_suggestion():
    db, table_id, order_id = create_test_order("SERVED", "PAID")

    try:
        order = db.get(RestaurantOrder, order_id)
        response = client.post(
            f"/api/v1/orders/track/{order.public_token}/feedback",
            json={
                "rating": 5,
                "feedback": "Food was fresh and tasty.",
                "suggestion": "Please add more vegetarian options.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
        assert data["feedback"] == "Food was fresh and tasty."
        assert data["suggestion"] == "Please add more vegetarian options."
        assert data["created_at"] is not None

        db.expire_all()
        saved = (
            db.query(RestaurantOrderFeedback)
            .filter(RestaurantOrderFeedback.order_id == order_id)
            .one()
        )
        assert saved.rating == 5
        assert saved.feedback == "Food was fresh and tasty."
        assert saved.suggestion == "Please add more vegetarian options."
    finally:
        cleanup_test_order(db, table_id, order_id)


def test_customer_can_retrieve_saved_feedback():
    db, table_id, order_id = create_test_order("SERVED", "PAID")

    try:
        order = db.get(RestaurantOrder, order_id)
        db.add(
            RestaurantOrderFeedback(
                order_id=order_id,
                rating=4,
                feedback="Good service.",
                suggestion="Add more dessert choices.",
            )
        )
        db.commit()

        response = client.get(
            f"/api/v1/orders/track/{order.public_token}/feedback"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 4
        assert data["feedback"] == "Good service."
        assert data["suggestion"] == "Add more dessert choices."
    finally:
        cleanup_test_order(db, table_id, order_id)


def test_customer_gets_null_when_no_feedback_exists():
    db, table_id, order_id = create_test_order("SERVED", "PAID")

    try:
        order = db.get(RestaurantOrder, order_id)
        response = client.get(
            f"/api/v1/orders/track/{order.public_token}/feedback"
        )

        assert response.status_code == 200
        assert response.json() is None
    finally:
        cleanup_test_order(db, table_id, order_id)


def test_customer_cannot_submit_feedback_twice():
    db, table_id, order_id = create_test_order("SERVED", "PAID")

    try:
        order = db.get(RestaurantOrder, order_id)
        url = f"/api/v1/orders/track/{order.public_token}/feedback"

        first_response = client.post(
            url,
            json={"rating": 5, "feedback": "Excellent."},
        )
        second_response = client.post(
            url,
            json={"rating": 2, "feedback": "Changed review."},
        )

        assert first_response.status_code == 200
        assert second_response.status_code == 409

        db.expire_all()
        saved = (
            db.query(RestaurantOrderFeedback)
            .filter(RestaurantOrderFeedback.order_id == order_id)
            .one()
        )
        assert saved.rating == 5
        assert saved.feedback == "Excellent."
    finally:
        cleanup_test_order(db, table_id, order_id)


@pytest.mark.parametrize("payment_status", ["UNPAID", "PENDING"])
def test_customer_cannot_submit_feedback_before_payment(payment_status):
    db, table_id, order_id = create_test_order("SERVED", payment_status)

    try:
        order = db.get(RestaurantOrder, order_id)
        url = f"/api/v1/orders/track/{order.public_token}/feedback"

        post_response = client.post(
            url,
            json={"rating": 5, "suggestion": "More options."},
        )
        get_response = client.get(url)

        assert post_response.status_code == 409
        assert get_response.status_code == 409

        saved = (
            db.query(RestaurantOrderFeedback)
            .filter(RestaurantOrderFeedback.order_id == order_id)
            .first()
        )
        assert saved is None
    finally:
        cleanup_test_order(db, table_id, order_id)


def test_feedback_summary_requires_management_role():
    user_id, headers = create_test_user("WAITER")

    try:
        response = client.get(
            "/api/v1/management/feedback-summary",
            headers=headers,
        )
        assert response.status_code == 403
    finally:
        delete_test_user(user_id)


def test_feedback_summary_is_available_to_management():
    db, table_id, order_id = create_test_order("SERVED", "PAID")
    user_id, headers = create_test_user("OWNER")

    try:
        order = db.get(RestaurantOrder, order_id)
        db.add(
            RestaurantOrderFeedback(
                order_id=order_id,
                rating=5,
                feedback="Great food.",
                suggestion="Keep it up.",
            )
        )
        db.commit()

        response = client.get(
            "/api/v1/management/feedback-summary",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_reviews"] >= 1
        assert data["average_rating"] > 0
        assert any(
            entry["order_number"] == order.order_number
            and entry["rating"] == 5
            and entry["feedback"] == "Great food."
            and entry["suggestion"] == "Keep it up."
            for entry in data["recent_feedback"]
        )
    finally:
        cleanup_test_order(db, table_id, order_id)
        delete_test_user(user_id)


def test_feedback_summary_rejects_unauthenticated_request():
    response = client.get("/api/v1/management/feedback-summary")
    assert response.status_code == 401
