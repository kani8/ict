# M1 Results — Liquidity Magnetism (measurement program M, task M-01)

- **Role**: executor. This report records what the tested library produced at
  preregistered defaults. No study logic was re-implemented; no parameters were
  changed. Verdicts below apply the M1 reading rule verbatim.
- **Commit**: `69f8988` — "Open measurement program M; ship tested M1
  liquidity-magnetism study" (2026-07-03 05:04:00 +0000). HEAD == M-01 target.
- **Verification gate** (already passed this task): `117/117` tests pass; `ruff`
  clean.
- **Config note**: M1 is a pure event study on candles. It does **not** consume
  `configs/v3_origin.toml` (that config governs the concluded trading engine, not
  this descriptive study). The replays in step 2 were rendered with
  `v3_origin.toml`; M1 itself takes only candles + library defaults.
- **Data**: burned/in-sample only (BTC/ETH 2023–2026, ES 2010–2026). No sealed
  holdout was loaded or touched.

## Exact invocation

Driver: `reports/dev/_m1_runner.py` (thin wrapper — loads each dataset via
`ict_backtest.data.loader.load_candles`, then calls the tested library):

```python
from ict_backtest.analytics.magnetism import run_magnetism, render_magnetism_table
rows = run_magnetism(candles)              # all preregistered defaults
render_magnetism_table(rows, label)
```

Library defaults used for every dataset (no overrides):
`swing_k=3, eq_tol_atr=0.25, atr_period=14, horizons=(96, 384),`
`buckets=((0.5,1.0),(1.0,2.0),(2.0,4.0)), baseline_k=20, seed=42`.
Bootstrap CI is the library's own `_ratio_block_ci` (n_boot=4000, internal
seed=7, block size `b = round(n**(1/3))`, raw 2.5/97.5 percentiles).

For ES the run at `swing_k=3` **is** the default run (swing_k=3 is the library
default), so no second ES run was needed; per the task, per-bucket raw event
counts are reported below so thin cells are visible.

## Data integrity (re-verified on the exact ingestion path M1 consumes)

`reports/dev/_m1_integrity.py` → `load_candles(...)`; all three match prior
numbers exactly.

| dataset | n_rows | first_ts (UTC) | last_ts (UTC) | step | dups | backsteps | OHLC violations | min_low / max_high |
|---|---|---|---|---|---|---|---|---|
| btcusdt_15m | 122,588 | 2023-01-01T00:00:00Z | 2026-07-01T00:00:00Z | 900s | 0 | 0 | 0 | 16499.01 / 126199.63 |
| ethusdt_15m | 122,588 | 2023-01-01T00:00:00Z | 2026-07-01T00:00:00Z | 900s | 0 | 0 | 0 | 1190.57 / 4956.78 |
| es_15m (adj) | 376,768 | 2010-06-06T22:00:00Z | 2026-07-01T23:45:00Z | 900s | 0 | 0 | 0 | 1600.25 / 7697.0 |

OHLC-validity columns checked: `high < max(open,close)`, `low > min(open,close)`,
`high < low`, non-positive OHLC — all zero.

## The reading rule (as predeclared in `reports/PREREGISTRATION_M.md`)

- A cell **supports magnetism** only if its ratio CI **excludes 1.0 upward**
  (`ci_lo > 1.0`).
- "Magnetism is real" requires supported cells in **≥2 of 3 datasets** for the
  **same** bucket/horizon.
- All cells are reported, including nulls.

## Tables

**BTCUSDT 15m (2023-2026)** — pool touch rate vs ATR-matched unconditional move rate

| distance (ATR) | horizon | n | touch | baseline | ratio | 95% CI |
|---|---|---|---|---|---|---|
| 0.5-1.0 | 96 | 5380 | 0.903 | 0.907 | 1.00 | [0.99, 1.01] |
| 0.5-1.0 | 384 | 5364 | 0.949 | 0.955 | 0.99 | [0.99, 1.00] |
| 1.0-2.0 | 96 | 11039 | 0.818 | 0.824 | 0.99 | [0.98, 1.00] |
| 1.0-2.0 | 384 | 11015 | 0.916 | 0.913 | 1.00 | [1.00, 1.01] |
| 2.0-4.0 | 96 | 5107 | 0.683 | 0.696 | 0.98 | [0.96, 1.00] |
| 2.0-4.0 | 384 | 5094 | 0.832 | 0.847 | 0.98 | [0.97, 1.00] |

**ETHUSDT 15m (2023-2026)** — pool touch rate vs ATR-matched unconditional move rate

| distance (ATR) | horizon | n | touch | baseline | ratio | 95% CI |
|---|---|---|---|---|---|---|
| 0.5-1.0 | 96 | 5784 | 0.901 | 0.904 | 1.00 | [0.99, 1.01] |
| 0.5-1.0 | 384 | 5768 | 0.952 | 0.952 | 1.00 | [0.99, 1.01] |
| 1.0-2.0 | 96 | 11300 | 0.816 | 0.822 | 0.99 | [0.98, 1.00] |
| 1.0-2.0 | 384 | 11269 | 0.909 | 0.912 | 1.00 | [0.99, 1.01] |
| 2.0-4.0 | 96 | 4870 | 0.676 | 0.696 | 0.97 | [0.95, 0.99] |
| 2.0-4.0 | 384 | 4859 | 0.836 | 0.847 | 0.99 | [0.97, 1.00] |

**ES 15m adj (2010-2026)** — pool touch rate vs ATR-matched unconditional move rate

| distance (ATR) | horizon | n | touch | baseline | ratio | 95% CI |
|---|---|---|---|---|---|---|
| 0.5-1.0 | 96 | 18034 | 0.908 | 0.913 | 0.99 | [0.99, 1.00] |
| 0.5-1.0 | 384 | 18020 | 0.955 | 0.959 | 1.00 | [0.99, 1.00] |
| 1.0-2.0 | 96 | 31046 | 0.831 | 0.834 | 1.00 | [0.99, 1.00] |
| 1.0-2.0 | 384 | 31016 | 0.917 | 0.920 | 1.00 | [0.99, 1.00] |
| 2.0-4.0 | 96 | 15534 | 0.683 | 0.703 | 0.97 | [0.96, 0.98] |
| 2.0-4.0 | 384 | 15526 | 0.840 | 0.854 | 0.98 | [0.98, 0.99] |

### Exact CI bounds (4 dp — the tables above round to 2 dp)

The 2-dp render can look like `[1.00, 1.01]`; the raw values decide the rule.
`SUP-UP` = `ci_lo > 1.0`; `EXCL-DOWN` = `ci_hi < 1.0`.

| dataset | bucket | horizon | n | ratio | ci_lo | ci_hi | flag |
|---|---|---|---|---|---|---|---|
| BTC | 0.5-1.0 | 96 | 5380 | 0.9956 | 0.9852 | 1.0058 | — |
| BTC | 0.5-1.0 | 384 | 5364 | 0.9938 | 0.9865 | 1.0007 | — |
| BTC | 1.0-2.0 | 96 | 11039 | 0.9929 | 0.9831 | 1.0027 | — |
| BTC | 1.0-2.0 | 384 | 11015 | 1.0031 | 0.9951 | 1.0108 | — |
| BTC | 2.0-4.0 | 96 | 5107 | 0.9812 | 0.9634 | 0.9998 | EXCL-DOWN |
| BTC | 2.0-4.0 | 384 | 5094 | 0.9829 | 0.9694 | 0.9969 | EXCL-DOWN |
| ETH | 0.5-1.0 | 96 | 5784 | 0.9974 | 0.9881 | 1.0066 | — |
| ETH | 0.5-1.0 | 384 | 5768 | 1.0004 | 0.9933 | 1.0080 | — |
| ETH | 1.0-2.0 | 96 | 11300 | 0.9931 | 0.9832 | 1.0030 | — |
| ETH | 1.0-2.0 | 384 | 11269 | 0.9973 | 0.9888 | 1.0057 | — |
| ETH | 2.0-4.0 | 96 | 4870 | 0.9701 | 0.9509 | 0.9896 | EXCL-DOWN |
| ETH | 2.0-4.0 | 384 | 4859 | 0.9872 | 0.9738 | 1.0002 | — |
| ES | 0.5-1.0 | 96 | 18034 | 0.9938 | 0.9884 | 0.9989 | EXCL-DOWN |
| ES | 0.5-1.0 | 384 | 18020 | 0.9960 | 0.9924 | 0.9997 | EXCL-DOWN |
| ES | 1.0-2.0 | 96 | 31046 | 0.9961 | 0.9900 | 1.0019 | — |
| ES | 1.0-2.0 | 384 | 31016 | 0.9970 | 0.9924 | 1.0014 | — |
| ES | 2.0-4.0 | 96 | 15534 | 0.9715 | 0.9603 | 0.9826 | EXCL-DOWN |
| ES | 2.0-4.0 | 384 | 15526 | 0.9841 | 0.9759 | 0.9921 | EXCL-DOWN |

### ES per-bucket raw event counts (swing_k=3, unfiltered by horizon)

Confirms cells are well-populated — no thin cells on ES.

| bucket | events |
|---|---|
| 0.5-1.0 | 18,037 |
| 1.0-2.0 | 31,052 |
| 2.0-4.0 | 15,538 |
| (below 0.5 ATR — outside all buckets) | 6,597 |
| (≥4.0 ATR — outside all buckets) | 1,183 |
| **total confirmed pool events** | **72,407** |

(The bucketed `n` in the tables is slightly below these totals because
`run_magnetism` drops the last-N-bar events per horizon and any baseline-NaN
events. BTC/ETH bucketed `n` shows the same populated pattern — smallest cell is
BTC/ETH 2.0-4.0 ≈ 4.9–5.1k. No cell is thin on any dataset.)

## Reading-rule verdict

- **Cells with `ci_lo > 1.0` (support magnetism): none.** Zero of 18 cells across
  the three datasets. The single cell that renders as `[1.00, 1.01]` (BTC
  1.0-2.0/384) has exact `ci_lo = 0.9951` — it does **not** exclude 1.0 upward.
- **Any bucket/horizon supported on ≥2 of 3 datasets: no.** With zero supported
  cells anywhere, the cross-dataset agreement condition is vacuously unmet.
- **Plain statement**: at these preregistered parameters, on burned data, the M1
  study provides **no support for liquidity magnetism**. Confirmed pools are
  reached at essentially the same rate as ATR-matched unconditional moves in the
  same direction (all ratios within ≈3% of 1.0).

## Anomalies / notable observations (descriptive only)

1. **Replicated mild anti-magnetism at far distance.** The 2.0-4.0 ATR bucket
   excludes 1.0 **downward** (ratio < 1) at horizon 96 on **all three** datasets
   (BTC [0.963, 1.000], ETH [0.951, 0.990], ES [0.960, 0.983]) and at horizon 384
   on BTC and ES (ETH 384 is borderline, [0.974, 1.000]). Direction is
   consistent: distant confirmed pools are reached *slightly less* often than
   ATR-matched random moves. Effect size is small (~2–3%); CIs are tight only
   because n is large (5k–16k per cell). This is the *opposite* of the ICT claim,
   not weak support for it. I am flagging it as an observation for the architect;
   I am **not** proposing it as a signal.
2. **ES 0.5-1.0 also excludes downward** at both horizons, but by a hair
   (ratios 0.994 / 0.996) — plausibly just large-n precision around a true null.
3. **Monotone-in-distance pattern.** Across every dataset, ratio drifts from
   ≈1.00 in the nearest bucket to ≈0.97–0.98 in the farthest, at both horizons.
   Consistent shape; consistent sign (mild negative). Recorded, not interpreted.

## Replays (task M-01 step 2 — committed under `reports/replays/`)

Rendered with `configs/v3_origin.toml` via `ict-backtest viz`.

| file | window | bytes | MiB |
|---|---|---|---|
| `btcusdt_replay.html` | last 20,000 bars | 2,652,518 | 2.53 |
| `ethusdt_replay.html` | last 20,000 bars | 2,518,590 | 2.40 |
| `es_replay.html` | last 20,000 bars | 2,482,807 | 2.37 |
| `es_covid_replay.html` | 2020-02-01 → 2020-06-01, --max-bars 0 (full window) | 943,694 | 0.90 |

**Spot-check**: all four opened in a headless browser (Playwright over a local
`http.server`; `file://` is blocked by the browser). Each loaded with the correct
page title and rendered without console errors — the only console entry was a
benign `favicon.ico` 404, which is not a render error.

## Observations vs Proposals

- **Observations** (what the data shows, no action implied): (a) no cell supports
  magnetism on any dataset; (b) a small, replicated *negative* deviation at
  2.0-4.0 ATR / h=96 across all three datasets; (c) ratios are monotone-decreasing
  in distance. All are on burned/in-sample data.
- **Proposals**: none. Per executor discipline I am not proposing M2/M3 designs,
  parameter changes, or any strategy inference. Designing the next study is the
  architect's call.

## Blocking questions for the architect

1. **Bonferroni vs the literal reading rule.** The preregistration's Rules say
   "Bonferroni across cells within a study," but the shipped library
   `_ratio_block_ci` emits a raw 95% CI with no widening parameter. I applied the
   **raw** CI exactly as the tested code produces it (the reading rule is written
   in terms of `ci_lo > 1.0` on that CI). This does not change today's verdict —
   zero cells clear even the *raw* upward bar, so Bonferroni widening could only
   keep the count at zero. Flagging so the rule/library tension is resolved
   explicitly before any study where a cell *does* clear the raw bar. **Do not
   want me to modify library code to add a correction; confirm.**
2. **Interpretation authority for the replicated downward exclusion.** The
   2.0-4.0/h=96 negative effect replicates on 3/3. The reading rule only defines
   *upward* support; it is silent on downward exclusion. Is the intended reading
   simply "not magnetism" (my current stance), or do you want a symmetric
   pre-declared rule for anti-magnetism before M2? I am not treating it as a
   finding beyond "recorded observation" without your instruction.
3. **Write-boundary confirmation.** M-01 authorized committing four HTMLs under
   `reports/replays/`; the standing executor rule restricts my writes to
   `reports/dev/` and `data/`. I followed the task and committed under
   `reports/replays/`. Confirm this was intended (it is the only write I made
   outside `reports/dev/`).

---
*Scratch artifacts under `reports/dev/` for this task: `_m1_runner.py`,
`_m1_results.json`, `_m1_stdout.log`, `_m1_integrity.py`, `_m1_integrity.log`.*
