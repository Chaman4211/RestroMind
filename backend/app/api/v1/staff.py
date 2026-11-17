from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.schemas.staff_user import (
    StaffUserCreate,
    StaffUserResponse,
    StaffUserUpdate,
)

router = APIRouter(prefix="/staff", tags=["Staff"])


@router.post(
    "",
    response_model=StaffUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_staff_member(
    payload: StaffUserCreate,
    db: Session = Depends(get_db),
):
    staff_member = StaffUser(**payload.model_dump())

    try:
        db.add(staff_member)
        db.commit()
        db.refresh(staff_member)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A staff member with this email already exists",
        ) from None

    return staff_member


@router.get("", response_model=list[StaffUserResponse])
def list_staff_members(db: Session = Depends(get_db)):
    statement = select(StaffUser).order_by(StaffUser.name)
    return db.scalars(statement).all()


@router.get("/{staff_id}", response_model=StaffUserResponse)
def get_staff_member(
    staff_id: int,
    db: Session = Depends(get_db),
):
    staff_member = db.get(StaffUser, staff_id)

    if staff_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )

    return staff_member


@router.patch("/{staff_id}", response_model=StaffUserResponse)
def update_staff_member(
    staff_id: int,
    payload: StaffUserUpdate,
    db: Session = Depends(get_db),
):
    staff_member = db.get(StaffUser, staff_id)

    if staff_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Staff name cannot be empty",
        )

    if "role" in update_data and update_data["role"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Staff role cannot be empty",
        )

    for field, value in update_data.items():
        setattr(staff_member, field, value)

    try:
        db.commit()
        db.refresh(staff_member)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A staff member with this email already exists",
        ) from None

    return staff_member


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff_member(
    staff_id: int,
    db: Session = Depends(get_db),
):
    staff_member = db.get(StaffUser, staff_id)

    if staff_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )

    db.delete(staff_member)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
