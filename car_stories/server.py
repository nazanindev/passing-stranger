"""Live web viewer. The story lives in the image; interesting clusters are kept.

The server runs the detect→track→narrate pipeline on a background thread, bakes
a few short stories onto the frame, and streams it over a websocket — so the live
image is self-contained. When several stories land at once, it saves that frame
to a gallery on disk. The browser shows the live image + the accumulating gallery.
"""

from __future__ import annotations

import asyncio
import base64
import datetime as _dt
import json
import os
import pathlib
import threading
import time

import cv2
import yaml
from fastapi import Body, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .narration import NarrationManager
from .narrator import Narrator
from .observe import Tracker, iter_snapshots, iter_video
from .render import draw_live

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = pathlib.Path(__file__).resolve().parent / "web"
GALLERY = ROOT / "out" / "gallery"
GALLERY.mkdir(parents=True, exist_ok=True)
MAX_WIDTH = 960

# deployment knobs — a laptop takes the defaults; a small CPU server sets
# CS_MODEL=yolo11s.pt CS_IMGSZ=640 CS_CLASSIFY=0 and stays afloat
MODEL = os.environ.get("CS_MODEL", "yolo11m.pt")
IMGSZ = int(os.environ.get("CS_IMGSZ", "960"))
CLASSIFY = os.environ.get("CS_CLASSIFY", "1") != "0"
MAX_SESSIONS = int(os.environ.get("CS_MAX_SESSIONS", "4"))
# behind a reverse proxy every client looks like loopback, so the curated
# gallery needs a real key: set CS_CURATOR_TOKEN and clip with ?key=<token>
CURATOR_TOKEN = os.environ.get("CS_CURATOR_TOKEN", "")

# one storyteller for the whole house: its novelty memory spans cams, so
# Tokyo and Miami don't tell the same life minutes apart
_narrator = Narrator()

app = FastAPI()
app.mount("/gallery-img", StaticFiles(directory=str(GALLERY)), name="gallery")


def _scene_clock(tz_name: str | None) -> dict:
    """The cam's own local time — a Tokyo cam must not run on this laptop's clock."""
    try:
        import zoneinfo
        now = (_dt.datetime.now(zoneinfo.ZoneInfo(tz_name)) if tz_name
               else _dt.datetime.now())
    except Exception:
        now = _dt.datetime.now()
    h = now.hour
    bucket = ("the small hours" if h < 6 else "morning" if h < 11 else "midday"
              if h < 14 else "late afternoon" if h < 18 else "evening"
              if h < 22 else "night")
    return {"clock": bucket, "weekend": now.weekday() >= 5}


def _load_cams() -> dict:
    # CS_CAMS picks the roster: the laptop runs the full global list, the
    # server runs cams-prod.yaml (feeds reachable from a datacenter)
    with open(ROOT / os.environ.get("CS_CAMS", "cams.yaml")) as f:
        return yaml.safe_load(f)


def _resolve_youtube(url: str) -> str:
    """Resolve a YouTube (live) URL to a fresh HLS manifest via yt-dlp."""
    import subprocess
    try:
        out = subprocess.run(
            ["yt-dlp", "-g", "--no-warnings", "-f", "best[height<=720]/best", url],
            capture_output=True, text=True, timeout=40).stdout.strip().splitlines()
        return out[-1] if out else ""
    except Exception:
        return ""


def _frames(cam: dict, stop: threading.Event):
    if cam.get("type") == "snapshot":
        yield from iter_snapshots(cam["source"], cam.get("interval", 1.0), stop=stop)
    elif cam.get("type") == "youtube":
        while not stop.is_set():           # re-resolve when a live manifest expires
            manifest = _resolve_youtube(cam["source"])
            if not manifest:
                stop.wait(5)
                continue
            yield from iter_video(manifest, loop=False, stop=stop)
    else:
        src = cam["source"]
        if not str(src).startswith(("http", "rtsp", "/")):
            src = str(ROOT / src)
        yield from iter_video(src, loop=cam.get("loop", False), stop=stop)


class Session:
    def __init__(self, cam: dict) -> None:
        self.cam = cam
        self.stop = threading.Event()
        self._lock = threading.Lock()
        self._latest: dict | None = None
        self.refs = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def close(self) -> None:
        self.stop.set()

    def get(self) -> dict | None:
        with self._lock:
            return self._latest

    def _run(self) -> None:
        tracker = Tracker(model_path=MODEL, classify=CLASSIFY, imgsz=IMGSZ)
        default_min = 4 if self.cam.get("type") == "snapshot" else 12
        nm = NarrationManager(_narrator,
                              min_frames=self.cam.get("min_frames", default_min),
                              locale=self.cam.get("locale", "default"),
                              vibe=self.cam.get("vibe", ""),
                              region=self.cam.get("region", ""))
        for idx, frame in enumerate(_frames(self.cam, self.stop)):
            if self.stop.is_set():
                break
            if frame.shape[1] > MAX_WIDTH:
                s = MAX_WIDTH / frame.shape[1]
                frame = cv2.resize(frame, (MAX_WIDTH, int(frame.shape[0] * s)))
            # the stream's own metadata is evidence too: the cam's local hour,
            # the day of week, and how much light the street actually has
            scene = _scene_clock(self.cam.get("tz"))
            scene["brightness"] = float(frame[::16, ::16].mean())
            overlays = nm.step(tracker.update(frame, idx), fps=15.0, scene=scene)
            composed = draw_live(frame, overlays)
            ok, buf = cv2.imencode(".jpg", composed, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ok:
                continue
            with self._lock:
                self._latest = {"jpeg": buf.tobytes(), "seq": idx}


@app.get("/")
async def index():
    return FileResponse(WEB / "index.html")


@app.get("/cams")
async def cams():
    return JSONResponse(_load_cams())


def _is_curator(request: Request) -> bool:
    if CURATOR_TOKEN:
        return request.headers.get("x-curator", "") == CURATOR_TOKEN
    return bool(request.client) and request.client.host in ("127.0.0.1", "::1")


_ORDER = GALLERY / "order.json"


def _load_order() -> list[str]:
    try:
        return [str(n) for n in json.loads(_ORDER.read_text())]
    except Exception:
        return []


def _save_order(names: list[str]) -> None:
    _ORDER.write_text(json.dumps(names))


@app.get("/gallery")
async def gallery():
    """Curator's order first-class: arranged clips in their order, new
    (unarranged) clips on top, newest first."""
    files = {p.name: p for p in GALLERY.glob("*.jpg")}
    ordered = [n for n in _load_order() if n in files]
    fresh = sorted((n for n in files if n not in set(ordered)),
                   key=lambda n: files[n].stat().st_mtime, reverse=True)
    return JSONResponse([{"url": f"/gallery-img/{n}", "name": n}
                         for n in (fresh + ordered)[:60]])


@app.post("/gallery/delete")
async def gallery_delete(request: Request, payload: dict = Body(...)):
    if not _is_curator(request):
        return JSONResponse({"error": "the gallery is curated"}, status_code=403)
    name = pathlib.Path(str(payload.get("name", ""))).name   # no traversal
    p = GALLERY / name
    if name.endswith(".jpg") and p.is_file():
        p.unlink()
    _save_order([n for n in _load_order() if n != name])
    return JSONResponse({"ok": True})


@app.post("/gallery/order")
async def gallery_order(request: Request, payload: dict = Body(...)):
    if not _is_curator(request):
        return JSONResponse({"error": "the gallery is curated"}, status_code=403)
    names = [pathlib.Path(str(n)).name for n in payload.get("names", [])][:500]
    _save_order([n for n in names if n.endswith(".jpg")])
    return JSONResponse({"ok": True})


@app.post("/clip")
async def clip(request: Request, payload: dict = Body(...)):
    """Save the frame the curator clipped (base64 JPEG from the browser).
    The gallery is curated by one person: only loopback may clip. (Behind a
    reverse proxy every client looks like loopback — the deploy must put this
    route behind auth or not proxy it at all.)"""
    if not _is_curator(request):
        return JSONResponse({"error": "the gallery is curated"}, status_code=403)
    data = payload.get("jpeg", "")
    if "," in data:
        data = data.split(",", 1)[1]
    name = f"clip-{int(time.time() * 1000)}.jpg"
    (GALLERY / name).write_bytes(base64.b64decode(data))
    return JSONResponse({"url": f"/gallery-img/{name}"})


# one shared session per cam — reconnects and extra tabs must never stack
# duplicate YOLO trackers (each one is a full model on the GPU)
_sessions: dict[str, Session] = {}
_sessions_lock = threading.Lock()


def _acquire(cam: dict) -> Session | None:
    with _sessions_lock:
        s = _sessions.get(cam["id"])
        if s is None or s.stop.is_set():
            live = sum(1 for x in _sessions.values() if not x.stop.is_set())
            if live >= MAX_SESSIONS:
                return None                # every tracker seat is taken
            s = Session(cam)
            _sessions[cam["id"]] = s
            s.start()
        s.refs += 1
        return s


def _release(cam_id: str) -> None:
    with _sessions_lock:
        s = _sessions.get(cam_id)
        if s is not None:
            s.refs -= 1
            if s.refs <= 0:
                s.close()
                del _sessions[cam_id]


@app.get("/stream")
async def stream(cam: str | None = None):
    """Native MJPEG (multipart/x-mixed-replace) — the browser's <img> decodes
    it in C++ with no per-frame JavaScript at all."""
    config = _load_cams()
    cam_id = cam or config.get("default")
    chosen = next((c for c in config["cams"] if c["id"] == cam_id), config["cams"][0])
    session = _acquire(chosen)
    if session is None:                    # full house — the client retries
        return JSONResponse({"error": "every seat taken"}, status_code=503)

    async def gen():
        last_seq = -1
        try:
            while True:
                latest = session.get()
                if latest and latest["seq"] != last_seq:
                    last_seq = latest["seq"]
                    jpg = latest["jpeg"]
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                           + f"Content-Length: {len(jpg)}\r\n\r\n".encode()
                           + jpg + b"\r\n")
                await asyncio.sleep(1 / 15)
        finally:                                   # runs when the client disconnects
            _release(chosen["id"])

    return StreamingResponse(gen(),
                             media_type="multipart/x-mixed-replace; boundary=frame")


def main() -> None:
    import uvicorn
    host = os.environ.get("CS_HOST", "127.0.0.1")
    port = int(os.environ.get("CS_PORT", "8000"))
    print(f"passing stranger → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
