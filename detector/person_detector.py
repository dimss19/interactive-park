import cv2
import logging
from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Any, Tuple
import os

class PersonDetector:
    """Class to detect persons using YOLO11."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.load_model(model_path)

    def load_model(self, path: str) -> None:
        """Load the YOLO11 model. Downloads automatically if not exists."""
        try:
            logging.info(f"Loading Person model from {path}...")
            # Ultralytics will auto-download if path is a recognized standard model e.g., 'yolo11n.pt'
            # We map 'models/yolo11n.pt' -> 'yolo11n.pt' for auto-download, then move it.
            # But passing just the file name or path usually works if it's not found locally.
            self.model = YOLO(path)
            logging.info("Person model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load person model: {e}")

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect persons in the frame.
        :param frame: OpenCV BGR frame.
        :return: List of detections, each is a dict with bbox, conf, class_id.
        """
        detections = []
        if self.model is None:
            return detections

        # Run inference
        # classes=[0] to detect only person
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            classes=[0],
            verbose=False
        )

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                class_id = int(box.cls[0])
                
                detections.append({
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "conf": conf,
                    "class_id": class_id
                })
                
        return detections

    def draw(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draw bounding boxes on the frame.
        :param frame: Original frame.
        :param detections: List of detections.
        :return: Frame with bounding boxes.
        """
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["conf"]
            
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"Person {conf:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - text_h - 5), (x1 + text_w, y1), (0, 255, 0), -1)
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        return frame
