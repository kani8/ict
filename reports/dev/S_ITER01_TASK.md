# Executor task — Program S, Iteration 01 (Stage-1 battery on burned ES)

Architect tasking, 2026-07-06. Governing documents:
`reports/PREREGISTRATION_S.md` (binding), `docs/EXECUTOR_BRIEF.md`
(standing rules). One iteration = one report = `reports/dev/S_ITER01.md`.

## Scope

Stage-1 descriptive battery only. **No strategy backtests** (that is
S-02, after adjudication), **no parameter exploration, no holdout
contact of any kind — NQ is not fetched in this iteration.**

## Preflight

1. Fresh clone at the tasked commit; `uv sync --extra dev --extra fetch`.
2. `uv run pytest -q` must pass **138/138**; `uv run ruff check src
   tests` must be clean. If not: stop and report.

## Data

Rebuild the burned ES development set exactly as in
`reports/dev/V3_ITER04.md` §1 (same GLBX source file, sha256
`e9ebda22332f27ed31a360bc9d8c8f6dba18f6bec916702ed3bab624b8691000`,
same stitch/roll scripts, same integrity gates):

- `data/es_15m.parquet` — expect 376,768 rows, 2010-06-06T22:00Z →
  2026-07-01T23:45Z, 0 dupes, 0 OHLC violations, 65/65 roll continuity.
- The 1m file is not needed for Stage 1 (no execution in this
  iteration); do not rebuild it.

Report the §-1a-style integrity table. Any gate failure stops the run.

## Runs

Thin runner only (e.g. `reports/dev/_s01_runner.py`), calling the frozen
library — no re-implementation:

```python
import numpy as np, pandas as pd
from ict_backtest.data import load_candles
from ict_backtest.analytics import run_session_battery, render_session_battery

cal = pd.read_csv("data/calendars/high_impact_2010_2026.csv")
fomc_ts = (pd.to_datetime(cal.loc[cal["event"] == "FOMC", "datetime"], utc=True)
           .astype("int64") // 10**9).to_numpy()

candles = load_candles("data/es_15m.parquet")

def run(name, start=None, end=None):
    c = load_candles("data/es_15m.parquet", start=start, end=end)
    res = run_session_battery(c, fomc_ts=fomc_ts)
    print(render_session_battery(res, name))
    return res
```

Four batteries, rendered verbatim into the report:

| name | window (UTC) |
|---|---|
| ES full | all |
| ES half A | → 2018-06-30 23:59 |
| ES half B | 2018-07-01 00:00 → |
| ES 2021+ (descriptive) | 2021-01-01 00:00 → |

Also record per battery: `n_sessions`, and the count of sessions
dropped as incomplete (full-sample sanity: expect roughly 12 early
closes plus a handful of halts over 16y; a large number means a session
-detection problem — stop and report).

Save raw results as JSON next to the runner
(`reports/dev/_s01_results.json`).

## Report format

Standard iteration format (brief §"Report format") plus, in Results,
one line per preregistered support rule stating only the *arithmetic*
outcome (CI bounds vs 0; no adjudication — the ruling is the
architect's):

- S1 primary (rod/all): full CI, half-A CI, half-B CI.
- S2 (all): same three CIs.
- S3: FOMC CI + other-days mean.
- S4 (q1_minus_q5): same three CIs.

## Determinism anchors

Record: commit hash, exact invocations, data row counts/ranges, calendar
sha256, seeds (library defaults; `block_bootstrap_ci` seed=7,
`ibs_rows` spread seed=7), wall-clock.

## Hard reminders

- Write only under `reports/dev/` and `data/`.
- No holdouts: NQ, BNBUSDT, ETHUSDT 2019-22, SOLUSDT, BTCUSDT 2019-22
  all stay untouched.
- Anomalies (including too-good results) are reported, not patched.
- Finish, push, stop. Blocking questions go at the end of the report.
