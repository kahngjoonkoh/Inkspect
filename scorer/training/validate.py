"""Check synthetic training records against the authoring rules (standard library only).

Usage:  python3 scorer/training/validate.py scorer/training/synthetic/*.jsonl
Exits non-zero and prints every problem if any record is invalid.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MOVEMENT = {f"{b}{s}" for b in ("M", "FM", "m") for s in ("a", "p", "a-p")}
DETERMINANTS = MOVEMENT | {"F", "FC", "CF", "C", "Cn", "FC'", "C'F", "C'", "FT", "TF", "T", "FV", "VF", "V",
                           "FY", "YF", "Y", "Fr", "rF", "FD"}
CHROMATIC = {"FC", "CF", "C", "Cn"}
FORMLESS = {"C", "Cn", "C'", "T", "V", "Y"}
CONTENTS = {"H", "(H)", "Hd", "(Hd)", "Hx", "A", "(A)", "Ad", "(Ad)", "An", "Art", "Ay", "Bl", "Bt", "Cg", "Cl",
            "Ex", "Fd", "Fi", "Ge", "Hh", "Ls", "Na", "Sc", "Sx", "Xy", "Id"}
SPECIAL = {"DV1", "DV2", "INC1", "INC2", "DR1", "DR2", "FAB1", "FAB2", "ALOG", "CONTAM", "AB", "AG", "COP", "MOR",
           "PER", "CP"}
VALIDITY = {"genuine", "unserious", "gibberish", "refusal", "off_task"}
# Generic labels (mapped to region ids when the dataset is built) or concrete ones such as "D2", "DdS99".
LOCATIONS = {"W", "WS", "D", "DS", "Dd", "DdS", "Dd99"}
PERSONAS = {"standard", "terse", "nonnative", "typo", "elaborate", "odd_genuine", "unserious", "gibberish",
            "refusal", "off_task"}
ACHROMATIC_CARDS = {1, 4, 5, 6, 7}


def check(rec: dict) -> list[str]:
    errs = []
    for key in ("id", "card", "orientation", "location", "verbatim", "inquiry", "persona", "labels"):
        if key not in rec:
            errs.append(f"missing {key}")
    if errs:
        return errs
    if rec["card"] not in range(1, 11):
        errs.append("card must be 1-10")
    if rec["orientation"] not in ("^", "v", ">", "<"):
        errs.append("bad orientation")
    if rec["location"] not in LOCATIONS and not re.fullmatch(r"(W|D|Dd)S?\d*", str(rec["location"])):
        errs.append(f"bad location {rec['location']!r}")
    if rec["persona"] not in PERSONAS:
        errs.append(f"bad persona {rec['persona']!r}")
    if not isinstance(rec["verbatim"], str) or not isinstance(rec["inquiry"], str):
        errs.append("verbatim and inquiry must be strings")
    for f in rec.get("followups", []):
        if set(f) != {"prompt", "answer"}:
            errs.append("followups need prompt and answer")
    lab = rec["labels"]
    validity = lab.get("validity")
    if validity not in VALIDITY:
        return errs + [f"bad validity {validity!r}"]
    if validity != "genuine":
        return errs
    dets = lab.get("determinants", [])
    if not dets or any(d not in DETERMINANTS for d in dets):
        errs.append(f"bad determinants {dets}")
    if lab.get("dq") not in ("+", "o", "v/+", "v"):
        errs.append(f"bad dq {lab.get('dq')!r}")
    contents = lab.get("contents", [])
    if not contents or any(c not in CONTENTS for c in contents):
        errs.append(f"bad contents {contents}")
    specials = lab.get("special_scores", [])
    if any(s not in SPECIAL for s in specials):
        errs.append(f"bad special scores {specials}")
    if not isinstance(lab.get("pair"), bool):
        errs.append("pair must be true/false")
    if lab.get("fq_fallback") not in ("u", "-", "none"):
        errs.append(f"bad fq_fallback {lab.get('fq_fallback')!r}")
    if rec["card"] in ACHROMATIC_CARDS and set(dets) & CHROMATIC:
        errs.append("chromatic colour determinant on an achromatic card (use CP)")
    if rec["card"] not in ACHROMATIC_CARDS and "CP" in specials:
        errs.append("CP on a chromatic card")
    if lab.get("pair") and set(dets) & {"Fr", "rF"}:
        errs.append("reflection and pair together")
    formless = all(d in FORMLESS for d in dets)
    if formless and lab.get("fq_fallback") != "none":
        errs.append("formless determinants need fq_fallback none")
    # Inanimate movement can be formless too ("smoke drifting", mp.Y) when the DQ is vague.
    formless_movement = all(d in FORMLESS or d.startswith("m") for d in dets) and lab.get("dq") in ("v", "v/+")
    if not formless and lab.get("fq_fallback") == "none" and not formless_movement:
        errs.append("fq_fallback none needs formless determinants")
    if "F" in dets and len(dets) > 1:
        errs.append("F cannot be part of a blend")
    if len(set(specials) & {"DV1", "DV2"}) > 1 or len(set(specials) & {"INC1", "INC2"}) > 1:
        errs.append("level 1 and level 2 of the same score together")
    return errs


def main(paths: list[str]) -> int:
    seen, bad, total = set(), 0, 0
    for path in paths:
        for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"{path}:{n}: invalid JSON: {e}")
                bad += 1
                continue
            errs = check(rec)
            if rec.get("id") in seen:
                errs.append(f"duplicate id {rec.get('id')}")
            seen.add(rec.get("id"))
            for e in errs:
                print(f"{path}:{n} ({rec.get('id')}): {e}")
            bad += bool(errs)
    print(f"{total} records, {bad} with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
