"""M-01 integrity re-check on the exact ingestion path M1 consumes.

Loads each burned 15m dataset via the library's load_candles (same code
path run_magnetism will see) and prints row count, date range, duplicate
/ monotonicity checks, and OHLC-validity counts. Read-only; burned data
only (BTC/ETH 2023-2026, ES 2010-2026). No holdouts touched.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from ict_backtest.data.loader import load_candles

FILES = {
    "btcusdt_15m": "data/btcusdt_15m.parquet",
    "ethusdt_15m": "data/ethusdt_15m.parquet",
    "es_15m": "data/es_15m.parquet",
}


def _iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check(name: str, path: str) -> None:
    c = load_candles(path)
    n = len(c)
    ts = np.asarray(c.ts, dtype=np.int64)
    o, h, l, cl = (np.asarray(c.open), np.asarray(c.high),
                   np.asarray(c.low), np.asarray(c.close))
    diffs = np.diff(ts)
    n_dup = int((diffs == 0).sum())
    n_back = int((diffs < 0).sum())
    step = int(np.median(diffs)) if n > 1 else 0
    n_high_lt_maxoc = int((h < np.maximum(o, cl)).sum())
    n_low_gt_minoc = int((l > np.minimum(o, cl)).sum())
    n_high_lt_low = int((h < l).sum())
    n_nonpos = int(((o <= 0) | (h <= 0) | (l <= 0) | (cl <= 0)).sum())
    print(f"=== {name} ({path}) ===")
    print(f"  n_rows            : {n}")
    print(f"  first_ts          : {_iso(ts[0])}")
    print(f"  last_ts           : {_iso(ts[-1])}")
    print(f"  median_step_s     : {step}")
    print(f"  monotonic_increasing: {bool((diffs > 0).all())}")
    print(f"  n_duplicate_ts    : {n_dup}")
    print(f"  n_backsteps       : {n_back}")
    print(f"  n_high_lt_maxoc   : {n_high_lt_maxoc}")
    print(f"  n_low_gt_minoc    : {n_low_gt_minoc}")
    print(f"  n_high_lt_low     : {n_high_lt_low}")
    print(f"  n_nonpositive_ohlc: {n_nonpos}")
    print(f"  min_low / max_high: {float(l.min())} / {float(h.max())}")
    print()


if __name__ == "__main__":
    for name, path in FILES.items():
        check(name, path)
