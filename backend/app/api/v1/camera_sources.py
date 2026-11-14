from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.camera_source import CameraSource
from app.schemas.camera_source import (
    CameraSourceCreate,
    CameraSourceResponse,
    CameraSourceUpdate,
)

router = APIRouter(prefix="/camera-sources", tags=["Camera Sources"])


@router.post(
    "",
    response_model=CameraSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_camera_source(
    payload: CameraSourceCreate,
    db: Session = Depends(get_db),
):
    camera_source = CameraSource(**payload.model_dump())
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
