# Inkspect: rebuild spec

An online Rorschach test in which the test taker **types free-text responses** and **draws the area they mean on the blot**, instead of picking from multiple-choice options. Scoring follows the Exner Comprehensive System (CS). Coding uses NLP, and the NLP backend can be swapped (rules, a hosted LLM, or a fine-tuned local decision model such as Laya).

This replaces the 2022 Flask prototype. Git history keeps the old code, and the useful assets (`static/img/blot_*.jpg`, `data/FQ_tables.db`, `example.txt`) are migrated.

## Stack

| Service   | Tech                                                   | Notes |
|-----------|--------------------------------------------------------|-------|
| `web`     | React + TypeScript + Vite, built and served by nginx   | nginx also reverse-proxies `/api` to `api` |
| `api`     | Python 3.12, FastAPI, SQLAlchemy 2, Alembic            | Test flow, persistence, location mapping, structural summary, interpretation |
| `scorer`  | Python 3.12, FastAPI                                   | Response coding behind one `Coder` interface; keeps heavy ML deps out of `api` |
| `db`      | PostgreSQL 16                                          | Named volume |

- `docker compose up --build` starts the full app at `http://localhost:8080` with no extra setup.
- Config goes through a `.env` file, and `.env.example` is committed.
- Every service has a healthcheck.
- The Laya backend runs under a compose profile (`--profile laya`) so the default stack stays light.

## Test flow

1. **Landing / consent.** Explain what the test is, say the result is not a diagnosis, and create an anonymous session. Store no PII.
2. **Response phase (cards I–X).** Show one card at a time and collect free-text responses. Apply the standard CS examiner rules:
   - A response like "an inkblot" gets the "what might it be" prompt.
   - A single response on Card I gets the "take your time, you'll find something else" prompt.
   - Accept at most 5 responses per card.
   - If the total R is below 14 after Card X, explain and re-administer.
   - Record the time to first response per card.
3. **Inquiry phase.** For each response, show the card and the person's own words. Then:
   - **Area pointing:** the person draws one or more freehand lasso regions on the blot (mouse and touch), with a "the whole card" shortcut. Undo and clear work.
   - **Free-text explanation:** "What makes it look like that?"
   - **Keyword follow-ups:** CS-legal, non-leading prompts only (for example, "You said *pretty*; what makes it look pretty?"). The system picks prompts from a fixed template list and never invents leading questions.
4. **Results.** Show the scored protocol (sequence of scores), the structural summary, and the interpretation. The results page carries a clear "not a clinical diagnosis" notice.

## Scoring pipeline

Code every part that doesn't need language understanding deterministically. Use NLP only where it's needed.

| Code                                  | Method |
|---------------------------------------|--------|
| Location (W, D#, Dd#, S)              | **Geometric.** Compare the drawn polygons against per-card region masks using coverage/IoU. No NLP. |
| Developmental Quality (+, o, v/+, v)  | `Coder` |
| Determinants (F, M, FM, m, C, CF, FC, Cn, C', T, V, Y, FD, Fr/rF, blends) | `Coder`, with the a/p superscript for movement |
| Pair (2)                              | `Coder` |
| Form Quality (+, o, u, -)             | Look up in the FQ table (card + location + object) with fuzzy/semantic object matching. If nothing matches, fall back to `Coder` for u/-. |
| Contents                              | `Coder` |
| Popular (P)                           | Deterministic, from the CS Popular list per card and location |
| Z score                               | Deterministic, from the CS Z table |
| Special Scores (DV, INCOM, DR, FABCOM, CONTAM, ALOG, PSV, AB, AG, COP, MOR, PER, CP, GHR/PHR) | `Coder` |

**`Coder` interface:** `code(card, verbatim, inquiry, location) -> Codes`. The output is a typed schema, and every code carries a confidence value and the evidence text span it was based on. There are three implementations:

- `RuleCoder`: POS and keyword heuristics. It is deterministic, and the tests use it.
- `LLMCoder`: a hosted LLM with schema-constrained JSON output. Enabled when an API key is set.
- `LayaCoder`: a local Laya checkpoint. Each code family is one typed decision: choice for DQ and FQ fallback, yes/no per determinant, content, and special score.

**Structural summary:** compute every CS ratio, percentage, and derivation deterministically in `api`. This covers the upper and lower sections and the constellations (PTI, DEPI, CDI, S-CON, HVI, OBS), and it is fully unit-tested.

**Interpretation:** rule-based text produced from the structural summary, following the CS interpretive search strategy (key variables, then clusters). The LLM does not write free-form interpretation.

## Region maps

- Store each card's regions as normalized polygons in `regions/card_<n>.json`: W, the numbered D and Dd areas, and S.
- Add an **admin region editor** page for drawing and labelling regions on each card.
- The initial maps may be auto-generated placeholders (connected ink components) with `"placeholder": true`. A human must replace them with real CS location areas.

## Review and training data

- Add an examiner review page where a reviewer can inspect each response, override any code, and see the structural summary update.
- Store every override as a labelled example.
- `GET /api/export/training.jsonl` exports the labelled examples in the format the Laya fine-tuning notebook expects.

## Quality bar

- `api` and `scorer`: pytest. Cover the structural summary math, location mapping, FQ lookup, examiner-rule logic, and `RuleCoder`. Calibrate against the coded protocol in `example.txt`.
- `web`: typecheck and lint must be clean.
- **End-to-end:** a Playwright test runs against the compose stack and completes a full 10-card test, including lasso drawing, through to the results page.
- `README.md` documents setup, architecture, how to switch coders, how to edit region maps, and the licensing caveats for the FQ tables and CS norms.
