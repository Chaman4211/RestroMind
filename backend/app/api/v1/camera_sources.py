import cv2
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.camera_source import CameraSource
from app.schemas.camera_source import (
    CameraSourceCreate,
    CameraSourceResponse,
    CameraSourceUpdate,
)
from app.services.camera.rtsp_encryption import encrypt_rtsp_url
from app.services.video.rtsp_stream_manager import rtsp_stream_manager

router = APIRouter(prefix="/camera-sources", tags=["Camera Sources"])


def _encrypt_camera_url(url: SecretStr) -> str:
    try:
        return encrypt_rtsp_url(url.get_secret_value())
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RTSP encryption is not configured correctly.",
        ) from None


@router.post(
    "",
    response_model=CameraSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_camera_source(
    payload: CameraSourceCreate,
    db: Session = Depends(get_db),
):
    encrypted_url = None

    if payload.source_type == "RTSP":
        encrypted_url = _encrypt_camera_url(payload.rtsp_url)

    camera_source = CameraSource(
        name=payload.name,
        source_type=payload.source_type,
        rtsp_url_encrypted=encrypted_url,
    )

    db.add(camera_source)
    db.commit()
    db.refresh(camera_source)
    return camera_source


@router.get("", response_model=list[CameraSourceResponse])
def list_camera_sources(
    db: Session = Depends(get_db),
):
    statement = select(CameraSource).order_by(CameraSource.id)
    return db.scalars(statement).all()


@router.get("/{camera_source_id}", response_model=CameraSourceResponse)
def get_camera_source(
    camera_source_id: int,
    db: Session = Depends(get_db),
):
    camera_source = db.get(CameraSource, camera_source_id)

    if camera_source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    return camera_source


@router.patch("/{camera_source_id}", response_model=CameraSourceResponse)
def update_camera_source(
    camera_source_id: int,
    payload: CameraSourceUpdate,
    db: Session = Depends(get_db),
):
    camera_source = db.get(CameraSource, camera_source_id)

    if camera_source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    requested_url = update_data.pop("rtsp_url", None)

    new_source_type = update_data.get(
        "source_type",
        camera_source.source_type,
    )

    if requested_url is not None and new_source_type != "RTSP":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An RTSP address can only be used with RTSP cameras.",
        )

    if new_source_type == "RTSP":
        if requested_url is not None:
            camera_source.rtsp_url_encrypted = _encrypt_camera_url(requested_url)
        elif (
            camera_source.source_type != "RTSP" or not camera_source.rtsp_url_encrypted
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="An RTSP camera address is required.",
            )
    else:
        camera_source.rtsp_url_encrypted = None

    for field, value in update_data.items():
        setattr(camera_source, field, value)

    db.commit()
    db.refresh(camera_source)
    return camera_source


@router.delete(
    "/{camera_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_camera_source(
    camera_source_id: int,
    db: Session = Depends(get_db),
):
    camera_source = db.get(CameraSource, camera_source_id)

    if camera_source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    if camera_source.tables:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a camera source assigned to restaurant tables",
        )

    db.delete(camera_source)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{camera_source_id}/rtsp/start")
def start_rtsp_camera(
    camera_source_id: int,
    db: Session = Depends(get_db),
):
    camera = db.get(CameraSource, camera_source_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    if not camera.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Camera source is inactive",
        )

    if camera.source_type != "RTSP" or not camera.rtsp_url_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera does not have a configured RTSP address",
        )

    try:
        started = rtsp_stream_manager.start(
            camera_source_id=camera.id,
            encrypted_url=camera.rtsp_url_encrypted,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RTSP camera configuration could not be decrypted.",
        ) from None

    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera is already being processed",
        )

    return {
        "message": "RTSP camera connection started",
        **rtsp_stream_manager.get_status(camera_source_id),
    }


@router.post("/{camera_source_id}/rtsp/stop")
def stop_rtsp_camera(
    camera_source_id: int,
    db: Session = Depends(get_db),
):
    camera = db.get(CameraSource, camera_source_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    if camera.source_type != "RTSP":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera is not an RTSP source",
        )

    result = rtsp_stream_manager.stop(camera_source_id)

    if result is None:
        return {
            "camera_source_id": camera_source_id,
            "status": "STOPPED",
            "processed_frames": 0,
            "error": None,
        }

    return result


@router.get("/{camera_source_id}/rtsp/status")
def get_rtsp_camera_status(
    camera_source_id: int,
    db: Session = Depends(get_db),
):
    camera = db.get(CameraSource, camera_source_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    if camera.source_type != "RTSP":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera is not an RTSP source",
        )

    result = rtsp_stream_manager.get_status(camera_source_id)

    if result is None:
        return {
            "camera_source_id": camera_source_id,
            "status": "STOPPED",
            "processed_frames": 0,
            "error": None,
        }

    return result


@router.get("/{camera_source_id}/rtsp/frame")
def get_rtsp_camera_frame(
    camera_source_id: int,
    db: Session = Depends(get_db),
):
    camera = db.get(CameraSource, camera_source_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera source not found",
        )

    if camera.source_type != "RTSP":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera is not an RTSP source",
        )

    frame = rtsp_stream_manager.get_latest_frame(camera_source_id)

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No RTSP frame is available yet.",
        )

    success, encoded = cv2.imencode(".jpg", frame)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not encode the camera frame.",
        )

    return Response(
        content=encoded.tobytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )
