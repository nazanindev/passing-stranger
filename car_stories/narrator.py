"""Assemble a life from observed features + your style (style.py). No LLM.

Returns {"lines": [...], "archetype": ...}. Most vehicles get one short line; a
bus gets several (many stories through the windows). Each car is rolled once and
cached, so it never changes while it's on screen. None of it is real.

The taste lives in style.py — edit that. This file is just the machinery.
"""

from __future__ import annotations

import random

from . import style


def _pick(rng, pool_map, key):
    return rng.choice(pool_map.get(key, pool_map["_"]))


class Narrator:
    """narrate(track_id, features) → {"lines", "archetype"}. No API, no key."""

    def __init__(self) -> None:
        self._cache: dict[int, dict] = {}

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
            return [c for c in chips if c]
        ft = (features.get("fine_type") or "").replace("_", " ")
        chips = [f"a {ft or features['vehicle_type']}"]
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
        return [c for c in chips if c]

    def narrate(self, track_id: int, features: dict) -> dict:
        if track_id in self._cache:
            return self._cache[track_id]

        rng = random  # rolled once per car, then cached — stable while on screen
        kind = style.kind_of(features)
        names = style.names_for(features.get("locale", "default"))

        if features["vehicle_type"] == "person":
            mood = features.get("mood", "ambling")
            attrs = {"name": rng.choice(names),
                     "who": rng.choice(style.PERSON_WHO),
                     "mood": rng.choice(style.PERSON_MOOD[mood]),
                     "toward": rng.choice(style.TOWARD)}
            lines = [rng.choice(style.PERSON_TEMPLATES).format(**attrs)]
            archetype = "The Passerby"
        elif kind in style.MULTI:
            lines = rng.sample(style.BUS_LIVES, style.BUS_COUNT)  # situations, not names
            archetype = {"transit": "The Manyfold", "kids": "The School Run"}.get(
                kind, "The Busful")
        else:
            origin, _dest = style.GEOGRAPHY.get(features["direction"], style.GEOGRAPHY["_"])
            beh = features.get("behavior")
            emotion = (rng.choice(style.BEHAVIOR_EMOTION[beh]) if beh in style.BEHAVIOR_EMOTION
                       else _pick(rng, style.EMOTION, features["speed"]))
            attrs = {
                "name": rng.choice(names),
                "age": rng.randint(19, 74),
                "who": rng.choice(style.WHO[kind]),
                "emotion": emotion,
                "purpose": _pick(rng, style.PURPOSE, features["time_of_day"]),
                "toward": rng.choice(style.TOWARD),
                "origin": origin,
            }
            lines = [rng.choice(style.TEMPLATES).format(**attrs)]
            archetype = f"The {rng.choice(style.ARCH_ADJ)} {rng.choice(style.ARCH_NOUN)}"

        result = {"lines": lines, "archetype": archetype, "kind": kind}
        self._cache[track_id] = result
        return result
