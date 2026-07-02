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

What belongs *together* is not this file's job — that's the correlator
(correlator.py), the second taste surface.
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
    "police_van": "cop",
    "ambulance": "duty", "fire_engine": "duty",
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


# how the thinking-chips label a heuristic read. the label is a guess; how
# *sure* the machine sounds saying it is HEDGE's job (below).
KIND_LABEL = {"cabbie": "taxi", "kids": "school bus"}


# --- the machine's certainty, turned to voice ---------------------------------
# the detector reports its own confidence per detection; the thinking-chips wear
# it. a shaky read hedges out loud, a firm one commits. being wrong is still
# part of the piece — but now you can hear it doubting. `{a}` is the subject
# phrase, e.g. "a taxi", "a person".
HEDGE = {
    "low":  ["maybe {a}?", "{a}, I think?", "…{a}?", "a shape — {a}?",
             "hard to tell. {a}?", "{a}, if that"],
    "mid":  ["{a}, probably", "looks like {a}", "{a}, I'd say", "{a}, near enough",
             "{a}, most likely"],
    "high": ["{a}", "{a}", "{a}", "{a}, clearly", "{a}, no question"],
}

# which observations the machine is willing to take back once a sharper look
# overrules them. the rest read as fixed jottings — a live stream of guesses
# that only ever corrects the things worth correcting.
REVISABLE = {"id", "color"}

# it catches itself: a guess already voiced, corrected as the read sharpens
# (a closer crop resolves the body, the class vote flips, the color firms up).
# `{new}` is the corrected chip.
REVISION = ["— no, {new}", "— {new}, actually", "…make that {new}",
            "wait — {new}", "no: {new}", "correction — {new}"]

# not a correction but a firming: the same guess, now said with a straight back
# as the confidence climbs. `{a}` is the (unchanged) subject phrase.
CONFIRM = ["— yes, {a}", "{a}, definitely", "settled: {a}", "— {a} after all",
           "no, it is {a}"]

# the classic traffic-cam false positive: something that never moves, read as a
# person. NOT culled — kept, and then doubted. when a "person" holds perfectly
# still frame after frame, the machine stops believing in the soul and names the
# furniture instead. `{thing}` fills from here.
STREET_FURNITURE = ["a mailbox", "a street lamp", "a parking meter",
                    "a fire hydrant", "a newspaper box", "a trash can",
                    "a bollard", "a signpost", "a phone booth", "a standpipe",
                    "a mannequin in a window", "a sandwich board"]
FURNITURE_DOUBT = ["hasn't moved — {thing}?", "still hasn't budged. {thing}?",
                   "not a soul — {thing}, maybe", "frozen. just {thing}",
                   "no, nobody's there — {thing}"]


# who they are — the association per kind (your call)
WHO = {
    # coarse (type + size), used when we never saw the car up close
    "hauler": ["someone's mom", "a dad on pickup duty", "a carpool three kids deep",
               "a family", "the school-run shift",
               "a whole team's worth of cleats", "errands stacked three deep",
               "the designated aunt", "a caterer with trays sliding",
               "a dog-rescue volunteer", "a garage band and all their gear",
               "someone moving a couch as a favor"],
    "compact": ["young and broke", "a first car, barely", "a student",
                "someone starting out", "living close to the bone",
                "a parallel-parker by necessity", "renting, still",
                "a nurse coming off nights", "a retiree who downsized the car too",
                "paid off as of last month", "a barista with a second act",
                "someone who likes small cars, no story there",
                "an organist, believe it or not", "a grad student defending in spring",
                "a painter between commissions", "a realtor between showings",
                "a home-care aide on the third visit of four",
                "a poet with a day job", "an accountant who did the math on gas",
                "a substitute teacher, new school every week",
                # the fleshed-out one: a young woman newly transplanted, a beat-up
                # small sedan, the radio always up — work, the few friends she's
                # made, obscure errands, the occasional night date, and the
                # lonely-free drive that clears her head. (Gender's invention, not
                # a read; it stays in this kind's pool, so it never lands on a
                # truck. Nothing here claims a time or a speed — those are the
                # honest pools' job, so a noon compact never "night-drives".)
                "new to the city, and it shows a little",
                "a few months in, still learning the one-ways",
                "just moved here, everything still a wrong turn",
                "learning the city one wrong turn at a time",
                "a fresh transplant, half the boxes still packed",
                "her first city, her first lease",
                "off to see the handful of friends she's made",
                "a date she hasn't mentioned to the group chat",
                "running an errand only she would call urgent",
                "a glovebox full of half-finished errands",
                "the radio always a little too loud",
                "blasting something nobody else has heard of",
                "singing in the car like nobody can see in",
                "a dreamer who thinks best behind the wheel",
                "lonely in the way a new city makes you",
                "a beat-up first car she loves anyway",
                "young, broke, and free in about equal measure"],
    "sedan": ["someone ordinary, which is to say infinite", "a commuter",
              "nobody in particular", "a regular",
              "the middle of the bell curve, driving",
              "a work badge on the passenger seat", "a podcast half-listened to",
              "a middle manager rehearsing kindness", "half of a long-distance thing",
              "a notary with a full afternoon", "somebody's landlord, off the clock",
              "an inspector of something obscure", "a birdwatcher out of season",
              "a wedding guest who left early",
              "a regional manager with a trunk full of samples",
              "a quarterly-numbers kind of morning",
              "a session musician nobody waves at anymore",
              "a mother with twenty minutes to herself",
              "an old friend from a life that didn't happen",   # the Whitman line
              "a sculptor who welds for money"],
    "truck": ["a tradesman", "a hauler by trade", "someone who works with his hands",
              "a life of loading and unloading", "a bed full of somebody's weekend",
              "paid by the job, not the hour", "a beekeeper, oddly",
              "a fence-builder between jobs",
              "somebody's uncle with opinions about torque"],
    "motorcycle": ["free and a little reckless", "nothing to lose today",
                   "a shortcut kind of person", "one bad decision from a great story",
                   "cold hands, no regrets", "a commuter who did the math",
                   "quieter than the bike suggests"],
    # fine (classifier close-up, or a color+locale read)
    "family": ["someone's mom", "a dad on pickup duty", "a carpool three kids deep",
               "the school-run shift", "juice boxes and diplomacy",
               "a referee of the back seat"],
    "mover": ["starting over somewhere", "a whole life in boxes", "moving day, again",
              "an address about to be past tense"],
    "wanderer": ["no fixed address", "chasing summer", "running away in comfort",
                 "retired into motion", "light-hearted, taking to the open road"],
    "showoff": ["wants you to look", "young money, or faking it", "weekend adrenaline",
                "the payment's due on the 1st", "louder than necessary, on purpose",
                "a rockstar between reunions", "the divorce settlement, driving"],
    "wealth": ["someone being driven", "an occasion", "money that stays quiet",
               "tinted windows and a schedule", "a deal closing by phone",
               "a board seat running late"],
    "cabbie": ["a stranger in the back", "someone else's hurry", "the city's confessional",
               "forty stories a shift, none theirs", "a map of the city kept in the hands"],
    "duty": ["someone's worst day", "on the clock for a crisis", "paid to arrive fast",
             "the calm voice in the front"],
    # the cop is the one subject that is also a watcher — the machine sees a lot
    # of them, so the pool runs deep (an hour of squad cars shouldn't lap itself).
    # this is the piece's designated mirror: the watcher-thread runs richer here
    # than the rationed ache does elsewhere — the machine that invents lives off a
    # camera, reading the thing that reads us back — but the bulk stays mundane so
    # the mirror lands instead of lecturing.
    "cop": ["a badge and a long shift", "paid to be seen", "the beat, mostly boredom",
            "someone's authority, idling", "twenty years to the pension",
            "a rookie learning the quiet blocks", "a thermos and a good vantage",
            "an hour of paperwork in a uniform", "a local everyone knows and no one waves to",
            "a training officer and a nervous partner", "someone's whole idea of Tuesday",
            "counting down to the coffee, or the pension",
            "a name badge nobody reads", "a slow day they won't admit to hoping for",
            # the watcher, watched — the surveillance thread runs deeper here
            "another camera on the same corner", "reading plates, and read in turn",
            "the watcher, watched for once", "a lens that happens to drive",
            "a database with a siren", "keeping the same logs this machine keeps",
            # the rationed ache
            "a call they'll carry home", "one bad night they don't talk about"],
    "tradesman": ["tools in the back", "works with his hands", "a life of loading and unloading",
                  "an invoice riding shotgun"],
    "labor": ["the unglamorous shift", "up before the city", "the work nobody thanks",
              "the reason the streets are clean by seven"],
    "trucker": ["a thousand miles from home", "hauling for someone else", "coffee and centerlines",
                "home is a bunk behind the seat", "on a first-name basis with three time zones"],
    "rugged": ["allergic to pavement", "a weekend escape artist", "dogs in the back",
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
    "cop": {  # on the job, so never "errands" — and half its feeling is watching.
              # cruising is where a patrol car mostly lives, so that key runs deepest.
        "racing": ["lights on, someone called", "a call that came in hot",
                   "first to the thing nobody wants to see", "the radio turned it urgent",
                   "somewhere they have to be before it's worse",
                   "a code that clears the intersection",
                   "running toward what everyone runs from"],
        "cruising": ["the patrol, uneventful", "a slow loop of the same streets",
                     "windows down, just watching", "clocking every face out of habit",
                     "the block memorized years ago", "nothing to report, and grateful",
                     "eyes moving, car barely", "the same route, a different day",
                     "reading the street like a page they've read before",
                     "a nod to the crossing guard", "watching for the one thing out of place",
                     "everyone slowing down as they pass",
                     # the watcher-thread, threaded through the common key
                     "cataloguing the ordinary", "logging faces it'll never place",
                     "the mirror doing half the work"],
        "crawling": ["the speed trap, patient", "easing through the school zone",
                     "idling where the street can see them", "running a plate at the light",
                     "parked at an angle that means business",
                     "clocking speeds with nowhere to be", "the radar gun doing the waiting",
                     "watching the crosswalk win",
                     "stuck in the same traffic they'd ticket you for"],
        "_": ["posted at the corner, watching", "engine running, going nowhere",
              "parked in the shade, logging the block", "lights off, presence on",
              "a parked deterrent", "the corner car, part of the furniture now",
              "the long stakeout of an ordinary afternoon",
              "watching the watchers watch back"],
    },
    "trucker": {
        "racing": ["a deadline two states wide", "making up an hour lost at the scales"],
        "cruising": ["dead center of a long haul", "coffee, centerline, repeat",
                     "distance availing nothing"],
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
    "cop": ["a wellness check", "the plate that came back wrong",
            "the last hour of the shift", "the corner they always sit",
            "a noise complaint, probably nothing", "the same address as last week",
            "a report that writes itself", "shift change, and coffee first",
            "the school zone at three", "nothing, officially"],
    "trucker": ["a dock two states away", "the last leg"],
    "mover": ["the new place", "a lease that starts today"],
    "labor": ["the route", "the transfer station"],
}

KIND_TOWARD = {
    "duty": ["toward the sirens' reason", "to arrive first and stay longest"],
    "cop": ["toward whoever called", "back to the precinct, eventually",
            "the same corner as always", "wherever the radio points",
            "to the end of a quiet shift", "nowhere the dispatcher hasn't sent them",
            "toward the report, then the lot, then home",
            "to the next corner that can see them",
            # mutual surveillance — the one subject that can see the lens
            "eye to eye with the camera, neither blinking",
            "past the same lens it never clocks"],
    "trucker": ["another state by morning", "wherever the load is due"],
    "mover": ["to an empty room that echoes", "toward a key that still sticks"],
    "labor": ["one block at a time", "to the yard by end of shift"],
}

KIND_ARCHETYPE = {  # job kinds get named for the job, not a private drama
    "cabbie": ["The Meter Runner", "The City's Confessional", "The Night Fare"],
    "duty": ["The First to Arrive", "The Worst-Day Witness"],
    "cop": ["The Long Watch", "The Beat Cop", "The Other Camera", "The Corner Car",
            "The Speed Trap", "The Presence", "The One Who Watches Back"],
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
             "a paperback with a cracked spine", "leftovers riding shotgun",
             "one earbud, out of courtesy", "a birthday card, unsigned",
             "practicing the ask for a raise", "a plant balanced on one knee",
             "off at the next one, promise", "somebody's grandmother, unbothered",
             "a chess set and somewhere to be", "wet paint on their good jeans",
             "an umbrella on a clear day", "two crosswords ahead of the seatmate",
             "a cake box held level, mostly", "reading over a stranger's shoulder",
             # the rationed ache
             "texting someone they shouldn't", "watching their stop go by on purpose",
             "looking upon a stranger, longingly", "containing multitudes, quietly"]
BUS_COUNT = 2

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
EMOTION = {  # by speed — mostly mundane; one ache each, rationed.
    # These carry the one-clause stories, so the pools stay deep — an hour of
    # terse reads shouldn't lap itself.
    "racing": ["late again", "cutting it close, as usual", "hoping the lights cooperate",
               "rehearsing an excuse", "five minutes behind all day",
               "ten minutes from consequences", "driving like the light was personal",
               "green lights all the way, somehow", "passing on the right, sorry about it",
               "the fast lane as a personality", "wringing minutes out of the mile",
               "outrunning the forecast", "late to something unmissable",
               "running from it"],
    "cruising": ["easy for once", "in no rush", "between things",
                 "the radio doing the feeling", "letting the day settle",
                 "windows down on principle", "making good time and telling no one",
                 "humming something old", "tempted to miss the exit on purpose",
                 "keeping a comfortable distance", "signaling early, like they teach",
                 "at peace with the speed limit", "a full tank and no opinions",
                 "the commute on autopilot", "letting the fast ones pass",
                 "alone on purpose", "the radio up past all sense",
                 "a song they'd never admit to, loud",
                 "fluid, affectionate, chaste"],   # the collage, rationed
    "crawling": ["stuck and patient", "done with today", "waiting it out",
                 "counting brake lights", "resigned to the clock",
                 "one podcast from peace", "in line like everyone else",
                 "third cycle of the same red light",
                 "close enough to read bumper stickers",
                 "a car length gained, a car length lost",
                 "patience by necessity",
                 "too tired to arrive", "the procession, endless"],
    "_": ["not ready to go", "in no hurry to get out", "idling on it",
          "waiting on someone's front door", "double-parked and betting on it",
          "finishing the song first",
          "to wait, not doubting", "thinking of someone, sitting alone"],
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

PURPOSE = {  # by actual time of day (each hour keeps a free line — any life fits it)
    "morning": ["the school run", "a first shift", "a meeting they didn't ask for",
                "coffee before the hard part", "drop-off, then the day",
                "the day, already moving"],
    "midday": ["errands", "a late lunch", "an appointment",
               "the gym", "a lunch that's really a favor",
               "the middle stretch of the day"],
    "late afternoon": ["the way home", "a pickup", "the school gate",
                       "one last errand", "beating the rush, and failing",
                       "the tail end of the day"],
    "evening": ["home", "the night shift", "a dinner going cold",
                "somebody's birthday", "practice pickup",
                "the last stop of the day"],
    "night": ["nowhere in particular", "a friend's couch", "the late shift",
              "a drive to clear their head", "one more hour of freedom",
              "no plan past the on-ramp", "the drive itself, mostly",
              "the long way home, for the song", "a slow lap of the city, radio up",
              "out driving to feel like someone in a movie"],
    "the small hours": ["the airport", "a shift nobody wanted", "home, very late",
                        "the first flight out", "the hospital"],
    "_": ["the usual rounds", "somewhere they keep putting off"],
}

# people on foot — their own voice
PERSON_WHO = ["someone late for something",
              "a commuter on foot", "a tourist",
              "someone between appointments",
              "a student, headphones in", "a regular the cafe knows by order",
              "somebody's neighbor", "a dog walker without the dog today",
              "a night-shifter heading in early",
              "a stranger everyone here has seen before",
              "a retired teacher who knows this block",
              "someone sought, without knowing it"]
# identities that assume an unhurried gait — the narrator only draws these when
# the evidence doesn't show someone hurrying (a runner or a cyclist, both of whom
# reach us as a fast-moving "person", is never "a local, unhurried").
PERSON_WHO_CALM = ["a person with nowhere to be", "a local, unhurried",
                   "a worker on break", "someone walking off a big lunch",
                   "a new parent stealing an hour"]
PERSON_MOOD = {
    "waiting": ["waiting on someone", "killing time", "checking the time again",
                "not sure they're in the right place",
                "reading the same text again",
                "early for once, unsure what to do with it",
                "stopped somewhere, waiting"],
    "hurrying": ["late and moving", "half-running", "weaving through the slow",
                 "in shoes not meant for this", "the bus is now or never"],
    "ambling": ["in no rush", "taking the long way", "lost in a thought",
                "window-shopping the closed stores", "walking off a phone call",
                "practicing a conversation", "sauntering the pavement"],
}
PERSON_TEMPLATES = ["{who}, {mood}", "{who} · {toward}", "{mood}, {toward}",
                    "{who} · {mood}"]

TOWARD = ["toward home", "to the recital", "to the night shift", "home, finally",
          "to pick up the cake", "back for the thing they forgot",
          "home to let the dog out",
          "to the pharmacy before it closes", "toward dinner, eventually",
          "to return the drill", "to a friend's couch and the game",
          "to the grocery store, list forgotten", "toward nothing urgent",
          "out past the last exit", "toward an address on a napkin",
          "to a door with the porch light on", "to the gym",
          # free lines — any life fits (keep a few, or moods run out of road)
          "toward the usual exit", "down a road they could drive asleep",
          "a few blocks more", "the long way, chosen on purpose",
          # the rationed ache
          "to see his mother", "to the appointment they rescheduled twice",
          "toward a kitchen with the light still on",
          "certain they'll pass this way again",
          "toward a life of joy, somewhere surely"]

ARCH_ADJ = ["Reluctant", "Late", "Unhurried", "Homebound", "Patient",
            "Punctual", "Stubborn", "Quiet", "Reasonable", "Weekday",
            "Almost-There", "Second-Guessing", "Borrowed", "Faithful",
            "Restless", "Overdue", "Tender", "Turned-Around",
            "Sought", "Recall'd", "Glimpsed"]
ARCH_NOUN = ["Commuter", "Visitor", "Regular", "Neighbor", "Local",
             "Errand-Runner", "Carpooler", "Latecomer", "Optimist",
             "Middle Child", "Caretaker", "Provider", "Understudy",
             "Stranger", "Witness", "Wanderer", "Guest"]

# how a single line gets assembled (bus is handled separately).
# Most lives are ONE clause — the short templates below. The multi-clause
# shapes (plain, turn, scene, pack) are reserved for exceptional cars: notable
# behavior, a special body, or a read the votes were emphatic about.
TEMPLATES_SHORT = [
    "{emotion}", "{emotion}", "{emotion}",   # the feeling, mostly
    "{toward}",
    "{who}",
    "{purpose}",
]

TEMPLATES = [
    "{who}, {emotion}",
    "{who} · {toward}",
    "{emotion}, {toward}",
    "{who} · {purpose}",
    "{emotion}, in from {origin}",
    "{emotion} · {purpose}",
    "in from {origin} · {toward}",
]

# the turn — a clause that pulls against the first
TEMPLATES_TURN = [
    "{emotion}, but {toward}",
    "{who} — {emotion}, {toward} all the same",
]

# the street speaks — {scene_phrase} comes from what the cam can see right now
TEMPLATES_SCENE = [
    "{scene_phrase}, {emotion}",
    "{scene_phrase} · {toward}",
    "{who} · {scene_phrase}",
]

# (a "pack" shape once referenced another car by color — "trading lanes with the
# silver bike" — but nothing visually ties the story to that car, and there may
# be several silver ones, so the reference never lands. Removed: a clause may not
# point at something the viewer can't locate in the frame.)

# the place votes too — destinations that only exist *here*. Chains are fair
# game where a name isn't: a Wawa is a place, not a person, and nothing is more
# mundane than the store the locals have stopped seeing. Merged (thinly) into
# TOWARD / PURPOSE by region, so the local line lands occasionally, not always.
REGION_FLAVOR = {
    "philly": {  # Delaware / Philly orbit
        "toward": ["to the Wawa", "to the Acme before it closes",
                   "down toward the shore, off-season"],
        "purpose": ["a Wawa run", "a hoagie, half now half later"],
    },
    "nyc": {  # the hometown poet gets his borough back
        "toward": ["to the good bodega", "into a parking spot they won't surrender",
                   "crosstown the long way", "toward Brooklyn, of ample hills"],
        "purpose": ["the usual bagel order", "moving the car for street cleaning",
                    "the ferry, out of habit"],
    },
    "miami": {
        "toward": ["over the causeway", "to Publix"],
        "purpose": ["a cafecito at the window", "Publix, then maybe the beach"],
    },
    "socal": {
        "toward": ["to In-N-Out", "the 405, eventually"],
        "purpose": ["tacos from the same truck as always"],
    },
    "sandiego": {
        "toward": ["down to the water before sunset", "to the taco shop, the real one"],
        "purpose": ["a California burrito, no substitutions"],
    },
    "sacramento": {
        "toward": ["out toward the river", "to Raley's"],
        "purpose": ["the farmers market, early"],
    },
    "kingston": {
        "toward": ["up Constant Spring Road", "to Juici for a patty"],
        "purpose": ["a patty and cocoa bread", "beating the Half Way Tree traffic, badly"],
    },
    "bangkok": {
        "toward": ["to 7-Eleven, the near one", "through the soi shortcut"],
        "purpose": ["a 7-Eleven toastie", "the night market, before the crowd"],
    },
    "tokyo": {
        "toward": ["to the konbini, the usual one", "to the station, unhurried"],
        "purpose": ["a konbini stop", "home before the last train, easily"],
    },
    "london": {
        "toward": ["to the big Tesco", "round the chippy"],
        "purpose": ["a meal deal", "the school run, the long way round"],
    },
    "wyoming": {
        "toward": ["into town for the mail", "out past the elk fence"],
        "purpose": ["the feed store", "a tourist-season shift"],
    },
}

SCENE_PHRASE = {  # keyed by the scene tags narration.py derives from the stream
    "an empty street": ["the only one on the road", "no audience but the camera",
                        "the street to themselves"],
    "a quiet road": ["one of the few out", "the road mostly theirs"],
    "the thick of it": ["anonymous in the current", "one of the many",
                        "swimming with the school", "flitting by each other",
                        "among the multitude"],
    "the crawl": ["one brake light among hundreds", "boxed in on every side",
                  "part of the long red river"],
    # only tagged for a non-racing vehicle when people are actually on foot in
    # frame — so "watching the pedestrians win" never lands on an empty road
    "pedestrians": ["watching the pedestrians win", "waiting on the crossing",
                    "yielding to the crowd", "the crosswalk full, for now"],
    "dark": ["headlights doing the seeing", "past the lit windows"],
    "dim": ["under a flat gray sky", "in the day's last usable light"],
    "bright": ["squinting into the glare", "in hard daylight"],
    "weekend": ["nowhere to be till Monday", "on weekend time"],
}
