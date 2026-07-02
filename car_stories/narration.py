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
                 reveal_every: int = 2, locale: str = "default",
                 vibe: str = "", region: str = "") -> None:
        self.narrator = narrator          # may be shared across cam sessions —
        self._salt = id(self)             # so their track ids must not collide
        self.min_frames = min_frames
        self.clock = clock
        self.max_shown = max_shown        # how many cars carry an overlay at once
        self.reveal_every = reveal_every  # frames per revealed observation
        self.locale = locale              # grounds reads like yellow-car→cab
        self.vibe = vibe                  # the place's character (beach, tourist…)
        self.region = region              # local flavor (a Wawa run needs a Wawa)

    def _behavior(self, t: Track, pack_median: float, fps: float) -> str:
        """A driving-behavior read, relative to the other cars on screen."""
        d = t.recent_deltas()
        if d and max(d) > 12 and min(d) < 2.5:
            return "stop and go"
        if pack_median > 0.3:                     # body-lengths/sec (see observe)
            r = t.avg_speed(fps) / pack_median
            if r > 1.7:
                return "flooring it"
            if r < 0.5:
                return "dawdling"
        return ""

    def _person_mood(self, t: Track, fps: float) -> str:
        s = t.avg_speed(fps)                       # body-lengths/sec
        if s < 0.35:
            return "waiting"
        if s > 1.5:
            return "hurrying"
        return "ambling"

    @staticmethod
    def _parked(t: Track, fps: float) -> bool:
        """A vehicle that never went anywhere: near-zero net travel over a
        sustained watch, and still now. Parked cars aren't passing strangers —
        they're scenery, and re-reading the same one into a new life every time
        the tracker re-acquires it is what kills the vibe. So they get no overlay
        at all, like the mailbox. A car merely stopped at a light drove *in* —
        its net displacement is real — so it keeps its soul."""
        return (t.cls_name != "person"
                and t.frames_seen >= 6
                and t.direction() in ("stationary", "barely moving")
                and t.avg_speed(fps) < 0.15)

    @staticmethod
    def _twin(a: tuple, b: tuple) -> float:
        """Overlap over the smaller box — near-concentric double-detections
        score high even when IoU wouldn't."""
        iw = min(a[2], b[2]) - max(a[0], b[0])
        ih = min(a[3], b[3]) - max(a[1], b[1])
        if iw <= 0 or ih <= 0:
            return 0.0
        small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
        return iw * ih / small if small > 0 else 0.0

    def step(self, tracks: dict[int, Track], fps: float,
             scene: dict | None = None) -> list[dict]:
        scene = dict(scene or {})
        # one car, one soul: a tracker twin riding the same box (glare, id switch)
        # never gets its own read — people may overlap cars freely, though
        cur = max((t.last_frame for t in tracks.values()), default=0)
        shown: list[Track] = []
        for t in sorted(tracks.values(), key=lambda t: -t.rel_size):
            # the tracker remembers a gone car for ~60 frames (occlusion grace);
            # a ghost must not keep its box and story on screen that long
            if cur - t.last_frame > 2:
                continue
            # a parked car is scenery, not a passing stranger — no overlay, and
            # so no new life rolled each time it's re-acquired
            if self._parked(t, fps):
                continue
            # note: we no longer cull a low-confidence track here — a shape the
            # detector half-doubts (the lamppost read as a person) is KEPT and
            # thought about out loud. it just never earns a resolved story below.
            person = t.cls_name == "person"
            if any(self._twin(t.last_box, k.last_box) > 0.55 for k in shown
                   if (k.cls_name == "person") == person):
                continue
            shown.append(t)
            if len(shown) == self.max_shown:
                break
        speeds = [t.avg_speed(fps) for t in tracks.values()
                  if t.cls_name != "person" and t.frames_seen >= 4]
        pack_median = statistics.median(speeds) if speeds else 0.0

        # what the street is doing right now — evidence, from the stream itself
        n = sum(1 for t in tracks.values() if t.cls_name != "person")
        scene["tempo"] = ("the crawl" if n >= 7 and pack_median < 3.5 else
                          "the thick of it" if n >= 7 else
                          "an empty street" if n <= 1 else
                          "a quiet road" if n <= 3 else "")
        b = scene.get("brightness")
        scene["light"] = ("" if b is None else
                          "dark" if b < 55 else "dim" if b < 115 else
                          "bright" if b >= 180 else "")
        clock = scene.get("clock", self.clock)
        tags = [scene["tempo"], scene["light"]]
        if scene.get("weekend"):
            tags.append("weekend")
        base_tags = [t_ for t_ in tags if t_]

        # foot traffic is its own evidence. The tempo tags above count only
        # vehicles, so a street thick with people but empty of cars still reads
        # "an empty street" — and its solitude phrases ("no audience but the
        # camera") would be a plain lie. Count the people on screen so the
        # solitude/pedestrian reads stay honest per subject.
        people = sum(1 for t in tracks.values()
                     if t.cls_name == "person" and cur - t.last_frame <= 2)
        _SOLITUDE = {"an empty street", "a quiet road"}

        overlays = []
        for t in shown:
            feats = t.features(fps, clock)
            feats["locale"] = self.locale
            feats["vibe"] = self.vibe
            feats["region"] = self.region
            feats["scene"] = scene
            tags_t = list(base_tags)
            if people >= 2:                       # not out here alone
                tags_t = [x for x in tags_t if x not in _SOLITUDE]
                # a car actually among the crowd may speak of it (never a racer,
                # who isn't yielding to anyone)
                if t.cls_name != "person" and t.speed(fps) != "racing":
                    tags_t.append("pedestrians")
            feats["scene_tags"] = tags_t
            if t.cls_name == "person":
                feats["mood"] = self._person_mood(t, fps)
            else:
                feats["behavior"] = self._behavior(t, pack_median, fps)
            # a story is earned only once the read is both long enough AND sure
            # enough — a half-doubted shape keeps thinking (and second-guessing
            # itself) forever rather than being handed a soul it didn't earn
            if t.frames_seen >= self.min_frames and t.median_conf() >= 0.35:
                r = self.narrator.narrate((self._salt, t.track_id), feats)
                overlays.append({"id": t.track_id, "box": list(t.last_box),
                                 "stage": "resolved", "lines": r["lines"]})
            else:
                chips = self.narrator.thought((self._salt, t.track_id), feats,
                                              style.kind_of(feats), t.frames_seen,
                                              self.reveal_every)
                overlays.append({"id": t.track_id, "box": list(t.last_box),
                                 "stage": "thinking", "chips": chips})
        self.narrator.reap(self._salt, set(tracks))   # forget vanished tracks
        return overlays
