import time
import logging
from typing import List, Dict, Any

# COCO keypoint indices
LEFT_SHOULDER  = 5
RIGHT_SHOULDER = 6
LEFT_WRIST     = 9
RIGHT_WRIST    = 10

# Wrist must be this many pixels ABOVE the shoulder to count as "raised"
RAISE_THRESHOLD_PX = 20


class TouchManager:
    """
    Detects 'raised hand toward plants' gestures.

    Logic:
    - Determine person's side based on their body center X vs frame midpoint.
    - If the person is on the LEFT side of the frame and raises EITHER hand → LEFT_PLANT TOUCH
    - If the person is on the RIGHT side of the frame and raises EITHER hand → RIGHT_PLANT TOUCH
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

    def _get_person_side(self, kpts) -> str:
        """
        Determine which side of the frame the person is on.
        Uses midpoint between left and right shoulders as body center.
        Falls back to bounding box center if shoulders are not detected.
        Returns 'LEFT_PLANT' or 'RIGHT_PLANT'.
        """
        l_shoulder_conf = kpts[LEFT_SHOULDER][2]  if len(kpts) > LEFT_SHOULDER  else 0
        r_shoulder_conf = kpts[RIGHT_SHOULDER][2] if len(kpts) > RIGHT_SHOULDER else 0

        if l_shoulder_conf > 0.4 and r_shoulder_conf > 0.4:
            center_x = (kpts[LEFT_SHOULDER][0] + kpts[RIGHT_SHOULDER][0]) / 2
        elif l_shoulder_conf > 0.4:
            center_x = kpts[LEFT_SHOULDER][0]
        elif r_shoulder_conf > 0.4:
            center_x = kpts[RIGHT_SHOULDER][0]
        else:
            # Can't determine side from keypoints
            return "UNKNOWN"

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

            side = self._get_person_side(kpts)
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
