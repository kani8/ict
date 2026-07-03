"""M-03 (Study M3) runner — high-volume revisit.

Thin driver only: loads each burned dataset via load_candles, builds the
killzone mask exactly as the frozen M3 design specifies, and calls the
tested library (run_revisit_study / render_revisit_table). No study logic is
re-implemented here and no parameters are changed from the library defaults
(horizons=(96,384), q=0.99, trailing=2880, isolation=96, depart_atr=1.0,
k=20, vol_tol=0.25, atr_period=14, seed=42).

kz_mask (uniform across all three datasets, per the frozen design's
killzone matching):
    in_killzone(candles.ts,
                [ET_BY_NAME[n] for n in ("london","new_york","silver_bullet")],
                "America/New_York")

Burned data only (BTC/ETH 2023-2026, ES 2010-2026). No holdouts touched.
"""

from __future__ import annotations

import json

from ict_backtest.analytics.revisit import render_revisit_table, run_revisit_study
from ict_backtest.data.loader import load_candles
from ict_backtest.detectors.killzones import ET_BY_NAME, in_killzone

DATASETS = {
    "BTCUSDT 15m (2023-2026)": "data/btcusdt_15m.parquet",
    "ETHUSDT 15m (2023-2026)": "data/ethusdt_15m.parquet",
    "ES 15m adj (2010-2026)": "data/es_15m.parquet",
}

KZ_NAMES = ("london", "new_york", "silver_bullet")


def main() -> None:
    out = {}
    for label, path in DATASETS.items():
        candles = load_candles(path)
        kz_mask = in_killzone(
            candles.ts, [ET_BY_NAME[n] for n in KZ_NAMES], "America/New_York"
        )
        rows = run_revisit_study(candles, kz_mask=kz_mask)  # library defaults, seed=42
        table = render_revisit_table(rows, label)
        print(table)
        print()
        out[label] = {"n_bars": len(candles), "kz_bars": int(kz_mask.sum()),
                      "rows": rows}

    with open("reports/dev/_m3_results.json", "w") as fh:
        json.dump({"killzones": list(KZ_NAMES), "killzone_tz": "America/New_York",
                   "params": {"horizons": [96, 384], "q": 0.99, "trailing": 2880,
                              "isolation": 96, "depart_atr": 1.0, "k": 20,
                              "vol_tol": 0.25, "atr_period": 14, "seed": 42},
                   "datasets": out}, fh, indent=2)
    print("wrote reports/dev/_m3_results.json")


if __name__ == "__main__":
    main()
