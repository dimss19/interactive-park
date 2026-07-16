from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.monitor import MonitorService, check_source
from config.settings import Settings
from utils.logger import setup_logger

settings = Settings("config.yaml")
monitor = MonitorService(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logger()
    monitor.start()
    yield
    monitor.stop()


app = FastAPI(title="Interactive Park Monitor", version="0.1.0", lifespan=lifespan)


@app.get("/")
def dashboard():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/api/status")
def status():
    return monitor.status()


@app.get("/api/source/check")
def source_check(source: str | None = Query(default=None)):
    requested = settings.video_source if source is None else source
    current = monitor.status()
    if str(requested) == str(settings.video_source) and current["running"]:
        return {"source": current["source"], "source_type": current["source_type"],
                "opened": current["source_ok"], "frame_readable": current["frame_width"] > 0,
                "width": current["frame_width"], "height": current["frame_height"],
                "message": "Sumber sedang digunakan pipeline" if current["source_ok"] else current["last_error"]}
    return check_source(requested)


@app.get("/api/sfx")
def sfx_status():
    return monitor.audio.status()


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=settings.web_host, port=settings.web_port, reload=False)
