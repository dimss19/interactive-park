import cv2
import logging
from ultralytics import YOLO
import numpy as np
from typing import List, Dict, Any

class PoseDetector:
    def __init__(self, model_path: str, confidence_threshold: float = 0.5, imgsz: int = 640, device: str = "auto", half: bool = True, use_tracker: bool = False):
        self.confidence_threshold = confidence_threshold
        self.imgsz = imgsz
        self.device = self._resolve_device(device)
        self.half = half and self.device != "cpu"
        self.use_tracker = use_tracker
        if device == "auto" and self.device == "cpu":
            logging.warning("CUDA is not available to PyTorch; pose detection will run on CPU and may not reach 30 FPS.")
        try:
            logging.info(f"Loading Pose model (Person) from {model_path} | imgsz={self.imgsz} | device={self.device} | half={self.half} | tracker={self.use_tracker}...")
            self.model = YOLO(model_path)
        except Exception as e:
            logging.error(f"Failed to load pose model: {e}")
            self.model = None
        self._init_preprocessing()

    def _init_preprocessing(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.sharp_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) / 1.0

    def _resolve_device(self, device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        enhanced = cv2.filter2D(enhanced, -1, self.sharp_kernel)
        return enhanced

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        results = []
        if self.model is None:
            return results
        enhanced = self._preprocess(frame)
        kwargs = dict(
            source=enhanced,
            conf=self.confidence_threshold,
            classes=[0],
            imgsz=self.imgsz,
            device=self.device,
            half=self.half,
            verbose=False
        )
        if self.use_tracker:
            kwargs["persist"] = True
            kwargs["tracker"] = "bytetrack.yaml"
            pose_res = self.model.track(**kwargs)
        else:
            pose_res = self.model.predict(**kwargs)

        for r in pose_res:
            boxes = r.boxes
            keypoints = r.keypoints
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                track_id = None
                if self.use_tracker and box.id is not None:
                    track_id = int(box.id[0])
                kpts = []
                if keypoints is not None and i < len(keypoints.data):
                    kpts = keypoints.data[i].cpu().numpy()
                result = {
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "conf": conf,
                    "keypoints": kpts
                }
                if track_id is not None:
                    result["track_id"] = track_id
                results.append(result)
        return results

    def draw(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        skeleton = [
            (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
            (5, 11), (6, 12), (5, 6), (5, 7), (6, 8), (7, 9),
            (8, 10), (1, 2), (0, 1), (0, 2), (1, 3), (2, 4),
            (3, 5), (4, 6)
        ]
        for p in detections:
            x1, y1, x2, y2 = p["bbox"]
            conf = p["conf"]
            label = f"Person {conf:.2f}"
            if "track_id" in p:
                label = f"ID{p['track_id']} {conf:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, max(y1 - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
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
