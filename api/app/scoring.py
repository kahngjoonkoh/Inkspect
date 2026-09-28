"""Turn coded responses into the CS sequence of scores.

The scorer service supplies DQ, determinants, pair, contents and special scores.
This module adds everything that is table-driven or depends on the whole
record: Form Quality, Popular, Z, PSV and GHR/PHR.
"""

from typing import Any

from .fq import articulation
from .tables import ROMAN, is_popular, z_value

FORMLESS = {"C", "Cn", "C'", "T", "V", "Y"}
COGNITIVE = {"DV1", "DV2", "INC1", "INC2", "DR1", "DR2", "FAB1", "FAB2", "ALOG", "CONTAM"}
HUMAN_CONTENT = {"H", "(H)", "Hd", "(Hd)", "Hx"}
CODE_FIELDS = ("dq", "determinants", "pair", "contents", "special_scores", "validity")


def inquiry_text(explanation: str, followups: list[dict]) -> str:
    parts = [explanation or ""] + [f.get("answer", "") for f in followups or []]
    return " ".join(p for p in parts if p).strip()


def effective_codes(codes: dict | None, override: dict | None) -> dict:
    merged = dict(codes or {})
    for key, value in (override or {}).items():
        if key in CODE_FIELDS and value is not None:
            merged[key] = value
    merged.setdefault("dq", "o")
    merged.setdefault("determinants", ["F"])
    merged.setdefault("pair", False)
    merged.setdefault("contents", [])
    merged.setdefault("special_scores", [])
    merged.setdefault("validity", "genuine")
    return merged


def has_form(determinants: list[str], dq: str) -> bool:
    if all(d in FORMLESS for d in determinants):
        return False
    if all(d.startswith("m") for d in determinants) and dq == "v":
        return False
    return True


def form_quality(det: list[str], dq: str, fq_match: dict | None, fallback: str | None, text: str) -> str:
    if not has_form(det, dq):
        return "none"
    if fq_match and fq_match.get("location_match"):
        fq = fq_match["fq"]
        if fq == "o" and articulation(text) >= 4:
            return "+"
        return fq
    return fallback if fallback in ("u", "-") else "u"


def score_line(row: dict) -> str:
    loc = row["location"]
    parts = [
        f"{loc['code']}{'S' if loc['space'] else ''}{row['dq']}",
        str(loc["number"]) if loc["number"] is not None else "",
        ".".join(row["determinants"]),
        "" if row["fq"] == "none" else row["fq"],
        "(2)" if row["pair"] else "",
        ",".join(row["contents"]),
        "P" if row["popular"] else "",
        f"{row['z']:.1f}" if row["z"] is not None else "",
        ",".join(row["special_scores"]),
    ]
    return " ".join(p for p in parts if p)


def _ghr_phr(row: dict) -> str | None:
    """The CS algorithm for Good/Poor Human Representation."""
    contents, dets, specials = set(row["contents"]), row["determinants"], set(row["special_scores"])
    has_m = any(d.startswith("M") for d in dets)
    has_fm = any(d.startswith("FM") for d in dets)
    if not (contents & HUMAN_CONTENT or has_m or (has_fm and specials & {"COP", "AG"})):
        return None
    fq = row["fq"]
    good_fq = fq in ("+", "o", "u")
    if "H" in contents and good_fq and not (specials & (COGNITIVE - {"DV1", "DV2"})) and not specials & {"AG", "MOR"}:
        return "GHR"
    if not good_fq or specials & {"AB", "FAB2", "CONTAM"}:
        return "PHR"
    if "COP" in specials and "AG" not in specials:
        return "GHR"
    if specials & {"FAB1", "INC2", "MOR", "AG"}:
        return "PHR"
    if row["card"] in (3, 4, 7, 9) and row["popular"]:
        return "GHR"
    if specials & {"AG", "INC1", "DR1", "DR2"} or "Hd" in contents:
        return "PHR"
    return "GHR"


def build_protocol(responses: list[Any], include_raw: bool = False) -> list[dict]:
    """`responses` are ORM rows (or anything with the same attributes), already scored."""
    rows: list[dict] = []
    ordered = sorted(responses, key=lambda r: (r.card, r.id))
    for number, r in enumerate(ordered, start=1):
        override = r.override or {}
        codes = effective_codes(r.codes, override)
        location = dict(r.location or {"code": "Dd", "number": 99, "space": False, "label": "Dd99",
                                       "placeholder": True, "match": 0.0})
        if override.get("location"):
            location = override["location"]
        text = inquiry_text(r.explanation, r.followups)
        both = f"{r.verbatim} {text}"
        dq, det = codes["dq"], list(codes["determinants"])
        fq = override.get("fq") or form_quality(det, dq, r.fq_match, codes.get("fq_fallback"), both)
        row = {
            "response_id": r.id,
            "card": r.card,
            "card_roman": ROMAN[r.card],
            "number": number,
            "verbatim": r.verbatim,
            "inquiry": text,
            "orientation": r.orientation,
            "location": location,
            "dq": dq,
            "determinants": det,
            "fq": fq,
            "pair": bool(codes["pair"]),
            "contents": list(codes["contents"]),
            "popular": is_popular(r.card, location["label"], both),
            "z": z_value(r.card, location["code"], dq, location["space"], max(1, len(r.regions or [])),
                         fq != "none", space_only=location.get("space_only", False)),
            "special_scores": [s for s in codes["special_scores"] if s not in ("PSV", "GHR", "PHR")],
            "validity": codes["validity"],
            "coder": codes.get("coder", "rule"),
            "overridden": bool(override),
        }
        if include_raw:
            row["raw_codes"] = r.codes
            row["override"] = r.override
            row["fq_match"] = r.fq_match
        rows.append(row)

    signature_keys = ("dq", "determinants", "fq", "pair", "contents", "z")
    for prev, row in zip(rows, rows[1:]):
        if prev["card"] == row["card"] and prev["location"]["label"] == row["location"]["label"] and all(
            prev[k] == row[k] for k in signature_keys
        ):
            row["special_scores"].append("PSV")
    for row in rows:
        hr = _ghr_phr(row)
        if hr:
            row["special_scores"].append(hr)
        row["score_line"] = score_line(row)
    return rows
