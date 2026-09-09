"""TASK.md Step 6: prefix-consistency (no-lookahead) test, L=12 class-balanced.
Structure copied from premise3/test_no_lookahead.py (exercises THIS premise's
own pipeline), swapping in class_balanced_weights and this premise's loaders."""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import (class_balanced_weights, load_insample_prices,
                       load_insample_rf, p3)

N_CUTOFFS = 5
SEED = 0
L = 12


def _weights_for(px: pd.DataFrame) -> pd.DataFrame:
    rf = load_insample_rf(px.index)
    x = p3.daily_excess_returns(px, rf)
    elig = p3.eligibility(px)
    me = p3.month_ends(px.index)
    sigma, cov_pairs = p3.ewma_vol_cov(x)
    sig = p3.signals(x, L)
    w, _ = class_balanced_weights(sig, sigma, cov_pairs, elig, me)
    return w


def run() -> None:
    px = load_insample_prices()
    full = _weights_for(px)

    pool = px.index[300:-30]  # skip eligibility burn-in and the final incomplete month
    rng = np.random.default_rng(SEED)
    cutoffs = sorted(rng.choice(np.asarray(pool), size=N_CUTOFFS, replace=False))

    for cutoff in cutoffs:
        cutoff = pd.Timestamp(cutoff)
        px_trunc = px.loc[px.index < cutoff]
        trunc = _weights_for(px_trunc)

        boundary = cutoff.replace(day=1) - pd.Timedelta(days=1)
        full_prefix = full.loc[full.index <= boundary]
        trunc_prefix = trunc.loc[trunc.index <= boundary]
        assert len(full_prefix) > 0, f"vacuous test at cutoff={cutoff}"
        pd.testing.assert_frame_equal(full_prefix, trunc_prefix)
        print(f"OK  cutoff={cutoff.date()}  month-ends checked={len(full_prefix)}  (of {len(full)} full-sample)")

    print(f"PASS: all {N_CUTOFFS} cutoffs prefix-consistent at L={L}")


if __name__ == "__main__":
    run()
