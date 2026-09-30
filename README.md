# Inkspect

An online Rorschach inkblot test where people **type their own answers** and **draw the part of the blot they mean**. Most online versions make you pick from a list instead. Responses are coded with the Exner Comprehensive System (CS). A structural summary and a rule-based interpretation are produced from those codes.

> **Not a diagnostic tool.** The Rorschach is a clinical instrument that a trained examiner administers and interprets. Inkspect's automatic coding and interpretation are a research and learning aid. Every results page says so.

## Quick start

```sh
cp .env.example .env        # optional: every setting has a working default
docker compose up --build -d
open http://localhost:8080  # or http://localhost:$WEB_PORT
```

No API keys are needed. By default, answers are coded by the deterministic rule coder.

If port 8080 is already in use, set `WEB_PORT` in `.env` (for example `WEB_PORT=8090`).

| URL | What |
|-----|------|
| `/` | Take the test |
| `/results/<session>` | The scored protocol, structural summary and interpretation |
| `/admin` | Examiner tools: review and correct codes, edit region maps, export training data. Needs `ADMIN_TOKEN` (default `dev-admin`; change it). |
| `/api/docs` | OpenAPI docs for the API |

## How the test works

1. **Response phase.** Cards I–X are shown one at a time. The person types what each might be and can turn the card; the orientation is recorded with each response. The standard CS examiner rules are applied:
   - "It's an inkblot" gets the *what might it be* prompt.
   - A single answer on Card I gets the *take your time* prompt, once.
   - An empty card gets one encouragement.
   - Five responses per card is the limit.
   - A record with fewer than 14 responses is re-administered once.
2. **Inquiry phase.** For each response, the person draws one or more freehand lasso areas on the card, or picks "the whole card", and says what makes it look that way. If they use a key word that could hide a determinant ("pretty", "furry", "dark"…), they get a non-leading CS prompt taken from a fixed template list. At most two prompts are asked per response.
3. **Results.** Each response is scored, then the page shows the sequence of scores, the structural summary (upper and lower sections plus PTI, DEPI, CDI, S-CON, HVI and OBS), and an interpretation that follows the CS interpretive search strategy.

## Architecture

```
browser ──► web (nginx + React SPA) ──/api──► api (FastAPI) ──► db (Postgres)
                                                  │
                                                  └──► scorer (FastAPI) ──► [LLM API | laya model server]
```

| Service | Directory | Role |
|---------|-----------|------|
| `web` | `web/` | React + TypeScript + Vite app, served by nginx. Also proxies `/api` to the api. |
| `api` | `api/` | Test flow and examiner rules; location mapping; FQ lookup; Popular, Z, PSV and GHR/PHR; structural summary; interpretation; admin endpoints. Alembic migrations run on start. |
| `scorer` | `scorer/` | Codes each response (DQ, determinants, pair, contents, special scores) behind one `Coder` interface. Also chooses inquiry follow-up prompts. |
| `db` | — | PostgreSQL 16 in the named volume `db-data`. To use an external or production Postgres, set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname` in `.env`. The api runs its migrations there on start, and the bundled `db` container is then unused. |
| `laya` | `scorer/laya_server/` | Optional local Laya model server. Only runs with `--profile laya`. |

### What is coded how

Only the parts that need language understanding go through the coder. Everything else is deterministic.

| CS code | Method |
|---------|--------|
| Location (W, D#, Dd#, S) | The drawn polygons are rasterised and compared with the card's region map by coverage and F1 overlap (`api/app/location.py`). S is coded only when the response mentions the white space. |
| Form Quality | Looked up in the Exner FQ table (`api/app/data/fq_tables.db`, 5,128 entries, not in git: see below) by card, location, orientation and object (`api/app/fq.py`). With no entry for that location, the coder's u/− estimate is used. `+` means an ordinary (o) response with four or more named parts. |
| Popular, Z | CS tables (`api/app/tables.py`). One drawn area counts as adjacent (ZA); several count as distant (ZD). |
| PSV, GHR/PHR | Computed from the whole record (`api/app/scoring.py`). |
| DQ, determinants (with a/p), (2), contents, special scores | The scorer's `Coder` |
| Structural summary, constellations | `api/app/summary.py` |
| Interpretation | Rule-based sentences tied to thresholds (`api/app/interpretation.py`). No model writes free text. |

## Switching coders

Set `CODER` in `.env` and run `docker compose up -d scorer`.

| `CODER` | Needs | Notes |
|---------|-------|-------|
| `rule` (default) | nothing | Lexicon and heuristic coder. It is deterministic, and it is a baseline: expect it to miss subtle determinants and special scores. |
| `llm` | `ANTHROPIC_API_KEY` | Claude with a JSON-schema-constrained output. `LLM_MODEL` overrides the default model. |
| `laya` | a fine-tuned checkpoint in `models/`, plus `COMPOSE_PROFILES=laya` | The local fine-tuned Laya decision model. It handles typos and slang and runs offline. Train it and switch to it with `scorer/training/README.md`. |

Every coder also judges **validity**: whether an answer is a sincere attempt, or unserious, gibberish, a refusal or off-task. Non-genuine answers stay in the protocol with a badge, but they are left out of the structural summary. A record where a quarter or more of the answers aren't sincere is flagged as not interpretable. Reviewers can change validity on the review page.

If the chosen coder isn't available (no key, or the model server is unreachable), the scorer falls back to `rule`. The protocol row records which coder produced each code.

### Training the Laya coder

See `scorer/training/README.md`. In short:
- `scorer/training/train.sh v1` fine-tunes Laya on the bundled synthetic silver-label set.
- `scorer/training/train.sh v2 training.jsonl` adds reviewer corrections exported from `/admin`.
- Each run writes a report comparing the model with the rule coder, both on held-out synthetic data and on a real examiner-coded protocol.

## Region maps

Each card's location areas live in `regions/card_<n>.json` as normalised polygons (0–1, unrotated card coordinates):

```json
{"card": 1, "placeholder": true, "regions": [
  {"id": "W", "kind": "W", "polygons": [[[0.1, 0.2], ...]]},
  {"id": "D1", "kind": "D", "polygons": [[...], [...]]},
  {"id": "DdS50", "kind": "S", "polygons": [[...]]}]}
```

The committed maps are **placeholders** (`"placeholder": true`). `tools/generate_placeholder_regions.py` generated them automatically by segmenting the ink into colour clusters and connected components, splitting large parts into centre and sides, and merging mirror pairs. They are **not** the Exner location areas: their numbering doesn't match the CS D/Dd numbers. Until they are replaced, Location, FQ, Popular and Z are approximate, and the results page says so.

To draw the real areas:

1. Open `/admin` → **Region editor** → a card.
2. Select or create a region (id such as `D3` or `Dd22`, kind W/D/Dd/S) and lasso its polygons. A mirrored area (one on each side) is one region with two polygons.
3. Untick **placeholder**, then **Save**. This saves to the database and takes effect right away.
4. **Download JSON** and commit it over `regions/card_<n>.json`, so a fresh database gets the real maps. The api seeds a card from the file only when the database has no map for it.

## Development

```sh
docker compose exec api pytest       # examiner rules, location mapping, FQ lookup, scoring, structural summary, API flow
docker compose exec scorer pytest    # rule coder, follow-ups, LLM and Laya coders (mocked)
(cd web && npm ci && npm run typecheck && npm run lint)
docker compose --profile e2e run --rm e2e   # Playwright, a full 10-card test against the running stack
```

To work on the frontend with hot reload, run `cd web && npm run dev`. It proxies `/api` to the compose stack at `localhost:8080`; edit `web/vite.config.ts` if you changed `WEB_PORT`.

## Background

Inkspect started in July 2022 as Team Natural Intelligence's entry to the Uber Global Hackathon (Coding Track, *Solving Global Health*). The one-page poster is in [`docs/2022-uber-global-hackathon.pdf`](docs/2022-uber-global-hackathon.pdf). Its case still stands: many people with a mental illness never seek help, and the online inkblot tests that exist either skip the inquiry phase or reduce it to multiple choice. The 2022 prototype was a small Flask app. This rebuild carries out most of the poster's plan:

| 2022 plan | Now |
|---|---|
| Free-text answers, a lasso to mark the area, automated prompts that guide the test | The same: typed responses, a freehand lasso in the inquiry, and the CS examiner rules with key-word follow-ups (`api/app/examiner.py`) |
| NLP (POS tagging, semantic analysis, co-reference) scores every category | A coder handles only the language-dependent codes: rule-based, Claude, or the fine-tuned local Laya model. Location, FQ, Popular, Z and the summary are deterministic code |
| FQ, content and Popular looked up in the CHESSSS database | FQ is looked up in the Exner table, which is now kept outside git. Popular and Z are in the code |
| Results compared with norms and shown on a spectrum | The Overview tab places six bands against adult ranges. The Professional tab has the full structural summary |
| No name asked, no data stored | Still no name or personal details, but anonymous answers **are** stored. That's a deliberate change: the automatic coding can't be checked or improved without them |
| Get professional opinion once the prototype works | Still open. A validation needs real participants, ethics approval and trained coders (`TODO.md`) |

## Licensing caveats

- **Code:** GNU GPL v3 (`LICENSE`).
- **Inkblot images:** Hermann Rorschach's plates were published in 1921 and are in the public domain in many jurisdictions. Hogrefe, the test's publisher, still sells the official cards, and many professional bodies object to publishing them. Check your jurisdiction and professional code before making the site public.
- **Comprehensive System material:** the FQ table, the Popular list, Z values, Zest, the constellation criteria and the interpretive search strategy come from John E. Exner Jr.'s published CS works, which are copyrighted. The small tables (Popular, Z, Zest, constellations) are in the code for research and educational use. The FQ table is **not** in the repository: put your own copy at `api/app/data/fq_tables.db` (git-ignored, copied into the api image at build time) or point `FQ_DB_PATH` at it. It is a SQLite file with a table `FQ_tables(Card, Loc, v, Item, Cont, FQ)`; the 2022 poster names the free CHESSSS scoring software (Fontan et al., 2013) as its source. Without it, FQ falls back to the coder's u/− estimate and the FQ tests are skipped. Get permission before any commercial or public clinical use.
- **R-PAS:** the CS is no longer maintained. Its successor, R-PAS, has updated norms and FQ tables but is proprietary and licensed separately. Inkspect doesn't include it.
- **Norms:** the interpretation uses the CS adult conventions. It hasn't been validated for online self-administration or for automatic coding.

## References

- Exner, J. E., Jr. (2003). *The Rorschach: A Comprehensive System, Vol. 1: Basic Foundations and Principles of Interpretation* (4th ed.). Wiley.
- Fontan, P., Andronikof, A., Nicodemo, D., Al Nyssani, L., Guilheri, J., Hansen, K. G., Kumasaka, S., & Nakamura, N. (2013). CHESSSS: A free software solution to score and compute the Rorschach Comprehensive System and supplementary scales. *Rorschachiana, 34*(1), 56.
