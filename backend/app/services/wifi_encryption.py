import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    secret = settings.jwt_secret_key
    if not secret:
        raise RuntimeError("Application secret is not configured.")

    digest = hashlib.sha256(
        ("restromind-wifi-encryption-v1:" + secret).encode()
    ).digest()

    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_wifi_password(password: str) -> str:
    return _fernet().encrypt(password.encode()).decode()


def decrypt_wifi_password(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        raise RuntimeError(
            "Unable to decrypt the saved Wi-Fi password. Check the application secret."
        ) from None
