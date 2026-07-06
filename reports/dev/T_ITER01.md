# T_ITER01 — Program T, Iteration 01 (Stage-1 signal battery, dev markets)

**Status: BLOCKED — cannot complete the tasked Stage-1 battery.** The four
Databento fetches (CL, GC, ZN, 6E) require external Databento access and a
purchase, and this environment has neither credentials nor the client
library. ES is built and the pipeline is proven end-to-end, but the
five-market portfolio — the *primary object under test* — cannot be
computed with one market. No holdout was touched. No spec was changed. The
blocking question for the architect is at the end.

## 1. Header

| field | value |
|---|---|
| iteration | T-01 (Stage-1 signal battery, dev markets) |
| commit | `70fac68169edba33ff178748de4652b8a2502ef9` |
| branch | `claude/t-iter01` |
| date | 2026-07-06 |
| governing docs | `reports/PREREGISTRATION_T.md` (binding), `docs/EXECUTOR_BRIEF.md` |
| wall-clock (work done) | ES daily resample + ES-only plumbing test ≈ 30 s total |
| data cost | **$0.00** — no Databento purchase was made (fetch blocked; see §7) |

## 2. Preflight

Run at the tasked commit on a synced tree (`uv sync --extra dev --extra
fetch`):

| check | required | observed | result |
|---|---|---|---|
| `uv run pytest -q` | 150/150 | 150 passed | ✅ |
| `uv run ruff check src tests` | clean | clean | ✅ |
| commit | tasked | `70fac68` | ✅ |

Preflight passed; proceeded.

## 3. Data integrity

### 3.1 ES — built and verified ✅

Per task: reused the existing adjusted 15m series (`data/es_15m.parquet`,
sha256 `a3fc183db2a464410d54b9ce6fab442cacbf1ac390a99515a23efc1b38cdd478`)
and derived daily bars by resampling to CME trading-day buckets. **No
re-stitch.** Builder: `reports/dev/_es_daily_resample.py`. Session rule:
convert ts → America/Chicago, +7h, take the calendar date (DST-safe; the
17:00 CT open rolls to the settlement date, the 15:45 CT last bar stays).
Daily `ts` = midnight-UTC of the settlement date, epoch seconds (int) —
the shared convention so the portfolio inner-join on `ts // 86400` aligns
across all five instruments.

| metric | value |
|---|---|
| rows | 4137 (task expected ≈ 4,030 trading days) |
| date range | 2010-06-07 → 2026-07-01 |
| duplicates | 0 |
| OHLC violations | 0 |
| non-positive prices | 0 |
| min / max close | 1609.5 / 7693.0 |
| 20-random-day recon vs 15m extremes (seed 20100606) | 0 mismatches (exact) |
| out sha256 | `6527324697558f1c08851a2a4a18a86c86c4139113b1dadbb975a1fbb4488d2b` |
| meta | `reports/dev/_es_1d_meta.json` |

Construction hygiene (documented, not result-patching — see §5):
- Dropped two weekend-labeled "sessions" from lone Sunday pre-open prints:
  `2014-05-25`, `2018-08-05`.
- Dropped one out-of-window session stub: `2026-07-02` (8-bar fragment past
  the task window end `2026-07-01`).
- Thin-but-legitimate sessions kept (partial-data / early-close days, all
  real half-sessions): `2012-12-26` (44), `2013-01-02` (44),
  `2013-12-26` (44), `2014-01-02` (44), `2014-09-26` (39), `2025-11-28`
  (34).

The 4137 count exceeds the task's "~4,030" guide by ~2.6%; this is
expected — the 15m series spans 2010-06-07 → 2026-07-01 inclusive and the
"~4,030" is a round estimate. Range and recon are exact, so the count is
sound. Flagged as an observation, not patched.

### 3.2 CL, GC, ZN, 6E — NOT built ❌ (fetch blocked)

Required: fresh Databento GLBX.MDP3 **ohlcv-1d** for full products CL, GC,
ZN, 6E (parent symbology, all expiries), then a daily volume-roll +
additive back-adjust. **None of this could run.** This environment has:

| probe | result |
|---|---|
| `import databento` | `ModuleNotFoundError: No module named 'databento'` |
| `~/.databento` | absent |
| `DATABENTO_API_KEY` (env) | unset |
| repo fetcher `src/ict_backtest/data/fetch.py` | `fetch_binance(...)` only — Binance crypto, cannot reach GLBX |

The repo's only data fetcher is Binance-only; there is no GLBX path, no
API key, and no client library. Fetching therefore requires the architect
to provide credentials + spend authorization (or pre-downloaded ohlcv-1d
exports). Per the brief ("Report anomalies, don't patch them") and the
task ("Anomalies reported, not patched"), I did not attempt to install
tooling, synthesize data, or substitute any series. **No holdout was
touched** (HG/ZF/6J/ZC/NQ/crypto untouched).

The stitch is nonetheless **staged and ready** — `reports/dev/_t01_stitch.py`
generalizes the frozen ES recipe to daily resolution and monthly-listed
products (all twelve CME month codes; contract ordering by decoded
(year, month) with `max_dt`-anchored decade disambiguation, since CL/GC do
not settle on the third Friday; identical look-ahead-free volume roll —
crossover day *d* → membership effective `days[i+1]` — and identical
additive Panama back-adjust, newest segment offset 0). It fails loud if
run without data. Once the four ohlcv-1d exports exist:

```
uv run python reports/dev/_t01_stitch.py --sym cl --csv data/<cl>.ohlcv-1d.csv.zst
uv run python reports/dev/_t01_stitch.py --sym gc --csv data/<gc>.ohlcv-1d.csv.zst
uv run python reports/dev/_t01_stitch.py --sym zn --csv data/<zn>.ohlcv-1d.csv.zst
uv run python reports/dev/_t01_stitch.py --sym 6e --csv data/<6e>.ohlcv-1d.csv.zst
```

It writes `data/<sym>_1d.parquet`, `data/<sym>_1d_raw.parquet`,
`reports/dev/_<sym>_1d_meta.json` (rows, range, roll count, per-boundary
residual, OHLC violations, dupes, min/max, non-positive-adjusted flag,
last-segment offset == 0 spot check, sha256s), and
`reports/dev/_<sym>_roll_calendar.json`.

**One item to verify against the real export** (documented in the script,
to report not patch): the ohlcv-1d `ts_event` settlement-date labelling
must match `data/es_1d.parquet`'s midnight-UTC-of-settlement convention.
If Databento labels the daily bar's UTC *start* rather than the settlement
date, the `ts // 86400` join key could be off by a day for some
instruments — an anomaly to surface after the first real fetch, not to
silently correct.

## 4. Results

**The tasked Stage-1 results cannot be produced.** The support rule is
defined on the **portfolio** (equal-weight vote + vol-scaled across all
five dev markets) plus each half-window, and on per-instrument lines for
all five. With only ES available, none of the required arithmetic —
portfolio full CI + p_shift, half-A CI, half-B CI, and the five
per-instrument lines — can be computed. Running the runner today would
raise `ValueError: no candles in requested date range` on the first
missing market (`data/cl_1d.parquet`). I did **not** run a one-market
"portfolio" as a stand-in; a one-market portfolio is not the preregistered
object and would be misleading.

### Plumbing smoke test (NOT a Stage-1 result — burned ES only)

To prove the pipeline (loader → `tsmom_rows` → `portfolio_rows` →
`render_trend_battery`) works against the real `es_1d.parquet`, I ran the
frozen library on ES alone, full window. **This is a plumbing check, not a
Stage-1 finding, and ES is a burned dev market regardless.** Library
defaults (bootstrap seed 7, shift-null seed 42, 500 shifts, min_shift 260;
lookbacks 21/63/252; vol_lookback 63, target 0.10, cap 4.0):

- ES bars loaded: 4137.
- Variants produced: `21/raw, 21/scaled, 63/raw, 63/scaled, 252/raw,
  252/scaled, vote/raw, vote/scaled` (8 rows, as designed).
- ES **vote/scaled**: n = 3879, mean daily x = **+0.000074**,
  95% CI **[−0.000134, +0.000276]**, p_shift = **0.946**.

The CI straddles 0 and p_shift ≈ 0.95 — but again, this is a single-market
plumbing print, not evidence for or against Program T. It is recorded only
to show the code path is sound and the ES data feeds it cleanly.

### House tripwire (Sharpe > 1.5)

No portfolio Sharpe was computed (portfolio needs all five markets). The
only number produced — ES vote/scaled with a mean of +0.000074 and a CI
that includes 0 — implies **no** Sharpe anywhere near the 1.5 tripwire.
**No tripwire condition is present** in anything that ran. (A full-battery
Sharpe assessment is pending the blocked data.)

## 5. Anomalies

1. **Databento fetch fully blocked** (§3.2) — no credentials, no client
   library, no GLBX path in the repo fetcher. This is the blocking
   anomaly. Not patched.
2. **ES bar count 4137 vs ~4,030 guide** (§3.1) — +2.6%, explained by the
   inclusive 2010-06-07 → 2026-07-01 span and the round estimate; range
   and 20-day recon are exact. Observation, not patched.
3. **ES boundary hygiene** (§3.1) — two weekend-labeled Sunday pre-open
   prints and one out-of-window 2026-07-02 stub dropped during
   *construction* of the daily bars (documented in the builder); six thin
   half-sessions kept. These are session-definition decisions in building
   the series, not adjustments to any result.
4. **Unverified ohlcv-1d timestamp convention** (§3.2) — cannot be checked
   until a real export exists; to report after first fetch, not patch.

## 6. Observations / Proposals

**Observations (facts):**
- The ES daily resample reconciles exactly with the 15m extremes on 20
  random days — the "reuse the adjusted series, don't re-stitch" path is
  clean and the midnight-UTC-of-settlement `ts` convention is in place for
  the portfolio join.
- The frozen Stage-1 library runs end-to-end on the real ES daily file and
  emits the full variant grid; the plumbing is not in doubt.
- All non-fetch, non-holdout work in the task is complete or staged: ES
  built + verified; stitch generalized and staged; runner written; results
  JSON path wired.

**Proposals (for the architect to decide):**
- Provide one of: (a) a Databento API key + explicit spend authorization
  (task budget guard: single-digit dollars expected; STOP if a quote
  exceeds $25 total), so I can fetch CL/GC/ZN/6E ohlcv-1d and run the
  stitch + battery; or (b) pre-downloaded ohlcv-1d `.csv.zst` exports for
  CL/GC/ZN/6E (parent symbology, all expiries, 2010-06-06 → 2026-07-01)
  dropped into `data/`, which the staged `_t01_stitch.py` consumes as-is.
- If credentials arrive, confirm whether `databento` should be added to
  the `fetch` extra (a `src/` change, hence the architect's, not mine) or
  whether the export will be produced out-of-band and only the `.csv.zst`
  handed over.

## 7. Questions blocking the next iteration

**Blocking question (single, decisive):** The Stage-1 dev battery requires
fresh Databento GLBX **daily (ohlcv-1d)** OHLCV for **CL, GC, ZN, 6E**
(parent symbology, all expiries — needed for the volume roll). This
environment has no Databento credentials, no `databento` client library,
and the repo's only fetcher is Binance-only, so the fetch — and therefore
the four continuous builds, the five-market portfolio, and every
support-rule number — cannot be produced.

To unblock, please provide **either**:
1. a Databento API key **and** explicit spend authorization (budget guard:
   single-digit dollars expected; I will STOP and report before buying if
   any quote exceeds **$25 total**), **or**
2. pre-downloaded ohlcv-1d `.csv.zst` exports for CL/GC/ZN/6E (parent
   symbology, all expiries, window 2010-06-06 → 2026-07-01) placed under
   `data/`.

On receipt I will: run `_t01_stitch.py` for each of the four products
(recording rows, range, roll count, per-boundary residual, OHLC
violations, dupes, min/max, non-positive-adjusted flag, last-segment
offset == 0, sha256s), verify the ohlcv-1d timestamp convention against
the ES midnight-UTC-of-settlement convention (anomaly to report, not
patch, if it differs), run `_t01_runner.py` over the three windows, save
`reports/dev/_t01_results.json`, and complete this report with the
portfolio + per-instrument support-rule arithmetic and the tripwire check.

---

### Determinism anchors

| anchor | value |
|---|---|
| commit | `70fac68169edba33ff178748de4652b8a2502ef9` |
| branch | `claude/t-iter01` |
| ES source | `data/es_15m.parquet`, sha256 `a3fc183db2a464410d54b9ce6fab442cacbf1ac390a99515a23efc1b38cdd478` |
| ES daily out | `data/es_1d.parquet`, sha256 `6527324697558f1c08851a2a4a18a86c86c4139113b1dadbb975a1fbb4488d2b` |
| ES rows / range | 4137 / 2010-06-07 → 2026-07-01 |
| CL/GC/ZN/6E | **not fetched** — Databento job/file identifiers + sha256s N/A (blocked) |
| Databento job IDs | none (no fetch performed) |
| seeds (library defaults) | bootstrap 7, shift-null 42, 500 shifts, min_shift 260 |
| ES daily builder | `reports/dev/_es_daily_resample.py` |
| stitch (staged, unrun) | `reports/dev/_t01_stitch.py` |
| runner (written, unrun full) | `reports/dev/_t01_runner.py` |
| plumbing smoke invocation | frozen library on `data/es_1d.parquet`, ES-only, full window |
| wall-clock | ES resample + ES-only plumbing test ≈ 30 s |
| data cost | **$0.00** (no purchase) |
| holdout contact | none (HG/ZF/6J/ZC/NQ/crypto untouched) |
