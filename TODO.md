# TODO

## Before wider public use
- [ ] **S-CON and DEPI in public results** (owner: Kahngjoon). These clinical screening flags (suicide and depression constellations) still show on the Professional tab of every results page. Decide whether lay test takers should see them, e.g. show them only on the examiner review page.
- [ ] **Exner FQ table in the public repo.** `api/app/data/fq_tables.db` is copyrighted CS material and has been public since 2022. Move it out of git so it's loaded from a local file, then purge it from history (`git filter-repo`, force push). History also still holds `data/users.db` (34 responses from 2022).
- [ ] **Provenance of `api/tests/fixtures/example_protocol.txt`.** Confirm where the real coded protocol came from (published source vs a real person) and credit or remove it.
- [ ] **Keep results out of search engines.** Add a `robots.txt` and `noindex` so only the landing page is indexed, never `/test`, `/results` or `/admin`.
- [ ] **Cloudflare hardening.** Put `/admin` and `/api/admin` behind Cloudflare Access, turn on Always Use HTTPS, and add `www.inkspect.org.uk` if wanted.

## Product
- [ ] Donation link: an optional `DONATE_URL` setting, shown in the footer and on the results page only (never during the test).
- [ ] Real CS location maps: replace the placeholder region maps in `/admin/regions/<card>` and commit them to `regions/`.
- [ ] Check the Overview band ranges (`api/app/overview.py`) against CS adult reference data.
- [ ] Credit Exner in the README: *Exner (2003), The Rorschach: A Comprehensive System, Vol. 1, 4th ed., Wiley.*

## Laya coder
- [ ] Retrain with real reviewer corrections: `scorer/training/train.sh v2 training.jsonl`. See `scorer/training/README.md`.
- [ ] Measure it against real responses coded independently by trained examiners before trusting it.
- [ ] Pin the laya container to the GPU that llama-swap uses less (it holds 3.5 GB on GPU 0 all the time).

## Repo
- [ ] The `rebuild` branch isn't pushed or merged yet.
