import cv2
import logging
from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Any

class PoseDetector:
    """Class to detect Person bounding boxes and Skeletons."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        try:
            logging.info(f"Loading Pose model (Person) from {model_path}...")
            self.model = YOLO(model_path)
        except Exception as e:
            logging.error(f"Failed to load pose model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect person and pose in the frame using optimized imgsz=320."""
        results = []
        if self.model is None:
            return results

        # Predict with imgsz=320 for performance
        pose_res = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            classes=[0], # Person only
            imgsz=320,
            verbose=False
        )

        for r in pose_res:
            boxes = r.boxes
            keypoints = r.keypoints
            
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                
                kpts = []
                if keypoints is not None and i < len(keypoints.data):
                    kpts = keypoints.data[i].cpu().numpy()

                results.append({
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "conf": conf,
                    "keypoints": kpts
                })

        return results

    def draw(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Draw bounding boxes and keypoints for persons."""
        skeleton = [
            (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
            (5, 11), (6, 12), (5, 6), (5, 7), (6, 8), (7, 9),
            (8, 10), (1, 2), (0, 1), (0, 2), (1, 3), (2, 4),
            (3, 5), (4, 6)
        ]

        for p in detections:
            x1, y1, x2, y2 = p["bbox"]
            conf = p["conf"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {conf:.2f}", (x1, max(y1 - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            kpts = p["keypoints"]
            if len(kpts) > 0:
                for x, y, c in kpts:
                    if c > 0.5:
                        cv2.circle(frame, (int(x), int(y)), 4, (0, 0, 255), -1)
                
                for p1, p2 in skeleton:
                    if p1 < len(kpts) and p2 < len(kpts):
                        x1_k, y1_k, c1 = kpts[p1]
                        x2_k, y2_k, c2 = kpts[p2]
                        if c1 > 0.5 and c2 > 0.5:
                            cv2.line(frame, (int(x1_k), int(y1_k)), (int(x2_k), int(y2_k)), (255, 0, 0), 2)

        return frame
