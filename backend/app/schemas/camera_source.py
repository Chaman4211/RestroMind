from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)


CameraSourceType = Literal["UPLOAD", "LIVE", "RTSP"]


def validate_rtsp_url(value: SecretStr) -> None:
    raw_url = value.get_secret_value()

    try:
        parsed = urlsplit(raw_url)

        valid = (
            raw_url == raw_url.strip()
            and not any(character.isspace() for character in raw_url)
            and parsed.scheme.lower() in {"rtsp", "rtsps"}
            and parsed.hostname is not None
        )

        if parsed.port is not None:
            valid = valid and 1 <= parsed.port <= 65535

    except ValueError:
        valid = False

    if not valid:
        raise ValueError(
            "A valid RTSP or RTSPS camera address is required."
        )


class CameraSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    source_type: CameraSourceType
    rtsp_url: SecretStr | None = None

    @model_validator(mode="after")
    def validate_camera_configuration(self):
        if self.source_type == "RTSP":
            if self.rtsp_url is None:
                raise ValueError("An RTSP camera address is required.")

            validate_rtsp_url(self.rtsp_url)

        elif self.rtsp_url is not None:
            raise ValueError(
                "An RTSP address can only be used with RTSP cameras."
            )

        return self


class CameraSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    source_type: CameraSourceType | None = None
    is_active: bool | None = None
    rtsp_url: SecretStr | None = None

    @model_validator(mode="after")
    def validate_rtsp_address(self):
        if self.rtsp_url is not None:
            validate_rtsp_url(self.rtsp_url)

        return self


class CameraSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
