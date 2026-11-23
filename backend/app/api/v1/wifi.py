from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.models.wifi_settings import WifiSettings
from app.services.wifi_encryption import (
    decrypt_wifi_password,
    encrypt_wifi_password,
)

router = APIRouter(prefix="/wifi", tags=["Restaurant Wi-Fi"])

WIFI_MANAGERS = require_roles("OWNER", "MANAGER", "ASSISTANT_MANAGER")


class WifiUpdate(BaseModel):
    ssid: str = Field(default="", max_length=32)
    password: str | None = Field(default=None, max_length=63)
    is_enabled: bool = False


def get_settings(db: Session) -> WifiSettings | None:
    return db.get(WifiSettings, 1)


@router.get("/settings")
def read_wifi_settings(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(WIFI_MANAGERS),
):
    item = get_settings(db)
    if item is None:
        return {
            "ssid": "",
            "is_enabled": False,
            "password_configured": False,
        }

    return {
        "ssid": item.ssid,
        "is_enabled": item.is_enabled,
        "password_configured": bool(item.password_encrypted),
    }


@router.put("/settings")
def _escape_wifi_value(value: str) -> str:
    escaped = value
    for character in ("\\\\", ";", ",", ":", '"'):
        escaped = escaped.replace(character, "\\\\" + character)
    return escaped


@router.get("/qr")
def read_wifi_qr(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(WIFI_MANAGERS),
):
    item = get_settings(db)
    if (
        item is None
        or not item.is_enabled
        or not item.ssid
        or not item.password_encrypted
    ):
        return {"qr_payload": None}

    password = decrypt_wifi_password(item.password_encrypted)
    payload = (
        f"WIFI:T:WPA;S:{_escape_wifi_value(item.ssid)};"
        f"P:{_escape_wifi_value(password)};;"
    )
    return {"qr_payload": payload}


def update_wifi_settings(
    payload: WifiUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(WIFI_MANAGERS),
):
    ssid = payload.ssid.strip()
    password = payload.password.strip() if payload.password else None

    item = get_settings(db)
    if item is None:
        item = WifiSettings(id=1, ssid="", is_enabled=False)
        db.add(item)

    if payload.is_enabled and not ssid:
        raise HTTPException(status_code=422, detail="Enter the Wi-Fi network name.")

    if password:
        if len(password) < 8:
            raise HTTPException(
                status_code=422,
                detail="Wi-Fi password must contain at least 8 characters.",
            )
        item.password_encrypted = encrypt_wifi_password(password)

    if payload.is_enabled and not (password or item.password_encrypted):
        raise HTTPException(
            status_code=422,
            detail="Enter a Wi-Fi password before enabling customer Wi-Fi.",
        )

    item.ssid = ssid
    item.is_enabled = payload.is_enabled
    db.commit()
    db.refresh(item)

    return {
        "ssid": item.ssid,
        "is_enabled": item.is_enabled,
        "password_configured": bool(item.password_encrypted),
    }


@router.get("/public")
def public_wifi_settings(db: Session = Depends(get_db)):
    item = get_settings(db)

    if (
        item is None
        or not item.is_enabled
        or not item.ssid
        or not item.password_encrypted
    ):
        return {"is_enabled": False}

    return {
        "is_enabled": True,
        "ssid": item.ssid,
        "password": decrypt_wifi_password(item.password_encrypted),
    }
