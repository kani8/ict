"""Program S, Iteration 01 — diagnostic for the dropped-incomplete session
count (§5a) and the S3 FOMC timestamp-unit anomaly (§5b).

Read-only; imports the FROZEN library. Not part of the battery — it only
explains why sessions are dropped and why the tasked FOMC snippet fails.

Run from repo root:  uv run python reports/dev/_s01_diag.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ict_backtest.analytics.session_study import _REQUIRED, session_table
from ict_backtest.data import load_candles
from ict_backtest.detectors.killzones import RTH_OPEN, et_minutes_days

TZ = "America/New_York"


def drop_characterization() -> None:
    c = load_candles("data/es_15m.parquet")
    minute, day = et_minutes_days(c.ts, TZ)
    rth = (minute >= RTH_OPEN) & (minute < 960)
    cand = pd.unique(day[rth])
    kept = set(session_table(c)["day"].tolist())
    dropped = [int(d) for d in cand if int(d) not in kept]
    print(f"candidate_rth_days={len(cand)} kept={len(kept)} dropped={len(dropped)}")
    print(f"REQUIRED anchors (ET min): {_REQUIRED}")

    buckets = {"no_open_0930": 0, "early_close(<13:45)": 0,
               "partial_late(missing 15:15-15:45)": 0,
               "mid_session_gap": 0, "other": 0}
    for d in dropped:
        sel = np.flatnonzero((day == d) & rth)
        mins = {int(x) for x in minute[sel]}
        missing = [m for m in _REQUIRED if m not in mins]
        if 570 not in mins:
            b = "no_open_0930"
        elif max(mins) < 825:
            b = "early_close(<13:45)"
        elif any(m in missing for m in (915, 930, 945)) and 825 in mins:
            b = "partial_late(missing 15:15-15:45)"
        elif missing:
            b = "mid_session_gap"
        else:
            b = "other"
        buckets[b] += 1
    for b, n in buckets.items():
        print(f"  {b:38s}: {n}")
    yr = pd.Series([d // 10000 for d in dropped]).value_counts().sort_index()
    print("drops per year:")
    print(yr.to_string())


def fomc_unit_check() -> None:
    cal = pd.read_csv("data/calendars/high_impact_2010_2026.csv")
    dt = pd.to_datetime(cal.loc[cal["event"] == "FOMC", "datetime"], utc=True)
    astasked = (dt.astype("int64") // 10**9).to_numpy()
    robust = np.array([int(x.timestamp()) for x in dt], dtype=np.int64)
    _, d_bad = et_minutes_days(astasked.astype(np.int64), TZ)
    _, d_ok = et_minutes_days(robust, TZ)
    print(f"\nparsed dtype: {dt.dtype}")
    print(f"as-tasked //10**9 ev_day[:5]: {d_bad[:5].tolist()}  (1970 -> 0 matches)")
    print(f"robust timestamp() ev_day[:5]: {d_ok[:5].tolist()}  (correct)")


if __name__ == "__main__":
    drop_characterization()
    fomc_unit_check()
