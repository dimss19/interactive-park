import copy
import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import yaml


class AreaMapper:
    """Interactive first-frame polygon mapper for garden, plants, and walkway."""

    WINDOW_NAME = "Mapping Mode - click polygon points, q to start detection"

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.areas: Dict[str, Dict[str, Any]] = {}
        self.current_key = "garden"
        self.edit_started = set()
        self.controls = [
            "1 garden | 2 left plant | 3 right plant | 4 walkway",
            "Left click add point | Backspace undo | r reset area",
            "Enter commit | s save | q save and start detection",
        ]

    def run(self, frame) -> None:
        self._load_config()
        self._ensure_default_areas(frame)

        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.WINDOW_NAME, self._on_mouse)

        while True:
            cv2.imshow(self.WINDOW_NAME, self._draw(frame.copy()))
            key = cv2.waitKey(30) & 0xFF

            if key in (ord("1"), ord("2"), ord("3"), ord("4")):
                self.current_key = {ord("1"): "garden", ord("2"): "plant_left", ord("3"): "plant_right", ord("4"): "walkway"}[key]
            elif key in (8, 127):
                self._undo_point()
            elif key == ord("r"):
                self._reset_current_area()
            elif key in (13, 10):
                self._commit_current_area()
            elif key == ord("s"):
                self.save()
            elif key == ord("q"):
                self._commit_current_area()
                self.save()
                break

        cv2.destroyWindow(self.WINDOW_NAME)

    def _load_config(self) -> None:
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}
        self.areas = copy.deepcopy(self.config.get("areas", {}))

    def _ensure_default_areas(self, frame) -> None:
        height, width = frame.shape[:2]
        defaults = {
            "garden": {
                "name": "GARDEN_AREA",
                "type": "garden",
                "color": [0, 255, 0],
                "show_overlay": True,
                "polygon": [[0, 0], [width, 0], [width, height], [0, height]],
            },
            "plant_left": {
                "name": "LEFT_PLANT",
                "type": "plant",
                "color": [0, 0, 255],
                "show_overlay": True,
                "polygon": [[0, 50], [400, 50], [200, height], [0, height]],
            },
            "plant_right": {
                "name": "RIGHT_PLANT",
                "type": "plant",
                "color": [255, 0, 0],
                "show_overlay": True,
                "polygon": [[width - 400, 50], [width, 50], [width, height], [width - 200, height]],
            },
            "walkway": {
                "name": "WALKWAY",
                "type": "walkway",
                "color": [255, 255, 255],
                "show_overlay": True,
                "polygon": [[int(width * 0.35), 0], [int(width * 0.65), 0], [int(width * 0.75), height], [int(width * 0.25), height]],
            },
        }

        for key, value in defaults.items():
            self.areas.setdefault(key, value)

    def _on_mouse(self, event, x, y, flags, param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        area = self.areas[self.current_key]
        if self.current_key not in self.edit_started:
            area["polygon"] = []
            self.edit_started.add(self.current_key)
        area.setdefault("polygon", []).append([int(x), int(y)])

    def _undo_point(self) -> None:
        polygon = self.areas[self.current_key].setdefault("polygon", [])
        if polygon:
            polygon.pop()

    def _reset_current_area(self) -> None:
        self.areas[self.current_key]["polygon"] = []
        self.edit_started.add(self.current_key)

    def _commit_current_area(self) -> None:
        polygon = self.areas[self.current_key].get("polygon", [])
        if 0 < len(polygon) < 3:
            logging.warning(f"Area {self.current_key} needs at least 3 points; keeping it for editing.")

    def save(self) -> None:
        self.config["areas"] = self.areas
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, sort_keys=False, allow_unicode=False)
        logging.info(f"Mapping saved to {self.config_path}")

    def _draw(self, frame):
        overlay = frame.copy()
        for key, area in self.areas.items():
            color = tuple(area.get("color", [255, 255, 255]))
            points = [tuple(point) for point in area.get("polygon", [])]

            if len(points) >= 2:
                np_pts = np.array(points, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [np_pts], isClosed=len(points) >= 3, color=color, thickness=2)
                if len(points) >= 3:
                    cv2.fillPoly(overlay, [np_pts], color)

            for idx, point in enumerate(points):
                cv2.circle(frame, point, 5, color, -1)
                cv2.putText(frame, str(idx + 1), (point[0] + 6, point[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            if points:
                cv2.putText(frame, area.get("name", key), points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
        self._draw_hud(frame)
        return frame

    def _draw_hud(self, frame) -> None:
        active = self.areas[self.current_key]
        lines = [f"ACTIVE: {self.current_key} / {active.get('name')} ({active.get('type')})"] + self.controls
        y = 28
        for line in lines:
            cv2.putText(frame, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 4)
            cv2.putText(frame, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1)
            y += 24