"""Compare coders on labelled records, through the same decode path the scorer uses.

    python evaluate.py --data /data/val.jsonl /data/test.jsonl --checkpoint /models/inkspect-laya-v1 \
        [--checkpoint-label fine-tuned] [--base <base checkpoint dir>] --out report.json

Prints a markdown table per data file: the rule coder, and each Laya checkpoint given.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the scorer package
from scorer.coders.laya import decode  # noqa: E402
from scorer.coders.laya_questions import build_questions  # noqa: E402
from scorer.coders.rule import RuleCoder  # noqa: E402
from scorer.schema import CodeRequest, state_text  # noqa: E402

FAMILIES = ("F", "M", "FM", "m", "colour", "achromatic", "texture", "vista", "diffuse", "reflection", "FD")
_FAMILY = {"FC": "colour", "CF": "colour", "C": "colour", "Cn": "colour", "FC'": "achromatic", "C'F": "achromatic",
           "C'": "achromatic", "FT": "texture", "TF": "texture", "T": "texture", "FV": "vista", "VF": "vista",
           "V": "vista", "FY": "diffuse", "YF": "diffuse", "Y": "diffuse", "Fr": "reflection", "rF": "reflection",
           "FD": "FD", "F": "F"}


def family(det: str) -> str:
    if det.startswith("FM"):
        return "FM"
    if det[0] in "Mm" and det not in _FAMILY:
        return det[0]
    return _FAMILY[det]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def f1(tp: int, fp: int, fn: int) -> float | None:
    if tp + fp + fn == 0:
        return None
    return 2 * tp / (2 * tp + fp + fn)


class Scores:
    def __init__(self) -> None:
        self.n = defaultdict(int)
        self.hit = defaultdict(int)
        self.prf = defaultdict(lambda: [0, 0, 0])  # tp, fp, fn

    def acc(self, key: str, ok: bool) -> None:
        self.n[key] += 1
        self.hit[key] += int(ok)

    def sets(self, key: str, pred: set, gold: set) -> None:
        c = self.prf[key]
        c[0] += len(pred & gold)
        c[1] += len(pred - gold)
        c[2] += len(gold - pred)

    def add(self, pred, labels: dict) -> None:
        gold_validity = labels.get("validity", "genuine")
        self.acc("validity", pred.validity == gold_validity)
        self.sets("flag invalid", {"x"} if pred.validity != "genuine" else set(),
                  {"x"} if gold_validity != "genuine" else set())
        if gold_validity != "genuine":
            return
        self.acc("DQ", pred.dq == labels["dq"])
        self.acc("determinants exact", set(pred.determinants) == set(labels["determinants"]))
        gold_fam = {family(d) for d in labels["determinants"]}
        pred_fam = {family(d) for d in pred.determinants}
        self.sets("determinant families", pred_fam, gold_fam)
        for fam in FAMILIES:
            self.sets(f"  {fam}", pred_fam & {fam}, gold_fam & {fam})
        self.acc("pair (2)", pred.pair == labels["pair"])
        self.sets("contents", set(pred.contents), set(labels["contents"]))
        self.acc("primary content", bool(pred.contents) and pred.contents[0] == labels["contents"][0])
        self.sets("special scores", set(pred.special_scores), set(labels["special_scores"]))
        if labels.get("fq_fallback") in ("u", "-") and pred.fq_fallback is not None:
            self.acc("fq_fallback", pred.fq_fallback == labels["fq_fallback"])

    def table(self) -> dict[str, float | None]:
        out = {}
        for key in self.n:
            out[f"{key} (acc)"] = self.hit[key] / self.n[key]
        for key, (tp, fp, fn) in self.prf.items():
            out[f"{key} (F1)"] = f1(tp, fp, fn)
        return out


def run_laya(checkpoint: str, rows: list[dict]) -> list:
    import laya

    agent = laya.load(checkpoint, device="cuda")
    questions = build_questions()
    reqs = [CodeRequest(**r["request"]) for r in rows]
    states = [state_text(q) for q in reqs]
    preds = []
    for i in range(0, len(states), 16):
        answers = agent.predict_batch(states[i:i + 16], questions)
        preds += [decode(a["answers"], q) for a, q in zip(answers, reqs[i:i + 16])]
    return preds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, nargs="+", required=True)
    ap.add_argument("--checkpoint", action="append", default=[], help="label=path; repeatable")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    report = {}
    for path in args.data:
        rows = read_jsonl(path)
        coders = {"rule": [RuleCoder().code(CodeRequest(**r["request"])) for r in rows]}
        for spec in args.checkpoint:
            label, _, ckpt = spec.partition("=")
            coders[label] = run_laya(ckpt, rows)
        tables = {}
        for name, preds in coders.items():
            s = Scores()
            for p, r in zip(preds, rows):
                s.add(p, r["labels"])
            tables[name] = s.table()
        report[path.name] = {"rows": len(rows), "coders": tables}
        keys = list(dict.fromkeys(k for t in tables.values() for k in t))
        print(f"\n### {path.name} ({len(rows)} rows)\n")
        print("| metric | " + " | ".join(tables) + " |")
        print("|---|" + "---|" * len(tables))
        for k in keys:
            cells = ["—" if tables[c].get(k) is None else f"{tables[c][k]:.2f}" for c in tables]
            print(f"| {k} | " + " | ".join(cells) + " |")
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
