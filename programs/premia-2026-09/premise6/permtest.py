"""Premise 6 permutation test: 500 day-shuffles of the 38-column excess-return
matrix, full pipeline per permutation, stitched Sharpe. Mirrors premise3's
Amendment-A1 day-shuffle harness (permtest.py: permute_days/stitched_wf_
sharpe), reimplemented rather than imported: P3's PERM_CUTOFF is specific to
its 20-name universe (P6's is later, EMB 2007-12-19), and P3's permtest.py
itself does `from strategy import ...`, which would wrongly resolve against
*this* file if dynamically loaded (see strategy.py's docstring). No per-
window L-selection here (L=12 fixed): shuffle x -> EWMA vol/cov -> L=12
signal -> class-balanced weights -> simulate -> stitched net Sharpe.
elig/me are structural (price-listing timing) and are NOT permuted."""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import COST_BP, class_balanced_weights, p3

STITCH_START, STITCH_END = pd.Timestamp("2010-07-01"), pd.Timestamp("2024-06-30")


def permute_days(x: pd.DataFrame, cutoff: pd.Timestamp, rng: np.random.Generator) -> pd.DataFrame:
    """Shuffle rows (full cross-section as a unit) for dates >= cutoff, re-
    cumulated onto the original index; rows before cutoff untouched."""
    idx = x.index
    mask = idx >= cutoff
    block = x.loc[mask].to_numpy()
    perm = rng.permutation(len(block))
    out = x.copy()
    out.loc[mask] = block[perm]
    return out


def stitched_sharpe(x: pd.DataFrame, elig: pd.DataFrame, me: pd.DatetimeIndex) -> float:
    sigma, cov_pairs = p3.ewma_vol_cov(x)
    sig = p3.signals(x, 12)
    w, _ = class_balanced_weights(sig, sigma, cov_pairs, elig, me)
    pnl = p3.simulate(w, x, cost_bp=COST_BP)["net"].loc[STITCH_START:STITCH_END]
    return p3.sharpe(pnl)


def run_permutation_test(x, elig, me, cutoff, n_reps=500, seed=6):
    real = stitched_sharpe(x, elig, me)
    rng = np.random.default_rng(seed)
    null_sh = np.empty(n_reps)
    for k in range(n_reps):
        null_sh[k] = stitched_sharpe(permute_days(x, cutoff, rng), elig, me)
        if (k + 1) % 100 == 0:
            print(f"  permutation {k + 1}/{n_reps}")
    p = float((null_sh >= real).mean())
    return real, null_sh, p
