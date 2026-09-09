"""Premise 5 core: FX carry (XS/TS/BOTH) + bond term-spread sleeves, leg assembly.

Spec: ../PREMISE_5.md (frozen + Amendment A1 fixing FX variant=XS with zero free
parameters, + Amendment A2 missing-rate carry-forward <=6 months). See TASK.md.
No lookahead: carry_i(t) uses rate(m-1); bond signal uses last yield <= t; weights
decided at month-end t execute at close t+1 (P3 convention, via simulate()).

Reuses ../premise3/strategy.py directly (loaded by file path -- premise3 has no
internal relative imports, so no sys.path / module-name collision risk with this
package's own strategy.py/permtest.py): EWMA vol/cov, the covariance-tensor
slicer, simulate(), sharpe/max_drawdown/md_table, month_ends, daily_excess_returns,
load_insample_rf, and the sizing constants (COM, PORT_VOL_TARGET, GROSS_CAP,
BORROW_ANNUAL, BORROW_DAYCOUNT, ACCOUNT, OOS_CUTOFF).
"""
from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"

_spec = importlib.util.spec_from_file_location("p3strategy", f"{ROOT}/premise3/strategy.py")
p3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p3)

OOS_CUTOFF = p3.OOS_CUTOFF
ACCOUNT, COM = p3.ACCOUNT, p3.COM
PORT_VOL_TARGET, GROSS_CAP = p3.PORT_VOL_TARGET, p3.GROSS_CAP
BORROW_ANNUAL, BORROW_DAYCOUNT = p3.BORROW_ANNUAL, p3.BORROW_DAYCOUNT
sharpe, max_drawdown, md_table = p3.sharpe, p3.max_drawdown, p3.md_table
month_ends, daily_excess_returns = p3.month_ends, p3.daily_excess_returns
ewma_vol_cov, simulate, _cov_tensor = p3.ewma_vol_cov, p3.simulate, p3._cov_tensor
load_insample_rf = p3.load_insample_rf
pnl_breakdown, _lagged_positions = p3.pnl_breakdown, p3._lagged_positions

FX = ["FXE", "FXY", "FXA", "FXB", "FXC", "FXF"]
BONDS = ["IEF", "TLT"]
UNIVERSE = FX + BONDS
CCY_OF = {"FXE": "EUR", "FXY": "JPY", "FXA": "AUD", "FXB": "GBP", "FXC": "CAD", "FXF": "CHF"}
COST_BP = {**{t: 0.0010 for t in FX}, **{t: 0.0005 for t in BONDS}}  # 10bp FX / 5bp bonds
BOND_SCALE = 0.40       # PREMISE_5 bond sleeve per-instrument scale (= P3's PER_INSTR_SCALE)
MAX_CARRY_GAP = 6       # Amendment A2: carry-forward a missing monthly rate <=6 months


def load_insample_etf_prices(root: str = ROOT) -> pd.DataFrame:
    """Wide adj_close panel (date x ticker) for the 8-instrument carry universe.
    Guard: refuse if any date >= OOS_CUTOFF."""
    df = pd.read_parquet(f"{root}/data_carry/etf_daily_insample.parquet")
    df["date"] = pd.to_datetime(df["date"])
    mx = df["date"].max()
    if mx >= OOS_CUTOFF:
        raise ValueError(f"etf_daily_insample date.max()={mx} >= {OOS_CUTOFF} -- refusing (OOS leak)")
    return df.pivot(index="date", columns="ticker", values="adj_close").sort_index()[UNIVERSE]


def load_rates_monthly(root: str = ROOT) -> pd.DataFrame:
    """Wide monthly rate_pct panel (month x ccy). Rule 1: filter to date < cutoff
    ourselves (rates_3m_monthly is a signal series, not itself in/oos split)."""
    df = pd.read_parquet(f"{root}/data_carry/rates_3m_monthly.parquet")
    df["month"] = pd.to_datetime(df["month"])
    df = df[df["month"] < OOS_CUTOFF]
    return df.pivot(index="month", columns="ccy", values="rate_pct").sort_index()


def load_yields_daily(root: str = ROOT) -> pd.DataFrame:
    """Wide daily yield panel (date x series: DGS10/DGS20/DTB3), filtered to date < cutoff."""
    df = pd.read_parquet(f"{root}/data_carry/yields_daily.parquet")
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] < OOS_CUTOFF]
    return df.pivot(index="date", columns="series", values="pct").sort_index()


def load_spy(root: str = ROOT) -> pd.Series:
    """SPY adj_close only, from the shared daily panel. Guard: refuse OOS leak."""
    df = pd.read_parquet(f"{root}/data_daily/adj_close_wide_insample.parquet")
    df.index = pd.to_datetime(df.index)
    if df.index.max() >= OOS_CUTOFF:
        raise ValueError(f"adj_close_wide_insample date.max()={df.index.max()} >= {OOS_CUTOFF} -- refusing")
    return df["SPY"]


def _asof(s: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """Last non-NaN value of `s` on or before each date in `dates` (no lookahead)."""
    s = s.dropna().sort_index()
    pos = s.index.searchsorted(np.asarray(dates), side="right") - 1
    vals = np.where(pos >= 0, s.to_numpy()[np.clip(pos, 0, None)], np.nan)
    return pd.Series(vals, index=dates)


def fx_carry(rates: pd.DataFrame, me: pd.DatetimeIndex):
    """carry_i(t) = rate_ccy(m-1) - rate_USD(m-1), m = month containing t, one-month
    lag, each rate carried forward up to MAX_CARRY_GAP months (Amendment A2); beyond
    that carry_i(t) is NaN (fx_weights zeroes it that month). Returns (carry, missing,
    used_forward): missing/used_forward are boolean DataFrames (me x FX ticker) for
    the "how often" report.
    """
    full_idx = pd.date_range(rates.index.min(), rates.index.max(), freq="MS")
    r = rates.reindex(full_idx)
    filled = r.ffill(limit=MAX_CARRY_GAP)
    was_missing = r.isna()
    used_cf = was_missing & filled.notna()
    still_missing = filled.isna()
    lag = (me.to_period("M") - 1).to_timestamp()
    f = filled.reindex(lag).set_axis(me)
    u = used_cf.reindex(lag).set_axis(me)
    s = still_missing.reindex(lag).set_axis(me)
    carry = pd.DataFrame({t: f[c] - f["USD"] for t, c in CCY_OF.items()}, index=me)
    missing = pd.DataFrame({t: s[c] | s["USD"] for t, c in CCY_OF.items()}, index=me)
    used_forward = pd.DataFrame({t: (u[c] | u["USD"]) & ~missing[t] for t, c in CCY_OF.items()}, index=me)
    return carry.where(~missing, np.nan), missing, used_forward


def bond_signal(yields: pd.DataFrame, me: pd.DatetimeIndex) -> pd.DataFrame:
    """s_IEF = sign(DGS10_t - DTB3_t), s_TLT = sign(DGS20_t - DTB3_t), last obs <= t."""
    dgs10, dgs20, dtb3 = (_asof(yields[c], me) for c in ("DGS10", "DGS20", "DTB3"))
    return pd.DataFrame({"IEF": np.sign(dgs10 - dtb3), "TLT": np.sign(dgs20 - dtb3)}, index=me)


def fx_weights(carry: pd.DataFrame, variant: str) -> pd.DataFrame:
    """XS: rank(carry)-(n_avail+1)/2 (=rank-3.5 when all 6 available), Sigma|w|=1.
    TS: sign(carry)/6 (fixed denominator, no renormalisation -- see report). BOTH:
    average of the two, renormalised. Missing carry (Amendment A2) -> weight 0.
    """
    avail = carry.notna()
    n = avail.sum(axis=1).replace(0, np.nan)
    xs = carry.rank(axis=1, method="average").sub((n + 1) / 2.0, axis=0).where(avail, 0.0)
    xs = xs.div(xs.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    if variant == "XS":
        return xs
    ts = (np.sign(carry) / 6.0).where(avail, 0.0)
    if variant == "TS":
        return ts
    both = 0.5 * (xs + ts)
    return both.div(both.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def bond_weights(sig: pd.DataFrame, sigma_m: pd.DataFrame) -> pd.DataFrame:
    """w~_j = s_j * (BOND_SCALE / sigma_j) / 2, pre-portfolio-scaling."""
    return sig[BONDS] * (BOND_SCALE / sigma_m[BONDS]) / 2.0


def _scale_cap(raw: pd.DataFrame, cov_tensor: np.ndarray):
    """lambda = PORT_VOL_TARGET / sqrt(w~'Sigma w~); 3x gross cap. Returns (w, diag)."""
    arr = raw.to_numpy()
    var_p = np.einsum("ti,tij,tj->t", arr, cov_tensor, arr)
    with np.errstate(invalid="ignore"):
        lam = PORT_VOL_TARGET / np.sqrt(var_p)
        w = arr * lam[:, None]
        gross = np.abs(w).sum(axis=1)
        binding = gross > GROSS_CAP
        w = w * np.where(binding, GROSS_CAP / gross, 1.0)[:, None]
    wdf = pd.DataFrame(w, index=raw.index, columns=raw.columns)
    diag = pd.DataFrame({"gross_pre_cap": gross, "cap_binding": binding,
                          "gross_post_cap": np.abs(w).sum(axis=1)}, index=raw.index)
    return wdf, diag


def sleeve(raw: pd.DataFrame, x: pd.DataFrame, cov_pairs: pd.DataFrame, cost_mult: float = 1.0):
    """Size one sleeve's raw signal weights (10% vol target, 3x cap) and simulate it."""
    tickers = list(raw.columns)
    cov_t = _cov_tensor(cov_pairs.reindex(raw.index), tickers)
    w, diag = _scale_cap(raw, cov_t)
    pnl = simulate(w, x[tickers], cost_bp={t: COST_BP[t] for t in tickers}, cost_mult=cost_mult)
    return w, diag, pnl


def build_leg(x: pd.DataFrame, fx_raw: pd.DataFrame, bond_raw: pd.DataFrame,
              cov_pairs: pd.DataFrame, cost_mult: float = 1.0) -> dict:
    """Leg = 1/2 FX-sleeve $P&L + 1/2 bond-sleeve $P&L (fixed equal weight)."""
    w_fx, diag_fx, pnl_fx = sleeve(fx_raw, x, cov_pairs, cost_mult)
    w_bd, diag_bd, pnl_bd = sleeve(bond_raw, x, cov_pairs, cost_mult)
    leg_net = 0.5 * pnl_fx["net"] + 0.5 * pnl_bd["net"]
    leg_gross = 0.5 * pnl_fx["held_gross_lev"] + 0.5 * pnl_bd["held_gross_lev"]
    return dict(fx=dict(w=w_fx, diag=diag_fx, pnl=pnl_fx),
                bond=dict(w=w_bd, diag=diag_bd, pnl=pnl_bd),
                leg_net=leg_net, leg_gross=leg_gross)
