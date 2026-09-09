"""TASK.md Step 7: prefix-consistency (no-lookahead) test, 5 random cutoffs.

Truncate the ETF price panel at 5 random cutoff dates; the FX (XS) and bond
sleeve weights decided at every month-end strictly before the cutoff must be
identical to the full-sample run. Exercises EWMA vol/cov (which is causal/
recursive) and the carry/bond-signal loaders (independent of price, so trivially
prefix-consistent, but re-derived here end to end).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import strategy as s

N_CUTOFFS = 5
SEED = 0


def _weights_for(px: pd.DataFrame) -> pd.DataFrame:
    rf = s.load_insample_rf(px.index)
    x = s.daily_excess_returns(px, rf)
    me = s.month_ends(px.index)
    rates, yields = s.load_rates_monthly(), s.load_yields_daily()
    carry, _, _ = s.fx_carry(rates, me)
    bsig = s.bond_signal(yields, me)
    sigma, cov_pairs = s.ewma_vol_cov(x)
    fx_raw = s.fx_weights(carry, "XS")
    bond_raw = s.bond_weights(bsig, sigma.reindex(me))
    leg = s.build_leg(x, fx_raw, bond_raw, cov_pairs)
    return pd.concat([leg["fx"]["w"], leg["bond"]["w"]], axis=1)


def run() -> None:
    px = s.load_insample_etf_prices()
    full = _weights_for(px)

    pool = px.index[500:-30]  # skip early burn-in and the final incomplete month
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

    print(f"PASS: all {N_CUTOFFS} cutoffs prefix-consistent (FX-XS + bond sleeve weights)")


if __name__ == "__main__":
    run()
