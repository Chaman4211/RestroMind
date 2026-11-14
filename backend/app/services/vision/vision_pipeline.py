from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.camera_source import CameraSource
from app.models.restaurant_table import RestaurantTable
from app.services.occupancy.occupancy_service import OccupancyService
from app.services.occupancy.runtime import occupancy_service as shared_occupancy_service
from app.services.occupancy.zone_matcher import match_people_to_tables
from app.services.vision.person_tracker import PersonTracker


class VisionPipeline:
    """
    Connect person tracking, table-zone matching, and occupancy processing.

    Each camera source gets its own persistent tracker instance.
    """

    def __init__(
        self,
        occupancy_service: OccupancyService | None = None,
        tracker_factory: Callable[[], PersonTracker] | None = None,
    ):
        self.occupancy_service = (
    occupancy_service
    if occupancy_service is not None
    else shared_occupancy_service
)
        self.tracker_factory = tracker_factory or PersonTracker
        self.trackers: dict[int, PersonTracker] = {}

    def _get_tracker(self, camera_source_id: int):
        if camera_source_id not in self.trackers:
            self.trackers[camera_source_id] = self.tracker_factory()

        return self.trackers[camera_source_id]

    def reset_tracker(self, camera_source_id: int):
        self.trackers.pop(camera_source_id, None)

    def process_frame(
        self,
        db: Session,
        camera_source_id: int,
        frame,
        timestamp: datetime | None = None,
    ):
        if frame is None or len(frame.shape) < 2:
            raise ValueError("A valid video frame is required")

        camera_source = db.scalar(
            select(CameraSource).where(
                CameraSource.id == camera_source_id
            )
        )

        if camera_source is None:
            raise ValueError("Camera source not found")

        if not camera_source.is_active:
            raise ValueError("Camera source is inactive")

        tables = db.scalars(
            select(RestaurantTable).where(
                RestaurantTable.camera_source_id == camera_source_id,
                RestaurantTable.zone_coordinates.is_not(None),
            )
        ).all()

        tracker = self._get_tracker(camera_source_id)
        people = tracker.update(frame)

        frame_height, frame_width = frame.shape[:2]

        table_data = [
            {
                "id": table.id,
                "zone_coordinates": table.zone_coordinates,
            }
            for table in tables
        ]

        assignments = match_people_to_tables(
            people=people,
            tables=table_data,
            frame_width=frame_width,
            frame_height=frame_height,
        )

        occupancy_results = []

        for table in tables:
            table_people = assignments.get(table.id, [])

            result = self.occupancy_service.process_detection(
                db=db,
                table_id=table.id,
                occupied=bool(table_people),
                timestamp=timestamp,
            )

            occupancy_results.append({
                "table_id": table.id,
                "occupied": bool(table_people),
                "person_count": len(table_people),
                "track_ids": table_people,
                "status": result["status"],
                "events": result["events"],
            })

        return {
            "camera_source_id": camera_source_id,
            "people_detected": len(people),
            "table_count": len(tables),
            "assignments": assignments,
            "tables": occupancy_results,
        }
