"""Step 6: prefix-consistency (no-lookahead) test for build_daily_table.

Pattern adapted from ../ict/tests/test_no_lookahead.py: run the builder on
the full in-sample series and again on the series truncated at a random
cutoff date; every row for a date <= (cutoff - 1 day) must be byte-identical
between the two runs. Run at k=0.5, L=30 (Task step 6). Must pass.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import build_daily_table, load_insample

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
K, L = 0.5, 30
N_CUTOFFS = 5
SEED = 0


def run() -> None:
    h1 = load_insample(f"{ROOT}/data/es_1h_insample.parquet")
    h4 = load_insample(f"{ROOT}/data/es_4h_insample.parquet")

    full = build_daily_table(h1, h4, K, L)

    all_dates = sorted(h1["ts_et"].dt.date.unique())
    # avoid the first ~2 months (no L=60-worth of 4h history anywhere in the
    # grid) and the last week, so every cutoff has real rows to compare.
    pool = all_dates[60:-5]
    rng = np.random.default_rng(SEED)
    cutoffs = sorted(rng.choice(pool, size=N_CUTOFFS, replace=False))

    for cutoff in cutoffs:
        cutoff_ts = pd.Timestamp(cutoff, tz="America/New_York")
        h1_trunc = h1[h1["ts_et"] < cutoff_ts]
        h4_trunc = h4[h4["ts_et"] < cutoff_ts]
        trunc = build_daily_table(h1_trunc, h4_trunc, K, L)

        boundary = (cutoff_ts - pd.Timedelta(days=1)).date()
        full_prefix = full[full["date"] <= boundary].reset_index(drop=True)
        trunc_prefix = trunc[trunc["date"] <= boundary].reset_index(drop=True)

        assert len(full_prefix) > 0, f"vacuous test at cutoff={cutoff}: no rows before boundary"
        pd.testing.assert_frame_equal(full_prefix, trunc_prefix)
        print(f"OK  cutoff={cutoff}  rows_checked={len(full_prefix)}  (of {len(full)} full-series rows)")

    print(f"PASS: all {N_CUTOFFS} cutoffs prefix-consistent at k={K}, L={L}")


if __name__ == "__main__":
    run()
