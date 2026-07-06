"""Program T, Iter 01 — Stage-1 battery runner (thin; frozen library only).

Calls only the preregistered analytics (analytics.trend_study via the
public re-exports).  No parameter changes, no engine backtests.  Three
windows per the task table; raw rows dumped to _t01_results.json.

`load_candles` slices [lo, hi) with hi = timestamp(end) EXCLUSIVE, so the
clean temporal split (halves A = <=2018-06-30, B = >2018-06-30) is:
  half A -> end="2018-07-01"  (includes the 2018-06-30 session)
  half B -> start="2018-07-01"

Requires all five data/<sym>_1d.parquet.  ES is present; CL/GC/ZN/6E are
blocked on the Databento fetch (see reports/dev/T_ITER01.md), so the full
five-market battery cannot run yet.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ict_backtest.data import load_candles
from ict_backtest.analytics import portfolio_rows, render_trend_battery, tsmom_rows

SYMS = ["es", "cl", "gc", "zn", "6e"]
WINDOWS = [
    ("T dev full", None, None),
    ("T dev half A", None, "2018-07-01"),
    ("T dev half B", "2018-07-01", None),
]


def battery(start=None, end=None, label=""):
    instruments = {s.upper(): load_candles(f"data/{s}_1d.parquet", start=start, end=end)
                   for s in SYMS}
    per = {name: tsmom_rows(c) for name, c in instruments.items()}
    port = portfolio_rows(instruments)
    print(render_trend_battery(per, port, label))
    print()
    return per, port


def main() -> None:
    t0 = time.time()
    results = {}
    for label, start, end in WINDOWS:
        per, port = battery(start, end, label)
        results[label] = {
            "start": start, "end": end,
            "portfolio": port,
            "per_instrument": per,
            "live_days": {name: rows[0]["n"] if rows else None
                          for name, rows in per.items()},
            "portfolio_live_days": port[0]["n"] if port else None,
        }
    Path("reports/dev/_t01_results.json").write_text(json.dumps(results, indent=2))
    print(f"[wall-clock {time.time() - t0:.1f}s] wrote reports/dev/_t01_results.json")


if __name__ == "__main__":
    main()
