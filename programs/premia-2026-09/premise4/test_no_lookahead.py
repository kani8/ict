"""Prefix-consistency (no-lookahead) test, P3 pattern adapted to a daily series
(no month-end/eligibility subtlety here: every date is "complete" once its own
row exists). Truncate the raw vx_daily/contracts panels at 5 random cutoff
dates; positions() and size()'s weights decided strictly before the cutoff must
be identical to the full-sample run. Exercises the EWMA vol shift-by-1 (a fix
made during implementation, see strategy.size()) and the state machine's carry-
forward-on-NaN behaviour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import THETA_FIXED, held_series, load_insample, positions, size

N_CUTOFFS = 5
SEED = 0


def _pos_w_for(vd: pd.DataFrame, vc: pd.DataFrame):
    held = held_series(vd, vc)
    pos = positions(held["roll"], THETA_FIXED)
    w, _ = size(pos, held["ret_next"])
    return pd.DataFrame({"date": held["date"], "pos": pos, "w": w})


def run() -> None:
    vd, vc, _ = load_insample()
    full = _pos_w_for(vd, vc)

    pool = vd["date"].iloc[100:-2]  # skip EWMA burn-in and the last 2 rows (need t+1 data)
    rng = np.random.default_rng(SEED)
    cutoffs = sorted(rng.choice(pool.to_numpy(), size=N_CUTOFFS, replace=False))

    for cutoff in cutoffs:
        cutoff = pd.Timestamp(cutoff)
        vd_t = vd[vd["date"] < cutoff]
        vc_t = vc[vc["date"] < cutoff]
        trunc = _pos_w_for(vd_t, vc_t)

        full_prefix = full[full["date"] < cutoff].reset_index(drop=True)
        trunc_prefix = trunc[trunc["date"] < cutoff].reset_index(drop=True)
        assert len(full_prefix) > 0, f"vacuous test at cutoff={cutoff}"
        pd.testing.assert_frame_equal(full_prefix, trunc_prefix)
        print(f"OK  cutoff={cutoff.date()}  rows checked={len(full_prefix)}  (of {len(full)} full-sample)")

    print(f"PASS: all {N_CUTOFFS} cutoffs prefix-consistent at theta={THETA_FIXED}")


if __name__ == "__main__":
    run()
