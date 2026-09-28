"""Build train/val/test sets for the Laya coder from authored and reviewer-corrected records.

Inputs (all in the record format of AUTHORING.md):
  synthetic/*.jsonl         silver labels written for bootstrapping
  real/*.jsonl              examiner-coded real responses: always held out as the test set
  --overrides FILE          optional: the api's /api/admin/export/training.jsonl (real, reviewer-corrected)

Outputs (in --out): train.jsonl, val.jsonl, test.jsonl. Each line:
  {"id", "group", "source", "request": <scorer CodeRequest JSON>, "labels": {...}}

The split is by record, so a typo variant never lands on the other side of its original.
Typo variants are added to the training split only, with identical labels.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from validate import check

HERE = Path(__file__).resolve().parent
REGIONS = HERE.parents[1] / "regions"

# ---------------------------------------------------------------------------------------------- noise

_KEYBOARD = {c: n for row in ("qwertyuiop", "asdfghjkl", "zxcvbnm") for i, c in enumerate(row)
             for n in [row[max(0, i - 1)] + row[min(len(row) - 1, i + 1)]]}
_SHORT = {"you": "u", "your": "ur", "are": "r", "because": "bc", "probably": "prob", "something": "smth",
          "looks like": "lks like", "people": "ppl", "and": "n", "with": "w", "though": "tho", "two": "2",
          "to": "2", "really": "rly", "maybe": "mayb", "the": "da"}


def _typo_word(w: str, rng: random.Random) -> str:
    if len(w) < 4 or not w.isalpha():
        return w
    i = rng.randrange(1, len(w) - 1)
    op = rng.random()
    if op < 0.3:
        return w[:i] + w[i + 1] + w[i] + w[i + 2:]           # swap
    if op < 0.55:
        return w[:i] + w[i + 1:]                              # drop
    if op < 0.75:
        return w[:i] + w[i] + w[i:]                           # double
    near = _KEYBOARD.get(w[i].lower())
    return w[:i] + (rng.choice(near) if near else w[i]) + w[i + 1:]  # neighbour key


def add_noise(text: str, rng: random.Random, level: float) -> str:
    if not text:
        return text
    out = text
    for long, short in _SHORT.items():
        if rng.random() < level:
            out = re.sub(rf"\b{long}\b", short, out, flags=re.I)
    words = out.split(" ")
    words = [_typo_word(w, rng) if rng.random() < level * 0.5 else w for w in words]
    out = " ".join(words)
    if rng.random() < 0.6:
        out = out.lower()
    if rng.random() < 0.5:
        out = re.sub(r"[.,;:!?']", "", out)
    return out


# ------------------------------------------------------------------------------------------- location

def _region_ids(card: int) -> dict[str, list[int]]:
    data = json.loads((REGIONS / f"card_{card}.json").read_text())
    ids: dict[str, list[int]] = defaultdict(list)
    for r in data["regions"]:
        m = re.search(r"(\d+)$", r["id"])
        if r["kind"] in ("D", "Dd", "S") and m:
            ids[r["kind"]].append(int(m.group(1)))
    return ids


def to_location(card: int, generic: str, rng: random.Random) -> dict:
    m = re.fullmatch(r"(W|Dd|D)(S?)(\d*)", generic)
    code, s, num = m.groups()
    space = bool(s)
    if code == "W":
        number = None
    elif num:
        number = int(num)
    else:
        ids = _region_ids(card)
        pool = ids.get("S" if (code == "Dd" and space) else code) or ids.get("D") or [99]
        number = rng.choice(pool + ([99] if code == "Dd" else []))
    label = f"{code}{'S' if space else ''}{number if number is not None else ''}"
    return {"code": code, "number": number, "space": space, "label": label}


def to_request(rec: dict, rng: random.Random) -> dict:
    return {"card": rec["card"], "orientation": rec["orientation"], "verbatim": rec["verbatim"],
            "inquiry": rec["inquiry"], "followups": rec.get("followups", []),
            "location": to_location(rec["card"], rec["location"], rng)}


# ------------------------------------------------------------------------------------------------ main

def load(paths: list[Path]) -> list[dict]:
    records = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                problems = check(rec)
                if problems:
                    raise SystemExit(f"{path}: {rec.get('id')}: {problems}")
                records.append(rec)
    return records


def load_overrides(path: Path) -> list[dict]:
    """The api export already carries a full request; it is real, reviewer-corrected data."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out.append({"id": f"override-{rec['response_id']}", "group": "override", "source": "override",
                        "request": rec["request"], "labels": rec["labels"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--overrides", type=Path, help="api training.jsonl export (reviewer-corrected real data)")
    ap.add_argument("--val-share", type=float, default=0.15)
    ap.add_argument("--noisy-copies", type=int, default=1, help="typo variants per training record")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    synthetic = load(sorted((HERE / "synthetic").glob("*.jsonl")))
    real = load(sorted((HERE / "real").glob("*.jsonl")))

    # Stratify the split by card and validity so every class shows up in validation.
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for rec in synthetic:
        strata[(rec["card"], rec["labels"]["validity"])].append(rec)
    train, val = [], []
    for key in sorted(strata):
        group = strata[key]
        rng.shuffle(group)
        n_val = max(1, round(len(group) * args.val_share)) if len(group) > 3 else 0
        val += group[:n_val]
        train += group[n_val:]

    def rows(records, source, noisy=0):
        out = []
        for rec in records:
            base = {"id": rec["id"], "group": rec["id"], "source": source, "labels": rec["labels"]}
            out.append(base | {"request": to_request(rec, rng)})
            if rec["labels"]["validity"] == "gibberish":
                continue
            for k in range(noisy):
                req = to_request(rec, rng)
                req["verbatim"] = add_noise(req["verbatim"], rng, 0.35)
                req["inquiry"] = add_noise(req["inquiry"], rng, 0.35)
                out.append(base | {"id": f"{rec['id']}~{k + 1}", "request": req})
        return out

    splits = {"train": rows(train, "synthetic", args.noisy_copies), "val": rows(val, "synthetic"),
              "test": rows(real, "real")}
    if args.overrides:
        # Real reviewer data goes into training, with a slice held out for validation.
        overrides = load_overrides(args.overrides)
        rng.shuffle(overrides)
        n_val = round(len(overrides) * args.val_share)
        splits["val"] += overrides[:n_val]
        splits["train"] += overrides[n_val:]

    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in splits.items():
        rng.shuffle(data)
        with open(args.out / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for row in data:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        classes = defaultdict(int)
        for row in data:
            classes[row["labels"]["validity"]] += 1
        print(f"{name}: {len(data)} rows  {dict(classes)}")


if __name__ == "__main__":
    main()
