import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.schemas.auth import LoginRequest, OwnerSetupRequest, TokenResponse
from app.schemas.staff_user import StaffUserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/setup-owner", response_model=TokenResponse, status_code=201)
def setup_owner(payload: OwnerSetupRequest, db: Session = Depends(get_db)):
    if not settings.owner_setup_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Owner setup is not configured",
        )

    if not secrets.compare_digest(payload.setup_key, settings.owner_setup_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid owner setup key",
        )

    existing_owner = (
        db.query(StaffUser)
        .filter(
            StaffUser.role == "OWNER",
            StaffUser.password_hash.isnot(None),
        )
        .first()
    )
    if existing_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An owner account has already been created",
        )

    owner = StaffUser(
        name=payload.name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role="OWNER",
        is_active=True,
    )

    db.add(owner)

    try:
        db.commit()
        db.refresh(owner)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered",
        ) from None

    token = create_access_token(str(owner.id))

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=owner,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()

    user = (
        db.query(StaffUser)
        .filter(StaffUser.email == email)
        .first()
    )

    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=user,
    )


@router.get("/me", response_model=StaffUserResponse)
def get_me(current_user: StaffUser = Depends(get_current_user)):
    return current_user
