"""Assemble a life from observed features + your style (style.py). No LLM.

Returns {"lines": [...], "archetype": ...}. Most vehicles get one short line; a
bus gets several (many stories through the windows). Each car is rolled once and
cached, so it never changes while it's on screen. None of it is real.

The taste lives in style.py (what things are) and correlator.py (what belongs
together) — edit those. This file is just the machinery.
"""

from __future__ import annotations

import random

from . import correlator, style

_BANDS = ("low", "mid", "high")


def _band(conf: float) -> str:
    """The detector's certainty, bucketed into a register the voice can wear."""
    if conf < 0.45:
        return "low"
    if conf < 0.7:
        return "mid"
    return "high"


def _weave(rng, pool, actives, recent=None, tries=3):
    """Pick one line within the car's read: lines claimed by other reads are
    dropped; on-read and free lines stay in on equal footing (favoring the
    claimed ones concentrates picks and kills novelty). If the filter empties
    the pool, the pool stands.

    `recent` is the narrator's clause-level memory: a repeated *ingredient*
    reads as repetitive even inside a brand-new sentence, so each pick rerolls
    while it's still warm. A small pool may exhaust the retries — then the
    repeat stands rather than fighting the pool."""
    on = [e for e in pool if correlator.claims(e) & actives]
    free = [e for e in pool if not correlator.claims(e)]
    cands = on + free or list(pool)
    pick = rng.choice(cands)
    if recent is not None:
        for _ in range(tries):
            if pick not in recent:
                break
            pick = rng.choice(cands)
        recent.append(pick)
    return pick


def _pick(rng, pool_map, key, actives, recent=None):
    return _weave(rng, pool_map.get(key, pool_map["_"]), actives, recent)


class Narrator:
    """narrate(track_id, features) → {"lines", "archetype"}. No API, no key."""

    def __init__(self) -> None:
        self._cache: dict[int, dict] = {}
        self._think: dict = {}    # per-track thinking log, until the story resolves
        from collections import deque
        # novelty memory, two grains: whole lines get a long memory (a story
        # shouldn't come back for an hour), ingredients a short one — a warm
        # clause in a fresh sentence reads as a rerun, but only briefly; a
        # little repetition is the texture of a real street, not a bug
        self._recent: deque = deque(maxlen=220)   # assembled lines
        self._clauses: deque = deque(maxlen=60)   # individual picks (~a dozen stories)

    def _fresh(self, roll, tries: int = 10):
        """Reroll until the line hasn't been said recently (or give up)."""
        line = roll()
        for _ in range(tries):
            if line not in self._recent:
                break
            line = roll()
        self._recent.append(line)
        return line

    @staticmethod
    def _observe(features: dict, kind: str) -> list[tuple]:
        """The ordered observations the machine could voice, as (slot, value,
        chip) — identity first, the verdict last. `slot` names the observation so
        the log can tell a fresh note from a correction; `value` is what a later
        look is compared against; `chip` is the plain wording (identity gets
        hedged separately)."""
        f = features
        r = correlator.read(f)
        verdict = f"reads {r['temper']} · {r['orbit']}"
        if f["vehicle_type"] == "person":
            obs = [("id", "person", "a person")]
            if f["color"] not in ("unknown", ""):
                obs.append(("color", f["color"], f["color"]))
            if f["direction"] not in ("stationary", "barely moving"):
                obs.append(("direction", f["direction"], f["direction"]))
            if f.get("mood"):
                obs.append(("mood", f["mood"], f["mood"]))
            obs.append(("time", f["time_of_day"], f["time_of_day"]))
            obs.append(("verdict", verdict, verdict))
            return [o for o in obs if o[2]]
        ft = (f.get("fine_type") or "").replace("_", " ")
        label = ft or style.KIND_LABEL.get(kind) or f["vehicle_type"]
        obs = [("id", label, f"a {label}")]
        if f["color"] not in ("unknown", ""):
            obs.append(("color", f["color"], f["color"]))
        obs.append(("size", f.get("size"), {"big": "up close",
                    "midsize": "mid-distance", "small": "far off"}.get(f.get("size"), "")))
        if f.get("lane"):
            obs.append(("lane", f["lane"], f["lane"]))
        if f["direction"] not in ("stationary", "barely moving"):
            obs.append(("direction", f["direction"], f["direction"]))
        if f["speed"] != "still" and not f.get("behavior"):
            obs.append(("speed", f["speed"], f["speed"]))
        if f.get("behavior"):
            obs.append(("behavior", f["behavior"], f["behavior"]))
        obs.append(("time", f["time_of_day"], f["time_of_day"]))
        obs.append(("verdict", verdict, verdict))
        return [o for o in obs if o[2]]

    def thought(self, track_id, features: dict, kind: str,
                frames_seen: int, reveal_every: int = 2) -> list[str]:
        """The machine reading a subject live — an append-only log, not a tidied
        result: you watch it think. Guesses arrive one at a time, hedged by the
        detector's own certainty; the machine catches itself when a sharper look
        overrules an earlier read, and firms up when the confidence climbs. A
        thing that never moves is doubted out of being a soul (a lamppost read as
        a person is kept and named, not culled)."""
        st = self._think.get(track_id)
        if st is None:
            st = self._think[track_id] = {"log": [], "seen": {}, "furniture": False}
        log, seen = st["log"], st["seen"]
        conf = float(features.get("confidence", 1.0))

        obs = self._observe(features, kind)
        reveal = 1 + frames_seen // max(1, reveal_every)   # how far the read has got
        for i, (slot, value, chip) in enumerate(obs):
            if i >= reveal:
                break
            if slot not in seen:                            # a fresh note
                seen[slot] = value
                if slot == "id":
                    seen["_band"] = _band(conf)
                    log.append(random.choice(style.HEDGE[_band(conf)]).format(a=chip))
                else:
                    log.append(chip)
            elif slot in style.REVISABLE and value != seen[slot]:
                seen[slot] = value                          # a correction
                if slot == "id":
                    seen["_band"] = _band(conf)
                log.append(random.choice(style.REVISION).format(new=chip))
            elif slot == "id" and value == seen[slot]:      # same guess, firmer look
                new = _band(conf)
                if _BANDS.index(new) > _BANDS.index(seen.get("_band", "high")):
                    seen["_band"] = new
                    log.append(random.choice(style.CONFIRM).format(a=chip))

        # a "person" that never once moves stops reading as a life: the machine
        # gives up on the soul and names the furniture. fires once.
        if (not st["furniture"] and features["vehicle_type"] == "person"
                and conf < 0.55 and frames_seen >= 10
                and features["direction"] in ("stationary", "barely moving")):
            st["furniture"] = True
            thing = random.choice(style.STREET_FURNITURE)
            log.append(random.choice(style.FURNITURE_DOUBT).format(thing=thing))

        return list(log)

    def reap(self, salt, alive_ids: set) -> None:
        """Drop thinking/story state for tracks this cam session no longer sees.
        Keys are (salt, track_id); only this session's are touched (the narrator
        may be shared across cams)."""
        for store in (self._think, self._cache):
            for k in [k for k in store
                      if isinstance(k, tuple) and k[0] == salt and k[1] not in alive_ids]:
                del store[k]

    def narrate(self, track_id, features: dict) -> dict:
        # track_id is any hashable key — cam sessions pass (session, id) tuples
        # so one shared narrator can serve every cam without souls colliding
        if track_id in self._cache:
            return self._cache[track_id]
        self._think.pop(track_id, None)   # thinking's over — the story is told

        rng = random  # rolled once per car, then cached — stable while on screen
        kind = style.kind_of(features)
        # the read: evidence votes on two axes (no dice) — temper (how it feels)
        # and orbit (what the life is about); every clause below derives from both
        r = correlator.read(features)
        actives = {r["temper"], r["orbit"]}

        # what the street offers this car, if anything
        scene_phrases = [p for t in features.get("scene_tags", ())
                         for p in style.SCENE_PHRASE.get(t, ())]
        scene_phrase = (_weave(rng, scene_phrases, actives, self._clauses)
                        if scene_phrases else "")
        # the place votes too: this cam's region slips a local destination
        # into the pools now and then (a Wawa run only happens near a Wawa)
        flavor = style.REGION_FLAVOR.get(features.get("region", ""), {})

        # length is earned: one clause unless the evidence itself is notable —
        # visible behavior, a special body, or an emphatic read
        exceptional = (bool(features.get("behavior"))
                       or kind in style.KIND_ARCHETYPE or kind in style.MULTI
                       or r["conviction"] >= 6)

        if features["vehicle_type"] == "person":
            walk = features.get("mood", "ambling")  # gait, not the correlator's read

            def roll_person():
                attrs = {"who": _weave(rng, style.PERSON_WHO, actives, self._clauses),
                         "mood": _weave(rng, style.PERSON_MOOD[walk], actives,
                                        self._clauses),
                         "toward": _weave(rng, style.TOWARD
                                          + flavor.get("toward", []), actives,
                                          self._clauses)}
                if walk == "ambling" and r["conviction"] < 4:   # unremarkable gait
                    return attrs[rng.choice(("mood", "mood", "who"))]
                return rng.choice(style.PERSON_TEMPLATES).format(**attrs)

            lines = [self._fresh(roll_person)]
            archetype = "The Passerby"
        elif kind in style.MULTI:
            pool = style.MULTI_LIVES.get(kind, style.BUS_LIVES)  # situations, not names
            # passengers share the hour's read, not one life — filter, don't favor
            on_or_free = [e for e in pool
                          if not correlator.claims(e) or correlator.claims(e) & actives]
            cands = on_or_free if len(on_or_free) >= style.BUS_COUNT else list(pool)
            lines = []
            for _ in range(style.BUS_COUNT):
                line = self._fresh(lambda: rng.choice(cands))
                if line not in lines:
                    lines.append(line)
            archetype = {"transit": "The Manyfold", "kids": "The School Run"}.get(
                kind, "The Busful")
        else:
            origin, _dest = style.GEOGRAPHY.get(features["direction"], style.GEOGRAPHY["_"])
            beh = features.get("behavior")

            def roll_story():
                if kind in style.KIND_EMOTION:
                    # a kind with a visible telos: the job sets the feeling; behavior
                    # folds into speed so a hurrying cab is never "running from something"
                    key = style.BEH_TO_SPEED.get(beh, features["speed"])
                    emotion = _pick(rng, style.KIND_EMOTION[kind], key, actives,
                                    self._clauses)
                elif beh in style.BEHAVIOR_EMOTION:
                    emotion = _weave(rng, style.BEHAVIOR_EMOTION[beh], actives,
                                     self._clauses)
                else:
                    emotion = _pick(rng, style.EMOTION, features["speed"], actives,
                                    self._clauses)
                purpose = (_weave(rng, style.KIND_PURPOSE[kind], actives, self._clauses)
                           if kind in style.KIND_PURPOSE
                           else _weave(rng, style.PURPOSE.get(features["time_of_day"],
                                                              style.PURPOSE["_"])
                                       + flavor.get("purpose", []), actives,
                                       self._clauses))
                attrs = {
                    "who": _weave(rng, style.WHO[kind], actives, self._clauses),
                    "emotion": emotion,
                    "purpose": purpose,
                    "toward": _weave(rng, style.KIND_TOWARD.get(
                        kind, style.TOWARD + flavor.get("toward", [])), actives,
                        self._clauses),
                    "origin": origin,
                    "scene_phrase": scene_phrase,
                }
                if not exceptional:                # an ordinary life: one clause
                    return rng.choice(style.TEMPLATES_SHORT).format(**attrs)
                # exceptional: shape first, then a template within it — the scene
                # shape only exists when the street actually offered the evidence
                shapes = [("plain", 5), ("turn", 2)]
                if scene_phrase:
                    shapes.append(("scene", 3))
                shape = rng.choices([s for s, _ in shapes],
                                    weights=[w for _, w in shapes])[0]
                template_pool = {"plain": style.TEMPLATES, "turn": style.TEMPLATES_TURN,
                                 "scene": style.TEMPLATES_SCENE}[shape]
                return rng.choice(template_pool).format(**attrs)

            lines = [self._fresh(roll_story)]
            archetype = (rng.choice(style.KIND_ARCHETYPE[kind])
                         if kind in style.KIND_ARCHETYPE
                         else f"The {_weave(rng, style.ARCH_ADJ, actives)} "
                              f"{_weave(rng, style.ARCH_NOUN, actives)}")

        result = {"lines": lines, "archetype": archetype, "kind": kind,
                  "temper": r["temper"], "orbit": r["orbit"],
                  "elaborated": exceptional}
        self._cache[track_id] = result
        return result
