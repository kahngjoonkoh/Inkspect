# Training the Laya coder

The `laya` coder is [Laya](https://github.com/NandhaKishorM/laya), a 421M-parameter typed-decision
model (ModernBERT-large encoder plus a decision head), fine-tuned to code Rorschach responses. It runs
locally, so answers never leave your server. For every response it answers 64 typed questions:

- **validity:** genuine, unserious, gibberish, refusal or off-task
- **DQ**
- **movement:** M, FM, m, plus active or passive
- **each shading and colour family**, with form dominance
- **FD, pair**
- **each content code and each special score**

The questions are defined in `scorer/coders/laya_questions.py`.

## Data

| Source | Where | Used for |
|---|---|---|
| Synthetic silver labels | `synthetic/*.jsonl` | Bootstrapping, until real data exists |
| Real examiner-coded responses | `real/*.jsonl` | Always the held-out **test** set |
| Reviewer corrections from real users | `/admin` → **Download training.jsonl** | Training and validation, replacing synthetic data over time |

**Synthetic records.** Claude wrote these following `AUTHORING.md`:
- 1,300 genuine responses: 130 per card, in several writing styles (phone-typed, non-native English, misspelled, elaborate), including 100 hard "odd but genuine" answers.
- 260 non-genuine answers: unserious, gibberish, refusal and off-task.

Every record passes `validate.py`. Treat them as **silver labels**: they follow the CS rules but no trained examiner checked them.

**Real test set.** `real/example_protocol.jsonl` holds the 18 responses of a real examiner-coded protocol (`api/tests/fixtures/example_protocol.txt`). It is never trained on. The rule coder was calibrated on these same responses, so its scores there are optimistic.

## Train

Needs Docker with an NVIDIA GPU (about 12 GB of memory; one RTX 3090 is plenty).

```sh
scorer/training/train.sh v1                                  # synthetic data only
scorer/training/train.sh v2 ~/Downloads/training.jsonl        # plus reviewer corrections
```

The script:
1. Builds `models/laya-data-<v>/{train,val,test}.jsonl` (`build_dataset.py`).
   - The split is by record, stratified by card and validity.
   - Training records get label-preserving typo and texting variants, so the model learns that "buterfly" is a butterfly.
   - The generic `D`/`Dd` locations are mapped to the card's region ids.
2. Fine-tunes the public `typed-decisions` checkpoint (`finetune.py`). Every (response, question) pair is built with Laya's own `build_sequence`, so training sees exactly what inference sees. Rare "yes" answers are up-weighted.
3. Evaluates the rule coder, the base checkpoint and the fine-tuned one through the scorer's real decode path (`evaluate.py`). The result goes to `models/laya-data-<v>/report.md`.

`models/` is git-ignored. Checkpoints are about 850 MB.

## Use it

In `.env`:

```sh
COMPOSE_PROFILES=laya
CODER=laya
LAYA_CHECKPOINT=/models/inkspect-laya-v1
```

Then run `docker compose up -d --build`.

- For a GPU, use `docker compose -f compose.yaml -f compose.gpu.yaml up -d --build`.
- On CPU, coding takes a few seconds per response.
- If the model server is down, the scorer falls back to the rule coder.

## Updating with real data

1. Collect sessions. Reviewers check and correct codes at `/admin/review/<session>`, including validity.
2. Export with `/admin` → **Download training.jsonl**.
3. Run `scorer/training/train.sh v2 training.jsonl`. Real corrections are mixed in, and part of them is held out for validation.
4. Compare `report.md` with the previous version, and switch `LAYA_CHECKPOINT` only if the new model is better.
5. As real data grows, drop the synthetic set: move files out of `synthetic/`, or remove them.

Don't trust any version until it has been measured against real responses coded independently by trained examiners.
