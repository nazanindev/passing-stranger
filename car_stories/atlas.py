"""A generated map of the taste — run `python -m car_stories.atlas`.

Not a metrics dashboard: it *runs the narrator* and shows the real lines each
character says, so you design by reading voice. Two views:

  CHARACTERS — every kind as a sheet: when it's seen, how deep, and actual
               sampled lines across day / night / rush, so you can hear it.
  WORKLIST   — where the voice is thin (a pool that repeats on screen) or
               generic (an identity with no situational lines of its own).

Nothing here is authored; it reads the pools in style.py + correlator.py and the
same kind_of()/narrate() the live site uses, so it can't drift. Seeded, so a run
is a stable snapshot.
"""
from __future__ import annotations

import os
import random

from . import correlator as C  # noqa: F401  (kept for parity / future views)
from . import style
from .narrator import Narrator

# mirrors server.py: the ImageNet body classifier only runs when CS_CLASSIFY is
# on. With it off, fine_type is always empty, so classifier-only kinds are dark.
_CLASSIFY = os.environ.get("CS_CLASSIFY", "1") != "0"

# reach mirrors kind_of(): coarse type+size and the yellow reads are always live;
# fine bodies need a close crop (the classifier). Small, stable; the rest derived.
_COARSE = {"hauler", "compact", "sedan", "truck", "bus", "motorcycle"}
_HEURISTIC = {"cabbie": "yellow car+US", "kids": "yellow bus+US"}

# the three contexts each sheet is sampled in — enough to hear the range
_SCENES = (("day", "midday", "cruising"),
           ("night", "night", "cruising"),
           ("rush", "morning", "racing"))
_PERSON_SCENES = (("amble", "midday", "ambling"),
                  ("hurry", "morning", "hurrying"),
                  ("wait", "evening", "waiting"))


def _head(title: str) -> str:
    return f"\n{title} " + "─" * max(0, 65 - len(title))


# --- kinds --------------------------------------------------------------------
def _all_kinds() -> list[str]:
    ks = (set(style.FINE_KIND.values()) | _COARSE | set(style.WHO)
          | set(style.KIND_EMOTION) | set(style.KIND_PURPOSE)
          | set(style.KIND_TOWARD) | set(style.KIND_ARCHETYPE) | set(style.MULTI))
    return sorted(ks)


def _reach(kind: str) -> tuple[str, str]:
    fine = sorted(ft for ft, k in style.FINE_KIND.items() if k == kind)
    if kind in _HEURISTIC:
        note = _HEURISTIC[kind]
    elif kind in _COARSE:
        note = "coarse type+size"
    else:
        note = ",".join(fine) or "—"
    return ("common" if kind in _COARSE or kind in _HEURISTIC else "rare"), note


def _depth(kind: str) -> int:
    if kind in style.MULTI:
        return len(style.MULTI_LIVES.get(kind, style.BUS_LIVES))
    return len(style.WHO.get(kind, []))


def _has_telos(kind: str) -> bool:
    return kind in style.KIND_EMOTION


def roster_rows() -> list[dict]:
    rows = []
    for k in _all_kinds():
        reach, note = _reach(k)
        rows.append({"kind": k, "reach": reach, "detect": note, "depth": _depth(k),
                     "multi": k in style.MULTI, "telos": _has_telos(k)})
    rows.sort(key=lambda r: (r["reach"] != "common", -r["depth"]))
    return rows


# --- turn a kind into features the narrator will read as that kind ------------
def _features_for(kind: str) -> dict:
    base = {"color": "silver", "direction": "heading away", "speed": "cruising",
            "size": "midsize", "lane": "", "fine_type": "", "time_of_day": "midday",
            "confidence": 0.9, "locale": "default", "vibe": "", "region": "",
            "behavior": None, "scene": {}, "scene_tags": ()}
    if kind == "cabbie":
        base.update(vehicle_type="car", color="yellow")
    elif kind == "kids":
        base.update(vehicle_type="bus", color="yellow")
    elif (fine := [ft for ft, k in style.FINE_KIND.items() if k == kind]):
        base.update(vehicle_type="car", fine_type=fine[0])
    elif kind in ("truck", "bus", "motorcycle"):
        base.update(vehicle_type=kind)
    elif kind == "hauler":
        base.update(vehicle_type="car", size="big")
    elif kind == "compact":
        base.update(vehicle_type="car", size="small")
    else:  # sedan
        base.update(vehicle_type="car", size="midsize")
    return base


def sample_voice(kind: str, scenes, is_person: bool = False, per: int = 2) -> list[tuple]:
    """Real narrator output for this kind, grouped by scene. Returns
    [(scene_label, [line, ...]), ...] — the character's actual voice."""
    narr = Narrator()
    seen: set[str] = set()
    out, tid = [], 0
    for label, tod, sp in scenes:
        picks: list[str] = []
        for _ in range(16):
            f = _features_for("__person__" if is_person else kind)
            if is_person:
                f.update(vehicle_type="person", color="unknown", mood=sp)
            else:
                f.update(speed=sp)
            f.update(time_of_day=tod)
            line = narr.narrate((kind, label, tid), f)["lines"][0]
            tid += 1
            if line not in seen:
                seen.add(line)
                picks.append(line)
            if len(picks) >= per:
                break
        out.append((label, picks))
    return out


# --- render -------------------------------------------------------------------
def render() -> str:
    random.seed(7)  # stable snapshot
    L: list[str] = ["PASSING STRANGER · taste atlas",
                    "the narrator, sampled — the real voice of each character"]

    # ---- CHARACTERS ----
    L.append(_head("CHARACTERS"))
    if not _CLASSIFY:
        L.append("  CS_CLASSIFY=0 — × marks kinds that are dark (never reached live)")
    rows = roster_rows()
    for reach, label in (("common", "always live"),
                         ("rare", "needs the classifier"
                                  + (" — DARK" if not _CLASSIFY else ""))):
        L.append(f"\n  ──────── {label} ────────")
        for r in (x for x in rows if x["reach"] == reach):
            dark = " ×" if (reach == "rare" and not _CLASSIFY) else ""
            depth = "MULTI" if r["multi"] else f"{r['depth']} lines"
            voice = "bespoke voice" if r["telos"] else "generic voice"
            L.append(f"\n  {r['kind'].upper()}{dark}  ·  {r['detect']}  ·  {depth} · {voice}")
            for scene_label, picks in sample_voice(r["kind"], _SCENES):
                for i, line in enumerate(picks):
                    L.append(f"    {scene_label if i == 0 else '':6} \"{line}\"")

    # persons — their own machinery, no kind
    L.append("\n  ──────── on foot (person) ────────")
    L.append("\n  PERSON  ·  someone walking  ·  17 lines · gait-keyed")
    for scene_label, picks in sample_voice("person", _PERSON_SCENES, is_person=True):
        for i, line in enumerate(picks):
            L.append(f"    {scene_label if i == 0 else '':6} \"{line}\"")

    # ---- WORKLIST ----
    L.append(_head("WORKLIST — where the voice is thin or generic"))
    laps = sorted((r for r in rows if not r["multi"] and r["depth"] < 12),
                  key=lambda r: r["depth"])
    L.append("\n  laps fast — identity pool repeats while a car is on screen:")
    for r in laps:
        tag = "" if r["reach"] == "common" else "  (rare — only when it appears)"
        L.append(f"    {r['kind']:11}{r['depth']} lines{tag}")
    generic = [r["kind"] for r in rows if not r["multi"] and not r["telos"]]
    L.append("\n  generic voice — an identity, but no situational lines of its own")
    L.append("  (says who it is, then leans on the shared emotion/purpose pools):")
    L.append("    " + ", ".join(generic))
    bespoke = [r["kind"] for r in rows if r["telos"]]
    L.append("\n  bespoke voice — deep + its own situational pools (the exemplars):")
    L.append("    " + ", ".join(bespoke))

    L.append("\nedit the pools in style.py; the votes/claims in correlator.py; rerun me.")
    return "\n".join(L)


if __name__ == "__main__":
    print(render())
