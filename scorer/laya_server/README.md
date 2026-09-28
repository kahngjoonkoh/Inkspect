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

This server is the `laya` service in `compose.yaml`. Enabling it and training the checkpoint it
serves are covered in [`scorer/training/README.md`](../training/README.md).

| Environment variable | Default (compose) | Meaning |
|---|---|---|
| `LAYA_CHECKPOINT` | `/models/inkspect-laya-v1` | local checkpoint directory, or a Hugging Face repo id |
| `LAYA_SUBFOLDER`  | empty | subfolder inside a Hugging Face repo (`typed-decisions` for the public base model) |
| `LAYA_DEVICE`     | `cpu` (`cuda` with `compose.gpu.yaml`) | about 8 s per response on CPU, about 0.2 s on an RTX 3090 |

The scorer reaches it at `LAYA_URL` (default `http://laya:8100`). If it can't be reached, the scorer
falls back to the rule coder and marks the result `"coder": "rule"`.
