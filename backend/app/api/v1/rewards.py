from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.restaurant_table import RestaurantTable
from app.models.reward import RewardAccount, RewardClaim

router = APIRouter(prefix="/rewards", tags=["Customer Rewards"])

POINTS_PER_CORRECT_ANSWER = 10

CHALLENGES = [
    {
        "question": "Which ingredient is commonly used to make traditional hummus?",
        "options": ["Potatoes", "Chickpeas", "Rice", "Pasta"],
        "answer": 1,
    },
    {
        "question": "Which spice gives many dishes a yellow colour?",
        "options": ["Turmeric", "Black pepper", "Cinnamon", "Cloves"],
        "answer": 0,
    },
    {
        "question": "Basmati is a type of which food?",
        "options": ["Bread", "Cheese", "Rice", "Fruit"],
        "answer": 2,
    },
    {
        "question": "Which of these is commonly used to make a salad?",
        "options": ["Lettuce", "Chocolate", "Flour", "Tea leaves"],
        "answer": 0,
    },
    {
        "question": "Which drink is traditionally made using tea leaves?",
        "options": ["Lassi", "Tea", "Lemonade", "Milkshake"],
        "answer": 1,
    },
]


class RewardAnswer(BaseModel):
    answer_index: int = Field(ge=0, le=3)


def today_utc():
    return datetime.now(timezone.utc).date()


def get_challenge(challenge_date):
    # The same question is shown to every table on a given UTC date.
    return CHALLENGES[challenge_date.toordinal() % len(CHALLENGES)]


def get_or_create_account(db: Session, table_id: int):
    account = (
        db.query(RewardAccount)
        .filter(RewardAccount.table_id == table_id)
        .first()
    )
    if account is None:
        account = RewardAccount(table_id=table_id, points=0)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def validate_table(db: Session, table_id: int):
    if table_id < 1 or db.get(RestaurantTable, table_id) is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")


@router.get("/table/{table_id}")
def get_table_rewards(table_id: int, db: Session = Depends(get_db)):
    validate_table(db, table_id)
    account = get_or_create_account(db, table_id)
    challenge_date = today_utc()
    challenge = get_challenge(challenge_date)

    claim = (
        db.query(RewardClaim)
        .filter(
            RewardClaim.table_id == table_id,
            RewardClaim.challenge_date == challenge_date,
        )
        .first()
    )

    return {
        "table_id": table_id,
        "points": account.points,
        "challenge_date": challenge_date.isoformat(),
        "question": challenge["question"],
        "options": challenge["options"],
        "already_played": claim is not None,
        "last_answer_correct": claim.is_correct if claim else None,
        "points_awarded_today": claim.points_awarded if claim else 0,
    }


@router.post("/table/{table_id}/answer")
def submit_table_reward_answer(
    table_id: int,
    payload: RewardAnswer,
    db: Session = Depends(get_db),
):
    validate_table(db, table_id)
    account = get_or_create_account(db, table_id)
    challenge_date = today_utc()

    existing = (
        db.query(RewardClaim)
        .filter(
            RewardClaim.table_id == table_id,
            RewardClaim.challenge_date == challenge_date,
        )
        .first()
    )
    if existing:
        return {
            "already_played": True,
            "correct": existing.is_correct,
            "points_awarded": existing.points_awarded,
            "total_points": account.points,
        }

    challenge = get_challenge(challenge_date)
    correct = payload.answer_index == challenge["answer"]
    awarded = POINTS_PER_CORRECT_ANSWER if correct else 0

    claim = RewardClaim(
        table_id=table_id,
        challenge_date=challenge_date,
        is_correct=correct,
        points_awarded=awarded,
    )
    account.points += awarded
    db.add(claim)

    try:
        db.commit()
    except IntegrityError:
        # A second device may submit at the same time. The unique database
        # constraint ensures that the same table cannot earn twice that day.
        db.rollback()
        account = get_or_create_account(db, table_id)
        existing = (
            db.query(RewardClaim)
            .filter(
                RewardClaim.table_id == table_id,
                RewardClaim.challenge_date == challenge_date,
            )
            .first()
        )
        return {
            "already_played": True,
            "correct": existing.is_correct if existing else False,
            "points_awarded": existing.points_awarded if existing else 0,
            "total_points": account.points,
        }

    db.refresh(account)
    return {
        "already_played": False,
        "correct": correct,
        "points_awarded": awarded,
        "total_points": account.points,
    }
