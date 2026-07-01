"""CLI: detect vehicles in a video/stream and narrate each one's invented life."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import pathlib

from .narrator import Narrator
from .observe import observe
from .render import annotate, save_snapshot


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a .env in the project root (no dependency)."""
    env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        os.environ.setdefault(key, val)  # real env vars win


def _clock() -> str:
    h = _dt.datetime.now().hour
    if h < 6:
        return "the small hours"
    if h < 11:
        return "morning"
    if h < 14:
        return "midday"
    if h < 18:
        return "late afternoon"
    if h < 22:
        return "evening"
    return "night"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True,
                    help="video file path OR stream/cam URL (anything OpenCV opens)")
    ap.add_argument("--out", default="out", help="snapshot output dir")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--min-track-frames", type=int, default=12,
                    help="frames a vehicle must be seen before it gets a story")
    ap.add_argument("--fps", type=float, default=30.0, help="assumed source fps")
    args = ap.parse_args()

    _load_dotenv()
    narrator = Narrator()
    if narrator.dry:
        print("⚠️  ANTHROPIC_API_KEY not set — running in dry mode (stub stories).")
        print("   Set it and re-run for real narration: export ANTHROPIC_API_KEY=...\n")

    clock = _clock()
    seen_ids: set[int] = set()
    count = 0

    for idx, frame, tracks in observe(args.source, args.max_frames):
        for tid, tr in tracks.items():
            if tr.narrated or tr.frames_seen < args.min_track_frames:
                continue
            tr.narrated = True
            feats = tr.features(args.fps, clock)
            result = narrator.narrate(tid, feats)
            annotated = annotate(frame, tr.last_box,
                                 f"#{tid} {tr.color} {tr.cls_name}", result["story"])
            path = save_snapshot(annotated, args.out, tid, result["archetype"])
            count += 1
            seen_ids.add(tid)
            print(f"[frame {idx}] #{tid} ({result['archetype']}): {result['story']}")
            print(f"            → {path}")

    print(f"\nDone. Narrated {count} vehicle(s) into {args.out}/")


if __name__ == "__main__":
    main()
