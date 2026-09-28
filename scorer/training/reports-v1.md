# Laya coder v1: evaluation

The checkpoint is `models/inkspect-laya-v1`. It was fine-tuned from `convaiinnovations/laya`
typed-decisions for 3 epochs on 2,575 synthetic rows (127,613 question items), taking 1 hour on one RTX 3090.

**How to read these numbers:**
- `val` is **synthetic**. It is held out by record, but it was written by the same process as the
  training data, so it measures learning of the silver labels, not agreement with human examiners.
- `test` is the only **real** data: 18 examiner-coded responses. The rule coder was calibrated on
  these same responses, so its scores there are inflated. With 18 rows, one response moves accuracy by 0.06.
- Neither set is a validation of clinical accuracy. That needs real responses coded independently by
  trained examiners.

**Typo robustness.** The same `val` rows were re-scored with heavy typos and texting abbreviations
injected (for example "2 animal clibm da mountain maybe bear"):

| metric | rule | fine-tuned |
|---|---|---|
| validity (acc) | 0.86 | 0.95 |
| DQ (acc) | 0.62 | 0.89 |
| determinants exact (acc) | 0.32 | 0.74 |
| primary content (acc) | 0.64 | 0.81 |
| flag invalid (F1) | 0.52 | 0.98 |
| contents (F1) | 0.65 | 0.80 |
| special scores (F1) | 0.63 | 0.80 |


### val.jsonl (250 rows)

| metric | rule | base | fine-tuned |
|---|---|---|---|
| validity (acc) | 0.86 | 0.33 | 0.96 |
| DQ (acc) | 0.67 | 0.41 | 0.90 |
| determinants exact (acc) | 0.32 | 0.23 | 0.74 |
| pair (2) (acc) | 0.94 | 0.66 | 0.97 |
| primary content (acc) | 0.69 | 0.33 | 0.86 |
| fq_fallback (acc) | 0.74 | 0.70 | 0.72 |
| flag invalid (F1) | 0.52 | 0.38 | 0.97 |
| determinant families (F1) | 0.62 | 0.43 | 0.90 |
|   F (F1) | 0.76 | 0.51 | 0.92 |
|   M (F1) | 0.70 | 0.49 | 0.90 |
|   FM (F1) | 0.68 | 0.54 | 0.93 |
|   m (F1) | 0.31 | 0.18 | 0.80 |
|   colour (F1) | 0.67 | 0.33 | 0.92 |
|   achromatic (F1) | 0.34 | 0.00 | 0.91 |
|   texture (F1) | 0.91 | 0.61 | 0.88 |
|   vista (F1) | 0.91 | 0.29 | 0.80 |
|   diffuse (F1) | 0.47 | 0.29 | 0.76 |
|   reflection (F1) | 1.00 | 0.86 | 1.00 |
|   FD (F1) | 0.55 | 0.11 | 0.92 |
| contents (F1) | 0.70 | 0.28 | 0.83 |
| special scores (F1) | 0.65 | 0.20 | 0.83 |

### test.jsonl (18 rows)

| metric | rule | base | fine-tuned |
|---|---|---|---|
| validity (acc) | 1.00 | 0.17 | 1.00 |
| DQ (acc) | 1.00 | 0.67 | 0.94 |
| determinants exact (acc) | 0.72 | 0.61 | 0.72 |
| pair (2) (acc) | 1.00 | 0.78 | 1.00 |
| primary content (acc) | 0.89 | 0.67 | 0.78 |
| fq_fallback (acc) | 0.50 | 0.39 | 0.67 |
| flag invalid (F1) | — | 0.00 | — |
| determinant families (F1) | 0.76 | 0.62 | 0.70 |
|   F (F1) | 0.85 | 0.81 | 0.83 |
|   M (F1) | 1.00 | 0.00 | 0.00 |
|   FM (F1) | 1.00 | 0.40 | 0.67 |
|   m (F1) | 0.00 | 0.00 | 0.00 |
|   colour (F1) | 0.00 | 0.00 | — |
|   achromatic (F1) | 0.00 | — | 0.00 |
|   texture (F1) | — | — | — |
|   vista (F1) | 0.00 | 0.00 | 0.00 |
|   diffuse (F1) | 0.00 | 0.00 | 0.00 |
|   reflection (F1) | — | — | — |
|   FD (F1) | — | 0.00 | — |
| contents (F1) | 0.87 | 0.40 | 0.84 |
| special scores (F1) | 0.73 | 0.18 | 0.50 |
