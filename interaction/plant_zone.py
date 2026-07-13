import cv2
import numpy as np
import logging
from typing import Dict, Any, Tuple

class PlantZoneManager:
    """Manages Interactive Plant Zones (Polygons)."""

    def __init__(self):
        self.zones = {}

    def load(self, config_zones: Dict[str, Any]):
        """Load zones from config dict."""
        self.zones = {}
        for key, zone_data in config_zones.items():
            name = zone_data.get("name", "UNKNOWN")
            color = zone_data.get("color", [255, 255, 255])
            polygon_pts = zone_data.get("polygon", [])
            show_overlay = zone_data.get("show_overlay", True)  # Default: show
            
            if polygon_pts:
                # Convert to numpy array of shape (N, 1, 2) required by OpenCV
                pts = np.array(polygon_pts, np.int32).reshape((-1, 1, 2))
                self.zones[key] = {
                    "name": name,
                    "color": tuple(color),
                    "polygon": pts,
                    "show_overlay": show_overlay
                }
                logging.info(f"Loaded Plant Zone: {name} with {len(polygon_pts)} points (overlay={'ON' if show_overlay else 'OFF'}).")
            else:
                logging.warning(f"Zone {name} has no valid polygon points.")

    def is_inside(self, point: Tuple[int, int], zone_key: str) -> bool:
        """Check if a point is inside a specific zone."""
        if zone_key not in self.zones:
            return False
            
        pts = self.zones[zone_key]["polygon"]
        # measureDist=False means it returns +1, -1, or 0
        res = cv2.pointPolygonTest(pts, point, measureDist=False)
        return res >= 0

    def get_zone(self, point: Tuple[int, int]) -> str:
        """Get the zone name that contains the point."""
        for key, data in self.zones.items():
            pts = data["polygon"]
            if cv2.pointPolygonTest(pts, point, measureDist=False) >= 0:
                return data["name"]
        return "UNKNOWN"

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """Draw the zones as semi-transparent overlays on the frame."""
        overlay = frame.copy()
        
        for key, data in self.zones.items():
            # Skip drawing if show_overlay is disabled for this zone
            if not data.get("show_overlay", True):
                continue
                
            pts = data["polygon"]
            color = data["color"]
            
            # Fill poly
            cv2.fillPoly(overlay, [pts], color)
            
            # Draw outline
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
            
            # Draw label at the top of the bounding box
            x, y, w, h = cv2.boundingRect(pts)
            cv2.putText(frame, data["name"], (x + 10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Blend overlay (only drawn regions will be blended)
        alpha = 0.3
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        return frame
