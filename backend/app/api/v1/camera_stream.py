from datetime import UTC, datetime

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool

from app.db.session import SessionLocal
from app.models.camera_source import CameraSource
from app.services.vision.runtime import camera_sessions, vision_pipeline

router = APIRouter(tags=["Live Camera"])

MAX_FRAME_SIZE_BYTES = 2 * 1024 * 1024


def process_camera_frame(camera_source_id: int, frame: np.ndarray):
    with SessionLocal() as db:
        return vision_pipeline.process_frame(
            db=db,
            camera_source_id=camera_source_id,
            frame=frame,
            timestamp=datetime.now(UTC),
        )


@router.websocket("/camera-sources/{camera_source_id}/stream")
async def live_camera_stream(
    websocket: WebSocket,
    camera_source_id: int,
):
    with SessionLocal() as db:
        camera = db.get(CameraSource, camera_source_id)

        if camera is None:
            await websocket.close(code=1008, reason="Camera source not found")
            return

        if not camera.is_active:
            await websocket.close(code=1008, reason="Camera source is inactive")
            return

        if camera.source_type != "LIVE":
            await websocket.close(
                code=1008,
                reason="This camera source does not support live streaming",
            )
            return

    if not camera_sessions.acquire(camera_source_id):
        await websocket.close(
            code=1008,
            reason="This camera is already being processed",
        )
        return

    await websocket.accept()

    try:
        await websocket.send_json({
            "type": "connected",
            "camera_source_id": camera_source_id,
            "message": "Live camera connected",
        })

        while True:
            frame_bytes = await websocket.receive_bytes()

            if not frame_bytes:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty frame received",
                })
                continue

            if len(frame_bytes) > MAX_FRAME_SIZE_BYTES:
                await websocket.send_json({
                    "type": "error",
                    "message": "Frame exceeds the 2 MB limit",
                })
                continue

            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

            if frame is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JPEG frame",
                })
                continue

            result = await run_in_threadpool(
                process_camera_frame,
                camera_source_id,
                frame,
            )

            await websocket.send_json({
                "type": "frame_processed",
                "timestamp": datetime.now(UTC).isoformat(),
                "result": jsonable_encoder(result),
            })

    except WebSocketDisconnect:
        pass

    finally:
        vision_pipeline.reset_tracker(camera_source_id)
        camera_sessions.release(camera_source_id)
