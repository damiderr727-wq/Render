"""
Erzeugt die Partituren nach Sources/ResonanzCore/Resources/Scores.

Das Material stammt aus gemeinfreien Werken von J. S. Bach und ist fuer die
Welt umgeschrieben: durchsichtig und langsam beim Erkunden, dicht und
treibend im Bosskampf.

    BWV 846  Praeludium C-Dur      -> Der schlafende Hain / Aufloesung
    BWV 578  Fuge g-Moll           -> Kathedrale der Fugen
    BWV 1068 Air                   -> Kristallgrotten
    BWV 565  Toccata und Fuge      -> Der Verstimmte Kantor

Jede Spur traegt eine `layer`-Schwelle. Sie erklingt erst, wenn die
Intensitaet des Spiels sie erreicht - die Musik verdichtet sich also mit
der Gefahr, statt einfach lauter zu werden.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Scores"


# ------------------------------------------------------------ BWV 846

# Pro Takt fuenf Toene; die Figur laeuft 1 2 3 4 5 3 4 5 und wiederholt
# sich in der zweiten Takthaelfte. 16 Takte.
PRELUDE_BARS = [
    [48, 52, 55, 60, 64], [48, 50, 57, 62, 65], [47, 50, 55, 62, 65], [48, 52, 55, 60, 64],
    [48, 52, 57, 64, 69], [48, 50, 54, 57, 62], [47, 50, 55, 62, 67], [47, 48, 52, 55, 60],
    [45, 48, 52, 55, 60], [38, 45, 50, 54, 60], [43, 47, 50, 55, 59], [43, 46, 52, 55, 61],
    [41, 45, 50, 57, 62], [41, 44, 50, 53, 59], [40, 43, 48, 55, 60], [40, 41, 45, 48, 53],
]

FIGURE_ORDER = [0, 1, 2, 3, 4, 2, 3, 4]


def prelude_figure(count=8, transpose=12, vel=0.85, detune_every=0):
    notes = []
    for b in range(count):
        bar = PRELUDE_BARS[b % len(PRELUDE_BARS)]
        for half in range(2):
            for i, idx in enumerate(FIGURE_ORDER):
                pitch = bar[idx] + transpose
                if detune_every and (b * 16 + half * 8 + i) % detune_every == detune_every - 1:
                    pitch += 1  # die Welt ist verstimmt
                notes.append({
                    "t": round(b * 4 + half * 2 + i * 0.25, 4),
                    "n": pitch,
                    "d": 0.5,
                    "v": round(vel * (1.0 if i == 0 else 0.8 if i < 2 else 0.62)
                               * (1.0 if half == 0 else 0.92), 3),
                })
    return notes


def prelude_bass(count=8, transpose=-12, vel=0.8):
    return [{"t": b * 4, "n": PRELUDE_BARS[b % 16][0] + transpose, "d": 3.8, "v": vel}
            for b in range(count)]


def prelude_pad(count=8, transpose=0, vel=0.55):
    notes = []
    for b in range(0, count, 2):
        bar = PRELUDE_BARS[b % 16]
        notes.append({"t": b * 4, "n": bar[2] + transpose, "d": 7.6, "v": vel})
        notes.append({"t": b * 4, "n": bar[4] + transpose, "d": 7.6, "v": round(vel * 0.7, 3)})
    return notes


def every(notes, n):
    return [x for i, x in enumerate(notes) if i % n == 0]


# ------------------------------------------------------------ BWV 578

FUGUE_SUBJECT = [
    (0.0, 67, 1.0), (1.0, 74, 1.0), (2.0, 70, 0.5), (2.5, 69, 0.25), (2.75, 67, 0.25),
    (3.0, 66, 0.5), (3.5, 67, 0.5), (4.0, 69, 1.0), (5.0, 70, 0.5), (5.5, 72, 0.5),
    (6.0, 74, 0.5), (6.5, 75, 0.5), (7.0, 74, 1.0), (8.0, 72, 0.5), (8.5, 70, 0.5),
    (9.0, 69, 0.5), (9.5, 67, 0.5), (10.0, 66, 1.0), (11.0, 67, 1.0), (12.0, 62, 0.5),
    (12.5, 67, 0.5), (13.0, 70, 0.5), (13.5, 69, 0.5), (14.0, 67, 1.0), (15.0, 66, 1.0),
]

# ------------------------------------------------------------ BWV 1068

AIR_MELODY = [
    (0, 78, 4), (4, 79, 2), (6, 78, 1), (7, 76, 1), (8, 74, 2), (10, 76, 1), (11, 78, 1),
    (12, 81, 3), (15, 79, 1), (16, 78, 3), (19, 76, 1), (20, 74, 2), (22, 73, 2),
    (24, 71, 2), (26, 73, 1), (27, 74, 1), (28, 76, 3), (31, 74, 1),
]

AIR_BASS = [(0, 38, 4), (4, 45, 4), (8, 43, 4), (12, 42, 4),
            (16, 40, 4), (20, 38, 4), (24, 45, 4), (28, 38, 4)]

# ------------------------------------------------------------ BWV 565

TOCCATA_OPENING = [
    (0.0, 81, 0.25), (0.25, 79, 0.25), (0.5, 81, 1.25),
    (2.0, 79, 0.125), (2.125, 77, 0.125), (2.25, 76, 0.125), (2.375, 74, 0.125),
    (2.5, 73, 0.125), (2.625, 74, 0.125), (2.75, 73, 0.25), (3.0, 74, 1.0),
    (4.0, 69, 0.25), (4.25, 67, 0.25), (4.5, 69, 1.25),
    (6.0, 67, 0.125), (6.125, 65, 0.125), (6.25, 64, 0.125), (6.375, 62, 0.125),
    (6.5, 61, 0.125), (6.625, 62, 0.125), (6.75, 61, 0.25), (7.0, 62, 1.0),
]

TOCCATA_FUGUE = [
    (0.0, 69, 0.25), (0.25, 67, 0.25), (0.5, 69, 0.25), (0.75, 67, 0.25),
    (1.0, 65, 0.25), (1.25, 64, 0.25), (1.5, 62, 0.25), (1.75, 61, 0.25),
    (2.0, 62, 0.5), (2.5, 64, 0.5), (3.0, 65, 0.5), (3.5, 62, 0.5),
    (4.0, 69, 0.25), (4.25, 67, 0.25), (4.5, 69, 0.25), (4.75, 70, 0.25),
    (5.0, 72, 0.5), (5.5, 70, 0.5), (6.0, 69, 1.0), (7.0, 67, 1.0),
]


def seq(triples, offset=0.0, transpose=0, vel=0.9, scale=1.0):
    return [{"t": round(t * scale + offset, 4), "n": n + transpose,
             "d": round(d * scale, 4), "v": vel} for t, n, d in triples]


# ------------------------------------------------------------ Stuecke

def scores() -> dict[str, dict]:
    return {
        "titel": {
            "source": "BWV 846 - Praeludium C-Dur",
            "bpm": 50, "loop": 32,
            "tracks": [
                {"voice": "pluck", "gain": 0.20, "layer": 0.0, "notes": prelude_figure(8, 12, 0.70)},
                {"voice": "pad", "gain": 0.10, "layer": 0.0, "notes": prelude_pad(8, -12)},
                {"voice": "bass", "gain": 0.16, "layer": 0.4, "notes": prelude_bass(8)},
            ],
        },
        "hain": {
            "source": "BWV 846 - Praeludium C-Dur, ausgedehnt",
            "bpm": 58, "loop": 64,
            "tracks": [
                {"voice": "pluck", "gain": 0.24, "layer": 0.0, "notes": prelude_figure(16, 12, 0.80)},
                {"voice": "pad", "gain": 0.13, "layer": 0.0, "notes": prelude_pad(16, -12)},
                {"voice": "bass", "gain": 0.20, "layer": 0.15, "notes": prelude_bass(16, -12)},
                {"voice": "bell", "gain": 0.11, "layer": 0.55,
                 "notes": every(prelude_figure(16, 24, 0.50), 8)},
            ],
        },
        "bruecke": {
            # Die Bruecke ist das einzige Gebiet im Freien, und sie klingt
            # danach: weit auseinanderliegende Toene, viel Luft dazwischen,
            # kein Muster, das sich schnell schliesst. Dieselbe Air wie in
            # den Kavernen, aber langsamer und nur mit zwei Stimmen - der
            # Rest ist Wind.
            "source": "BWV 1068 - Air, ins Freie gestellt",
            "bpm": 40, "loop": 32,
            "tracks": [
                {"voice": "pad", "gain": 0.15, "layer": 0.0,
                 "notes": seq(AIR_BASS, 0, 0, 0.45)},
                {"voice": "bell", "gain": 0.13, "layer": 0.35,
                 "notes": every(seq(AIR_MELODY, 0, 12, 0.55), 2)},
                {"voice": "bass", "gain": 0.16, "layer": 0.55,
                 "notes": seq(AIR_BASS, 0, -24, 0.75)},
            ],
        },
        "kathedrale": {
            "source": "BWV 578 - Fuge g-Moll",
            # Vier Stimmeneinsaetze im Abstand von acht Schlaegen - deshalb
            # laeuft die Schleife hier ueber 48 statt 32 Schlaege.
            "bpm": 74, "loop": 48,
            "tracks": [
                {"voice": "organ", "gain": 0.20, "layer": 0.0,
                 "notes": seq(FUGUE_SUBJECT, 0, 0, 0.85) + seq(FUGUE_SUBJECT, 16, 0, 0.80)},
                {"voice": "organ", "gain": 0.13, "layer": 0.30,
                 "notes": seq(FUGUE_SUBJECT, 8, -12, 0.60) + seq(FUGUE_SUBJECT, 24, -19, 0.60)},
                {"voice": "bass", "gain": 0.22, "layer": 0.15, "notes": [
                    {"t": t, "n": n, "d": 3.6, "v": v} for t, n, v in
                    [(0, 43, .9), (4, 46, .8), (8, 50, .85), (12, 43, .8),
                     (16, 48, .85), (20, 46, .8), (24, 45, .85), (28, 43, .9),
                     (32, 41, .85), (36, 43, .8), (40, 46, .85), (44, 43, .9)]
                ]},
                {"voice": "pad", "gain": 0.09, "layer": 0.60, "notes": [
                    {"t": 0, "n": 55, "d": 46, "v": 0.5}, {"t": 0, "n": 58, "d": 46, "v": 0.35}]},
            ],
        },
        "grotten": {
            "source": "BWV 1068 - Air, gedehnt",
            "bpm": 46, "loop": 32,
            "tracks": [
                {"voice": "bell", "gain": 0.17, "layer": 0.0, "notes": seq(AIR_MELODY, 0, 0, 0.80)},
                {"voice": "pad", "gain": 0.14, "layer": 0.0, "notes": seq(AIR_BASS, 0, 12, 0.50)},
                {"voice": "bass", "gain": 0.20, "layer": 0.20, "notes": seq(AIR_BASS, 0, -12, 0.85)},
                {"voice": "pluck", "gain": 0.12, "layer": 0.50,
                 "notes": every(seq(AIR_MELODY, 0.5, -12, 0.45), 2)},
            ],
        },
        "dissonanz": {
            "source": "BWV 846 - verstimmt",
            "bpm": 52, "loop": 32,
            "tracks": [
                {"voice": "pluck", "gain": 0.20, "layer": 0.0, "detune": -22,
                 "notes": prelude_figure(8, 12, 0.70, detune_every=4)},
                {"voice": "pad", "gain": 0.16, "layer": 0.0, "notes": [
                    {"t": 0, "n": 38, "d": 30, "v": 0.7}, {"t": 0, "n": 44, "d": 30, "v": 0.5}]},
                {"voice": "bass", "gain": 0.24, "layer": 0.20, "notes": [
                    {"t": 0, "n": 26, "d": 15, "v": 0.9}, {"t": 16, "n": 25, "d": 15, "v": 0.9}]},
            ],
        },
        "boss": {
            "source": "BWV 565 - Toccata und Fuge d-Moll",
            "bpm": 132, "loop": 32,
            "tracks": [
                {"voice": "organ", "gain": 0.20, "layer": 0.0, "notes": seq(TOCCATA_OPENING, 0, 0, 0.95)},
                {"voice": "organ", "gain": 0.18, "layer": 0.0, "notes": seq(TOCCATA_FUGUE, 8, 0, 0.85)},
                {"voice": "organ", "gain": 0.15, "layer": 0.45, "notes": seq(TOCCATA_FUGUE, 16, -12, 0.75)},
                {"voice": "organ", "gain": 0.14, "layer": 0.75, "notes": seq(TOCCATA_OPENING, 24, -12, 0.80)},
                {"voice": "bass", "gain": 0.28, "layer": 0.0, "notes": [
                    {"t": i, "n": 38 if i % 8 == 0 else (45 if i % 4 == 2 else 38),
                     "d": 0.9, "v": 1.0 if i % 4 == 0 else 0.7} for i in range(32)]},
                {"voice": "perc", "gain": 0.30, "layer": 0.30, "notes": [
                    {"t": i * 0.5, "n": 0 if i % 4 == 0 else (1 if i % 2 == 0 else 2),
                     "d": 0.2, "v": 1.0} for i in range(64)]},
                {"voice": "pad", "gain": 0.12, "layer": 0.60, "notes": [
                    {"t": 0, "n": 50, "d": 8, "v": .6}, {"t": 0, "n": 53, "d": 8, "v": .5},
                    {"t": 0, "n": 56, "d": 8, "v": .4}, {"t": 16, "n": 49, "d": 8, "v": .6},
                    {"t": 16, "n": 52, "d": 8, "v": .5}, {"t": 16, "n": 55, "d": 8, "v": .4}]},
            ],
        },
        "aufloesung": {
            "source": "BWV 846 - endlich rein",
            "bpm": 62, "loop": 32,
            "tracks": [
                {"voice": "pluck", "gain": 0.26, "layer": 0.0, "notes": prelude_figure(8, 12, 0.90)},
                {"voice": "bell", "gain": 0.14, "layer": 0.0, "notes": every(prelude_figure(8, 24, 0.50), 8)},
                {"voice": "pad", "gain": 0.14, "layer": 0.0, "notes": prelude_pad(8, -12)},
                {"voice": "bass", "gain": 0.22, "layer": 0.0, "notes": prelude_bass(8, -12)},
            ],
        },
    }


def validate(all_scores: dict[str, dict]) -> list[str]:
    problems = []
    for name, s in all_scores.items():
        if not s["tracks"]:
            problems.append(f"{name}: keine Spuren")
        if not any(t.get("layer", 0) == 0 for t in s["tracks"]):
            problems.append(f"{name}: keine Spur bei Intensitaet 0 - Stille beim Erkunden")
        for t in s["tracks"]:
            for n in t["notes"]:
                if not (0 <= n["t"] < s["loop"]):
                    problems.append(f"{name}/{t['voice']}: Note bei {n['t']} liegt ausserhalb der Schleife")
                    break
                if t["voice"] != "perc" and not (12 <= n["n"] <= 108):
                    problems.append(f"{name}/{t['voice']}: Tonhoehe {n['n']} unbrauchbar")
                    break
    return problems


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_scores = scores()
    for p in validate(all_scores):
        print(f"  ! {p}")

    for name, s in all_scores.items():
        (OUT / f"{name}.json").write_text(
            json.dumps({"id": name, **s}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    index = {"scores": [{"id": k, "source": v["source"], "bpm": v["bpm"], "loop": v["loop"],
                         "tracks": len(v["tracks"]),
                         "notes": sum(len(t["notes"]) for t in v["tracks"])}
                        for k, v in all_scores.items()]}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n",
                                    encoding="utf-8")
    total = sum(e["notes"] for e in index["scores"])
    print(f"scores     -> {len(all_scores)} Stuecke, {total} Noten")


if __name__ == "__main__":
    build()
