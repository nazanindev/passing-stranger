"""YOUR style — the associations the piece is built on. Edit this freely.

This is the "trained on my taste" surface. Everything here maps something the
camera can observe to a story ingredient. The narrator (narrator.py) is just the
machinery that assembles these; the *taste* lives here.

`kind` is derived from the reliable signals we actually get: COCO vehicle type
(car / bus / truck / motorcycle) + size (big/near vs small/far, a rough proxy for
van-vs-compact). Fine reads like "old car" or "minivan" aren't reliably
detectable on traffic-cam footage, so the associations key off what is.
"""

# Names are used *sparingly* (the piece gives stories, not names) and match the
# cam's locale. Set `locale:` per cam in cams.yaml.
NAMES_BY_LOCALE = {
    "usa": ["Marcus", "Priya", "Sam", "Ruth", "Omar", "Nadia", "Theo", "June",
            "Hassan", "Mara", "Cora", "Idris", "Bea", "Danny", "Gwen", "Lena"],
    "latin": ["Sofía", "Mateo", "Valentina", "Diego", "Camila", "Santiago",
              "Lucía", "Tomás", "Isabela", "Javier", "Elena", "Rafael", "Paula"],
    "japan": ["Haru", "Yuki", "Sora", "Ren", "Aoi", "Hana", "Kaito", "Mei",
              "Riku", "Yui", "Daiki", "Nao", "Emi", "Takumi"],
    "uk": ["Oliver", "Amelia", "Jack", "Freya", "Harry", "Grace", "Alfie",
           "Poppy", "Arthur", "Nia", "Charlie", "Esme", "Reggie", "Maeve"],
}
NAMES_BY_LOCALE["default"] = NAMES_BY_LOCALE["usa"]


def names_for(locale: str) -> list[str]:
    return NAMES_BY_LOCALE.get(locale, NAMES_BY_LOCALE["default"])


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


# --- kind: fine type if we saw it up close, else coarse type + size ------------
def kind_of(features: dict) -> str:
    ft = (features.get("fine_type") or "").replace(" ", "_")
    if ft in FINE_KIND:
        return FINE_KIND[ft]
    t = features["vehicle_type"]
    if t in ("bus", "truck", "motorcycle"):
        return t
    return {"big": "hauler", "small": "compact"}.get(features["size"], "sedan")


# who they are — the association per kind (your call)
WHO = {
    # coarse (type + size), used when we never saw the car up close
    "hauler": ["someone's mom", "a dad on pickup duty", "a carpool three kids deep",
               "a family, probably", "the school-run shift"],
    "compact": ["young and broke", "a first car, barely", "a student, probably",
                "someone starting out"],
    "sedan": ["someone ordinary, which is to say infinite", "a commuter",
              "nobody in particular", "a regular"],
    "truck": ["a tradesman", "a hauler by trade", "someone who works with his hands",
              "a life of loading and unloading"],
    "motorcycle": ["free and a little reckless", "nothing to lose today",
                   "a shortcut kind of person"],
    # fine (only when the classifier got a close look)
    "family": ["someone's mom", "a dad on pickup duty", "a carpool three kids deep",
               "the school-run shift"],
    "mover": ["starting over somewhere", "a whole life in boxes", "moving day, again"],
    "wanderer": ["no fixed address", "chasing summer", "running away in comfort"],
    "showoff": ["wants you to look", "young money, or faking it", "weekend adrenaline"],
    "wealth": ["someone being driven", "an occasion, or a funeral", "money that stays quiet"],
    "cabbie": ["a stranger in the back", "someone else's hurry", "the city's confessional"],
    "duty": ["someone's worst day", "on the clock for a crisis", "paid to arrive fast"],
    "tradesman": ["tools in the back", "works with his hands", "a life of loading and unloading"],
    "labor": ["the unglamorous shift", "up before the city", "the work nobody thanks"],
    "trucker": ["a thousand miles from home", "hauling for someone else", "coffee and centerlines"],
    "rugged": ["allergic to pavement", "a weekend escape artist", "dogs in the back, probably"],
    "vintage": ["an old soul, kept running", "loved for decades", "slower on purpose"],
}

# bus → many stories: little lives glimpsed through the windows
BUS_LIVES = ["late for work", "going home", "asleep by the window",
             "headed to the hospital", "on the way to a first date",
             "dreading the shift", "groceries and regrets in their lap",
             "reading the same page twice", "running from something",
             "one stop from crying", "almost there"]
BUS_COUNT = 3

# --- the rest: grounded in motion / time / direction --------------------------
EMOTION = {  # by speed
    "racing": ["late again", "in a hurry to nowhere", "chasing something", "running from it"],
    "cruising": ["easy for once", "alone on purpose", "in no rush", "between things"],
    "crawling": ["stuck and patient", "too tired to arrive", "done with today", "waiting it out"],
    "_": ["not ready to go", "somewhere else", "idling on it"],
}

BEHAVIOR_EMOTION = {  # how they drive → how they feel (overrides plain speed)
    "flooring it": ["late and flooring it", "in a dangerous hurry", "running from something"],
    "dawdling": ["in no rush at all", "lost, maybe", "killing time on purpose"],
    "stop and go": ["stuck in it, patience fraying", "brake lights and small sighs",
                    "going nowhere, slowly"],
}

GEOGRAPHY = {  # (from, toward) by direction
    "eastbound": ("downtown", "the suburbs"), "westbound": ("the suburbs", "downtown"),
    "approaching the camera": ("the interstate", "close now"),
    "heading away": ("here", "the edge of town"), "_": ("across town", "the other side"),
}

PURPOSE = {  # by actual time of day
    "morning": ["the school run", "a first shift"],
    "midday": ["errands", "a late lunch"],
    "late afternoon": ["the way home", "a pickup"],
    "evening": ["home", "the night shift"],
    "night": ["nowhere in particular", "a friend's couch"],
    "the small hours": ["the hospital", "away"],
    "_": ["somewhere they keep putting off"],
}

# people on foot — their own voice
PERSON_WHO = ["someone late for something", "a person with nowhere to be",
              "a commuter on foot", "a local, unhurried", "a tourist, probably",
              "someone between appointments", "a worker on break",
              "a student, headphones in"]
PERSON_MOOD = {
    "waiting": ["waiting on someone", "killing time", "checking the time again",
                "not sure they're in the right place"],
    "hurrying": ["late and moving", "half-running", "weaving through the slow"],
    "ambling": ["in no rush", "taking the long way", "lost in a thought"],
}
# mostly nameless — a name only slips in occasionally (last entry)
PERSON_TEMPLATES = ["{who}, {mood}", "{who} · {toward}", "{mood}, {toward}", "{name} · {mood}"]

TOWARD = ["toward home", "to see his mother", "to the recital", "toward nobody",
          "to the ex who kept the dog", "to the night shift", "home, finally",
          "toward the son who stopped calling"]

ARCH_ADJ = ["Reluctant", "Late", "Unhurried", "Faithful", "Vanishing",
            "Homebound", "Overdue", "Patient", "Restless", "Forgiven"]
ARCH_NOUN = ["Apologizer", "Commuter", "Visitor", "Runaway", "Provider",
             "Prodigal", "Ghost", "Caretaker", "Optimist", "Stranger"]

# how a single line gets assembled (bus is handled separately)
# mostly nameless — foreground the story; a name only slips in occasionally (last)
TEMPLATES = [
    "{who}, {emotion}",
    "{who} · {toward}",
    "{emotion}, {toward}",
    "{who} · {purpose}",
    "{emotion}, in from {origin}",
    "{name} · {who}",
]
