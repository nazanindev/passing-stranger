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


def _weave(rng, pool, actives):
    """Pick one line within the car's read: lines claimed by other reads are
    dropped; on-read and free lines stay in on equal footing (favoring the
    claimed ones concentrates picks and kills novelty). If the filter empties
    the pool, the pool stands."""
    on = [e for e in pool if correlator.claims(e) & actives]
    free = [e for e in pool if not correlator.claims(e)]
    return rng.choice(on + free or list(pool))


def _pick(rng, pool_map, key, actives):
    return _weave(rng, pool_map.get(key, pool_map["_"]), actives)


class Narrator:
    """narrate(track_id, features) → {"lines", "archetype"}. No API, no key."""

    def __init__(self) -> None:
        self._cache: dict[int, dict] = {}
        # novelty memory: the storyteller won't repeat a line it said recently —
        # if the dice land on one, it rerolls (~an hour of stories at busy cams)
        from collections import deque
        self._recent: deque = deque(maxlen=220)

    def _fresh(self, roll, tries: int = 10):
        """Reroll until the line hasn't been said recently (or give up)."""
        line = roll()
        for _ in range(tries):
            if line not in self._recent:
                break
            line = roll()
        self._recent.append(line)
        return line

    @property
    def dry(self) -> bool:
        return False

    def thought(self, features: dict, kind: str) -> list[str]:
        """The raw notes the system is 'seeing' — revealed one by one, live."""
        if features["vehicle_type"] == "person":
            chips = ["a person"]
            if features["color"] not in ("unknown", ""):
                chips.append(features["color"])
            if features["direction"] not in ("stationary", "barely moving"):
                chips.append(features["direction"])
            if features.get("mood"):
                chips.append(features["mood"])
            chips.append(features["time_of_day"])
            r = correlator.read(features)
            chips.append(f"reads {r['temper']} · {r['orbit']}")  # the verdict, last
            return [c for c in chips if c]
        ft = (features.get("fine_type") or "").replace("_", " ")
        label = ft or style.KIND_LABEL.get(kind) or features["vehicle_type"]
        chips = [f"a {label}"]
        if features["color"] not in ("unknown", ""):
            chips.append(features["color"])
        chips.append({"big": "up close", "midsize": "mid-distance",
                      "small": "far off"}.get(features.get("size"), ""))
        if features.get("lane"):
            chips.append(features["lane"])
        if features["direction"] not in ("stationary", "barely moving"):
            chips.append(features["direction"])
        if features["speed"] != "still" and not features.get("behavior"):
            chips.append(features["speed"])
        if features.get("behavior"):
            chips.append(features["behavior"])
        chips.append(features["time_of_day"])
        r = correlator.read(features)
        chips.append(f"reads {r['temper']} · {r['orbit']}")  # the verdict, last
        return [c for c in chips if c]

    def narrate(self, track_id: int, features: dict) -> dict:
        if track_id in self._cache:
            return self._cache[track_id]

        rng = random  # rolled once per car, then cached — stable while on screen
        kind = style.kind_of(features)
        # the read: evidence votes on two axes (no dice) — temper (how it feels)
        # and orbit (what the life is about); every clause below derives from both
        r = correlator.read(features)
        actives = {r["temper"], r["orbit"]}

        # what the street offers this car, if anything
        scene_phrases = [p for t in features.get("scene_tags", ())
                         for p in style.SCENE_PHRASE.get(t, ())]
        scene_phrase = rng.choice(scene_phrases) if scene_phrases else ""
        other = features.get("other", "")

        # length is earned: one clause unless the evidence itself is notable —
        # visible behavior, a special body, or an emphatic read
        exceptional = (bool(features.get("behavior"))
                       or kind in style.KIND_ARCHETYPE or kind in style.MULTI
                       or r["conviction"] >= 6)

        if features["vehicle_type"] == "person":
            walk = features.get("mood", "ambling")  # gait, not the correlator's read

            def roll_person():
                attrs = {"who": _weave(rng, style.PERSON_WHO, actives),
                         "mood": _weave(rng, style.PERSON_MOOD[walk], actives),
                         "toward": _weave(rng, style.TOWARD, actives)}
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
                    emotion = _pick(rng, style.KIND_EMOTION[kind], key, actives)
                elif beh in style.BEHAVIOR_EMOTION:
                    emotion = _weave(rng, style.BEHAVIOR_EMOTION[beh], actives)
                else:
                    emotion = _pick(rng, style.EMOTION, features["speed"], actives)
                purpose = (rng.choice(style.KIND_PURPOSE[kind])
                           if kind in style.KIND_PURPOSE
                           else _pick(rng, style.PURPOSE, features["time_of_day"], actives))
                attrs = {
                    "who": _weave(rng, style.WHO[kind], actives),
                    "emotion": emotion,
                    "purpose": purpose,
                    "toward": _weave(rng, style.KIND_TOWARD.get(kind, style.TOWARD),
                                     actives),
                    "origin": origin,
                    "scene_phrase": scene_phrase,
                    "other": other,
                }
                if not exceptional:                # an ordinary life: one clause
                    return rng.choice(style.TEMPLATES_SHORT).format(**attrs)
                # exceptional: shape first, then a template within it — scene and
                # pack shapes only exist when the street offered the evidence
                shapes = [("plain", 5), ("turn", 2)]
                if scene_phrase:
                    shapes.append(("scene", 3))
                if other:
                    shapes.append(("pack", 3))
                shape = rng.choices([s for s, _ in shapes],
                                    weights=[w for _, w in shapes])[0]
                template_pool = {"plain": style.TEMPLATES, "turn": style.TEMPLATES_TURN,
                                 "scene": style.TEMPLATES_SCENE,
                                 "pack": style.TEMPLATES_PACK}[shape]
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
