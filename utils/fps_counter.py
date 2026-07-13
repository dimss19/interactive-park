import time
import cv2
import numpy as np


class FPSCounter:
    """Calculate and draw FPS using a high-resolution timer."""

    def __init__(self):
        self.prev_time = time.perf_counter()
        self.fps = 0.0

    def tick(self) -> None:
        current_time = time.perf_counter()
        time_diff = current_time - self.prev_time
        if time_diff > 0:
            self.fps = 1.0 / time_diff
        self.prev_time = current_time

    def get_fps(self) -> float:
        return self.fps

    def draw(self, frame: np.ndarray) -> np.ndarray:
        label = f"FPS: {self.fps:.1f}"
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        return frame