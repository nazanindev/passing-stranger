"""Bake boxes, thinking-chips, and stories onto the live frame."""

from __future__ import annotations

import textwrap
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
        # candidates all tethered to the box — below, above, beside, then small
        # downward nudges. A story that can't sit by its car sits as close as
        # it can; it never flies to the far side of the frame (orphaned text
        # at the top of nowhere reads as a glitch).
        step = lh + gap + 4
        raw = [(x1 + 2, y2 + 10), (x1 + 2, y1 - total - 10),
               (x2 + 12, y1 + 2), (x1 - maxw - 12, y1 + 2)]
        raw += [(x1 + 2, y2 + 10 + step * k) for k in range(1, 7)]
        cands = [(max(6, min(cx_, W - maxw - 6)), max(6, min(cy_, H - total - 6)))
                 for cx_, cy_ in raw]

        def _crowding(c):
            r = (c[0] - 2, c[1] - 2, c[0] + maxw + 2, c[1] + total + 2)
            return sum(max(0, min(r[2], p[2]) - max(r[0], p[0]))
                       * max(0, min(r[3], p[3]) - max(r[1], p[1])) for p in placed)

        tx, ty = min(cands, key=_crowding)                 # least overlap wins
        for c in cands:                                    # but a clear spot wins outright
            if _crowding(c) == 0:
                tx, ty = c
                break
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
