from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.core.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> StaffUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        staff_id = int(subject)
    except (InvalidTokenError, ValueError, TypeError):
        raise unauthorized from None

    staff_member = db.get(StaffUser, staff_id)

    if staff_member is None or not staff_member.is_active:
        raise unauthorized

    return staff_member


def require_roles(*allowed_roles: str):
    def role_checker(
        current_user: StaffUser = Depends(get_current_user),
    ) -> StaffUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker
