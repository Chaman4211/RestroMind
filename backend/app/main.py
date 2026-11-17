from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.alerts import router as alerts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.camera_sources import router as camera_sources_router
from app.api.v1.camera_stream import router as camera_stream_router
from app.api.v1.health import router as health_router
from app.api.v1.restaurant_tables import router as restaurant_tables_router
from app.api.v1.staff import router as staff_router
from app.api.v1.video_processing import router as video_processing_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Restaurant table monitoring and service management API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    health_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    auth_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    alerts_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    camera_sources_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    camera_stream_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    restaurant_tables_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    staff_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    video_processing_router,
    prefix=settings.api_v1_prefix,
)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to RestroMind API",
        "docs": "/docs",
    }
