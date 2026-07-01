# car-stories

Invented lives for strangers in traffic.

<!-- demo gif / screenshot here -->

A camera watches a street. For each car it sees, it makes up a driver — where
they're coming from, where they're going, what they're carrying. None of it is
real. The machine just over-reads: red car, eastbound, late afternoon → a whole
person, late for something.

Each guess is grounded in what the camera can actually see, so it feels less like
a dice roll and more like being read. Same car, same soul.

> every life invented · none of it is real

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m car_stories.server      # → http://127.0.0.1:8000
```

Point it somewhere in `cams.yaml`. It opens on the mechanism, already running.

## How

YOLO finds the cars and follows them. It watches a few at a time — the one it's
been staring at longest gets a story. The storyteller (`narrator.py`) is just
word-lists and dice, seeded by the car so its soul never changes. No model, no key.
