"""YOUR correlator — how a combination of evidence becomes a read.

style.py maps what the camera sees to ingredients. This file reads the
*combination* — and the read has two axes, so the space is wide enough that an
hour of watching doesn't repeat:

    temper — how the driving feels   (voted by speed, behavior, color,
             direction, body kind, and the scene's light and density)
    orbit  — what the life is about  (voted by the cam's local hour, the day
             of the week, and the body kind)

Every attribute votes (the tables below); each axis's winner is the read. No
dice in the reading: same evidence, same temper, same orbit. The dice only pick
lines *within* the read — a line claimed by "harried" or by "school" surfaces
when that temper or orbit is active, a line claimed by neither is free.

tempers: harried dutiful steady weary light restless tender lost quiet
orbits:  work school errands home social escape nowhere

Scene evidence arrives from the live stream itself (density, pack speed, frame
brightness, the cam's own timezone, weekend) — the street votes too.

How to edit: TEMPERS and ORBITS claim lines from style.py, verbatim; a line may
sit in several sets. If you reword a line in style.py, move it here too — run
`python -m car_stories.correlator` to list orphans.
"""

# tiebreak order per axis — the more particular wins a tie; the last is the shrug
TEMPER_ORDER = ["tender", "lost", "quiet", "harried", "restless",
                "dutiful", "weary", "light", "steady"]
ORBIT_ORDER = ["school", "escape", "social", "errands", "home", "work", "nowhere"]

TEMPER_VOTES = {
    # speed — the loudest evidence
    "racing": {"harried": 2},
    "cruising": {"steady": 2},
    "crawling": {"weary": 2},
    "still": {"quiet": 1, "weary": 1},
    # behavior (relative to the pack)
    "flooring it": {"harried": 2},
    "dawdling": {"lost": 2, "quiet": 1},
    "stop and go": {"weary": 2},
    # color — the over-read: paint as temperament
    "red": {"harried": 1},
    "blue": {"quiet": 1},
    "green": {"light": 1},
    "yellow": {"light": 1},
    "orange": {"light": 1},
    "purple": {"tender": 1},
    "white": {"steady": 1},
    "silver": {"steady": 1},
    "black": {"steady": 1},
    # direction — leaving reads lonelier than arriving; arriving reads warmer
    "heading away": {"quiet": 1, "restless": 1},
    "approaching the camera": {"tender": 1},
    # the hour still colors the feeling a little
    "morning": {"dutiful": 2, "harried": 1},
    "midday": {"steady": 1},
    "late afternoon": {"dutiful": 1, "weary": 1},
    "evening": {"weary": 2, "light": 1, "tender": 1},
    "night": {"light": 2, "restless": 1, "quiet": 1},
    "the small hours": {"quiet": 2, "restless": 1, "weary": 1},
    # kind (when we know it) — the body votes too
    "family": {"dutiful": 2},
    "hauler": {"dutiful": 1},
    "showoff": {"light": 1, "harried": 1},
    "vintage": {"tender": 2},
    "wanderer": {"restless": 2},
    "rugged": {"restless": 2},
    "motorcycle": {"restless": 2},
    # the small beat-up sedan leans introspective/free — enough to tip a night
    # read toward quiet or light (her registers), never enough to beat the strong
    # steady of a daytime cruise
    "compact": {"quiet": 1, "restless": 1, "light": 1},
    # the place itself (vibe: in cams.yaml)
    "beach": {"light": 2},
    "tourist": {"lost": 1, "light": 1},
    # the street itself
    "the crawl": {"weary": 2},
    "the thick of it": {"steady": 1},
    "an empty street": {"quiet": 1, "restless": 1},
    "a quiet road": {"quiet": 1},
    "dark": {"quiet": 1},
    "dim": {"weary": 1},
    "bright": {"light": 1},
}

ORBIT_VOTES = {
    # the cam's local hour — the biggest tell of what a life is up to
    "morning": {"work": 2, "school": 2},
    "midday": {"errands": 2, "work": 1},
    "late afternoon": {"school": 2, "home": 1, "errands": 1},
    "evening": {"home": 2, "social": 1},
    "night": {"social": 1, "home": 1, "nowhere": 1},
    "the small hours": {"nowhere": 2, "work": 1},
    # the day of the week — a Saturday morning is not a commute
    "weekend": {"social": 2, "escape": 2, "school": -2, "work": -2},
    "weekday": {"work": 1},
    # the body
    "family": {"school": 2, "home": 1},
    "hauler": {"school": 1, "errands": 1},
    "showoff": {"social": 2},
    "wanderer": {"escape": 2},
    "rugged": {"escape": 2},
    "motorcycle": {"escape": 1, "social": 1},
    "vintage": {"social": 1},
    "compact": {"escape": 1, "social": 1},   # errands by day, friends/drives by night
    # the place itself (vibe: in cams.yaml) — nobody on Ocean Drive is
    # commuting to a night shift
    "beach": {"social": 2, "escape": 2, "work": -2, "school": -1},
    "tourist": {"social": 1, "escape": 1, "work": -1},
    "downtown": {"work": 1, "social": 1},
    "freeway": {"work": 1},
}

TEMPERS = {
    "harried": {
        "late again", "rehearsing an excuse", "five minutes behind all day",
        "cutting it close, as usual", "ten minutes from consequences",
        "driving like the light was personal",
        "late and flooring it", "late enough to risk it",
        "making the next light a personal matter",
        "someone late for something",
        "almost missed it, still catching their breath",
        "Late", "Overdue", "Latecomer",
    },
    "dutiful": {
        "a whole team's worth of cleats", "the designated aunt",
        "first day, wrong shoes",
        "Punctual", "Weekday", "Faithful", "Provider",
    },
    "steady": {
        "making good time and telling no one",
        "a local, unhurried", "someone between appointments",
        "Reasonable", "Unhurried", "Patient", "Regular", "Neighbor", "Local",
    },
    "weary": {
        "done with today", "too tired to arrive", "resigned to the clock",
        "counting brake lights", "one podcast from peace",
        "asleep by the window", "two shifts deep, one to go",
        "a night-shifter heading in early",
        "Reluctant", "Homebound",
    },
    "light": {
        "windows down on principle", "easy for once",
        "old friends by accident", "a regular the cafe knows by order",
        "the radio up past all sense",
        "Borrowed", "Optimist",
    },
    "restless": {
        "tempted to miss the exit on purpose", "running from it",
        "free and a little reckless", "nothing to lose today",
        "a shortcut kind of person", "one bad decision from a great story",
        "cold hands, no regrets",
        "Restless", "Wanderer",
    },
    "tender": {
        "humming something old", "holding flowers wrong",
        "carrying soup, carefully",
        "on the phone with their mom, mostly listening",
        "to see his mother", "toward a kitchen with the light still on",
        "to a door with the porch light on", "on the way to a first date",
        "Tender", "Guest", "Caretaker",
    },
    "lost": {
        "looking for an address", "first time on this street",
        "not sure they're in the right place", "a tourist",
        "new to the city, acting otherwise",
        "counting stops in a language they're learning",
        "toward an address on a napkin",
        "Turned-Around", "Visitor",
    },
    "quiet": {  # the introspective temper — where the rationed ache lives
        "alone on purpose", "the radio doing the feeling",
        "letting the day settle", "not ready to go",
        "finishing the song first",
        "a crossword, in pen", "reading the same page twice",
        "texting someone they shouldn't", "watching their stop go by on purpose",
        "a person with nowhere to be",
        "singing in the car like nobody can see in",
        "lonely in the way a new city makes you",
        "a song they'd never admit to, loud",
        "to the appointment they rescheduled twice", "the hospital",
        "Quiet", "Second-Guessing", "Stranger", "Witness",
    },
}

ORBITS = {
    "work": {
        "a commuter", "a work badge on the passenger seat", "someone starting out",
        "a first shift", "a meeting they didn't ask for",
        "coffee before the hard part",
        "the night shift", "to the night shift", "the late shift",
        "a shift nobody wanted", "late for work", "first day, wrong shoes",
        "a commuter on foot", "two shifts deep, one to go",
        "Commuter", "Provider",
    },
    "school": {
        "someone's mom", "a dad on pickup duty", "a carpool three kids deep",
        "the school-run shift", "a whole team's worth of cleats",
        "the designated aunt", "a student", "a student, headphones in",
        "the school run", "drop-off, then the day", "a pickup",
        "the school gate", "practice pickup", "to the recital",
        "Carpooler",
    },
    "errands": {
        "errands", "errands stacked three deep", "an appointment",
        "one last errand", "the usual rounds",
        "to the pharmacy before it closes", "to return the drill",
        "to the grocery store, list forgotten", "to pick up the cake",
        "groceries in their lap",
        "running an errand only she would call urgent",
        "a glovebox full of half-finished errands",
        "Errand-Runner",
    },
    "home": {
        "toward home", "the way home", "home, finally",
        "toward dinner, eventually", "home to let the dog out", "home",
        "a dinner going cold", "beating the rush, and failing",
        "home, very late", "going home", "deciding what's for dinner",
        "toward a kitchen with the light still on",
        "Homebound",
    },
    "social": {
        "somebody's birthday", "a friend's couch",
        "to a friend's couch and the game", "a late lunch",
        "a lunch that's really a favor", "the gym", "to the gym",
        "on the way to a first date", "old friends by accident",
        "holding flowers wrong",
        "off to see the handful of friends she's made",
        "a date she hasn't mentioned to the group chat",
        "Visitor", "Guest",
    },
    "escape": {
        "out past the last exit", "no plan past the on-ramp",
        "one more hour of freedom", "a drive to clear their head",
        "the drive itself, mostly", "tempted to miss the exit on purpose",
        "Wanderer",
    },
    "nowhere": {
        "nowhere in particular", "toward nothing urgent",
        "a person with nowhere to be", "down a road they could drive asleep",
        "Stranger",
    },
}

# --- machinery (index + helpers); the taste is all above this line ------------

_CLAIMS: dict[str, frozenset] = {}
for _axis in (TEMPERS, ORBITS):
    for _name, _entries in _axis.items():
        for _e in _entries:
            _CLAIMS[_e] = frozenset(_CLAIMS.get(_e, frozenset()) | {_name})

_EMPTY = frozenset()


def claims(entry: str) -> frozenset:
    """Which tempers/orbits claim this line (empty = free, fits any life)."""
    return _CLAIMS.get(entry, _EMPTY)


def _tally(votes: dict, signals, order: list, default: str) -> tuple[str, int]:
    """Returns (winner, margin) — margin is how far ahead the winner was."""
    score = {m: 0 for m in order}
    for s in signals:
        for m, w in votes.get(s or "", {}).items():
            score[m] += w
    ranked = sorted(score.values(), reverse=True)
    best, second = ranked[0], ranked[1] if len(ranked) > 1 else 0
    if best <= 0:
        return default, 0
    return next(m for m in order if score[m] == best), best - second


def read(features: dict) -> dict:
    """The reading: every attribute votes on each axis; the winners are the
    read. Deterministic — same evidence, same read. `conviction` is how
    emphatic the votes were — an unremarkable car reads near zero."""
    from . import style
    kind = style.kind_of(features)
    sc = features.get("scene") or {}
    day = "weekend" if sc.get("weekend") else "weekday"
    temper, tm = _tally(TEMPER_VOTES,
                        (features.get("speed"), features.get("behavior"),
                         features.get("color"), features.get("direction"), kind,
                         features.get("time_of_day"), features.get("vibe"),
                         sc.get("tempo"), sc.get("light")),
                        TEMPER_ORDER, "steady")
    orbit, om = _tally(ORBIT_VOTES,
                       (features.get("time_of_day"), day, kind,
                        features.get("vibe")),
                       ORBIT_ORDER, "errands")
    return {"temper": temper, "orbit": orbit, "conviction": tm + om}


def _style_lines() -> set:
    """Every line that exists in style.py's pools, flattened."""
    from . import style

    def flatten(x, out):
        if isinstance(x, str):
            out.add(x)
        elif isinstance(x, dict):
            for v in x.values():
                flatten(v, out)
        elif isinstance(x, (list, tuple, set)):
            for v in x:
                flatten(v, out)

    out: set = set()
    for pool in (style.WHO, style.EMOTION, style.BEHAVIOR_EMOTION, style.PURPOSE,
                 style.TOWARD, style.BUS_LIVES, style.KIDS_LIVES, style.PERSON_WHO,
                 style.PERSON_WHO_CALM, style.PERSON_MOOD, style.ARCH_ADJ, style.ARCH_NOUN,
                 style.KIND_EMOTION, style.KIND_PURPOSE, style.KIND_TOWARD,
                 style.KIND_ARCHETYPE):
        flatten(pool, out)
    return out


def orphans() -> list:
    """Claims that match no style.py line — usually a rewording drift."""
    known = _style_lines()
    return sorted(e for e in _CLAIMS if e not in known)


if __name__ == "__main__":
    bad = orphans()
    if bad:
        print("orphaned claims (no matching line in style.py):")
        for e in bad:
            print(f"  {e!r}")
    else:
        print("correlator clean — every claim matches a style.py line")
