"""M-02 Part A runner — temporal robustness of the M1 anti-magnetism cell.

Thin driver only: loads each dataset over its predeclared temporal halves via
the library's own date-windowed `load_candles(start=, end=)`, then calls the
tested library `run_magnetism` at the preregistered defaults. No study logic is
re-implemented and no parameters are changed from the M1 defaults:
swing_k=3, eq_tol_atr=0.25, atr_period=14, horizons=(96,384),
default buckets ((0.5,1),(1,2),(2,4)), baseline_k=20, seed=42.

Predeclared halves (M1_ADJUDICATION.md / PREREGISTRATION_M.md):
  ES  2010-06-06 -> 2018-06-30  and  2018-07-01 -> 2026-07-01
  BTC 2023-01-01 -> 2024-09-30  and  2024-10-01 -> 2026-07-01
  ETH same split as BTC.

The loader is half-open (ts >= start & ts < end). Each dataset is cut at a
single split date so the two halves are disjoint, gap-free, and their union is
exactly the M1 full sample (verified: union n == full n for all three). H1 is
`end=SPLIT`; H2 is `start=SPLIT`. H1's last trading day is thus the declared
first-half end (ES 2018-06-30 falls on a Saturday, so its last bar is Fri
2018-06-29); H2 runs to the dataset end.

Ruling object: the 2.0-4.0 ATR / horizon-96 cell. Per the adjudication it is
CONFIRMED iff it excludes 1.0 *downward* (ci_hi < 1.0) in BOTH halves of >=2
of the 3 datasets. Any other outcome: recorded unstable, no claim.

Burned data only (BTC/ETH 2023-2026, ES 2010-2026). No holdouts touched.
"""

from __future__ import annotations

import json

import pandas as pd

from ict_backtest.analytics.magnetism import (
    DIST_BUCKETS,
    HORIZONS,
    render_magnetism_table,
    run_magnetism,
)
from ict_backtest.data.loader import load_candles

# dataset -> (path, split_date). Halves derive from the single split.
DATASETS = {
    "ES": ("data/es_15m.parquet", "2018-07-01"),
    "BTC": ("data/btcusdt_15m.parquet", "2024-10-01"),
    "ETH": ("data/ethusdt_15m.parquet", "2024-10-01"),
}

RULING_BUCKET = "2.0-4.0"
RULING_HORIZON = 96


def _ts(sec: int) -> str:
    return pd.Timestamp(int(sec), unit="s", tz="UTC").isoformat()


def ruling_cell(rows: list[dict]) -> dict | None:
    for r in rows:
        if r["bucket"] == RULING_BUCKET and r["horizon"] == RULING_HORIZON:
            return r
    return None


def main() -> None:
    out: dict = {
        "params": {"swing_k": 3, "eq_tol_atr": 0.25, "atr_period": 14,
                   "baseline_k": 20, "seed": 42},
        "horizons": list(HORIZONS),
        "buckets": [list(b) for b in DIST_BUCKETS],
        "ruling": {"bucket": RULING_BUCKET, "horizon": RULING_HORIZON,
                   "test": "ci_hi < 1.0 (EXCL-DOWN) in BOTH halves of >=2 datasets"},
        "datasets": {},
    }

    for ds, (path, split) in DATASETS.items():
        halves = {
            "H1": load_candles(path, end=split),
            "H2": load_candles(path, start=split),
        }
        out["datasets"][ds] = {"split": split, "halves": {}}
        for half, candles in halves.items():
            rows = run_magnetism(candles)  # all preregistered defaults, seed 42
            label = (f"{ds} {half} (n={len(candles.ts)}, "
                     f"{_ts(candles.ts[0])[:10]}..{_ts(candles.ts[-1])[:10]})")
            print(render_magnetism_table(rows, label))
            print()
            cell = ruling_cell(rows)
            excl_down = bool(cell is not None and cell["ci_hi"] < 1.0)
            out["datasets"][ds]["halves"][half] = {
                "n_bars": len(candles.ts),
                "first_ts": _ts(candles.ts[0]),
                "last_ts": _ts(candles.ts[-1]),
                "rows": rows,
                "ruling_cell": cell,
                "ruling_excl_down": excl_down,
            }

    # Apply the ruling.
    print("=" * 70)
    print(f"RULING CELL: {RULING_BUCKET} ATR / h={RULING_HORIZON}  (EXCL-DOWN = ci_hi < 1.0)")
    datasets_passing = []
    for ds in DATASETS:
        h = out["datasets"][ds]["halves"]
        h1 = h["H1"]["ruling_excl_down"]
        h2 = h["H2"]["ruling_excl_down"]
        both = h1 and h2
        if both:
            datasets_passing.append(ds)
        c1, c2 = h["H1"]["ruling_cell"], h["H2"]["ruling_cell"]
        print(f"  {ds}: H1 ci=[{c1['ci_lo']:.4f},{c1['ci_hi']:.4f}] excl_down={h1}  "
              f"H2 ci=[{c2['ci_lo']:.4f},{c2['ci_hi']:.4f}] excl_down={h2}  "
              f"BOTH={both}")
    confirmed = len(datasets_passing) >= 2
    print(f"\n  datasets passing (both halves EXCL-DOWN): {datasets_passing} "
          f"({len(datasets_passing)}/3)")
    print(f"  VERDICT: anti-magnetism cell {'CONFIRMED' if confirmed else 'NOT CONFIRMED (unstable)'} "
          f"(rule: >=2/3 datasets with both halves EXCL-DOWN)")
    out["verdict"] = {
        "datasets_passing": datasets_passing,
        "n_passing": len(datasets_passing),
        "confirmed": confirmed,
    }

    with open("reports/dev/_m2_parta_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote reports/dev/_m2_parta_results.json")


if __name__ == "__main__":
    main()
