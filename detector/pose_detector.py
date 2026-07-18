import cv2
import logging
from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Any, Tuple

class PoseDetector:
    """Class to detect person poses (skeleton) using YOLO11 Pose."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.25):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.load_model(model_path)

    def load_model(self, path: str) -> None:
        """Load the YOLO11 pose model."""
        try:
            logging.info(f"Loading Pose model from {path}...")
            self.model = YOLO(path)
            logging.info("Pose model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load pose model: {e}")

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect poses in the frame.
        :param frame: OpenCV BGR frame.
        :return: List of pose detections, containing keypoints.
        """
        poses = []
        if self.model is None:
            return poses

        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            classes=[0], # Only person
            verbose=False
        )

        for r in results:
            if r.keypoints is not None:
                # Iterate through each detected person's keypoints
                for kp_data in r.keypoints.data:
                    keypoints = kp_data.cpu().numpy()
                    poses.append({
                        "keypoints": keypoints
                    })
                    
        return poses

    def draw(self, frame: np.ndarray, poses: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draw skeleton and keypoints on the frame.
        Uses Ultralytics default plotting for simplicity if preferred, 
        or we can draw manually. Here we draw manually to have full control.
        """
        # COCO keypoint connections
        skeleton = [
            (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
            (5, 11), (6, 12), (5, 6), (5, 7), (6, 8), (7, 9),
            (8, 10), (1, 2), (0, 1), (0, 2), (1, 3), (2, 4),
            (3, 5), (4, 6)
        ]

        for pose in poses:
            keypoints = pose["keypoints"]
            
            # Draw keypoints
            for x, y, conf in keypoints:
                if conf > 0.5:
                    cv2.circle(frame, (int(x), int(y)), 4, (0, 0, 255), -1)
                    
            # Draw skeleton connections
            for p1, p2 in skeleton:
                if p1 < len(keypoints) and p2 < len(keypoints):
                    x1, y1, c1 = keypoints[p1]
                    x2, y2, c2 = keypoints[p2]
                    
                    if c1 > 0.5 and c2 > 0.5:
                        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                        
        return frame

    def get_wrists(self, poses: List[Dict[str, Any]]) -> List[Dict[str, Tuple[int, int]]]:
        """
        Extract left and right wrist coordinates for Touch Detection (Milestone 4).
        COCO format: 9 = left wrist, 10 = right wrist
        """
        wrists_list = []
        for pose in poses:
            keypoints = pose["keypoints"]
            wrists = {}
            
            # Check left wrist (index 9)
            if len(keypoints) > 9 and keypoints[9][2] > 0.5:
                wrists["left"] = (int(keypoints[9][0]), int(keypoints[9][1]))
                
            # Check right wrist (index 10)
            if len(keypoints) > 10 and keypoints[10][2] > 0.5:
                wrists["right"] = (int(keypoints[10][0]), int(keypoints[10][1]))
                
            if wrists:
                wrists_list.append(wrists)
                
        return wrists_list

