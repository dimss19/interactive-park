import logging
import os
import threading
import time
from typing import Any, Dict, Iterable


class AudioManager:
    """Configurable pygame SFX player with a safe no-audio fallback."""

    def __init__(self, sfx: Dict[str, Any] | None = None, enabled: bool = True,
                 master_volume: float = 0.8, log_cooldown: float = 2.0):
        self.playing_ambience: Dict[str, bool] = {}
        self.last_log: Dict[str, float] = {}
        self.log_cooldown = log_cooldown
        self.enabled = enabled
        self.master_volume = max(0.0, min(1.0, master_volume))
        self.sfx_config = sfx or {}
        self.sounds: Dict[str, Any] = {}
        self.channels: Dict[str, Any] = {}
        self._mixer = None
        self._lock = threading.Lock()
        self._initialize_mixer()

    @staticmethod
    def _normalize(value: Any) -> Dict[str, Any]:
        return {"path": value} if isinstance(value, str) else dict(value or {})

    def _initialize_mixer(self) -> None:
        if not self.enabled:
            return
        try:
            import pygame
            pygame.mixer.init()
            self._mixer = pygame.mixer
            for name, raw in self.sfx_config.items():
                cfg = self._normalize(raw)
                path = cfg.get("path", "")
                if path and os.path.isfile(path):
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(self.master_volume * float(cfg.get("volume", 1.0)))
                    self.sounds[name] = sound
                else:
                    logging.warning(f"[AUDIO] SFX '{name}' not loaded; file not found: {path}")
        except Exception as exc:
            logging.warning(f"[AUDIO] Mixer unavailable; continuing without sound: {exc}")

    def status(self) -> Dict[str, Any]:
        items = []
        for name, raw in self.sfx_config.items():
            cfg = self._normalize(raw)
            path = cfg.get("path", "")
            items.append({"name": name, "path": path, "exists": os.path.isfile(path),
                          "loaded": name in self.sounds, "loop": bool(cfg.get("loop", False)),
                          "volume": float(cfg.get("volume", 1.0))})
        return {"enabled": self.enabled, "mixer_ready": self._mixer is not None,
                "master_volume": self.master_volume, "items": items}

    def play(self, name: str, loops: int | None = None) -> bool:
        with self._lock:
            sound = self.sounds.get(name)
            if sound is None:
                logging.warning(f"[AUDIO] Cannot play unloaded SFX: {name}")
                return False
            cfg = self._normalize(self.sfx_config.get(name))
            repeat = loops if loops is not None else (-1 if cfg.get("loop", False) else 0)
            self.channels[name] = sound.play(loops=repeat)
            return True

    def stop(self, name: str) -> bool:
        with self._lock:
            channel = self.channels.pop(name, None)
            if channel is None:
                return False
            channel.stop()
            return True

    def shutdown(self) -> None:
        """Stop channels owned by this manager before configuration reload."""
        with self._lock:
            for channel in self.channels.values():
                if channel is not None:
                    channel.stop()
            self.channels.clear()
            self.playing_ambience.clear()

    def update_ambience(self, active_area_names: Iterable[str]) -> None:
        current_time = time.time()
        active = set(active_area_names)
        for area_name in active:
            if not self.playing_ambience.get(area_name, False):
                self.playing_ambience[area_name] = True
                logging.info(f"[AUDIO] -> START AMBIENCE: {area_name}")
                self.play("ambience")
            elif current_time - self.last_log.get(area_name, 0.0) > self.log_cooldown:
                self.last_log[area_name] = current_time
        for area_name in list(self.playing_ambience):
            if area_name not in active and self.playing_ambience[area_name]:
                self.playing_ambience[area_name] = False
                if not any(self.playing_ambience.values()):
                    self.stop("ambience")

    def update_plant_events(self, events: Dict[str, list], zone_sfx: Dict[str, str] | None = None) -> None:
        routes = zone_sfx or {}
        for zone_name in events.get("touch", []):
            effect = routes.get(zone_name) or (zone_name.lower() if zone_name.lower() in self.sfx_config else "plant_touch")
            logging.info(f"[AUDIO] -> PLAY EFFECT: {effect}")
            self.play(effect, loops=0)
