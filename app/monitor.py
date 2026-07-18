import logging
import os
import threading
import time
from typing import Any, Dict, Iterator

import cv2

from audio.audio_manager import AudioManager
from config.settings import Settings
from input.video_loader import VideoLoader
from interaction.area_manager import AreaManager
from interaction.touch_manager import TouchManager
from pose.pose_detector import PoseDetector


class MonitorService:
    """Run one camera/video pipeline and expose its latest frame and status."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = None
        self.detector = None
        self.areas = AreaManager()
        self.areas.load(settings.areas)
        self.touches = TouchManager(0.5, self.areas)
        self.audio = AudioManager(settings.audio_sfx, settings.audio_enabled, settings.audio_master_volume)
        self._thread = None
        self._stop = threading.Event()
        self._lifecycle_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._latest_jpeg = None
        self._latest_raw_jpeg = None
        self._status: Dict[str, Any] = {
            "running": False, "source_ok": False, "source": str(settings.video_source),
            "source_type": "webcam" if isinstance(settings.video_source, int) else "video",
            "fps": 0.0, "person_count": 0, "active_areas": [], "active_touches": [],
            "last_error": None, "frame_width": 0, "frame_height": 0,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="monitor-pipeline")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=20)
            if self._thread.is_alive():
                raise RuntimeError("Pipeline belum berhenti; tunggu inference selesai lalu coba lagi")

    def reconfigure(self, settings: Settings) -> None:
        """Restart the pipeline with settings that were saved from the web UI."""
        with self._lifecycle_lock:
            self.stop()
            self.audio.shutdown()
            self.settings = settings
            self.areas = AreaManager()
            self.areas.load(settings.areas)
            self.touches = TouchManager(0.5, self.areas)
            self.audio = AudioManager(settings.audio_sfx, settings.audio_enabled,
                                      settings.audio_master_volume)
            self.loader = None
            self.detector = None
            self._latest_jpeg = None
            self._latest_raw_jpeg = None
            self._status = {
                "running": False, "source_ok": False, "source": str(settings.video_source),
                "source_type": "webcam" if isinstance(settings.video_source, int) else "video",
                "fps": 0.0, "person_count": 0, "active_areas": [], "active_touches": [],
                "last_error": None, "frame_width": 0, "frame_height": 0,
            }
            self._stop = threading.Event()
            self.start()

    def status(self) -> Dict[str, Any]:
        with self._status_lock:
            result = dict(self._status)
        result["audio"] = self.audio.status()
        return result

    def _set_status(self, **values: Any) -> None:
        with self._status_lock:
            self._status.update(values)

    def _run(self) -> None:
        self._set_status(running=True, last_error=None)
        try:
            self.loader = VideoLoader(self.settings.video_source)
            if not self.loader.load_video():
                raise RuntimeError(f"Tidak dapat membuka sumber: {self.settings.video_source}")
            self._set_status(source_ok=True)
            self.detector = PoseDetector(
                self.settings.pose_model_path, self.settings.confidence_threshold,
                imgsz=self.settings.pose_imgsz, device=self.settings.pose_device,
                half=self.settings.pose_half, use_tracker=self.settings.use_tracker,
                preprocessing_enabled=self.settings.preprocessing_enabled)
            persons, count = [], 0
            started = time.perf_counter()
            target_frame_time = 1.0 / max(self.settings.target_fps, 1)
            while not self._stop.is_set():
                frame_started = time.perf_counter()
                ok, frame = self.loader.read_frame()
                if not ok:
                    if isinstance(self.settings.video_source, str) and os.path.isfile(self.settings.video_source):
                        retry_count = retry_count + 1 if 'retry_count' in dir() else 1
                        if retry_count > 10:
                            raise RuntimeError("Video terlalu sering gagal dibaca setelah reset")
                        self.loader.reset()
                        continue
                    raise RuntimeError("Kamera terputus atau frame tidak dapat dibaca")
                count += 1
                if count == 1 or count % self.settings.detect_every_n_frames == 0:
                    try:
                        persons = self.detector.detect(frame)
                    except Exception as exc:
                        logging.error(f"Inference gagal: {exc}")

                garden_names, in_garden = set(), []
                for person in persons:
                    area = self.areas.person_in_area_type(person, "garden")
                    if area:
                        in_garden.append(person)
                        garden_names.add(area["name"])
                self.audio.update_ambience(garden_names)
                events = self.touches.update(in_garden)
                zone_sfx = {area["name"]: area.get("audio") for area in self.areas.areas.values()
                            if area.get("type") == "plant" and area.get("audio")}
                self.audio.update_plant_events(events, zone_sfx)

                raw_encoded, raw_jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if raw_encoded:
                    with self._frame_lock:
                        self._latest_raw_jpeg = raw_jpeg.tobytes()
                display = frame.copy()
                if self.settings.draw_pose_overlay:
                    display = self.detector.draw(display, persons)
                if self.settings.draw_debug_overlay:
                    display = self.areas.draw(display)
                    display = self.areas.draw_person_area_status(display, persons)
                display = self._draw_interaction_overlay(display, persons, events)
                encoded, jpeg = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if encoded:
                    with self._frame_lock:
                        self._latest_jpeg = jpeg.tobytes()
                height, width = frame.shape[:2]
                elapsed = time.perf_counter() - started
                self._set_status(fps=round(count / elapsed, 1), person_count=len(persons),
                                 active_areas=sorted(garden_names), active_touches=events["active"],
                                 frame_width=width, frame_height=height)
                remaining = target_frame_time - (time.perf_counter() - frame_started)
                if remaining > 0:
                    time.sleep(remaining)
        except Exception as exc:
            logging.exception("Monitor pipeline stopped")
            self._set_status(last_error=str(exc), source_ok=False)
        finally:
            if self.loader:
                self.loader.release()
            self._set_status(running=False)

    def _draw_interaction_overlay(self, frame, persons, events):
        """Highlight wrists and plant contact so interaction is easy to see."""
        active_zones = set(events.get("active", []))
        for person_index, person in enumerate(persons, start=1):
            keypoints = person.get("keypoints", [])
            for keypoint_index, hand_name in ((9, "L"), (10, "R")):
                if len(keypoints) <= keypoint_index or keypoints[keypoint_index][2] < 0.4:
                    continue
                x, y = int(keypoints[keypoint_index][0]), int(keypoints[keypoint_index][1])
                area = self.areas.first_area_at_point((x, y), "plant")
                touching = area is not None
                color = (0, 255, 255) if touching else (255, 255, 0)
                radius = 13 if touching else 8
                cv2.circle(frame, (x, y), radius, color, 3)
                label = f"P{person_index} {hand_name}"
                if area:
                    label += f" TOUCH {area['name']}"
                cv2.putText(frame, label, (x + 12, max(24, y - 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        status = "TOUCH: " + (", ".join(sorted(active_zones)) if active_zones else "-")
        cv2.rectangle(frame, (8, 8), (min(frame.shape[1] - 8, 430), 42), (0, 0, 0), -1)
        cv2.putText(frame, status, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (0, 255, 255) if active_zones else (210, 210, 210), 2)
        return frame

    def mjpeg(self, raw: bool = False) -> Iterator[bytes]:
        stale_frames = 0
        while True:
            with self._frame_lock:
                jpeg = self._latest_raw_jpeg if raw else self._latest_jpeg
            if jpeg:
                stale_frames = 0
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            else:
                stale_frames += 1
                if stale_frames > 125:
                    break
            time.sleep(0.04)


def check_source(source: str | int) -> Dict[str, Any]:
    parsed = int(source) if isinstance(source, str) and source.isdigit() else source
    capture = cv2.VideoCapture(parsed)
    try:
        opened = capture.isOpened()
        ok, frame = capture.read() if opened else (False, None)
        return {"source": str(parsed), "source_type": "webcam" if isinstance(parsed, int) else "video",
                "opened": opened, "frame_readable": bool(ok),
                "width": int(frame.shape[1]) if ok else 0, "height": int(frame.shape[0]) if ok else 0,
                "message": "Sumber siap digunakan" if ok else "Sumber tidak dapat dibuka atau dibaca"}
    finally:
        capture.release()


