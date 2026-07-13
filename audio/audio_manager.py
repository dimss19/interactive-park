import logging
import time
from typing import Dict, Iterable


class AudioManager:
    """Simulates ambience and plant effect audio triggers."""

    def __init__(self, log_cooldown: float = 2.0):
        self.playing_ambience: Dict[str, bool] = {}
        self.last_log: Dict[str, float] = {}
        self.log_cooldown = log_cooldown

    def update_ambience(self, active_area_names: Iterable[str]) -> None:
        current_time = time.time()
        active = set(active_area_names)

        for area_name in active:
            if not self.playing_ambience.get(area_name, False):
                self.playing_ambience[area_name] = True
                logging.info(f"[AUDIO] -> START AMBIENCE: {area_name}")
            elif current_time - self.last_log.get(area_name, 0.0) > self.log_cooldown:
                logging.info(f"[AUDIO] AMBIENCE PLAYING: {area_name}")
                self.last_log[area_name] = current_time

        for area_name in list(self.playing_ambience.keys()):
            if area_name not in active and self.playing_ambience.get(area_name, False):
                self.playing_ambience[area_name] = False
                logging.info(f"[AUDIO] -> STOP AMBIENCE: {area_name}")

    def update_plant_events(self, events: Dict[str, list]) -> None:
        for zone_name in events.get("touch", []):
            logging.info(f"[AUDIO] -> PLAY PLANT EFFECT: {zone_name}")
        for zone_name in events.get("release", []):
            logging.info(f"[AUDIO] -> RELEASE PLANT EFFECT: {zone_name}")