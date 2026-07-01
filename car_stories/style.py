"""YOUR style — the associations the piece is built on. Edit this freely.

This is the "trained on my taste" surface. Everything here maps something the
camera can observe to a story ingredient. The narrator (narrator.py) is just the
machinery that assembles these; the *taste* lives here.

`kind` is derived from the reliable signals we actually get: COCO vehicle type
(car / bus / truck / motorcycle) + size (big/near vs small/far, a rough proxy for
van-vs-compact). Fine reads like "old car" or "minivan" aren't reliably
detectable on traffic-cam footage, so the associations key off what is — plus a
few cheap color+locale reads (a yellow car in a US city is a cab) that reach
where the classifier can't.

One rule everything here obeys: invention may go anywhere the evidence is
silent, but must never fight the evidence we have. A cab visibly has a
destination, so a cab is never "going nowhere" — kinds with a visible telos get
their own emotion/purpose pools (KIND_EMOTION etc.) instead of the generic ones.

Register: mostly mundane. Most lives are errands, dinner, the gym — the ache is
rationed to a few entries per pool so it lands rarely and therefore lands.
Nobody's long-lost daughter shows up on a Tuesday commute.
"""

# No names. The camera can't know a name, and a guessed one claims too much —
# "a commuter" is the honest register. (`locale:` in cams.yaml still matters:
# it grounds reads like yellow-car→cab.)

# fine body-type (ImageNet, only on close crops) → a kind you have opinions about
FINE_KIND = {
    "minivan": "family", "beach_wagon": "family",
    "moving_van": "mover", "recreational_vehicle": "wanderer",
    "sports_car": "showoff", "convertible": "showoff", "racer": "showoff",
    "limousine": "wealth",
    "cab": "cabbie",
    "police_van": "duty", "ambulance": "duty", "fire_engine": "duty",
    "pickup": "tradesman", "tow_truck": "tradesman",
    "garbage_truck": "labor", "trailer_truck": "trucker",
    "jeep": "rugged",
    "minibus": "transit", "streetcar": "transit", "trolleybus": "transit",
    "school_bus": "kids",
    "Model_T": "vintage",
}

# kinds that hold many lives at once
MULTI = {"bus", "transit", "kids"}


# --- kind: fine type if we saw it up close, else cheap grounded reads, ---------
# --- else coarse type + size ----------------------------------------------------
def kind_of(features: dict) -> str:
    ft = (features.get("fine_type") or "").replace(" ", "_")
    if ft in FINE_KIND:
        return FINE_KIND[ft]
    t = features["vehicle_type"]
    # color+locale heuristics — the classifier rarely gets a close enough crop on
    # traffic cams, but a yellow car in a US city still reads at any distance
    if features.get("color") == "yellow" and features.get("locale") in ("usa", "default"):
        if t == "car":
            return "cabbie"
        if t == "bus":
            return "kids"
    if t in ("bus", "truck", "motorcycle"):
        return t
    return {"big": "hauler", "small": "compact"}.get(features["size"], "sedan")


# how the thinking-chips label a heuristic read (hedged — it's a guess, own it)
KIND_LABEL = {"cabbie": "taxi, probably", "kids": "school bus"}


# who they are — the association per kind (your call)
WHO = {
    # coarse (type + size), used when we never saw the car up close
    "hauler": ["someone's mom", "a dad on pickup duty", "a carpool three kids deep",
               "a family, probably", "the school-run shift",
               "a whole team's worth of cleats", "errands stacked three deep",
               "the designated aunt"],
    "compact": ["young and broke", "a first car, barely", "a student, probably",
                "someone starting out", "living close to the bone",
                "a parallel-parker by necessity", "renting, still"],
    "sedan": ["someone ordinary, which is to say infinite", "a commuter",
              "nobody in particular", "a regular",
              "the middle of the bell curve, driving",
              "a work badge on the passenger seat", "a podcast half-listened to"],
    "truck": ["a tradesman", "a hauler by trade", "someone who works with his hands",
              "a life of loading and unloading", "a bed full of somebody's weekend",
              "paid by the job, not the hour"],
    "motorcycle": ["free and a little reckless", "nothing to lose today",
                   "a shortcut kind of person", "one bad decision from a great story",
                   "cold hands, no regrets"],
    # fine (classifier close-up, or a color+locale read)
    "family": ["someone's mom", "a dad on pickup duty", "a carpool three kids deep",
               "the school-run shift", "juice boxes and diplomacy",
               "a referee of the back seat"],
    "mover": ["starting over somewhere", "a whole life in boxes", "moving day, again",
              "an address about to be past tense"],
    "wanderer": ["no fixed address", "chasing summer", "running away in comfort",
                 "retired into motion"],
    "showoff": ["wants you to look", "young money, or faking it", "weekend adrenaline",
                "the payment's due on the 1st", "louder than necessary, on purpose"],
    "wealth": ["someone being driven", "an occasion, probably", "money that stays quiet",
               "tinted windows and a schedule"],
    "cabbie": ["a stranger in the back", "someone else's hurry", "the city's confessional",
               "forty stories a shift, none theirs", "a map of the city kept in the hands"],
    "duty": ["someone's worst day", "on the clock for a crisis", "paid to arrive fast",
             "the calm voice in the front"],
    "tradesman": ["tools in the back", "works with his hands", "a life of loading and unloading",
                  "an invoice riding shotgun"],
    "labor": ["the unglamorous shift", "up before the city", "the work nobody thanks",
              "the reason the streets are clean by seven"],
    "trucker": ["a thousand miles from home", "hauling for someone else", "coffee and centerlines",
                "home is a bunk behind the seat", "on a first-name basis with three time zones"],
    "rugged": ["allergic to pavement", "a weekend escape artist", "dogs in the back, probably",
               "mud as a personality"],
    "vintage": ["an old soul, kept running", "loved for decades", "slower on purpose",
                "original parts, mostly"],
}

# --- kinds with a visible telos: the destination is on the outside of the car. --
# These pools replace the generic EMOTION / PURPOSE / TOWARD so the invention
# never contradicts what the camera plainly knows (a cab is never "going nowhere").
# For cabbie, TOWARD is deliberately NOT overridden — the default destinations
# read as the fare's, which is the whole point of a cab.
KIND_EMOTION = {  # keyed by speed (behavior folds into speed via BEH_TO_SPEED)
    "cabbie": {
        "racing": ["a fare cutting it close", "the meter running hot",
                   "an airport run behind schedule", "someone else's emergency, metered"],
        "cruising": ["between fares", "circling for the next raised hand",
                     "listening more than talking", "the city sliding by at cost"],
        "crawling": ["the meter ticking through gridlock", "a fare gone quiet in the back",
                     "the long way, not by choice"],
        "_": ["posted up, waiting on a wave", "off duty in name only"],
    },
    "duty": {
        "racing": ["someone's worst day, minutes out", "lights first, questions later"],
        "cruising": ["between calls, coffee cooling", "patrolling nothing in particular"],
        "crawling": ["easing through the scene", "the slow part of a bad night"],
        "_": ["on standby", "waiting for the radio to ruin the quiet"],
    },
    "trucker": {
        "racing": ["a deadline two states wide", "making up an hour lost at the scales"],
        "cruising": ["dead center of a long haul", "coffee, centerline, repeat"],
        "crawling": ["fourteen gears and no room to use them",
                     "the city's revenge on a highway animal"],
        "_": ["logbook says stop"],
    },
    "mover": {
        "racing": ["the deposit riding on a deadline"],
        "cruising": ["a whole apartment doing the speed limit",
                     "someone's life, strapped and steady"],
        "crawling": ["the last mile of an old address", "careful past every pothole"],
        "_": ["double-parked at a threshold"],
    },
    "labor": {
        "racing": ["behind on the route"],
        "cruising": ["the route on rails", "halfway through the city's leftovers"],
        "crawling": ["stop by stop, bin by bin", "the pace the job actually goes"],
        "_": ["mid-shift pause"],
    },
}

KIND_PURPOSE = {  # flat — the job overrides the time of day
    "cabbie": ["a fare", "the airport run", "whoever waves next", "the bar crowd, later"],
    "duty": ["the call", "someone's emergency"],
    "trucker": ["a dock two states away", "the last leg"],
    "mover": ["the new place", "a lease that starts today"],
    "labor": ["the route", "the transfer station"],
}

KIND_TOWARD = {
    "duty": ["toward the sirens' reason", "to arrive first and stay longest"],
    "trucker": ["another state by morning", "wherever the load is due"],
    "mover": ["to an empty room that echoes", "toward a key that still sticks"],
    "labor": ["one block at a time", "to the yard by end of shift"],
}

KIND_ARCHETYPE = {  # job kinds get named for the job, not a private drama
    "cabbie": ["The Meter Runner", "The City's Confessional", "The Night Fare"],
    "duty": ["The First to Arrive", "The Worst-Day Witness"],
    "trucker": ["The Long Hauler", "The Centerline Monk"],
    "mover": ["The Fresh Start", "The Address Changer"],
    "labor": ["The Early Shift", "The Unthanked"],
    "kids": ["The School Run"],
    "vintage": ["The Kept Promise", "The Slow Century"],
}

# bus → many stories: little lives glimpsed through the windows (mostly ordinary)
BUS_LIVES = ["late for work", "going home", "asleep by the window",
             "on the way to a first date", "groceries in their lap",
             "reading the same page twice", "almost there",
             "same song, third time", "a crossword, in pen",
             "playing a game on 4% battery", "deciding what's for dinner",
             "half-asleep, trusting the route",
             "on the phone with their mom, mostly listening",
             "almost missed it, still catching their breath",
             "two shifts deep, one to go", "holding flowers wrong",
             "new to the city, acting otherwise", "pretending to sleep",
             "carrying soup, carefully", "first day, wrong shoes",
             "old friends by accident",
             "counting stops in a language they're learning",
             # the rationed ache
             "texting someone they shouldn't", "watching their stop go by on purpose"]
BUS_COUNT = 3

# school bus → the lives are small and the stakes are enormous
KIDS_LIVES = ["homework finished on a knee", "a permission slip, unsigned",
              "the back row, as always", "show-and-tell in a shoebox",
              "a best friend since Tuesday", "practicing a spelling word",
              "asleep before the second stop", "a loose tooth and a plan",
              "still in yesterday's argument with a brother",
              "the window seat, won fairly", "lunch traded before first bell",
              "a secret held all the way to the gate"]
MULTI_LIVES = {"kids": KIDS_LIVES}  # everyone else glimpses BUS_LIVES

# --- the rest: grounded in motion / time / direction --------------------------
EMOTION = {  # by speed — mostly mundane; one ache each, rationed
    "racing": ["late again", "cutting it close, as usual", "hoping the lights cooperate",
               "rehearsing an excuse", "five minutes behind all day",
               "ten minutes from consequences", "driving like the light was personal",
               "running from it"],
    "cruising": ["easy for once", "in no rush", "between things",
                 "the radio doing the feeling", "letting the day settle",
                 "windows down on principle", "making good time and telling no one",
                 "alone on purpose"],
    "crawling": ["stuck and patient", "done with today", "waiting it out",
                 "counting brake lights", "resigned to the clock",
                 "one podcast from peace", "in line like everyone else",
                 "too tired to arrive"],
    "_": ["not ready to go", "in no hurry to get out", "idling on it",
          "finishing the song first"],
}

BEHAVIOR_EMOTION = {  # how they drive → how they feel (overrides plain speed)
    "flooring it": ["late and flooring it", "late enough to risk it",
                    "making the next light a personal matter"],
    "dawdling": ["in no rush at all", "looking for an address", "killing time on purpose",
                 "first time on this street"],
    "stop and go": ["stuck in it, patience fraying", "brake lights and small sighs",
                    "going nowhere, slowly", "in traffic and in thought"],
}

# fold behavior into a speed key for the telos-kind pools (a cab flooring it is
# still a cab in a hurry — never "running from something")
BEH_TO_SPEED = {"flooring it": "racing", "dawdling": "crawling", "stop and go": "crawling"}

GEOGRAPHY = {  # (from, toward) by direction
    "eastbound": ("downtown", "the suburbs"), "westbound": ("the suburbs", "downtown"),
    "approaching the camera": ("the interstate", "close now"),
    "heading away": ("this side of town", "the edge of town"),
    "_": ("across town", "the other side"),
}

PURPOSE = {  # by actual time of day
    "morning": ["the school run", "a first shift", "a meeting they didn't ask for",
                "coffee before the hard part", "drop-off, then the day"],
    "midday": ["errands", "a late lunch", "an appointment",
               "the gym, allegedly", "a lunch that's really a favor"],
    "late afternoon": ["the way home", "a pickup", "the school gate",
                       "one last errand", "beating the rush, and failing"],
    "evening": ["home", "the night shift", "a dinner going cold",
                "somebody's birthday", "practice pickup"],
    "night": ["nowhere in particular", "a friend's couch", "the late shift",
              "a drive to clear their head", "one more hour of freedom"],
    "the small hours": ["the airport", "a shift nobody wanted", "home, very late",
                        "the first flight out", "the hospital"],
    "_": ["the usual rounds", "somewhere they keep putting off"],
}

# people on foot — their own voice
PERSON_WHO = ["someone late for something", "a person with nowhere to be",
              "a commuter on foot", "a local, unhurried", "a tourist, probably",
              "someone between appointments", "a worker on break",
              "a student, headphones in", "a regular the cafe knows by order",
              "somebody's neighbor", "a dog walker without the dog today",
              "a night-shifter heading in early",
              "a stranger everyone here has seen before"]
PERSON_MOOD = {
    "waiting": ["waiting on someone", "killing time", "checking the time again",
                "not sure they're in the right place",
                "reading the same text again",
                "early for once, unsure what to do with it"],
    "hurrying": ["late and moving", "half-running", "weaving through the slow",
                 "in shoes not meant for this", "the bus is now or never"],
    "ambling": ["in no rush", "taking the long way", "lost in a thought",
                "window-shopping the closed stores", "walking off a phone call",
                "practicing a conversation"],
}
PERSON_TEMPLATES = ["{who}, {mood}", "{who} · {toward}", "{mood}, {toward}",
                    "{who} · {mood}"]

TOWARD = ["toward home", "to the recital", "to the night shift", "home, finally",
          "to pick up the cake", "back for the thing they forgot",
          "home to let the dog out", "to the gym, probably",
          "to the pharmacy before it closes", "toward dinner, eventually",
          "to return the drill", "to a friend's couch and the game",
          "to the grocery store, list forgotten", "toward nothing urgent",
          # the rationed ache
          "to see his mother", "to the appointment they rescheduled twice",
          "toward a kitchen with the light still on"]

ARCH_ADJ = ["Reluctant", "Late", "Unhurried", "Homebound", "Patient",
            "Punctual", "Stubborn", "Quiet", "Reasonable", "Weekday",
            "Almost-There", "Second-Guessing", "Borrowed", "Faithful",
            "Restless", "Overdue"]
ARCH_NOUN = ["Commuter", "Visitor", "Regular", "Neighbor", "Local",
             "Errand-Runner", "Carpooler", "Latecomer", "Optimist",
             "Middle Child", "Caretaker", "Provider", "Understudy",
             "Stranger", "Witness"]

# how a single line gets assembled (bus is handled separately)
TEMPLATES = [
    "{who}, {emotion}",
    "{who} · {toward}",
    "{emotion}, {toward}",
    "{who} · {purpose}",
    "{emotion}, in from {origin}",
    "{emotion} · {purpose}",
    "in from {origin} · {toward}",
]
