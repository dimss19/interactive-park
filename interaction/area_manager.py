import cv2
import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

VISIBLE_KEYPOINT_CONF = 0.25
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12
BODY_CENTER_KEYPOINTS = (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP)


class AreaManager:
    """Loads, checks, and draws user-mapped polygon areas."""

    def __init__(self):
        self.areas: Dict[str, Dict[str, Any]] = {}

    def load(self, config_areas: Dict[str, Any]) -> None:
        self.areas = {}
        for key, area_data in (config_areas or {}).items():
            polygon_pts = area_data.get("polygon", [])
            if len(polygon_pts) < 3:
                logging.warning(f"Area {key} skipped: polygon needs at least 3 points.")
                continue

            pts = np.array(polygon_pts, np.int32).reshape((-1, 1, 2))
            self.areas[key] = {
                "key": key,
                "name": area_data.get("name", key.upper()),
                "type": area_data.get("type", "generic"),
                "color": tuple(area_data.get("color", [255, 255, 255])),
                "polygon": pts,
                "points": polygon_pts,
                "show_overlay": area_data.get("show_overlay", True),
                "audio": area_data.get("audio"),
            }
            logging.info(
                f"Loaded Area: {self.areas[key]['name']} "
                f"type={self.areas[key]['type']} points={len(polygon_pts)}"
            )

    def is_inside(self, point: Tuple[int, int], area_key: str) -> bool:
        area = self.areas.get(area_key)
        if not area:
            return False
        return cv2.pointPolygonTest(area["polygon"], point, measureDist=False) >= 0

    def areas_at_point(self, point: Tuple[int, int], area_type: Optional[str] = None) -> List[Dict[str, Any]]:
        matches = []
        for area in self.areas.values():
            if area_type and area["type"] != area_type:
                continue
            if cv2.pointPolygonTest(area["polygon"], point, measureDist=False) >= 0:
                matches.append(area)
        return matches

    def first_area_at_point(self, point: Tuple[int, int], area_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        matches = self.areas_at_point(point, area_type)
        return matches[0] if matches else None

    def person_center(self, person: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        kpts = person.get("keypoints", [])
        visible_points = [
            (float(kpts[idx][0]), float(kpts[idx][1]))
            for idx in BODY_CENTER_KEYPOINTS
            if len(kpts) > idx and kpts[idx][2] >= VISIBLE_KEYPOINT_CONF
        ]
        if visible_points:
            x = sum(point[0] for point in visible_points) / len(visible_points)
            y = sum(point[1] for point in visible_points) / len(visible_points)
            return int(x), int(y)

        bbox = person.get("bbox")
        if not bbox:
            return None
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    def person_in_area_type(self, person: Dict[str, Any], area_type: str) -> Optional[Dict[str, Any]]:
        center = self.person_center(person)
        if center is None:
            return None
        return self.first_area_at_point(center, area_type)

    def draw_person_area_status(self, frame: np.ndarray, persons: List[Dict[str, Any]]) -> np.ndarray:
        for person in persons:
            center = self.person_center(person)
            if center is None:
                continue
            garden = self.first_area_at_point(center, "garden")
            color = (0, 255, 0) if garden else (0, 0, 255)
            label = garden["name"] if garden else "OUTSIDE_GARDEN"
            cv2.circle(frame, center, 5, color, -1)
            cv2.putText(frame, label, (center[0] + 8, center[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame

    def draw(self, frame: np.ndarray) -> np.ndarray:
        overlay = frame.copy()
        for area in self.areas.values():
            if not area.get("show_overlay", True):
                continue

            pts = area["polygon"]
            color = area["color"]
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

            x, y, _, _ = cv2.boundingRect(pts)
            label = f"{area['name']} ({area['type']})"
            cv2.putText(frame, label, (x + 8, max(y + 24, 24)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
        return frame
