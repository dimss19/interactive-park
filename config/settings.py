import yaml
import os
import logging
from typing import Dict, Any

class Settings:
    """Class to load and hold configuration settings."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load YAML configuration from file."""
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
        # Convert to int if it's a digit string representing webcam index
        if isinstance(source, str) and source.isdigit():
            return int(source)
        return source

    @property
    def target_fps(self) -> int:
        return self.config.get("target_fps", 30)

    @property
    def person_model_path(self) -> str:
        return self.config.get("models", {}).get("person_model", "models/yolo11n.pt")

    @property
    def pose_model_path(self) -> str:
        return self.config.get("models", {}).get("pose_model", "models/yolo11n-pose.pt")
        
    @property
    def confidence_threshold(self) -> float:
        return float(self.config.get("models", {}).get("confidence_threshold", 0.5))

    @property
    def pose_imgsz(self) -> int:
        return int(self.config.get("models", {}).get("pose_imgsz", 640))

    @property
    def pose_device(self) -> str:
        return str(self.config.get("models", {}).get("pose_device", "auto"))

    @property
    def pose_half(self) -> bool:
        return bool(self.config.get("models", {}).get("pose_half", True))

    @property
    def plant_zones(self) -> Dict[str, Any]:
        """Returns the dictionary defining plant zones polygons and properties."""
        return self.config.get("plant_zones", {})

    @property
    def audio_ambience_path(self) -> str:
        return self.config.get("audio", {}).get("ambience", "assets/audio/ambience.ogg")

    @property
    def audio_plant_touch_path(self) -> str:
        return self.config.get("audio", {}).get("plant_touch", "assets/audio/plant.ogg")

    @property
    def cooldown_seconds(self) -> float:
        return float(self.config.get("audio", {}).get("cooldown_seconds", 5.0))
