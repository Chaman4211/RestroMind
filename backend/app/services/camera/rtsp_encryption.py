from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.rtsp_encryption_key

    if not key:
        raise RuntimeError("RTSP encryption key is not configured.")

    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        raise RuntimeError("RTSP encryption key is invalid.") from None


def encrypt_rtsp_url(rtsp_url: str) -> str:
    return _get_fernet().encrypt(rtsp_url.encode()).decode()


def decrypt_rtsp_url(encrypted_url: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted_url.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        raise RuntimeError("Unable to decrypt RTSP camera address.") from None
