import time
import logging
from typing import Dict, List, Tuple
from interaction.plant_zone import PlantZoneManager

class TouchManager:
    """Monitors wrists and triggers PLANT_TOUCH / PLANT_RELEASE events."""

    def __init__(self, touch_duration_threshold: float = 0.5):
        self.touch_duration_threshold = touch_duration_threshold
        
        # State tracking per zone. 
        # For simplicity without deep tracking, we track if ANY wrist is in the zone.
        # Format: { "ZONE_NAME": {"is_touching": bool, "first_detected_time": float, "triggered": bool} }
        self.zone_states = {}

    def update(self, wrists: List[Tuple[int, int]], plant_zones: PlantZoneManager):
        """
        Check wrists against zones and trigger events.
        """
        current_time = time.time()
        
        # Determine which zones currently have at least one wrist
        active_zones_current_frame = set()
        
        for w in wrists:
            zone_name = plant_zones.get_zone(w)
            if zone_name != "UNKNOWN":
                active_zones_current_frame.add(zone_name)
                
        # Initialize any new zones in our state dictionary
        for key, data in plant_zones.zones.items():
            z_name = data["name"]
            if z_name not in self.zone_states:
                self.zone_states[z_name] = {
                    "is_touching": False,
                    "first_detected_time": 0.0,
                    "triggered": False
                }

        # Evaluate each zone
        for z_name, state in self.zone_states.items():
            if z_name in active_zones_current_frame:
                # Wrist is currently in this zone
                if not state["is_touching"]:
                    # Just entered
                    state["is_touching"] = True
                    state["first_detected_time"] = current_time
                    state["triggered"] = False
                else:
                    # Already touching, check duration
                    elapsed = current_time - state["first_detected_time"]
                    if elapsed >= self.touch_duration_threshold and not state["triggered"]:
                        logging.info(f"[EVENT] PLANT_TOUCH - {z_name}")
                        state["triggered"] = True
            else:
                # No wrist in this zone
                if state["is_touching"]:
                    # Just left
                    state["is_touching"] = False
                    if state["triggered"]:
                        logging.info(f"[EVENT] PLANT_RELEASE - {z_name}")
                    state["triggered"] = False
                    state["first_detected_time"] = 0.0
