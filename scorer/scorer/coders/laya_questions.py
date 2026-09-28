"""CS coding framed as Laya typed decisions.

Laya (https://github.com/NandhaKishorM/laya) answers typed questions about a
`state` in one forward pass: `choice` (pick one key of `criteria`), `score`
(ordinal) and `noul` (yes/no probability). Laya has no multi-label question
type, so each determinant family, content category and special score is its
own yes/no question.

This module has no dependencies so that `laya_server/convert_training.py`
can reuse it to turn reviewer overrides into fine-tuning records.
"""

from __future__ import annotations

from typing import Any

DQ_CHOICES = {
    "synthesized": ("+", "two or more objects described as related, at least one with a specific form"),
    "ordinary": ("o", "a single object with a specific form"),
    "vague_synthesized": ("v/+", "two or more related objects, none with a specific form"),
    "vague": ("v", "an object with no specific form, like a cloud, blood or a stain"),
}
FQ_CHOICES = {
    "unusual": ("u", "the object is easy to see in that area, though uncommon"),
    "minus": ("-", "the object distorts the shape of the area"),
}
MOVEMENT_AP = {
    "active": ("a", "active movement such as running, fighting, lifting, flying"),
    "passive": ("p", "passive movement such as standing, sitting, looking, floating"),
    "both": ("a-p", "both active and passive movement"),
}
# family key -> (question, {choice key: (code, description)} for form dominance)
SHADED_FAMILIES: dict[str, tuple[str, dict[str, tuple[str, str]]]] = {
    "color": ("Does the person say chromatic colour (red, blue, pink...) helped make it look like that?",
              {"form_primary": ("FC", "shape matters most, colour adds to it"),
               "color_primary": ("CF", "colour matters most, shape is secondary"),
               "pure": ("C", "colour alone, no shape"),
               "naming": ("Cn", "just names the colours")}),
    "achromatic": ("Does the person say black, white or gray colour helped make it look like that?",
                   {"form_primary": ("FC'", "shape first"), "color_primary": ("C'F", "achromatic colour first"),
                    "pure": ("C'", "achromatic colour alone")}),
    "texture": ("Does the person describe texture (furry, soft, rough) from the shading?",
                {"form_primary": ("FT", "shape first"), "texture_primary": ("TF", "texture first"),
                 "pure": ("T", "texture alone")}),
    "vista": ("Does the person use shading to describe depth or distance?",
              {"form_primary": ("FV", "shape first"), "vista_primary": ("VF", "depth first"),
               "pure": ("V", "depth alone")}),
    "diffuse": ("Does the person use light-and-dark shading in some other way (not texture or depth)?",
                {"form_primary": ("FY", "shape first"), "shading_primary": ("YF", "shading first"),
                 "pure": ("Y", "shading alone")}),
    "reflection": ("Does the person see a reflection or mirror image?",
                   {"form_primary": ("Fr", "a reflected object with specific form"),
                    "formless": ("rF", "a reflected object with no specific form")}),
}
MOVEMENT_FAMILIES = {
    "M": "Is a person (or anything) doing human activity or showing human experience or emotion?",
    "FM": "Is an animal moving or doing something animals do?",
    "m": "Is something inanimate or a natural force moving (falling, exploding, flowing, blowing)?",
}
CONTENT_QUESTIONS = {
    "H": "a whole real human", "(H)": "a whole fictional or mythological human (giant, ghost, angel)",
    "Hd": "part of a real human", "(Hd)": "part of a fictional human, or a mask",
    "Hx": "human emotion or sensory experience", "A": "a whole real animal",
    "(A)": "a whole fictional animal (dragon, unicorn, cartoon)", "Ad": "part of an animal, or an animal skin",
    "(Ad)": "part of a fictional animal", "An": "anatomy (bones, organs)", "Art": "art or decoration",
    "Ay": "anthropology or history (totem, pharaoh)", "Bl": "blood", "Bt": "plants or flowers",
    "Cg": "clothing", "Cl": "clouds", "Ex": "an explosion", "Fd": "food", "Fi": "fire or smoke",
    "Ge": "a map or geography", "Hh": "household items", "Ls": "landscape", "Na": "nature (sun, water, sky)",
    "Sc": "science or manufactured objects", "Sx": "sexual content", "Xy": "an x-ray",
    "Id": "something that fits no other category",
}
SPECIAL_QUESTIONS = {
    "DV1": "a mild odd word use or redundancy", "DV2": "a bizarre neologism or odd word use",
    "INC1": "a mildly impossible feature merged into one object (a bat with hands)",
    "INC2": "a bizarre impossible merging of features",
    "DR1": "a mildly irrelevant or rambling comment", "DR2": "a markedly irrelevant, derailed comment",
    "FAB1": "an implausible relationship between objects (two chickens playing cards)",
    "FAB2": "an impossible relationship (a person walking through a wall)",
    "ALOG": "strained, unconventional logic to justify the answer",
    "CONTAM": "two percepts fused into one impossible object",
    "AB": "abstract or symbolic meaning", "AG": "aggressive action, now happening",
    "COP": "clearly positive or cooperative interaction", "MOR": "something dead, damaged, sad or ruined",
    "PER": "personal experience used to justify the answer",
    "CP": "chromatic colour reported on an achromatic card",
}


def _choice(instructions: str, table: dict[str, tuple[str, str]]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions,
            "criteria": {k: desc for k, (_, desc) in table.items()}}


def _noul(instructions: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": instructions}


def build_questions() -> dict[str, dict[str, Any]]:
    q: dict[str, dict[str, Any]] = {
        "dq": _choice("Which Developmental Quality fits the response?", DQ_CHOICES),
        "fq_fallback": _choice("How well does the object fit the shape of the area?", FQ_CHOICES),
        "pair": _noul("Are two identical objects seen, one on each side of the card (not a reflection)?"),
        "movement_ap": _choice("Is the movement active or passive?", MOVEMENT_AP),
        "form_dimension": _noul("Is depth or distance described from size or position alone, without shading?"),
    }
    for base, text in MOVEMENT_FAMILIES.items():
        q[f"move_{base}"] = _noul(text)
    for fam, (text, table) in SHADED_FAMILIES.items():
        q[f"det_{fam}"] = _noul(text)
        q[f"det_{fam}_dominance"] = _choice("How do shape and this feature combine?", table)
    for code, text in CONTENT_QUESTIONS.items():
        q[f"content_{code}"] = _noul(f"Does the response include {text}?")
    for code, text in SPECIAL_QUESTIONS.items():
        q[f"special_{code}"] = _noul(f"Does the response show {text}?")
    return q


def labels_to_answers(labels: dict[str, Any]) -> dict[str, Any]:
    """Invert decoding: Codes-shaped labels -> Laya ground-truth answers (for fine-tuning)."""
    dets = set(labels.get("determinants", []))
    answers: dict[str, Any] = {
        "dq": next(k for k, (code, _) in DQ_CHOICES.items() if code == labels.get("dq", "o")),
        "pair": bool(labels.get("pair", False)),
        "form_dimension": "FD" in dets,
    }
    fq = labels.get("fq_fallback") or labels.get("fq")
    if fq in ("u", "-"):
        answers["fq_fallback"] = "unusual" if fq == "u" else "minus"
    sups = set()
    for base in MOVEMENT_FAMILIES:
        present = [d for d in dets if d.startswith(base) and d[len(base):] in ("a", "p", "a-p")
                   and not (base == "M" and d.startswith("FM"))]
        answers[f"move_{base}"] = bool(present)
        sups.update(d[len(base):] for d in present)
    if sups:
        answers["movement_ap"] = "both" if "a-p" in sups or sups == {"a", "p"} else (
            "active" if "a" in sups else "passive")
    for fam, (_, table) in SHADED_FAMILIES.items():
        hit = next((k for k, (code, _) in table.items() if code in dets), None)
        answers[f"det_{fam}"] = hit is not None
        if hit is not None:
            answers[f"det_{fam}_dominance"] = hit
    contents = set(labels.get("contents", []))
    for code in CONTENT_QUESTIONS:
        answers[f"content_{code}"] = code in contents
    special = set(labels.get("special_scores", []))
    for code in SPECIAL_QUESTIONS:
        answers[f"special_{code}"] = code in special
    return answers
