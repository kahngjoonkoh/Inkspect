"""Convert Inkspect reviewer overrides into Laya fine-tuning records.

Input:  the api's `GET /api/admin/export/training.jsonl`, one line per reviewed response:
        {"state": "<card, orientation, location, response, inquiry>", "labels": Codes, "source": "override"}
Output: Laya's fine-tuning JSONL (as used by notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb):
        {"state": str, "questions": {...}, "answers": {name: choice-key | bool}}

The questions are exactly the ones LayaCoder asks at inference time
(scorer/coders/laya_questions.py), so a checkpoint fine-tuned on this file
answers them in the same vocabulary.

Usage:  python laya_server/convert_training.py training.jsonl > laya_train.jsonl
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Load the question definitions by path so this script needs nothing beyond the standard library.
_spec = importlib.util.spec_from_file_location(
    "laya_questions", Path(__file__).resolve().parents[1] / "scorer" / "coders" / "laya_questions.py")
_questions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_questions)
build_questions = _questions.build_questions
labels_to_answers = _questions.labels_to_answers


def convert(lines):
    questions = build_questions()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        yield {"state": record["state"], "questions": questions, "answers": labels_to_answers(record["labels"])}


def main(argv: list[str]) -> int:
    src = open(argv[1], encoding="utf-8") if len(argv) > 1 else sys.stdin
    with src:
        for out in convert(src):
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
