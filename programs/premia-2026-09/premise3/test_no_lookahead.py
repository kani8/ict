"""TASK.md Step 5: prefix-consistency (no-lookahead) test.

Truncate the input price panel at 5 random cutoff dates; the target weights
decided at every month-end strictly before the cutoff must be identical to the
full-sample run. Exercises EWMA vol/cov, signals, and eligibility. Run at L=12.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import (daily_excess_returns, eligibility, ewma_vol_cov,
                       load_insample_prices, load_insample_rf, month_ends,
                       signals, target_weights)

N_CUTOFFS = 5
SEED = 0
L = 12


def _weights_for(px: pd.DataFrame) -> pd.DataFrame:
    rf = load_insample_rf(px.index)
    x = daily_excess_returns(px, rf)
    elig = eligibility(px)
    me = month_ends(px.index)
    sigma, cov_pairs = ewma_vol_cov(x)
    sig = signals(x, L)
    w, _ = target_weights(sig, sigma, cov_pairs, elig, me)
    return w


def run() -> None:
    px = load_insample_prices()
    full = _weights_for(px)

    pool = px.index[300:-30]  # skip the eligibility burn-in and the final incomplete month
    rng = np.random.default_rng(SEED)
    cutoffs = sorted(rng.choice(np.asarray(pool), size=N_CUTOFFS, replace=False))

    for cutoff in cutoffs:
        cutoff = pd.Timestamp(cutoff)
        px_trunc = px.loc[px.index < cutoff]
        trunc = _weights_for(px_trunc)

        # exclude cutoff's own (possibly still in-progress) calendar month entirely:
        # from truncated data alone we cannot know whether its last visible day is
        # truly that month's last trading day, so only compare fully-completed months.
        boundary = cutoff.replace(day=1) - pd.Timedelta(days=1)
        full_prefix = full.loc[full.index <= boundary]
        trunc_prefix = trunc.loc[trunc.index <= boundary]
        assert len(full_prefix) > 0, f"vacuous test at cutoff={cutoff}"
        pd.testing.assert_frame_equal(full_prefix, trunc_prefix)
        print(f"OK  cutoff={cutoff.date()}  month-ends checked={len(full_prefix)}  (of {len(full)} full-sample)")

    print(f"PASS: all {N_CUTOFFS} cutoffs prefix-consistent at L={L}")


if __name__ == "__main__":
    run()
