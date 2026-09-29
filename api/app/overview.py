"""Plain-language result bands for test takers (the "Overview" results tab).

Each band places one group of CS variables as lower / typical / higher than most adults and
explains it in everyday words. The typical ranges approximate the CS adult non-patient
reference data; they are constants here so they can be tuned. The professional tab keeps the
full structural summary. Clinical screening flags (S-CON, DEPI...) are deliberately not
turned into bands.
"""

from dataclasses import dataclass

LEVELS = ("lower", "typical", "higher")


@dataclass(frozen=True)
class Band:
    key: str
    title: str
    low: float   # below this is "lower"
    high: float  # above this is "higher"
    unit: str
    text: dict[str, str]


BANDS = [
    Band("responses", "How much you saw", 17, 27, "answers", {
        "lower": "You gave fewer answers than most people. That can mean you were careful and selective, "
                 "or that you took the task briefly.",
        "typical": "You gave about as many answers as most people do.",
        "higher": "You gave more answers than most people, which suggests you engaged with the cards "
                  "energetically and saw many possibilities.",
    }),
    Band("big_picture", "Big picture or details", 0.25, 0.55, "of answers used the whole blot", {
        "lower": "You tended to focus on parts and details rather than the whole blot: you notice specifics "
                 "and may prefer to work piece by piece.",
        "typical": "You balanced seeing the whole blot with picking out its parts, as most people do.",
        "higher": "You often used the whole blot for one idea: you tend to look for the overall picture and "
                  "tie things together.",
    }),
    Band("imagination", "Imagination and inner life", 2, 6, "answers with people in action or feeling", {
        "lower": "You rarely saw people moving, doing or feeling things. You may rely more on what's in front "
                 "of you than on imagination when you take things in.",
        "typical": "You saw people moving or feeling things about as often as most people, a sign of an "
                   "ordinary, healthy use of imagination.",
        "higher": "You often saw people in action or with feelings: you likely have an active inner life and "
                  "like to think things through.",
    }),
    Band("emotion", "Responding to colour and feeling", 2, 6, "weighted colour answers", {
        "lower": "Colour rarely shaped what you saw. You may keep your feelings in check, or take a while to "
                 "warm up in emotional situations.",
        "typical": "Colour played a part in what you saw about as much as for most people.",
        "higher": "Colour strongly shaped what you saw: you may respond quickly and openly to emotional "
                  "situations.",
    }),
    Band("conventional", "Common or original seeing", 4, 7, "of the commonly seen answers", {
        "lower": "You gave few of the answers most people give. You see things your own way, which can be "
                 "original, and sometimes less expected by others.",
        "typical": "You saw the commonly seen things about as often as most people.",
        "higher": "You gave many of the answers most people give: you tend to see things the way others do "
                  "and may value fitting in.",
    }),
    Band("people", "Interest in people", 3, 7, "answers involving people", {
        "lower": "People appeared less often in your answers than usual, which can reflect less interest in, "
                 "or more distance from, others right now.",
        "typical": "People appeared in your answers about as often as for most people.",
        "higher": "People appeared often in your answers, which suggests a strong interest in others and "
                  "relationships.",
    }),
]


def _value(key: str, v: dict) -> float:
    if key == "responses":
        return v["R"]
    if key == "big_picture":
        return v["W"] / v["R"] if v["R"] else 0.0
    if key == "imagination":
        return v["M"]
    if key == "emotion":
        return v["WSumC"]
    if key == "conventional":
        return v["P"]
    if key == "people":
        return v["HumanCont"]
    raise KeyError(key)


def _shown(key: str, value: float) -> str:
    if key == "big_picture":
        return f"{round(value * 100)}%"
    return f"{value:g}"


def overview(v: dict) -> dict:
    """The Overview tab: plain-language bands, or an explanation when the record is too short."""
    if not v["valid"]:
        return {"available": False, "message": (
            f"You gave {v['R']} sincere answers. At least 14 are needed for the results to mean anything, "
            "so there is no overview for this test."), "bands": []}
    bands = []
    for b in BANDS:
        value = _value(b.key, v)
        level = "lower" if value < b.low else "higher" if value > b.high else "typical"
        typical = (f"{round(b.low * 100)}–{round(b.high * 100)}%" if b.key == "big_picture"
                   else f"{b.low:g}–{b.high:g}")
        bands.append({"key": b.key, "title": b.title, "level": level, "value": _shown(b.key, value),
                      "unit": b.unit, "typical": typical, "text": b.text[level]})
    return {"available": True, "message": None, "bands": bands}
