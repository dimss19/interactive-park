import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
        self._frame_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._latest_jpeg = None
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
            self._thread.join(timeout=5)

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
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            self.loader = VideoLoader(self.settings.video_source)
            if not self.loader.load_video():
                raise RuntimeError(f"Tidak dapat membuka sumber: {self.settings.video_source}")
            self._set_status(source_ok=True)
            self.detector = PoseDetector(
                self.settings.pose_model_path, self.settings.confidence_threshold,
                imgsz=self.settings.pose_imgsz, device=self.settings.pose_device,
                half=self.settings.pose_half)
            persons, future, count = [], None, 0
            started = time.perf_counter()
            while not self._stop.is_set():
                ok, frame = self.loader.read_frame()
                if not ok:
                    if isinstance(self.settings.video_source, str) and os.path.isfile(self.settings.video_source):
                        self.loader.reset()
                        continue
                    raise RuntimeError("Kamera terputus atau frame tidak dapat dibaca")
                count += 1
                if future is not None and future.done():
                    try:
                        persons = future.result()
                    except Exception as exc:
                        logging.error(f"Inference gagal: {exc}")
                    future = None
                if future is None and (count == 1 or count % self.settings.detect_every_n_frames == 0):
                    future = executor.submit(self.detector.detect, frame.copy())

                garden_names, in_garden = set(), []
                for person in persons:
                    area = self.areas.person_in_area_type(person, "garden")
                    if area:
                        in_garden.append(person)
                        garden_names.add(area["name"])
                self.audio.update_ambience(garden_names)
                events = self.touches.update(in_garden)
                self.audio.update_plant_events(events)

                display = frame.copy()
                if self.settings.draw_pose_overlay:
                    display = self.detector.draw(display, persons)
                if self.settings.draw_debug_overlay:
                    display = self.areas.draw(display)
                    display = self.areas.draw_person_area_status(display, persons)
                encoded, jpeg = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if encoded:
                    with self._frame_lock:
                        self._latest_jpeg = jpeg.tobytes()
                height, width = frame.shape[:2]
                elapsed = time.perf_counter() - started
                self._set_status(fps=round(count / elapsed, 1), person_count=len(persons),
                                 active_areas=sorted(garden_names), active_touches=events["active"],
                                 frame_width=width, frame_height=height)
                time.sleep(0.001)
        except Exception as exc:
            logging.exception("Monitor pipeline stopped")
            self._set_status(last_error=str(exc), source_ok=False)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            if self.loader:
                self.loader.release()
            self._set_status(running=False)

    def mjpeg(self) -> Iterator[bytes]:
        while True:
            with self._frame_lock:
                jpeg = self._latest_jpeg
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
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
