import cv2
import logging
from typing import Tuple, Optional
import numpy as np

class VideoLoader:
    """Class to handle loading and reading frames from video file or webcam."""

    def __init__(self, source: str | int):
        """
        Initialize video loader.
        :param source: Path to video file (str) or webcam index (int).
        """
        self.source = source
        self.cap: Optional[cv2.VideoCapture] = None

    def load_video(self) -> bool:
        """Open the video capture."""
        try:
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                logging.error(f"Failed to open video source: {self.source}")
                return False
            
            # Set a sane resolution for webcam if necessary, or just rely on default
            if isinstance(self.source, int):
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                
            logging.info(f"Video Loaded from source: {self.source}")
            return True
        except Exception as e:
            logging.error(f"Error loading video {self.source}: {e}")
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read the next frame.
        :return: Tuple of (success, frame)
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None
            
        ret, frame = self.cap.read()
        
        # If video file ends, we might want to loop it or just stop. 
        # For this base project, we just return ret (False if ended).
        return ret, frame

    def reset(self) -> None:
        """Reset video to the first frame (only works for video files)."""
        if self.cap is not None and isinstance(self.source, str):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            logging.info("Video reset to frame 0")

    def release(self) -> None:
        """Release the video capture."""
        if self.cap is not None:
            self.cap.release()
            logging.info("Video capture released")
