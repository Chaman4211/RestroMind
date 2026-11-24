from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.rewards import get_challenge, today_utc
from app.db.session import SessionLocal
from app.main import app
from app.models.restaurant_table import RestaurantTable
from app.models.reward import VisitorRewardAccount, VisitorRewardClaim

client = TestClient(app)


def create_test_table():
    with SessionLocal() as db:
        table = RestaurantTable(
            table_number=f"REWARD-{uuid4().hex[:8]}",
            name="Visitor Rewards Test Table",
            status="FREE",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        return table.id


def cleanup_visitor_rewards(visitor_ids, table_ids):
    with SessionLocal() as db:
        db.query(VisitorRewardClaim).filter(
            VisitorRewardClaim.visitor_id.in_(visitor_ids)
        ).delete(synchronize_session=False)

        db.query(VisitorRewardAccount).filter(
            VisitorRewardAccount.visitor_id.in_(visitor_ids)
        ).delete(synchronize_session=False)

        db.query(RestaurantTable).filter(
            RestaurantTable.id.in_(table_ids)
        ).delete(synchronize_session=False)

        db.commit()


def correct_answer_index():
    return get_challenge(today_utc())["answer"]


def test_different_visitors_can_earn_rewards_at_same_table():
    table_id = create_test_table()
    visitor_one = str(uuid4())
    visitor_two = str(uuid4())
    visitor_ids = [visitor_one, visitor_two]

    try:
        answer_index = correct_answer_index()

        for visitor_id in visitor_ids:
            response = client.post(
                f"/api/v1/rewards/visitor/{visitor_id}/table/{table_id}/answer",
                json={"answer_index": answer_index},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["already_played"] is False
            assert data["correct"] is True
            assert data["points_awarded"] == 10
            assert data["total_points"] == 10

        for visitor_id in visitor_ids:
            response = client.get(
                f"/api/v1/rewards/visitor/{visitor_id}/table/{table_id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["points"] == 10
            assert data["already_played"] is True
            assert data["points_awarded_today"] == 10
    finally:
        cleanup_visitor_rewards(visitor_ids, [table_id])


def test_visitor_cannot_claim_daily_reward_at_another_table():
    first_table_id = create_test_table()
    second_table_id = create_test_table()
    visitor_id = str(uuid4())

    try:
        answer_index = correct_answer_index()

        first_response = client.post(
            f"/api/v1/rewards/visitor/{visitor_id}/table/{first_table_id}/answer",
            json={"answer_index": answer_index},
        )

        assert first_response.status_code == 200
        assert first_response.json()["points_awarded"] == 10
        assert first_response.json()["total_points"] == 10

        second_table_response = client.get(
            f"/api/v1/rewards/visitor/{visitor_id}/table/{second_table_id}"
        )

        assert second_table_response.status_code == 200
        second_table_data = second_table_response.json()
        assert second_table_data["points"] == 10
        assert second_table_data["already_played"] is True

        second_answer_response = client.post(
            f"/api/v1/rewards/visitor/{visitor_id}/table/{second_table_id}/answer",
            json={"answer_index": answer_index},
        )

        assert second_answer_response.status_code == 200
        second_answer_data = second_answer_response.json()
        assert second_answer_data["already_played"] is True
        assert second_answer_data["points_awarded"] == 10
        assert second_answer_data["total_points"] == 10

        with SessionLocal() as db:
            claims = (
                db.query(VisitorRewardClaim)
                .filter(
                    VisitorRewardClaim.visitor_id == visitor_id,
                    VisitorRewardClaim.challenge_date == today_utc(),
                )
                .all()
            )
            assert len(claims) == 1
            assert claims[0].table_id == first_table_id
    finally:
        cleanup_visitor_rewards(
            [visitor_id],
            [first_table_id, second_table_id],
        )
