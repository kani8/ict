"""Program S, Iteration 01 — Stage-1 descriptive battery on burned ES 15m.

Thin runner: calls the FROZEN library only (``run_session_battery`` /
``render_session_battery``); no re-implementation of any statistic.  The
sole extra computation is the count of RTH candidate days per window, so
that "sessions dropped as incomplete" can be reported — it reuses the
exact helper and RTH bounds (``et_minutes_days``; minute in [570, 960))
that ``session_study.session_table`` uses to decide session completeness.

Windows (task S_ITER01):
  ES full                 all
  ES half A               ->  2018-06-30 23:59  (sessions <= 2018-06-30)
  ES half B               2018-07-01 00:00 ->   (sessions >  2018-06-30)
  ES 2021+ (descriptive)  2021-01-01 00:00 ->

Run from repo root:  uv run python reports/dev/_s01_runner.py
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ict_backtest.analytics import render_session_battery, run_session_battery
from ict_backtest.data import load_candles
from ict_backtest.detectors.killzones import RTH_OPEN, et_minutes_days

ROOT = Path(__file__).resolve().parents[2]
DATA = str(ROOT / "data/es_15m.parquet")
CAL = str(ROOT / "data/calendars/high_impact_2010_2026.csv")
TZ = "America/New_York"
RTH_END_MIN = 960  # session_table's hardcoded RTH close-minute bound

WINDOWS = [
    ("ES full", None, None),
    ("ES half A", None, "2018-06-30 23:59"),
    ("ES half B", "2018-07-01 00:00", None),
    ("ES 2021+ (descriptive)", "2021-01-01 00:00", None),
]


def candidate_rth_days(ts: np.ndarray) -> int:
    """# distinct ET days with >=1 RTH bar — the denominator session_table
    iterates before dropping incomplete sessions."""
    minute, day = et_minutes_days(ts, TZ)
    rth = (minute >= RTH_OPEN) & (minute < RTH_END_MIN)
    return int(len(pd.unique(day[rth])))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True).stdout.strip()


def _sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    t0 = time.time()
    cal = pd.read_csv(CAL)
    fomc_dt = pd.to_datetime(cal.loc[cal["event"] == "FOMC", "datetime"], utc=True)

    # --- FOMC timestamp unit: DEVIATION FROM TASK SNIPPET (documented) -------
    # The tasked snippet uses ``.astype("int64") // 10**9`` which assumes
    # nanosecond datetime resolution.  On this environment pandas parses the
    # calendar's ISO strings to ``datetime64[us]`` (microsecond) resolution,
    # so that division yields ~1.28e6 (mid-Jan-1970) instead of ~1.28e9 epoch
    # seconds -> every FOMC day-code becomes 1970 -> ``fomc_rows`` matches ZERO
    # sessions -> S3 reports n=0/NaN in every window.  ``et_minutes_days`` and
    # ``candles.ts`` are both epoch SECONDS, so seconds is the intended unit.
    # We convert unit-agnostically via Timestamp.timestamp() (always seconds).
    # The as-tasked path is recorded below as anomaly evidence, not used.
    fomc_ts = np.array([int(x.timestamp()) for x in fomc_dt], dtype=np.int64)
    fomc_ts_astasked = (fomc_dt.astype("int64") // 10**9).to_numpy()
    from ict_backtest.detectors.killzones import et_minutes_days as _emd
    _, day_robust = _emd(fomc_ts, TZ)
    _, day_astasked = _emd(fomc_ts_astasked.astype(np.int64), TZ)

    out: dict = {
        "commit": _git("rev-parse", "HEAD"),
        "data_file": "data/es_15m.parquet",
        "data_sha256": _sha256(DATA),
        "calendar_file": "data/calendars/high_impact_2010_2026.csv",
        "calendar_sha256": _sha256(CAL),
        "n_fomc_events": int(len(fomc_ts)),
        "seeds": {"block_bootstrap_ci": 7, "ibs_spread": 7},
        "tz": TZ,
        "fomc_ts_deviation": {
            "reason": "task snippet //10**9 assumes ns resolution; pandas "
                      "parsed calendar as datetime64[us] -> 1970 day-codes -> "
                      "S3 n=0. Corrected to int(Timestamp.timestamp()) seconds.",
            "parsed_dtype": str(fomc_dt.dtype),
            "ev_day_astasked_first5": [int(x) for x in day_astasked[:5]],
            "ev_day_robust_first5": [int(x) for x in day_robust[:5]],
        },
        "batteries": {},
    }

    for name, start, end in WINDOWS:
        c = load_candles(DATA, start=start, end=end)
        res = run_session_battery(c, fomc_ts=fomc_ts)
        cand = candidate_rth_days(c.ts)
        res["_meta"] = {
            "window_start": start,
            "window_end": end,
            "n_candles": int(len(c.ts)),
            "first_ts": pd.Timestamp(int(c.ts[0]), unit="s", tz="UTC")
                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_ts": pd.Timestamp(int(c.ts[-1]), unit="s", tz="UTC")
                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "n_candidate_rth_days": cand,
            "n_sessions": int(res["n_sessions"]),
            "n_dropped_incomplete": cand - int(res["n_sessions"]),
        }
        print(render_session_battery(res, name))
        print(f"    [meta] candles={res['_meta']['n_candles']:,}  "
              f"range {res['_meta']['first_ts']} -> {res['_meta']['last_ts']}  "
              f"candidate_rth_days={cand}  n_sessions={res['n_sessions']}  "
              f"dropped_incomplete={res['_meta']['n_dropped_incomplete']}\n")
        out["batteries"][name] = res

    out["wall_clock_s"] = round(time.time() - t0, 2)
    (ROOT / "reports/dev/_s01_results.json").write_text(
        json.dumps(out, indent=2, allow_nan=True))
    print(f"wrote reports/dev/_s01_results.json  (wall-clock {out['wall_clock_s']}s)")


if __name__ == "__main__":
    main()
