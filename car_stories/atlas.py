"""A generated map of the taste — run `python -m car_stories.atlas`.

Nothing here is authored. It reads the pools in style.py and the vote/claim
tables in correlator.py and reports their *shape*: which characters exist and
how deep, which (feeling × focus) reads have a voice, and which observed signals
still don't vote. The map can't drift, because the code it maps IS the taste.

Use it while designing: a common character with a shallow pool will lap; an empty
temper×orbit cell is a mood the machine can read but can't yet say; an idle
signal is a lever you haven't pulled. The data functions (roster_rows, etc.)
return plain values so a prettier renderer can reuse them.
"""
from __future__ import annotations

from . import correlator as C
from . import style

# reach mirrors kind_of(): fine-body kinds surface only on a close crop (rare on
# a traffic cam); the coarse type+size buckets and the cheap yellow reads are
# common. This is the one hand-kept surface — small and stable. Everything else
# is derived from the pools themselves.
_COARSE = {"hauler", "compact", "sedan", "truck", "bus", "motorcycle"}
_HEURISTIC = {"cabbie": "yellow car+US", "kids": "yellow bus+US"}

# observed attributes and their value spaces — mirrors observe.py / narration.py.
# used only to check which signals reach the vote tables (utilization).
_OBSERVABLES = {
    "speed": ["still", "crawling", "cruising", "racing"],
    "behavior": ["flooring it", "dawdling", "stop and go"],
    "color": ["black", "white", "silver", "red", "orange", "yellow", "green",
              "blue", "purple"],
    "direction": ["stationary", "barely moving", "eastbound", "westbound",
                  "approaching the camera", "heading away"],
    "size": ["big", "midsize", "small"],
    "lane": ["left lane", "center lane", "right lane"],
    "time_of_day": ["the small hours", "morning", "midday", "late afternoon",
                    "evening", "night"],
    "day": ["weekday", "weekend"],
    "scene tempo": ["an empty street", "a quiet road", "the thick of it",
                    "the crawl"],
    "scene light": ["dark", "dim", "bright"],
    "mood (person)": ["waiting", "hurrying", "ambling"],
    "vibe": ["beach", "tourist", "downtown", "freeway"],
    "region": sorted(style.REGION_FLAVOR),
}

# display orders — the readable arrangement, not the tiebreak order
_TEMPERS = ["harried", "dutiful", "steady", "weary", "light", "restless",
            "tender", "lost", "quiet"]
_ORBITS = ["work", "school", "errands", "home", "social", "escape", "nowhere"]

_THIN = 6   # a temper/orbit with fewer claimed lines than this is under-voiced


# --- kinds --------------------------------------------------------------------
def _all_kinds() -> list[str]:
    ks = (set(style.FINE_KIND.values()) | _COARSE | set(style.WHO)
          | set(style.KIND_EMOTION) | set(style.KIND_PURPOSE)
          | set(style.KIND_TOWARD) | set(style.KIND_ARCHETYPE) | set(style.MULTI))
    return sorted(ks)


def _reach(kind: str) -> tuple[str, str]:
    fine = sorted(ft for ft, k in style.FINE_KIND.items() if k == kind)
    if kind in _COARSE:
        note = "coarse type+size"
    elif kind in _HEURISTIC:
        note = _HEURISTIC[kind] + (" +" + ",".join(fine) if fine else "")
    else:
        note = ",".join(fine) or "—"
    common = kind in _COARSE or kind in _HEURISTIC
    return ("common" if common else "rare"), note


def _depth(kind: str) -> int | None:
    """Identity-pool depth: WHO size, or the shared-lives pool for MULTI kinds."""
    if kind in style.MULTI:
        return len(style.MULTI_LIVES.get(kind, style.BUS_LIVES))
    return len(style.WHO[kind]) if kind in style.WHO else None


def _telos(kind: str) -> tuple[int, int, int, int]:
    e = sum(len(v) for v in style.KIND_EMOTION.get(kind, {}).values())
    return (e, len(style.KIND_PURPOSE.get(kind, [])),
            len(style.KIND_TOWARD.get(kind, [])),
            len(style.KIND_ARCHETYPE.get(kind, [])))


def roster_rows() -> list[dict]:
    rows = []
    for k in _all_kinds():
        reach, note = _reach(k)
        e, p, t, a = _telos(k)
        rows.append({"kind": k, "reach": reach, "detect": note,
                     "depth": _depth(k), "multi": k in style.MULTI,
                     "emotion": e, "purpose": p, "toward": t, "arch": a})
    # common first, then deepest — the "seen a lot, said thinly" risks float up
    rows.sort(key=lambda r: (r["reach"] != "common", -(r["depth"] or 0)))
    return rows


def _laps(depth: int | None) -> str:
    if depth is None:
        return "—"
    return "laps" if depth < 8 else "ok" if depth < 20 else "deep"


# --- temper × orbit coverage --------------------------------------------------
def temper_counts() -> dict[str, int]:
    return {t: len(C.TEMPERS.get(t, ())) for t in _TEMPERS}


def orbit_counts() -> dict[str, int]:
    return {o: len(C.ORBITS.get(o, ())) for o in _ORBITS}


def matrix() -> dict[tuple[str, str], int]:
    """Dedicated lines per (temper, orbit): lines claimed by that temper AND that
    orbit — the ones that pin an exact life ("on the way to a first date" is
    tender+social). A 0 cell is a feeling×focus the machine can read but has no
    bespoke word for — the design gap. (Every read still draws deep generic
    pools; this is only the specifically-pinned layer.)"""
    tl = {t: set(C.TEMPERS.get(t, ())) for t in _TEMPERS}
    ol = {o: set(C.ORBITS.get(o, ())) for o in _ORBITS}
    return {(t, o): len(tl[t] & ol[o]) for t in _TEMPERS for o in _ORBITS}


# --- signal utilization -------------------------------------------------------
def signal_use() -> list[dict]:
    out = []
    for attr, values in _OBSERVABLES.items():
        vals = set(values)
        temp = len(vals & set(C.TEMPER_VOTES))
        orb = len(vals & set(C.ORBIT_VOTES))
        out.append({"attr": attr, "n": len(vals), "temper": temp, "orbit": orb})
    return out


# --- line inventory -----------------------------------------------------------
def inventory() -> dict[str, int]:
    lines = C._style_lines()
    claimed = {e for e in lines if C.claims(e)}
    return {"lines": len(lines), "claimed": len(claimed),
            "free": len(lines) - len(claimed)}


# --- render -------------------------------------------------------------------
_ABBR = {"work": "work", "school": "schl", "errands": "errd", "home": "home",
         "social": "socl", "escape": "escp", "nowhere": "nowh"}


def _head(title: str) -> str:
    return f"\n{title} " + "─" * max(0, 65 - len(title))


def _n(x) -> str:            # a 0 reads as clutter; dot it out
    return "·" if not x else str(x)


def _roster_line(k, w, e, p, t, a, flag, note) -> str:
    return f"  {k:<11}{w:>5}{e:>4}{p:>4}{t:>4}{a:>5}   {flag:<2}{note}"


def render() -> str:
    L: list[str] = []
    L.append("PASSING STRANGER · taste atlas")
    L.append("generated from style.py + correlator.py — edit the pools, rerun me")

    # roster, grouped by reach (no repeated reach column)
    rows = roster_rows()
    L.append(_head("CHARACTERS"))
    L.append(_roster_line("", "WHO", "E", "P", "T", "arch", "", "detect →").rstrip())
    for reach, label in (("common", "common — coarse type+size, or a cheap yellow read"),
                         ("rare", "rare — only on a close crop (ImageNet body)")):
        L.append(f"  · {label}")
        for r in (x for x in rows if x["reach"] == reach):
            depth = "MULTI" if r["multi"] else str(r["depth"])
            shallow = (not r["multi"] and r["reach"] == "common" and r["depth"] < 8)
            L.append(_roster_line(
                r["kind"], depth, _n(r["emotion"]), _n(r["purpose"]),
                _n(r["toward"]), _n(r["arch"]), "⚠" if shallow else "",
                r["detect"]))
    L.append("  WHO=identity lines · E/P/T=telos pools · arch=archetypes · ⚠=common+shallow")

    # temper × orbit — the bespoke-line radar
    L.append(_head("TEMPER × ORBIT"))
    L.append("  bespoke lines pinned to a feeling × focus  (· = none written yet)")
    L.append("  " + " " * 10 + "".join(f"{_ABBR[o]:>6}" for o in _ORBITS))
    mx, tc = matrix(), temper_counts()
    for t in _TEMPERS:
        cells = "".join((f"{mx[(t, o)]:>6}" if mx[(t, o)] else "     ·")
                        for o in _ORBITS)
        L.append(f"  {t:<10}{cells}")
    L.append("  orbit Σ    " + "  ".join(f"{_ABBR[o]}:{orbit_counts()[o]}" for o in _ORBITS))
    L.append("  temper Σ   " + "  ".join(f"{t[:4]}:{tc[t]}" for t in _TEMPERS))

    # signals — voters vs idle
    L.append(_head("SIGNALS"))
    voters = [s for s in signal_use() if s["temper"] or s["orbit"]]
    idle = [s for s in signal_use() if not (s["temper"] or s["orbit"])]
    for s in voters:
        L.append(f"  {s['attr']:14}temper {s['temper']}/{s['n']:<4}"
                 f"orbit {s['orbit']}/{s['n']}")
    L.append("  idle (seen, never votes): " + ", ".join(s["attr"] for s in idle))

    inv = inventory()
    L.append(f"\n{inv['lines']} claimable lines · {inv['claimed']} claimed · "
             f"{inv['free']} free ({100 * inv['free'] // max(1, inv['lines'])}%)")
    return "\n".join(L)


if __name__ == "__main__":
    print(render())
