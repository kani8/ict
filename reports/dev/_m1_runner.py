"""M-01 Study M1 runner — liquidity magnetism on the three burned datasets.

Thin driver only: loads each dataset via load_candles and calls the tested
library (run_magnetism / render_magnetism_table / pool_touch_events). No
study logic is re-implemented here and no parameters are changed from the
preregistered library defaults: swing_k=3, eq_tol_atr=0.25, atr_period=14,
horizons=(96,384), default buckets ((0.5,1),(1,2),(2,4)), baseline_k=20,
seed=42.

Burned data only (BTC/ETH 2023-2026, ES 2010-2026). No holdouts touched.
"""

from __future__ import annotations

import json

from ict_backtest.analytics.magnetism import (
    DIST_BUCKETS,
    HORIZONS,
    pool_touch_events,
    render_magnetism_table,
    run_magnetism,
)
from ict_backtest.data.loader import load_candles

DATASETS = {
    "BTCUSDT 15m (2023-2026)": "data/btcusdt_15m.parquet",
    "ETHUSDT 15m (2023-2026)": "data/ethusdt_15m.parquet",
    "ES 15m adj (2010-2026)": "data/es_15m.parquet",
}


def bucket_event_counts(candles) -> dict:
    """Raw event distribution across distance buckets (before horizon filter).

    Shows how many confirmed-pool events land in each ATR bucket, plus how
    many fall outside all buckets (<0.5 or >=4.0 ATR), so thin cells are
    explicit. Uses the library's own pool_touch_events at default params.
    """
    events = pool_touch_events(candles)  # swing_k=3, eq_tol_atr=0.25, atr_period=14
    counts = {f"{lo}-{hi}": 0 for lo, hi in DIST_BUCKETS}
    below = above = 0
    for e in events:
        d = e["d_atr"]
        placed = False
        for lo, hi in DIST_BUCKETS:
            if lo <= d < hi:
                counts[f"{lo}-{hi}"] += 1
                placed = True
                break
        if not placed:
            if d < DIST_BUCKETS[0][0]:
                below += 1
            else:
                above += 1
    return {"total_events": len(events), "per_bucket": counts,
            "below_0.5_atr": below, "above_4.0_atr": above}


def main() -> None:
    out = {}
    for label, path in DATASETS.items():
        candles = load_candles(path)
        rows = run_magnetism(candles)  # all preregistered defaults
        table = render_magnetism_table(rows, label)
        print(table)
        print()
        out[label] = {"n_bars": len(candles), "rows": rows}

    # ES thin-cell visibility: per-bucket raw event counts at swing_k=3.
    es = load_candles(DATASETS["ES 15m adj (2010-2026)"])
    es_counts = bucket_event_counts(es)
    print("ES per-bucket raw event counts (swing_k=3, unfiltered by horizon):")
    print(json.dumps(es_counts, indent=2))
    out["ES 15m adj (2010-2026)"]["bucket_event_counts_swing_k3"] = es_counts

    with open("reports/dev/_m1_results.json", "w") as fh:
        json.dump({"horizons": list(HORIZONS),
                   "buckets": [list(b) for b in DIST_BUCKETS],
                   "params": {"swing_k": 3, "eq_tol_atr": 0.25, "atr_period": 14,
                              "baseline_k": 20, "seed": 42},
                   "datasets": out}, fh, indent=2)
    print("\nwrote reports/dev/_m1_results.json")


if __name__ == "__main__":
    main()
