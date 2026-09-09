"""Premise 4 core: held-contract series, roll signal, state machine, sizing, simulation.

Spec: ../PREMISE_4.md (frozen + Amendment A1: theta fixed at 0.0050, zero free
parameters). See TASK.md for file layout and hard rules.
No lookahead: roll_t/dte/settle at date t use data known at t's own settle only;
ret_next(t) additionally uses t+1's settle of the SAME (held-at-t) contract, which
is realized/known only at t+1 -- it is never used to decide position/weight at t
(positions()/size() only see `roll`, which is itself a pure function of date-t data).
Execution lag: position decided at t is established at settle t+1 and first earns
the t+1->t+2 return (identical convention to P3, see simulate()).
Pure functions; the state machine is a simple loop over days (explicitly allowed).
"""
from __future__ import annotations

import importlib.util as _ilu

import numpy as np
import pandas as pd

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
OOS_CUTOFF = pd.Timestamp("2024-07-01")

THETA_FIXED = 0.0050
THETA_GRID = [0.0, 0.0025, 0.0050, 0.0075]
COM = 60
TARGET_VOL = 0.10
GROSS_CAP = 3.0
ACCOUNT = 100_000.0
COST_TICK = 0.05
COST_COMM = 0.00125  # $1.25 commission expressed as VX points via the $1000 multiplier

# Reuse P3's generic (signature-fits-as-is) Sharpe / max-DD / markdown-table helpers
# rather than re-deriving them (TASK.md: "import where signatures fit").
_spec = _ilu.spec_from_file_location("_p3_strategy", f"{ROOT}/premise3/strategy.py")
_p3 = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_p3)
sharpe, max_drawdown, md_table = _p3.sharpe, _p3.max_drawdown, _p3.md_table


def load_insample(root: str = ROOT):
    """Loads the 4 permitted files only; guards each against the OOS cutoff.
    Returns (vx_daily, contracts, spy) -- vix_spot is read+guarded+cross-checked
    against vx_daily's own vix_close (identical on every overlapping date) and then
    dropped: held_series()'s signature (per TASK.md) takes vx_daily/contracts only,
    and vx_daily.vix_close IS spot VIX (see Implementation choices)."""
    vd = pd.read_parquet(f"{root}/data_vx/vx_daily_insample.parquet")
    vd["date"] = pd.to_datetime(vd["date"])
    if vd["date"].max() >= OOS_CUTOFF:
        raise ValueError("vx_daily_insample.parquet: OOS leak")

    vc = pd.read_parquet(f"{root}/data_vx/vx_contracts_insample.parquet")
    vc["date"] = pd.to_datetime(vc["date"]); vc["expiry"] = pd.to_datetime(vc["expiry"])
    if vc["date"].max() >= OOS_CUTOFF:
        raise ValueError("vx_contracts_insample.parquet: OOS leak")

    vs = pd.read_parquet(f"{root}/data_vx/vix_spot.parquet")
    vs["date"] = pd.to_datetime(vs["date"])
    vs = vs[vs["date"] < OOS_CUTOFF]
    if vs["date"].max() >= OOS_CUTOFF:
        raise ValueError("vix_spot.parquet: filter failed, OOS leak")
    chk = vd[["date", "vix_close"]].merge(vs.rename(columns={"close": "spot"})[["date", "spot"]], on="date")
    mism = int((chk["vix_close"] - chk["spot"]).abs().gt(1e-6).sum())
    assert mism == 0, f"vix_spot vs vx_daily.vix_close mismatch on {mism} rows"

    spy = pd.read_parquet(f"{root}/data_daily/adj_close_wide_insample.parquet")
    spy.index = pd.to_datetime(spy.index)
    if spy.index.max() >= OOS_CUTOFF:
        raise ValueError("adj_close_wide_insample.parquet: OOS leak")
    return vd, vc, spy["SPY"]


def held_series(vx_daily: pd.DataFrame, contracts: pd.DataFrame) -> pd.DataFrame:
    """held = f1 while f1_dte>=10 else f2; ret_next(t) = settle of THAT SAME
    (held-at-t) expiry at t+1 / its own settle at t - 1, looked up in `contracts`
    (not vx_daily's own f1/f2 columns) because on a roll day the outgoing contract
    is no longer f1 or f2 the next day. Days with no VX settle at all (empty
    contracts that date) carry expiry forward (ffill) and get roll/ret_next = NaN.
    """
    vd = vx_daily.sort_values("date").reset_index(drop=True)
    is_f1 = vd["f1_dte"] >= 10
    cand_expiry = vd["f1_expiry"].where(is_f1, vd["f2_expiry"])
    cand_dte = vd["f1_dte"].where(is_f1, vd["f2_dte"])
    cand_settle = vd["f1_settle"].where(is_f1, vd["f2_settle"])
    expiry = cand_expiry.ffill()

    c_idx = contracts.set_index(["date", "expiry"])["settle"]
    key = pd.MultiIndex.from_arrays([vd["date"].shift(-1), expiry])
    settle_next = pd.Series(c_idx.reindex(key).to_numpy(), index=vd.index)

    ret_next = settle_next / cand_settle - 1.0
    roll = (cand_settle - vd["vix_close"]) / cand_settle / np.maximum(cand_dte, 1.0)
    return pd.DataFrame({"date": vd["date"], "expiry": expiry, "settle": cand_settle,
                          "dte": cand_dte, "ret_next": ret_next, "roll": roll})


def roll_flag(held: pd.DataFrame) -> pd.Series:
    """True on days the held expiry changed vs the prior row (first row = False)."""
    rf = held["expiry"].ne(held["expiry"].shift(1))
    rf.iloc[0] = False
    return rf


def positions(roll: pd.Series, theta: float) -> pd.Series:
    """State machine, theta/2 exit, direct flip on a sign change past theta.
    NaN roll (no VX settle that day) -> state carried unchanged."""
    half = theta / 2.0
    s = np.empty(len(roll)); state = 0
    for i, r in enumerate(roll.to_numpy()):
        if np.isnan(r):
            pass
        elif state == 0:
            if r > theta: state = -1
            elif r < -theta: state = 1
        elif state == -1:
            if r < -theta: state = 1
            elif r < half: state = 0
        else:
            if r > theta: state = -1
            elif r > -half: state = 0
        s[i] = state
    return pd.Series(s, index=roll.index)


def ewma_vol(ret: pd.Series, com: int = COM) -> pd.Series:
    """Annualised EWMA vol, COM=60: raw (non-demeaned) 2nd moment, recursive,
    NaN-ignored -- same convention as premise3.strategy.ewma_vol_cov, copied in
    minimal univariate form (that function is DataFrame/multi-asset with a
    cross-covariance tensor this single-instrument leg does not need)."""
    var = (ret ** 2).ewm(com=com, adjust=False, ignore_na=True).mean() * 252
    return np.sqrt(var)


def size(pos: pd.Series, ret: pd.Series, com: int = COM):
    """w_t = s_t * 0.10 / sigma_t; sigma from the held-series returns (signal-
    independent). `ret` is ret_next, indexed by its START date (t -> t+1 return,
    per held_series()); sigma_t must use only returns REALIZED by t, i.e. the
    return ending at t = ret_next[t-1], hence the shift(1) here -- using ret_next
    unshifted would leak t+1's settle into the weight decided at t. Returns
    (weights, cap_binding bool Series)."""
    sigma = ewma_vol(ret.shift(1), com)
    w_raw = pos * TARGET_VOL / sigma
    cap_binding = w_raw.abs() > GROSS_CAP
    return w_raw.clip(-GROSS_CAP, GROSS_CAP), cap_binding


def simulate(weights: pd.Series, ret: pd.Series, F: pd.Series, roll_day: pd.Series,
             ticks: int = 1, account: float = ACCOUNT) -> pd.DataFrame:
    """Weight decided at t is established at settle t+1 and earns ret[t+1] (the
    t+1->t+2 return) onward: gross[k] = notional[k-2]*ret[k-1] (2-day lag, P3
    convention). Turnover cost at k = rate(k)*|notional[k-1]-notional[k-2]|, or on
    a roll day rate(k)*(|notional[k-1]|+|notional[k-2]|) -- close the full old
    notional and reopen the full new notional, per spec, using the held contract's
    OWN settle F[k] on the roll day for both legs (a documented simplification:
    the spec gives one F_t, not a separate F for the outgoing/incoming legs)."""
    notional = weights * account
    prev_n, new_n = notional.shift(2), notional.shift(1)
    cost_rate = (COST_TICK * ticks + COST_COMM) / F
    cost_amt = pd.Series(np.where(roll_day, new_n.abs() + prev_n.abs(), (new_n - prev_n).abs()),
                          index=weights.index)
    turnover_cost = cost_rate * cost_amt
    roll_cost = turnover_cost.where(roll_day, 0.0)
    gross = notional.shift(2) * ret.shift(1)
    net = gross - turnover_cost
    return pd.DataFrame({"gross": gross, "turnover_cost": turnover_cost, "roll_cost": roll_cost,
                          "net": net, "notional": notional}, index=weights.index)


if __name__ == "__main__":
    vd, vc, spy = load_insample()
    print(f"vx_daily {vd.shape}, {vd.date.min().date()}..{vd.date.max().date()}; SPY {spy.shape}")
    held = held_series(vd, vc)
    rf = roll_flag(held)
    print(f"held rows={len(held)}, rolls={int(rf.sum())}, nan ret_next={held.ret_next.isna().sum()}")
    pos = positions(held["roll"], THETA_FIXED)
    w, cap = size(pos, held["ret_next"])
    pnl = simulate(w, held["ret_next"], held["settle"], rf)
    print(f"theta={THETA_FIXED}: Sharpe(all)={sharpe(pnl['net']):.3f}, cap_binding={cap.mean():.4%}")
