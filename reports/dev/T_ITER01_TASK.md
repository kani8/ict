# Executor task — Program T, Iteration 01 (Stage-1 signal battery, dev markets)

Architect tasking, 2026-07-06. Governing: `reports/PREREGISTRATION_T.md`
(binding), `docs/EXECUTOR_BRIEF.md` (standing). One iteration = one
report = `reports/dev/T_ITER01.md`.

## Scope

Stage-1 battery on the five development markets. **No engine
backtests** (that is T-02, after adjudication), no parameter changes,
no holdout contact: HG/ZF/6J/ZC are NOT fetched; NQ stays sealed.

## Preflight

Fresh clone at the tasked commit; `uv sync --extra dev --extra fetch`;
`uv run pytest -q` must pass **150/150**; `uv run ruff check src tests`
clean. Else stop and report.

## Data — five GLBX daily continuous series

Window 2010-06-06 → 2026-07-01. Instruments: **ES** (reuse the existing
adjusted series — derive daily bars by resampling `data/es_15m.parquet`
to 1d buckets aligned to the CME trading day; do NOT re-stitch), and
fresh Databento GLBX **daily** OHLCV for full products **CL, GC, ZN,
6E** (parent symbology, all expiries — needed for the volume roll).
Budget guard: daily data for four products should cost single-digit
dollars; if a quote exceeds $25 total, stop and report before buying.

Build each continuous series with the ES recipe at daily resolution:
volume-based roll on instrument_id membership (crossover day d →
effective next trading day), Panama/additive back-adjustment, newest
segment offset 0. For each instrument record: rows, date range, roll
count, per-boundary residual check, OHLC violations, dupes, min/max
price (flag adjusted prices ≤ 0 — additive caveat), and the
front-vs-continuous spot check on the last segment (offset must be 0).
Write `data/<sym>_1d.parquet` + a stitch-meta JSON with sha256s.

ES daily resample sanity: bar count ≈ trading days (~4,030), daily
OHLC must reconcile with 15m extremes on 20 random days (exact match).

## Runs

Thin runner (`reports/dev/_t01_runner.py`) calling the frozen library
only:

```python
from ict_backtest.data import load_candles
from ict_backtest.analytics import portfolio_rows, render_trend_battery, tsmom_rows

SYMS = ["es", "cl", "gc", "zn", "6e"]

def battery(start=None, end=None, label=""):
    instruments = {s.upper(): load_candles(f"data/{s}_1d.parquet", start=start, end=end)
                   for s in SYMS}
    per = {name: tsmom_rows(c) for name, c in instruments.items()}
    port = portfolio_rows(instruments)
    print(render_trend_battery(per, port, label))
    return per, port
```

Three windows, rendered verbatim into the report:

| label | window (UTC) |
|---|---|
| T dev full | all |
| T dev half A | → 2018-06-30 |
| T dev half B | 2018-07-01 → |

Note: in the halves, warmup consumes the first max-lookback+vol window
of each slice (the library re-warms on the slice); state the live day
counts per window. Save raw rows as `reports/dev/_t01_results.json`.

## Report format

Standard format, plus in Results the support-rule arithmetic only (no
adjudication):

- Portfolio (vote, vol-scaled): full CI + p_shift, half-A CI, half-B CI.
- Per-instrument (vote, vol-scaled) one line each: mean, CI, p_shift.
- State explicitly whether any number implies portfolio Sharpe > 1.5
  (house tripwire: too good = suspected defect, stop and flag).

## Determinism anchors

Commit hash, Databento job/file identifiers + sha256s, per-instrument
row counts/ranges/roll counts, seeds (library defaults: bootstrap 7,
shift-null 42, 500 shifts), invocations, wall-clock, data cost in $.

## Hard reminders

Write only under `reports/dev/` and `data/`. No holdout contact
(HG/ZF/6J/ZC/NQ/crypto). Anomalies reported, not patched. Finish, push,
stop; blocking questions at the end of the report.
