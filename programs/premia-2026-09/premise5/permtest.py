"""Premise 5 permutation test: 500 reps, exogenous-signal scheme, stitched calendar.

PREMISE_5.md: "shuffle the order of trading days for the 8-instrument daily
excess-return matrix (rows move as units), re-cumulated onto the original date
index; the carry and term-spread signal series stay on their original dates;
recompute vol/cov, weights, costs, P&L." `fx_raw` (rank-weights, a function of
carry only) is literally invariant to the permutation and passed in fixed; the
bond sleeve's 0.40/sigma scaling depends on EWMA vol, so sigma/cov (and hence the
bond raw weights and both sleeves' 3x-cap sizing) ARE recomputed per permutation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import strategy as s

PERM_CUTOFF = pd.Timestamp("2007-02-13")  # FXY's first valid price -- last of the 8 to list


def permute_days(x: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Shuffle row order for dates >= PERM_CUTOFF (each day's cross-section moves as
    a unit); earlier burn-in rows untouched; re-cumulated onto the original index."""
    idx = x.index
    mask = idx >= PERM_CUTOFF
    block = x.loc[mask].to_numpy()
    perm = rng.permutation(len(block))
    out = x.copy()
    out.loc[mask] = block[perm]
    return out


def stitched_leg_sharpe(x, fx_raw, bond_sig, me, start, end, cost_mult=1.0) -> float:
    sigma, cov_pairs = s.ewma_vol_cov(x)
    bond_raw = s.bond_weights(bond_sig, sigma.reindex(me))
    leg_net = s.build_leg(x, fx_raw, bond_raw, cov_pairs, cost_mult)["leg_net"]
    return s.sharpe(leg_net.loc[start:end])


def run_permutation(x, fx_raw, bond_sig, me, start, end, n_reps, seed, cost_mult=1.0):
    real_sh = stitched_leg_sharpe(x, fx_raw, bond_sig, me, start, end, cost_mult)
    rng = np.random.default_rng(seed)
    null_sh = np.empty(n_reps)
    for k in range(n_reps):
        null_sh[k] = stitched_leg_sharpe(permute_days(x, rng), fx_raw, bond_sig, me, start, end, cost_mult)
        if (k + 1) % 100 == 0:
            print(f"  permutation {k + 1}/{n_reps}")
    p = float((null_sh >= real_sh).mean())
    return real_sh, null_sh, p
