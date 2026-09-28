"""Fine-tune a Laya typed-decision checkpoint on Inkspect coding data.

Every (response, question) pair becomes one training row, built with Laya's own
`build_sequence`, so training sees exactly the input layout inference will use. The loss
is cross-entropy over the option markers. Rare yes answers (most content and special-score
questions are "no" almost every time) are up-weighted so the model does not learn to always
say no.

    python finetune.py --data /data --base <checkpoint dir> --out /models/inkspect-laya-v1
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F
from laya import load as laya_load
from laya.agent import Agent
from laya.common import QTYPES, build_sequence, collate_items
from safetensors.torch import save_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the scorer package
from scorer.coders.laya_questions import build_questions, labels_to_answers  # noqa: E402
from scorer.schema import CodeRequest, state_text  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def make_items(rows: list[dict], agent: Agent, questions: dict) -> list[dict]:
    internal = {qid: Agent._to_internal(q) for qid, q in questions.items()}
    max_len, head_max_len = agent.cfg.get("max_len", 512), agent.cfg.get("head_max_len", 192)
    items = []
    for row in rows:
        state = state_text(CodeRequest(**row["request"]))
        for qid, answer in labels_to_answers(row["labels"]).items():
            q = internal[qid]
            ids, markers = build_sequence(agent.tok, state, q, min(max_len, 512), head_max_len)
            if q["t"] == "choice":
                label = list(q["crit"].keys()).index(answer)
            else:
                label = int(bool(answer))
            items.append({"ids": ids, "markers": markers, "qtype": QTYPES[q["t"]], "label": label, "qid": qid,
                          "row": row["id"]})
    return items


def class_weights(items: list[dict]) -> dict[tuple[str, int], float]:
    """Inverse-frequency weight per (question, answer), square-rooted and clipped."""
    counts = Counter((it["qid"], it["label"]) for it in items)
    per_q = defaultdict(int)
    options = defaultdict(set)
    for (qid, label), n in counts.items():
        per_q[qid] += n
        options[qid].add(label)
    weights = {}
    for (qid, label), n in counts.items():
        k = max(2, len(options[qid]))
        weights[(qid, label)] = min(8.0, max(0.5, math.sqrt(per_q[qid] / (k * n))))
    return weights


def batches(items: list[dict], max_tokens: int, shuffle: bool, rng: random.Random):
    order = sorted(range(len(items)), key=lambda i: len(items[i]["ids"]))
    chunks, cur, cur_max = [], [], 0
    for i in order:
        n = len(items[i]["ids"])
        if cur and max(cur_max, n) * (len(cur) + 1) > max_tokens:
            chunks.append(cur)
            cur, cur_max = [], 0
        cur.append(i)
        cur_max = max(cur_max, n)
    if cur:
        chunks.append(cur)
    if shuffle:
        rng.shuffle(chunks)
    return chunks


def run_batch(model, batch, device):
    with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
        logits, _ = model(batch["input_ids"].to(device), batch["attention_mask"].to(device),
                          batch["marker_pos"].to(device), batch["marker_mask"].to(device),
                          batch["qtype"].to(device))
    return logits.float()


@torch.no_grad()
def evaluate(model, items, pad_id, device, max_tokens) -> dict:
    model.eval()
    correct, total = defaultdict(int), defaultdict(int)
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    for chunk in batches(items, max_tokens, False, random.Random(0)):
        group = [items[i] for i in chunk]
        b = collate_items([[{k: it[k] for k in ("ids", "markers", "qtype", "label")} for it in group]], pad_id)
        pred = run_batch(model, b, device).argmax(-1).cpu().tolist()
        for it, p in zip(group, pred):
            q = it["qid"]
            total[q] += 1
            correct[q] += int(p == it["label"])
            if it["qtype"] == QTYPES["noul"]:
                tp[q] += int(p == 1 and it["label"] == 1)
                fp[q] += int(p == 1 and it["label"] == 0)
                fn[q] += int(p == 0 and it["label"] == 1)
    model.train()
    f1s = []
    for q in tp:
        if tp[q] + fn[q] == 0:
            continue  # no positives in this split
        prec = tp[q] / (tp[q] + fp[q]) if tp[q] + fp[q] else 0.0
        rec = tp[q] / (tp[q] + fn[q])
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    acc = sum(correct.values()) / max(1, sum(total.values()))
    return {"accuracy": acc, "yes_macro_f1": sum(f1s) / max(1, len(f1s)),
            "per_question_accuracy": {q: correct[q] / total[q] for q in sorted(total)}}


def save_checkpoint(model, base_dir: Path, out: Path, cfg: dict, info: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("tokenizer", "encoder"):
        if (base_dir / sub).exists():
            shutil.copytree(base_dir / sub, out / sub, dirs_exist_ok=True)
    state = {k: v.detach().to(torch.bfloat16 if v.is_floating_point() else v.dtype).cpu().contiguous()
             for k, v in model.state_dict().items()}
    save_file(state, str(out / "model.safetensors"))
    (out / "model.safetensors").chmod(0o644)  # the model server runs as a different user
    new_cfg = dict(cfg)
    new_cfg.update({"model_name": "inkspect-laya", "fine_tuned": True,
                    # The base checkpoint's temperatures were fitted to its own training data.
                    "temperature": [1.0, 1.0, 1.0], "temperature_by_options": {},
                    "training": info})
    (out / "rl_agent_config.json").write_text(json.dumps(new_cfg, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True, help="base checkpoint directory")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--head-lr", type=float, default=1e-4)
    ap.add_argument("--max-tokens", type=int, default=12000, help="padded tokens per batch")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    device = torch.device("cuda")
    agent = laya_load(str(args.base), device="cuda")
    model, pad_id = agent.model, agent.tok.pad_token_id
    model.to(device).float()
    model.train()
    model.encoder.gradient_checkpointing_enable()

    questions = build_questions()
    train = make_items(read_jsonl(args.data / "train.jsonl"), agent, questions)
    val = make_items(read_jsonl(args.data / "val.jsonl"), agent, questions)
    weights = class_weights(train)
    print(f"train items {len(train)}  val items {len(val)}  questions {len(questions)}", flush=True)

    head_params = [p for n, p in model.named_parameters() if not n.startswith("encoder.")]
    enc_params = [p for n, p in model.named_parameters() if n.startswith("encoder.")]
    opt = torch.optim.AdamW([{"params": enc_params, "lr": args.lr}, {"params": head_params, "lr": args.head_lr}],
                            weight_decay=0.01)
    steps_per_epoch = len(batches(train, args.max_tokens, False, rng))
    total_steps = steps_per_epoch * args.epochs
    warmup = max(1, int(0.06 * total_steps))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warmup) * max(0.0, (total_steps - s) / max(1, total_steps - warmup)))

    base_eval = evaluate(model, val, pad_id, device, args.max_tokens)
    print(f"before fine-tuning: val accuracy {base_eval['accuracy']:.4f}  yes-F1 {base_eval['yes_macro_f1']:.4f}",
          flush=True)
    best, history, step, t0 = -1.0, [], 0, time.time()
    for epoch in range(1, args.epochs + 1):
        running = 0.0
        for n, chunk in enumerate(batches(train, args.max_tokens, True, rng), 1):
            group = [train[i] for i in chunk]
            b = collate_items([[{k: it[k] for k in ("ids", "markers", "qtype", "label")} for it in group]], pad_id)
            logits = run_batch(model, b, device)
            labels = b["label"].to(device)
            w = torch.tensor([weights.get((it["qid"], it["label"]), 1.0) for it in group], device=device)
            loss = (F.cross_entropy(logits, labels, reduction="none") * w).sum() / w.sum()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            step += 1
            running += loss.item()
            if n % 100 == 0:
                print(f"epoch {epoch} step {n}/{steps_per_epoch} loss {running / 100:.4f} "
                      f"({time.time() - t0:.0f}s)", flush=True)
                running = 0.0
        ev = evaluate(model, val, pad_id, device, args.max_tokens)
        history.append({"epoch": epoch, "val_accuracy": ev["accuracy"], "val_yes_macro_f1": ev["yes_macro_f1"]})
        print(f"epoch {epoch}: val accuracy {ev['accuracy']:.4f}  yes-F1 {ev['yes_macro_f1']:.4f}", flush=True)
        score = ev["yes_macro_f1"] + ev["accuracy"]
        if score > best:
            best = score
            save_checkpoint(model, args.base, args.out, agent.cfg, {
                "base": str(args.base), "epochs_completed": epoch, "train_rows": len(read_jsonl(args.data / "train.jsonl")),
                "train_items": len(train), "val_accuracy": ev["accuracy"], "val_yes_macro_f1": ev["yes_macro_f1"],
                "before_val_accuracy": base_eval["accuracy"], "before_val_yes_macro_f1": base_eval["yes_macro_f1"],
                "history": history, "hours": round((time.time() - t0) / 3600, 3)})
            (args.out / "val_per_question.json").write_text(json.dumps(ev["per_question_accuracy"], indent=1))
            print(f"saved {args.out}", flush=True)


if __name__ == "__main__":
    main()
