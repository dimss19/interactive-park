import yaml
import os
import logging
from typing import Dict, Any


class Settings:
    """Load and expose application configuration."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        if not os.path.exists(self.config_path):
            logging.warning(f"Config file {self.config_path} not found. Using defaults.")
            self.config = {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
                logging.info(f"Loaded config from {self.config_path}")
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            self.config = {}

    @property
    def video_source(self) -> str | int:
        source = self.config.get("video_source", 0)
        if isinstance(source, str) and source.isdigit():
            return int(source)
        return source

    @property
    def target_fps(self) -> int:
        return int(self.config.get("target_fps", 30))

    @property
    def mapping_enabled(self) -> bool:
        return bool(self.config.get("mapping", {}).get("enabled", True))

    @property
    def areas(self) -> Dict[str, Any]:
        return self.config.get("areas", {})

    @property
    def pose_model_path(self) -> str:
        return self.config.get("models", {}).get("pose_model", "models/yolo11s-pose.pt")

    @property
    def confidence_threshold(self) -> float:
        return float(self.config.get("models", {}).get("confidence_threshold", 0.25))

    @property
    def pose_imgsz(self) -> int:
        return int(self.config.get("models", {}).get("pose_imgsz", 640))

    @property
    def pose_device(self) -> str:
        return str(self.config.get("models", {}).get("pose_device", "cuda:0"))

    @property
    def pose_half(self) -> bool:
        return bool(self.config.get("models", {}).get("pose_half", True))

    @property
    def use_tracker(self) -> bool:
        return bool(self.config.get("models", {}).get("use_tracker", False))

    @property
    def detect_every_n_frames(self) -> int:
        return max(1, int(self.config.get("models", {}).get("detect_every_n_frames", 5)))

    @property
    def draw_debug_overlay(self) -> bool:
        return bool(self.config.get("display", {}).get("draw_debug_overlay", False))

    @property
    def draw_pose_overlay(self) -> bool:
        return bool(self.config.get("display", {}).get("draw_pose_overlay", False))

    @property
    def audio_ambience_path(self) -> str:
        return self.config.get("audio", {}).get("ambience", "assets/audio/ambience.ogg")

    @property
    def audio_plant_touch_path(self) -> str:
        return self.config.get("audio", {}).get("plant_touch", "assets/audio/plant.ogg")

    @property
    def cooldown_seconds(self) -> float:
        return float(self.config.get("audio", {}).get("cooldown_seconds", 5.0))

    @property
    def audio_enabled(self) -> bool:
        return bool(self.config.get("audio", {}).get("enabled", True))

    @property
    def audio_master_volume(self) -> float:
        return max(0.0, min(1.0, float(self.config.get("audio", {}).get("master_volume", 0.8))))

    @property
    def audio_sfx(self) -> Dict[str, Any]:
        configured = self.config.get("audio", {}).get("sfx", {})
        return configured or {
            "ambience": {"path": self.audio_ambience_path, "loop": True},
            "plant_touch": {"path": self.audio_plant_touch_path, "loop": False},
        }

    @property
    def web_host(self) -> str:
        return str(self.config.get("web", {}).get("host", "127.0.0.1"))

    @property
    def web_port(self) -> int:
        return int(self.config.get("web", {}).get("port", 8000))


