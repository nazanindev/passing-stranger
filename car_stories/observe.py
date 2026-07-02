"""Detect + track vehicles and accumulate the *real* observable features.

`Tracker` processes one frame at a time, so it drives live streams and
snapshot cams alike. The narrator consumes the per-track feature dicts
produced here.
"""

from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass, field

import cv2
import numpy as np
from ultralytics import YOLO

from . import style

# COCO class ids for the things we care about.
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
SUBJECT_CLASSES = {0: "person", **VEHICLE_CLASSES}   # people get stories too


@dataclass
class Track:
    track_id: int
    cls_name: str
    first_frame: int
    centers: list[tuple[float, float]] = field(default_factory=list)
    last_frame: int = 0
    last_box: tuple[int, int, int, int] = (0, 0, 0, 0)
    color: str = "unknown"
    rel_size: float = 0.0          # box area / frame area — near/big vs far/small
    rel_x: float = 0.5             # center x / frame width — which lane
    fine_type: str = ""            # ImageNet body-type, only when the crop is big
    class_votes: dict = field(default_factory=dict)  # COCO-class tally → majority vote
    confs: list[float] = field(default_factory=list)  # detector's own certainty
    narrated: bool = False

    @property
    def frames_seen(self) -> int:
        return len(self.centers)

    def median_conf(self) -> float:
        if not self.confs:
            return 1.0
        return float(np.median(self.confs))

    def direction(self) -> str:
        """Net travel direction in screen space (x→right, y→down)."""
        if len(self.centers) < 2:
            return "stationary"
        (x0, y0), (x1, y1) = self.centers[0], self.centers[-1]
        dx, dy = x1 - x0, y1 - y0
        if abs(dx) < 12 and abs(dy) < 12:
            return "barely moving"
        if abs(dx) >= abs(dy):
            return "eastbound" if dx > 0 else "westbound"
        return "approaching the camera" if dy > 0 else "heading away"

    def speed(self) -> str:
        if len(self.centers) < 2:
            return "still"
        deltas = [
            float(np.hypot(b[0] - a[0], b[1] - a[1]))
            for a, b in zip(self.centers, self.centers[1:])
        ]
        avg = float(np.mean(deltas[-10:]))
        if avg < 4:
            return "crawling"
        if avg < 18:
            return "cruising"
        return "racing"

    def recent_deltas(self, n: int = 8) -> list[float]:
        pts = self.centers[-(n + 1):]
        return [float(np.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(pts, pts[1:])]

    def avg_speed(self) -> float:
        d = self.recent_deltas()
        return float(np.mean(d)) if d else 0.0

    def size(self) -> str:
        if self.rel_size > 0.045:
            return "big"
        if self.rel_size > 0.015:
            return "midsize"
        return "small"

    def lane(self) -> str:
        if self.rel_x < 0.34:
            return "left lane"
        if self.rel_x > 0.66:
            return "right lane"
        return "center lane"

    def features(self, fps: float, clock: str | None) -> dict:
        return {
            "vehicle_type": self.cls_name,
            "color": self.color,
            "direction": self.direction(),
            "speed": self.speed(),
            "size": self.size(),
            "lane": self.lane(),
            "fine_type": self.fine_type,
            "time_of_day": clock or "unknown",
        }


def _dominant_color(frame: np.ndarray, box: tuple[int, int, int, int]) -> str:
    """Crude color name from the HSV median of the box's central patch."""
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    cx1, cy1 = max(0, int(x1 + (x2 - x1) * 0.25)), max(0, int(y1 + (y2 - y1) * 0.25))
    cx2, cy2 = min(w, int(x1 + (x2 - x1) * 0.75)), min(h, int(y1 + (y2 - y1) * 0.75))
    if cx2 <= cx1 or cy2 <= cy1:
        return "unknown"
    patch = frame[cy1:cy2, cx1:cx2]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    hue, sat, val = (int(np.median(hsv[:, i])) for i in range(3))
    if val < 50:
        return "black"
    if sat < 40:
        return "white" if val > 170 else "silver"
    if hue < 10 or hue >= 170:
        return "red"
    if hue < 25:
        return "orange"
    if hue < 35:
        return "yellow"
    if hue < 85:
        return "green"
    if hue < 130:
        return "blue"
    return "purple"


class Tracker:
    """Wraps a YOLO model + ByteTrack; feed it frames, get accumulated tracks."""

    def __init__(self, model_path: str = "yolo11m.pt", classify: bool = False,
                 imgsz: int = 960, device: str | None = None) -> None:
        import torch
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.imgsz = imgsz
        self.model = YOLO(model_path)  # auto-downloads on first run
        # optional body-type classifier — only useful on close/large crops
        self.cls = YOLO("yolo11m-cls.pt") if classify else None
        self.tracks: dict[int, Track] = {}

    def update(self, frame: np.ndarray, idx: int = 0) -> dict[int, Track]:
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=list(SUBJECT_CLASSES),
            imgsz=self.imgsz,
            device=self.device,
            conf=0.25,
            # NMS is per-class by default: headlight glare reads as a car and a
            # truck at once, and both boxes survive — two souls on one windshield
            agnostic_nms=True,
            verbose=False,
        )
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return self.tracks

        ids = boxes.id.int().tolist()
        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        clss = boxes.cls.int().tolist()
        confs = boxes.conf.cpu().tolist()

        present = set()
        for tid, box, cls, conf in zip(ids, xyxy, clss, confs):
            present.add(tid)
            x1, y1, x2, y2 = (int(v) for v in box)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            name = SUBJECT_CLASSES.get(cls, "vehicle")
            tr = self.tracks.get(tid)
            if tr is None:
                tr = Track(track_id=tid, cls_name=name, first_frame=idx)
                self.tracks[tid] = tr
            tr.class_votes[name] = tr.class_votes.get(name, 0) + 1
            tr.cls_name = max(tr.class_votes, key=tr.class_votes.get)  # majority over time
            tr.confs.append(float(conf))
            tr.centers.append((cx, cy))
            tr.last_frame = idx
            tr.last_box = (x1, y1, x2, y2)
            fh, fw = frame.shape[:2]
            tr.rel_size = (x2 - x1) * (y2 - y1) / float(fh * fw)
            tr.rel_x = cx / float(fw)
            if tr.color == "unknown" and (x2 - x1) * (y2 - y1) > 1500:
                tr.color = _dominant_color(frame, (x1, y1, x2, y2))
            # classify body-type once, only when the crop is big enough to be legible
            # (0.02 ≈ a car filling a seventh of the frame edge-to-edge; below that
            # ImageNet is dice, and dice is the narrator's job)
            if (self.cls is not None and tr.cls_name != "person" and not tr.fine_type
                    and tr.rel_size > 0.02 and tr.frames_seen % 4 == 0
                    and (x2 - x1) >= 24 and (y2 - y1) >= 24):
                crop = frame[max(0, y1):y2, max(0, x1):x2]
                if crop.size:
                    pr = self.cls(crop, verbose=False, device=self.device)[0].probs
                    name_ = self.cls.names[int(pr.top1)]
                    # keep only vehicle-ish reads we have opinions about — ImageNet
                    # on small crops happily answers "container_ship" for a sedan
                    if float(pr.top1conf) > 0.35 and name_ in style.FINE_KIND:
                        tr.fine_type = name_

        # forget tracks that have been gone a while (keeps the dict bounded)
        for tid in list(self.tracks):
            if tid not in present and idx - self.tracks[tid].last_frame > 60:
                del self.tracks[tid]
        return self.tracks


def iter_video(source, loop: bool = False, max_frames: int | None = None,
               target_fps: float = 15.0, stop=None):
    """Yield frames from a file/stream via OpenCV. Loops files if `loop`."""
    spf = 1.0 / target_fps
    n = 0
    while stop is None or not stop.is_set():
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            break
        while stop is None or not stop.is_set():
            t0 = time.time()
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
            n += 1
            if max_frames is not None and n >= max_frames:
                cap.release()
                return
            dt = time.time() - t0
            if dt < spf:
                time.sleep(spf - dt)
        cap.release()
        if not loop:
            break


def iter_snapshots(url: str, interval: float = 1.0, stop=None):
    """Poll a periodic-JPEG cam URL (no ffmpeg needed) and yield frames."""
    while stop is None or not stop.is_set():
        try:
            data = urllib.request.urlopen(url, timeout=5).read()
            arr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None:
                yield frame
        except Exception:
            pass
        if stop is not None:
            stop.wait(interval)
        else:
            time.sleep(interval)
