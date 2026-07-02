"""Draw boxes + captions and write annotated snapshots."""

from __future__ import annotations

import os
import textwrap
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT = cv2.FONT_HERSHEY_SIMPLEX

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Palatino.ttc",
    "/Library/Fonts/Georgia.ttf",
]


def _load_font(size: int):
    for p in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


_STORY_FONT = _load_font(19)

_ITALIC_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
]


def _load_italic(size: int):
    for p in _ITALIC_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return _load_font(size)


_STORY_ITALIC = _load_italic(20)

# per-car accent palette — amber, sky, rose, mint, lilac, gold
PALETTE = [(255, 209, 148), (150, 206, 255), (255, 166, 183),
           (168, 238, 190), (214, 166, 255), (255, 236, 150)]

_MONO_CANDIDATES = ["/System/Library/Fonts/Menlo.ttc",
                    "/System/Library/Fonts/Supplemental/Courier New.ttf"]


def _load_mono(size: int):
    for p in _MONO_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


_MONO = _load_mono(14)   # the "thinking" font


def _draw_caption(frame: np.ndarray, lines: list[str], anchor: tuple[int, int]) -> None:
    x, y = anchor
    pad = 6
    sizes = [cv2.getTextSize(ln, _FONT, 0.5, 1)[0] for ln in lines]
    bw = max(w for w, _ in sizes) + pad * 2
    bh = sum(h for _, h in sizes) + pad * (len(lines) + 1)
    y = max(0, y - bh)
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
    cy = y + pad
    for ln, (_, h) in zip(lines, sizes):
        cy += h
        cv2.putText(frame, ln, (x + pad, cy), _FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cy += pad


def annotate(frame: np.ndarray, box, label: str, story: str) -> np.ndarray:
    out = frame.copy()
    x1, y1, x2, y2 = box
    cv2.rectangle(out, (x1, y1), (x2, y2), (60, 200, 255), 2)
    cv2.putText(out, label, (x1, max(14, y1 - 6)), _FONT, 0.5, (60, 200, 255), 1, cv2.LINE_AA)
    lines = textwrap.wrap(story, width=52) or [""]
    _draw_caption(out, lines, anchor=(x1, y2 + 4 + len(lines) * 20))
    return out


def save_snapshot(frame: np.ndarray, out_dir: str, track_id: int, archetype: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    slug = "".join(c if c.isalnum() else "-" for c in archetype.lower())[:30] or "car"
    path = os.path.join(out_dir, f"car-{track_id:03d}-{slug}.jpg")
    cv2.imwrite(path, frame)
    return path


def _overlaps(a, b) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


# label anchors remembered across frames so text glides instead of teleporting
_ANCHORS: dict[int, list] = {}


def draw_live(frame: np.ndarray, overlays: list[dict]) -> np.ndarray:
    """Dim monospace 'thinking' while a car is read; serif accent story on resolve."""
    live_ids = {o["id"] for o in overlays}
    for tid in [k for k in _ANCHORS if k not in live_ids]:
        del _ANCHORS[tid]
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    gap = 7
    blink = int(time.time() * 2) % 2 == 0

    for o in overlays:                                     # boxes
        x1, y1, x2, y2 = o["box"]
        ac = PALETTE[o["id"] % len(PALETTE)]
        d.rounded_rectangle([x1 - 2, y1 - 2, x2 + 2, y2 + 2], radius=8,
                            outline=ac + (70,), width=6)
        d.rounded_rectangle([x1, y1, x2, y2], radius=6, outline=ac + (245,), width=2)

    placed: list[tuple] = []
    for o in sorted(overlays, key=lambda o: o["box"][1]):
        x1, y1, x2, y2 = o["box"]
        ac = PALETTE[o["id"] % len(PALETTE)]
        if o.get("stage") == "thinking":
            font = _MONO
            lines = [f"· {c}" for c in o.get("chips", [])]
            if not lines:
                continue
            if blink:
                lines[-1] += " |"                          # blinking cursor
            fill = (216, 212, 202)                         # dim, near-white
        else:
            font = _STORY_FONT
            lines = []
            for s in o.get("lines", []):
                lines += textwrap.wrap(s, 26) or [""]
            fill = ac
        lines = lines[:5]
        if not lines:
            continue

        dims = [font.getbbox(ln) for ln in lines]
        lh = max((b[3] - b[1]) for b in dims)
        maxw = max((b[2] - b[0]) for b in dims)
        total = lh * len(lines) + gap * (len(lines) - 1)
        tx = max(6, min(x1 + 2, W - maxw - 6))
        ty = y2 + 10
        if ty + total > H - 6:                             # prefer above if no room below
            ty = max(6, y1 - total - 10)
        step = lh + gap + 4
        for _ in range(14):                                # nudge down until clear
            rect = (tx - 2, ty - 2, tx + maxw + 2, ty + total + 2)
            if not any(_overlaps(rect, p) for p in placed):
                break
            ty += step
            if ty + total > H - 6:
                ty = 6
        # ease toward the target instead of snapping — unless it jumped far
        # (new slot after a collision), in which case follow it immediately
        prev = _ANCHORS.get(o["id"])
        if prev is not None and abs(prev[0] - tx) + abs(prev[1] - ty) < 120:
            tx = int(prev[0] * 0.75 + tx * 0.25)
            ty = int(prev[1] * 0.75 + ty * 0.25)
        _ANCHORS[o["id"]] = [tx, ty]
        placed.append((tx - 2, ty - 2, tx + maxw + 2, ty + total + 2))

        cy = ty
        for ln in lines:                                   # text + soft shadow
            d.text((tx + 1, cy + 1), ln, font=font, fill=(0, 0, 0, 150))
            d.text((tx, cy), ln, font=font, fill=fill + (255,))
            cy += lh + gap
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
