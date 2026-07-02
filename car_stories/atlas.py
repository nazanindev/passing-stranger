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
def _bar(n: int, hi: int, w: int = 10) -> str:
    filled = 0 if hi <= 0 else round(w * n / hi)
    return "█" * filled + "·" * (w - filled)


def render() -> str:
    L: list[str] = []
    L.append("PASSING STRANGER · taste atlas  (generated from style.py + correlator.py)")

    # roster
    L.append("\nCHARACTER ROSTER")
    L.append(f"  {'kind':11}{'reach':8}{'detect':22}{'WHO':>5}"
             f"{'E':>4}{'P':>3}{'T':>3}{'arch':>5}  depth")
    for r in roster_rows():
        depth = "MULTI" if r["multi"] else (str(r["depth"]) if r["depth"] is not None else "—")
        who = f"{depth:>5}"
        det = (r["detect"][:20] + "…") if len(r["detect"]) > 21 else r["detect"]
        flag = _laps(None if r["multi"] else r["depth"])
        star = "  ⚠" if (r["reach"] == "common" and flag == "laps") else ""
        L.append(f"  {r['kind']:11}{r['reach']:8}{det:22}{who}"
                 f"{r['emotion']:>4}{r['purpose']:>3}{r['toward']:>3}{r['arch']:>5}"
                 f"  {flag}{star}")
    L.append("  E/P/T = telos emotion/purpose/toward pools · ⚠ = common but shallow")

    # temper × orbit
    L.append("\nTEMPER × ORBIT  (lines pinned to both — 0 = a life with no bespoke word)")
    L.append("  " + " " * 9 + "".join(f"{o[:4]:>5}" for o in _ORBITS))
    mx = matrix()
    for t in _TEMPERS:
        cells = "".join((f"{mx[(t, o)]:>5}" if mx[(t, o)] else "    ·")
                        for o in _ORBITS)
        thin = " ← thin" if temper_counts()[t] < _THIN else ""
        L.append(f"  {t:9}{cells}{thin}")
    tc, oc = temper_counts(), orbit_counts()
    L.append("  temper claims: " + " ".join(f"{t}:{tc[t]}" for t in _TEMPERS))
    L.append("  orbit claims:  " + " ".join(f"{o}:{oc[o]}" for o in _ORBITS))

    # signals
    L.append("\nSIGNAL UTILIZATION  (values that vote / total)")
    for s in signal_use():
        tv = f"temper {s['temper']}/{s['n']}"
        ov = f"orbit {s['orbit']}/{s['n']}"
        idle = "  ← IDLE" if s["temper"] == 0 and s["orbit"] == 0 else ""
        L.append(f"  {s['attr']:15}{tv:14}{ov:14}{idle}")

    # inventory
    inv = inventory()
    L.append(f"\nLINE INVENTORY  {inv['lines']} claimable lines · "
             f"{inv['claimed']} claimed · {inv['free']} free "
             f"({100 * inv['free'] // max(1, inv['lines'])}% free)")
    L.append("edit the pools in style.py; edit the votes/claims in correlator.py; rerun me.")
    return "\n".join(L)


if __name__ == "__main__":
    print(render())
