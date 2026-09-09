"""Premise 4 permutation test (Amendment A1 collapse of Masters (ii)/(iv) into one
test, since theta has no per-window selection). P3's permtest.py harness (grid
search over lookback L, per-window walk-forward re-selection) does not apply --
P4 has no selection step -- so this is a minimal from-scratch harness following
the same shuffle-and-recompute-the-pipeline / p=share>=real pattern, per
TASK.md's exogenous-signal scheme: shuffle held-series returns WITHIN the
stitched span only; `roll` (hence `pos`, decided from roll alone) and the
roll-day/F used for costs stay on their original dates; sigma/weights/costs/P&L
are recomputed per permutation over the full (mostly-unshuffled) series so the
EWMA warm-up before the stitched span is undisturbed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import sharpe, simulate, size


def permutation_test(ret: pd.Series, pos: pd.Series, F: pd.Series, roll_day: pd.Series,
                      mask: np.ndarray, n_reps: int = 500, seed: int = 0):
    idx = np.flatnonzero(mask)
    block = ret.to_numpy()[idx]

    w, _ = size(pos, ret)
    real_pnl = simulate(w, ret, F, roll_day)["net"].to_numpy()[mask]
    real_sh = sharpe(pd.Series(real_pnl))

    rng = np.random.default_rng(seed)
    null_sh = np.empty(n_reps)
    perm_ret = ret.copy()
    for k in range(n_reps):
        perm_ret.iloc[idx] = block[rng.permutation(len(idx))]
        w_k, _ = size(pos, perm_ret)
        pnl_k = simulate(w_k, perm_ret, F, roll_day)["net"].to_numpy()[mask]
        null_sh[k] = sharpe(pd.Series(pnl_k))
        if (k + 1) % 100 == 0:
            print(f"  permutation {k + 1}/{n_reps}")
    p = float((null_sh >= real_sh).mean())
    return real_sh, null_sh, p
