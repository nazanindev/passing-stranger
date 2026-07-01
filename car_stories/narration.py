"""Show the machine reading cars as they pass: thinking → resolved story.

Each of the most prominent (closest) cars on screen carries a live overlay. While
it's still being read, you see its observations accrue one by one (the thinking);
the read sharpens as the car moves. Once it's been seen enough, that resolves into
the story. Saving is user-driven (clip button) — nothing auto-saves here.
"""

from __future__ import annotations

import statistics

from . import style
from .narrator import Narrator
from .observe import Track


class NarrationManager:
    def __init__(self, narrator: Narrator, min_frames: int = 12,
                 clock: str = "unknown", max_shown: int = 4,
                 reveal_every: int = 2, locale: str = "default") -> None:
        self.narrator = narrator
        self.min_frames = min_frames
        self.clock = clock
        self.max_shown = max_shown        # how many cars carry an overlay at once
        self.reveal_every = reveal_every  # frames per revealed observation
        self.locale = locale              # which name pool fits this cam

    def _behavior(self, t: Track, pack_median: float) -> str:
        """A driving-behavior read, relative to the other cars on screen."""
        d = t.recent_deltas()
        if d and max(d) > 12 and min(d) < 2.5:
            return "stop and go"
        if pack_median > 0.6:
            r = t.avg_speed() / pack_median
            if r > 1.7:
                return "flooring it"
            if r < 0.5:
                return "dawdling"
        return ""

    def _person_mood(self, t: Track) -> str:
        s = t.avg_speed()
        if s < 1.5:
            return "waiting"
        if s > 6:
            return "hurrying"
        return "ambling"

    def step(self, tracks: dict[int, Track], fps: float) -> list[dict]:
        shown = sorted(tracks.values(), key=lambda t: -t.rel_size)[:self.max_shown]
        speeds = [t.avg_speed() for t in tracks.values()
                  if t.cls_name != "person" and t.frames_seen >= 4]
        pack_median = statistics.median(speeds) if speeds else 0.0
        overlays = []
        for t in shown:
            feats = t.features(fps, self.clock)
            feats["locale"] = self.locale
            if t.cls_name == "person":
                feats["mood"] = self._person_mood(t)
            else:
                feats["behavior"] = self._behavior(t, pack_median)
            if t.frames_seen >= self.min_frames:
                r = self.narrator.narrate(t.track_id, feats)
                overlays.append({"id": t.track_id, "box": list(t.last_box),
                                 "stage": "resolved", "lines": r["lines"]})
            else:
                chips = self.narrator.thought(feats, style.kind_of(feats))
                reveal = min(len(chips), 1 + t.frames_seen // self.reveal_every)
                overlays.append({"id": t.track_id, "box": list(t.last_box),
                                 "stage": "thinking", "chips": chips[:reveal]})
        return overlays
