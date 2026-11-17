from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.camera_source import CameraSource
from app.services.video.video_processor import VideoProcessor
from app.services.vision.runtime import camera_sessions, vision_pipeline

router = APIRouter(prefix="/camera-sources", tags=["Video Processing"])

MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

video_processor = VideoProcessor(
    pipeline=vision_pipeline,
    frame_interval=5,
)



@router.post("/{camera_source_id}/process-video")
def process_uploaded_video(
    camera_source_id: int,
    file: Annotated[UploadFile, File()],
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

    if camera.source_type != "UPLOAD":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera source does not support video uploads",
        )

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported video format",
        )

    if not camera_sessions.acquire(camera_source_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This camera is already being processed",
        )

    try:
        with TemporaryDirectory(prefix="restromind-video-") as temp_dir:
            video_path = Path(temp_dir) / f"upload{extension}"
            total_size = 0

            with video_path.open("wb") as destination:
                while chunk := file.file.read(1024 * 1024):
                    total_size += len(chunk)

                    if total_size > MAX_VIDEO_SIZE_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail="Video exceeds the 100 MB upload limit",
                        )

                    destination.write(chunk)

            if total_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded video is empty",
                )

            try:
                result = video_processor.process_video(
                    db=db,
                    camera_source_id=camera_source_id,
                    video_path=video_path,
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=str(error),
                ) from error

            return {
                "message": "Video processed successfully",
                "file_name": Path(file.filename or "video").name,
                **result,
            }

    finally:
        camera_sessions.release(camera_source_id)
        file.file.close()
