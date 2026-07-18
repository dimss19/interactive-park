import os
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.monitor import MonitorService, check_source
from config.config_lock import config_lock
from config.settings import Settings
from utils.logger import setup_logger
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
VIDEO_DIR = ROOT / "assets" / "videos"
AUDIO_DIR = ROOT / "assets" / "audio"
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".ogg", ".wav", ".mp3"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


settings = Settings(str(CONFIG_PATH))
monitor = MonitorService(settings)


class SourceRequest(BaseModel):
    source: str | int


class MappingRequest(BaseModel):
    areas: Dict[str, Dict[str, Any]]


def read_config() -> Dict[str, Any]:
    with config_lock:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}


def write_config(config: Dict[str, Any]) -> None:
    """Atomically replace YAML so an interrupted save cannot corrupt it."""
    with config_lock:
        temporary = CONFIG_PATH.with_suffix(".yaml.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=True)
        os.replace(temporary, CONFIG_PATH)


def validate_config(config: Dict[str, Any]) -> None:
    """Validate config structure; raises ValueError on critical issues."""
    models = config.get("models", {})
    if models.get("pose_imgsz", 640) not in (256, 384, 448, 512, 640, 736, 832, 960, 1088, 1216, 1280):
        raise ValueError(f"pose_imgsz harus salah satu dari nilai YOLO yang valid: 256-1280")
    conf = models.get("confidence_threshold", 0.25)
    if not (0.0 < conf <= 1.0):
        raise ValueError("confidence_threshold harus antara 0.0 dan 1.0")
    for key, area in config.get("areas", {}).items():
        polygon = area.get("polygon", [])
        if len(polygon) >= 3:
            for point in polygon:
                if len(point) != 2:
                    raise ValueError(f"Area {key}: setiap titik polygon harus [x, y]")
        if area.get("type") not in (None, "garden", "plant", "walkway", "ignore"):
            raise ValueError(f"Area {key}: tipe tidak dikenal '{area.get('type')}'")


def reload_monitor() -> None:
    settings.load_config()
    monitor.reconfigure(settings)


def relative_media_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def list_media(directory: Path, extensions: set[str]) -> list[Dict[str, Any]]:
    directory.mkdir(parents=True, exist_ok=True)
    return [{"name": item.name, "path": relative_media_path(item), "size": item.stat().st_size}
            for item in sorted(directory.iterdir()) if item.is_file() and item.suffix.lower() in extensions]


async def save_upload(upload: UploadFile, directory: Path, extensions: set[str]) -> Path:
    filename = Path(upload.filename or "").name
    if not filename or Path(filename).suffix.lower() not in extensions:
        raise HTTPException(status_code=400, detail="Format file tidak didukung")
    directory.mkdir(parents=True, exist_ok=True)
    destination = (directory / filename).resolve()
    if destination.parent != directory.resolve():
        raise HTTPException(status_code=400, detail="Nama file tidak valid")
    size = 0
    with destination.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > 500 * 1024 * 1024:
                handle.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File melebihi batas 500 MB")
            handle.write(chunk)
    return destination


def validate_areas(areas: Dict[str, Dict[str, Any]]) -> None:
    if not areas:
        raise HTTPException(status_code=400, detail="Minimal satu area harus tersedia")
    for key, area in areas.items():
        if not ID_PATTERN.fullmatch(key):
            raise HTTPException(status_code=400, detail=f"ID area tidak valid: {key}")
        if area.get("type") not in {"garden", "plant", "walkway", "ignore"}:
            raise HTTPException(status_code=400, detail=f"Tipe area tidak valid: {key}")
        polygon = area.get("polygon", [])
        if len(polygon) < 3:
            raise HTTPException(status_code=400, detail=f"Area {key} membutuhkan minimal 3 titik")
        for point in polygon:
            if not isinstance(point, list) or len(point) != 2:
                raise HTTPException(status_code=400, detail=f"Titik polygon {key} tidak valid")


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logger(log_level=settings.log_level)
    monitor.start()
    yield
    monitor.stop()


app = FastAPI(title="Interactive Park Monitor", version="0.2.0", lifespan=lifespan)


@app.get("/")
def dashboard():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/styles.css")
def styles():
    return FileResponse(ROOT / "web" / "styles.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(ROOT / "web" / "app.js", media_type="application/javascript")


@app.get("/api/status")
def status():
    return monitor.status()


@app.get("/api/health")
def health():
    s = monitor.status()
    return {"status": "ok" if s["running"] and s["source_ok"] else "degraded" if s["running"] else "stopped",
            "uptime": -1, "source": s["source"], "source_ok": s["source_ok"],
            "fps": s["fps"], "person_count": s["person_count"]}


@app.get("/api/config")
def web_config():
    config = read_config()
    return {"video_source": config.get("video_source", 0), "areas": config.get("areas", {}),
            "audio": config.get("audio", {}), "target_fps": config.get("target_fps", 30)}


@app.get("/api/media")
def media():
    return {"videos": list_media(VIDEO_DIR, VIDEO_EXTENSIONS),
            "audio": list_media(AUDIO_DIR, AUDIO_EXTENSIONS)}


@app.post("/api/videos/upload")
async def upload_video(file: UploadFile = File(...)):
    path = await save_upload(file, VIDEO_DIR, VIDEO_EXTENSIONS)
    return {"ok": True, "name": path.name, "path": relative_media_path(path)}


@app.post("/api/source")
def select_source(request: SourceRequest):
    source: str | int = request.source
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    if isinstance(source, str):
        candidate = Path(source)
        resolved = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="File video tidak ditemukan")
        source = relative_media_path(resolved) if resolved.is_relative_to(ROOT) else str(resolved)
    config = read_config()
    config["video_source"] = source
    write_config(config)
    try:
        reload_monitor()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "source": source}


@app.get("/api/source/check")
async def source_check(source: str | None = Query(default=None)):
    requested = settings.video_source if source is None else source
    current = monitor.status()
    if str(requested) == str(settings.video_source) and current["running"]:
        return {"source": current["source"], "source_type": current["source_type"],
                "opened": current["source_ok"], "frame_readable": current["frame_width"] > 0,
                "width": current["frame_width"], "height": current["frame_height"],
                "message": "Sumber sedang digunakan pipeline" if current["source_ok"] else current["last_error"]}
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_source, requested)


@app.put("/api/mapping")
def save_mapping(request: MappingRequest):
    validate_areas(request.areas)
    config = read_config()
    config["areas"] = request.areas
    write_config(config)
    try:
        reload_monitor()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "area_count": len(request.areas)}


@app.get("/api/sfx")
def sfx_status():
    return monitor.audio.status()


@app.post("/api/sfx/upload")
async def upload_sfx(name: str = Form(...), volume: float = Form(1.0),
                     loop: bool = Form(False), file: UploadFile = File(...)):
    if not ID_PATTERN.fullmatch(name):
        raise HTTPException(status_code=400, detail="ID SFX hanya boleh berisi huruf, angka, _ dan -")
    path = await save_upload(file, AUDIO_DIR, AUDIO_EXTENSIONS)
    config = read_config()
    audio = config.setdefault("audio", {})
    audio.setdefault("enabled", True)
    audio.setdefault("master_volume", 0.8)
    audio.setdefault("sfx", {})[name] = {
        "path": relative_media_path(path), "volume": max(0.0, min(1.0, volume)), "loop": loop}
    write_config(config)
    reload_monitor()
    return {"ok": True, "name": name, "path": relative_media_path(path)}


@app.delete("/api/sfx/{name}")
def remove_sfx(name: str):
    config = read_config()
    items = config.setdefault("audio", {}).setdefault("sfx", {})
    if name not in items:
        raise HTTPException(status_code=404, detail="SFX tidak ditemukan")
    del items[name]
    for area in config.get("areas", {}).values():
        if area.get("audio") == name:
            area["audio"] = None
    write_config(config)
    reload_monitor()
    return {"ok": True, "name": name}


@app.post("/api/sfx/{name}/play")
def play_sfx(name: str):
    if name not in settings.audio_sfx:
        raise HTTPException(status_code=404, detail="SFX tidak ditemukan")
    if not monitor.audio.play(name, loops=0):
        raise HTTPException(status_code=409, detail="SFX belum dimuat; periksa file dan audio device")
    return {"ok": True, "name": name}


@app.post("/api/sfx/{name}/stop")
def stop_sfx(name: str):
    return {"ok": monitor.audio.stop(name), "name": name}


@app.get("/video-feed")
def video_feed():
    return StreamingResponse(monitor.mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/video-feed/raw")
def raw_video_feed():
    return StreamingResponse(monitor.mjpeg(raw=True), media_type="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, reload=False)





