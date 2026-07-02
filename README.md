# passing stranger

*I am to see to it that I do not lose you*

![a Tokyo crossing, being read](assets/hero.jpg)

A camera watches a street — Shinjuku, South Beach, Half Way Tree. For each car
it sees, it makes up a driver: where they're coming from, where they're going,
what they're carrying. None of it is real. The machine just over-reads: red
car, eastbound, late afternoon → a whole person, late for something.

Each guess is grounded in what the camera can actually see, so it feels less
like a dice roll and more like being read. Same car, same soul.

> every life invented · none of it is real

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m car_stories.server      # → http://127.0.0.1:8000
```

The tabs are curated live public feeds (`cams.yaml`) — street cams and DOT
cameras, each verified genuinely live, fixed, and full of cars. Streams die
and loop and freeze out there; the roster is a garden, not a list.

## How

YOLO finds the cars and follows them. It watches a few at a time — the one
it's been staring at longest gets a story. The storyteller (`narrator.py`) is
word-lists and dice, seeded per car so a soul never changes while it's on
screen. No model, no key.

One rule: invention goes wherever the evidence is silent, but never fights the
evidence we have. A yellow car on a US cam reads as a cab, and a cab is never
"going nowhere" — kinds with a visible destination (cab, mover, trucker,
school bus…) get their own pools in `style.py`.

The taste lives on two surfaces. `style.py` says what things *are* — including
what the place offers: a car near Philadelphia might be on a Wawa run, one in
Kingston headed to Juici for a patty. `correlator.py` says how a combination
of evidence becomes a **mood** — every attribute votes (racing votes harried,
a blue car votes quiet, the small hours vote quiet twice), the combination's
winner is the read, and every clause of the story derives from it. No dice in
the reading: same evidence, same mood.

The narrator keeps two novelty memories — whole lines stay gone a long while,
single clauses a short one — so the street repeats itself the way real streets
do: a little, and not on purpose.

## Later

- **Surveillance framing** — foreground the apparatus next to the tenderness:
  real cam id, "public feed", a running count of souls invented from public
  cameras today. Stick to genuinely public feeds (DOT, city, transit) — that
  openness *is* the commentary; no scraping unsecured private cams.
- **LLM narrator** — only if the deterministic path is truly exhausted, and
  only a local open-weight model (ollama / llama.cpp). No frontier API on the
  hot path. The dice stay as the default and the fallback.
