"""Step 6: prefix-consistency (no-lookahead) test for build_day_frame.

Pattern from premise1/test_no_lookahead.py: run the builder on the full
in-sample series and again on the series truncated at a random cutoff date;
every row for a date <= (cutoff - 1 day) must be byte-identical between the
two runs. Truncates ALL THREE inputs (m1/h1/h4) since this premise reads O
from m1 too. Exercises sigma_t (prior N days) and sigma_4h (prior 30 4h
bars) since both are backward-looking rolling windows evaluated at every
cutoff. Run at m=1, N=14 (Task step 6). Must pass.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import build_day_frame, load_insample

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
M, N = 1.0, 14
N_CUTOFFS = 5
SEED = 0


def run() -> None:
    m1 = load_insample(f"{ROOT}/data/es_1m_insample.parquet")
    h1 = load_insample(f"{ROOT}/data/es_1h_insample.parquet")
    h4 = load_insample(f"{ROOT}/data/es_4h_insample.parquet")

    full = build_day_frame(m1, h1, h4, M, N)

    all_dates = sorted(h1["ts_et"].dt.date.unique())
    # avoid the first ~4 months (no N=60-worth of history anywhere in the
    # broader grid, plus 30 4h bars ~ 5 days) and the last week.
    pool = all_dates[90:-5]
    rng = np.random.default_rng(SEED)
    cutoffs = sorted(rng.choice(pool, size=N_CUTOFFS, replace=False))

    for cutoff in cutoffs:
        cutoff_ts = pd.Timestamp(cutoff, tz="America/New_York")
        m1_trunc = m1[m1["ts_et"] < cutoff_ts]
        h1_trunc = h1[h1["ts_et"] < cutoff_ts]
        h4_trunc = h4[h4["ts_et"] < cutoff_ts]
        trunc = build_day_frame(m1_trunc, h1_trunc, h4_trunc, M, N)

        boundary = (cutoff_ts - pd.Timedelta(days=1)).date()
        full_prefix = full[full["date"] <= boundary].reset_index(drop=True)
        trunc_prefix = trunc[trunc["date"] <= boundary].reset_index(drop=True)

        assert len(full_prefix) > 0, f"vacuous test at cutoff={cutoff}: no rows before boundary"
        pd.testing.assert_frame_equal(full_prefix, trunc_prefix)
        print(f"OK  cutoff={cutoff}  rows_checked={len(full_prefix)}  (of {len(full)} full-series rows)")

    print(f"PASS: all {N_CUTOFFS} cutoffs prefix-consistent at m={M}, N={N} (exercises sigma_t and sigma_4h)")


if __name__ == "__main__":
    run()
