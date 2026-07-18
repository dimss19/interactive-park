import logging
import time
from typing import Any, Dict, List, Tuple

LEFT_WRIST = 9
RIGHT_WRIST = 10
VISIBLE_KEYPOINT_CONF = 0.25
WRIST_KEYPOINTS = (LEFT_WRIST, RIGHT_WRIST)


class TouchManager:
    """Detects wrist touches against mapped plant areas."""

    def __init__(self, touch_duration_threshold: float = 0.5, area_manager: Any = None):
        self.touch_duration_threshold = touch_duration_threshold
        self.area_manager = area_manager
        self.zone_states: Dict[str, Any] = {}

    def _get_visible_wrists(self, kpts) -> List[Tuple[int, int]]:
        wrists = []
        for idx in WRIST_KEYPOINTS:
            if len(kpts) > idx and kpts[idx][2] >= VISIBLE_KEYPOINT_CONF:
                wrists.append((int(kpts[idx][0]), int(kpts[idx][1])))
        return wrists

    def _ensure_state(self, zone_name: str) -> Dict[str, Any]:
        if zone_name not in self.zone_states:
            self.zone_states[zone_name] = {"is_touching": False, "first_detected_time": 0.0, "triggered": False}
        return self.zone_states[zone_name]

    def update(self, persons: List[Dict]) -> Dict[str, List[str]]:
        """Update touch states and return touch/release events for audio or logs."""
        current_time = time.time()
        active_zones_this_frame = set()
        events = {"touch": [], "release": [], "active": []}

        if self.area_manager is None:
            return events

        for person in persons:
            kpts = person.get("keypoints", [])
            if len(kpts) == 0:
                continue

            for wrist_point in self._get_visible_wrists(kpts):
                plant_area = self.area_manager.first_area_at_point(wrist_point, "plant")
                if plant_area:
                    active_zones_this_frame.add(plant_area["name"])

        for zone_name in active_zones_this_frame:
            self._ensure_state(zone_name)

        for zone_name, state in list(self.zone_states.items()):
            if zone_name in active_zones_this_frame:
                events["active"].append(zone_name)
                if not state["is_touching"]:
                    state["is_touching"] = True
                    state["first_detected_time"] = current_time
                    state["triggered"] = False
                else:
                    elapsed = current_time - state["first_detected_time"]
                    if elapsed >= self.touch_duration_threshold and not state["triggered"]:
                        logging.info(f"[EVENT] PLANT_TOUCH - {zone_name}")
                        state["triggered"] = True
                        events["touch"].append(zone_name)
            else:
                if state["is_touching"]:
                    state["is_touching"] = False
                    if state["triggered"]:
                        logging.info(f"[EVENT] PLANT_RELEASE - {zone_name}")
                        events["release"].append(zone_name)
                    state["triggered"] = False
                    state["first_detected_time"] = 0.0

        return events
