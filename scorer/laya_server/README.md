# Laya decision server (optional)

`LayaCoder` (in `scorer/coders/laya.py`) codes responses with
[Laya](https://github.com/NandhaKishorM/laya), a 421M-parameter open-weight
model (Apache 2.0) that answers **typed decisions** about a piece of text in a
single forward pass. It doesn't generate text. This directory holds the small
server that `LayaCoder` calls. It runs only under the `laya` compose profile.

## What Laya answers

Laya takes a `state` (text, or a dict) and a set of named questions. Each
question has one of three types:

| type     | request fields                                   | answer                                                  |
|----------|--------------------------------------------------|---------------------------------------------------------|
| `choice` | `instructions`, `criteria: {key: description}`   | `{"choice": key, "confidence": p, "probabilities": {...}}` |
| `score`  | `instructions`, `criteria: [level, ...]`         | `{"score": x, "confidence": p, "probabilities": {...}}`    |
| `noul`   | `instructions`                                   | `{"noul": P(yes), "confidence": p}`                        |

The HTTP shape is Laya's own `laya-serve` one:
`POST /v1/systemone {"state", "questions", "model"?}` returns `{"answers": {...}, "usage": {...}}`.
(Sources: the GitHub README and the Hugging Face card at
<https://huggingface.co/convaiinnovations/laya>.)

Laya has no multi-label question type, so `scorer/coders/laya_questions.py`
turns CS coding into 63 questions:

| Questions | Type |
|---|---|
| `dq` (+, o, v/+, v) | choice |
| `fq_fallback` (u, -) | choice |
| `movement_ap` (active, passive, both) | choice |
| `pair` | yes/no |
| `form_dimension` (FD) | yes/no |
| `move_M`, `move_FM`, `move_m` | yes/no, one per movement family |
| `det_<family>` for colour, achromatic, texture, vista, diffuse shading and reflection | yes/no, one per family |
| `det_<family>_dominance` (FC / CF / C / Cn, and so on) | choice, one per family |
| `content_<code>` | yes/no, one per CS content code |
| `special_<code>` | yes/no, one per special score |

Any yes/no answer at or above 0.5 counts as yes.

## Running it

```bash
# LAYA_URL=http://laya:8100 and CODER=laya tell the scorer to use it
docker compose --profile laya up --build
```

| Environment variable | Default | Meaning |
|---|---|---|
| `LAYA_CHECKPOINT` | `convaiinnovations/laya` | Hugging Face repo id, or a local path to a fine-tuned checkpoint |
| `LAYA_SUBFOLDER`  | `typed-decisions` | subfolder inside the repo (leave empty for a local checkpoint) |
| `LAYA_DEVICE`     | `cpu` | `cuda` if a GPU is passed through |

The scorer side reads three settings:
- `LAYA_URL`: where this server is.
- `LAYA_MODEL`: sent as the request's `model`. The default is `typed-decisions`, which only matters if you point `LAYA_URL` at a stock `laya-serve`.
- `LAYA_API_KEY`: optional; sent as a bearer token.

If the server can't be reached, or it returns an error, the scorer falls back
to the rule coder and marks the result `"coder": "rule"`.

You can also skip this image and run Laya's own server:
`pip install "laya[serve]" && laya-serve` listens on port 8000 with the same endpoint.

## Fine-tuning on reviewer corrections

The base checkpoints don't know the Exner CS. On Laya's own typed-decision
benchmark, the base checkpoints score *below* the majority-class baseline, and
only the fine-tuned checkpoint is useful. You need labelled data:

1. Reviewers correct codes on the api's review page. Every override is stored.
2. Export the corrections:
   `curl -H "X-Admin-Token: $ADMIN_TOKEN" localhost:8080/api/admin/export/training.jsonl > training.jsonl`.
   Each line is `{"state": str, "labels": Codes, "source": "override"}`.
3. Convert them to Laya's fine-tuning format. The script needs only the standard library:
   ```bash
   python scorer/laya_server/convert_training.py training.jsonl > laya_train.jsonl
   ```
   Each output line is `{"state", "questions", "answers"}`:
   - For `choice` questions, the answer is the chosen criteria key.
   - For `noul` questions, the answer is a boolean.
   - The questions are the same ones `LayaCoder` asks at inference time.
4. Fine-tune with Laya's `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`.
5. Point `LAYA_CHECKPOINT` at the result, and set `LAYA_SUBFOLDER=` (empty).

Reviewed protocols are sensitive clinical data. Keep the export and the
fine-tuned weights on infrastructure you control.
