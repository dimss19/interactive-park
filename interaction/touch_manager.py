import time
import logging
from typing import List, Dict, Any

# COCO keypoint indices
LEFT_SHOULDER  = 5
RIGHT_SHOULDER = 6
LEFT_HIP       = 11
RIGHT_HIP      = 12
LEFT_WRIST     = 9
RIGHT_WRIST    = 10

VISIBLE_KEYPOINT_CONF = 0.4
BODY_CENTER_KEYPOINTS = (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP)

# Wrist must be this many pixels ABOVE the shoulder to count as "raised"
RAISE_THRESHOLD_PX = 20


class TouchManager:
    """
    Detects 'raised hand toward plants' gestures.

    Logic:
    - Determine person's side from torso skeleton position vs frame midpoint.
    - If the person is on the LEFT side and raises EITHER hand, LEFT_PLANT touches.
    - If the person is on the RIGHT side and raises EITHER hand, RIGHT_PLANT touches.
    - Touch is confirmed after the gesture is held for `touch_duration_threshold` seconds.
    """

    def __init__(self, frame_width: int, touch_duration_threshold: float = 0.5):
        self.frame_midpoint = frame_width // 2
        self.touch_duration_threshold = touch_duration_threshold

        # State per zone
        self.zone_states: Dict[str, Any] = {
            "LEFT_PLANT":  {"is_touching": False, "first_detected_time": 0.0, "triggered": False},
            "RIGHT_PLANT": {"is_touching": False, "first_detected_time": 0.0, "triggered": False},
        }

    def _get_person_side(self, person: Dict[str, Any]) -> str:
        """
        Determine which side of the frame the person is on.
        Uses visible torso keypoints as body center, so raised hands do not
        decide left/right. Falls back to bounding box center if torso is missing.
        Returns 'LEFT_PLANT' or 'RIGHT_PLANT'.
        """
        kpts = person.get("keypoints", [])
        visible_body_x = [
            kpts[idx][0]
            for idx in BODY_CENTER_KEYPOINTS
            if len(kpts) > idx and kpts[idx][2] >= VISIBLE_KEYPOINT_CONF
        ]

        if visible_body_x:
            center_x = sum(visible_body_x) / len(visible_body_x)
        else:
            bbox = person.get("bbox")
            if not bbox:
                return "UNKNOWN"
            x1, _, x2, _ = bbox
            center_x = (x1 + x2) / 2

        return "LEFT_PLANT" if center_x < self.frame_midpoint else "RIGHT_PLANT"

    def _is_any_hand_raised(self, kpts) -> bool:
        """
        Returns True if EITHER the left or right wrist is raised above its respective shoulder.
        """
        def raised(wrist_idx, shoulder_idx):
            if len(kpts) <= max(wrist_idx, shoulder_idx):
                return False
            if kpts[wrist_idx][2] < 0.4 or kpts[shoulder_idx][2] < 0.4:
                return False
            # In image coords Y increases downward, so raised = wrist_y < shoulder_y
            return (kpts[shoulder_idx][1] - kpts[wrist_idx][1]) > RAISE_THRESHOLD_PX

        return raised(LEFT_WRIST, LEFT_SHOULDER) or raised(RIGHT_WRIST, RIGHT_SHOULDER)

    def update(self, persons: List[Dict]):
        """
        Evaluate each detected person's side and hand gesture, then update touch states.
        """
        current_time = time.time()

        # Collect which zones are actively being touched this frame
        active_zones_this_frame = set()

        for person in persons:
            kpts = person.get("keypoints", [])
            if len(kpts) == 0:
                continue

            side = self._get_person_side(person)
            if side == "UNKNOWN":
                continue

            if self._is_any_hand_raised(kpts):
                active_zones_this_frame.add(side)

        # State machine: evaluate each zone
        for z_name, state in self.zone_states.items():
            if z_name in active_zones_this_frame:
                if not state["is_touching"]:
                    # Just started
                    state["is_touching"] = True
                    state["first_detected_time"] = current_time
                    state["triggered"] = False
                else:
                    elapsed = current_time - state["first_detected_time"]
                    if elapsed >= self.touch_duration_threshold and not state["triggered"]:
                        logging.info(f"[EVENT] PLANT_TOUCH - {z_name}")
                        state["triggered"] = True
            else:
                if state["is_touching"]:
                    state["is_touching"] = False
                    if state["triggered"]:
                        logging.info(f"[EVENT] PLANT_RELEASE - {z_name}")
                    state["triggered"] = False
                    state["first_detected_time"] = 0.0
