"""Premise 3 core: daily panel, EWMA vol/cov, signals, weights, simulation.

Spec: ../PREMISE_3.md (frozen + Amendment A1, see RESULTS_INSAMPLE.md for the
integrity note on how the Amendment was handled). See TASK.md for file layout.
No lookahead: every quantity decided at month-end t uses data <= t; execution
at close t+1; the position earns returns from t+2 onward (see simulate()).
Pure functions, vectorised pandas/numpy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
OOS_CUTOFF = pd.Timestamp("2024-07-01")

UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ", "TLT", "IEF", "LQD", "HYG",
            "TIP", "GLD", "SLV", "USO", "DBC", "UUP", "FXE", "FXY", "FXA", "VNQ"]
ASSET_CLASS = {**{t: "equities" for t in ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ"]},
               **{t: "bonds" for t in ["TLT", "IEF", "LQD", "HYG", "TIP"]},
               **{t: "commodities" for t in ["GLD", "SLV", "USO", "DBC"]},
               **{t: "currencies" for t in ["UUP", "FXE", "FXY", "FXA"]},
               "VNQ": "real_estate"}
LOW_COST = {"SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "GLD", "VNQ"}
COST_BP = {t: (0.0005 if t in LOW_COST else 0.0010) for t in UNIVERSE}

COM = 60
PER_INSTR_SCALE = 0.40
PORT_VOL_TARGET = 0.10
GROSS_CAP = 3.0
ANNUALIZATION = 252          # trading days/yr; documented interpretation choice, see report
ELIGIBLE_DAYS = 261          # eligible from the 261st trading day of price history
BORROW_ANNUAL = 0.01
BORROW_DAYCOUNT = 360.0      # matches T-bill's actual/360 convention; documented choice
ACCOUNT = 100_000.0
GRID = [3, 6, 12, "COMBO"]


def load_insample_prices(root: str = ROOT) -> pd.DataFrame:
    """Wide adj_close panel (date x ticker). Guard: refuse if any date >= OOS cutoff."""
    df = pd.read_parquet(f"{root}/data_daily/etf_daily_insample.parquet")
    df["date"] = pd.to_datetime(df["date"])
    mx = df["date"].max()
    if mx >= OOS_CUTOFF:
        raise ValueError(f"etf_daily_insample.parquet date.max()={mx} >= {OOS_CUTOFF} -- refusing (OOS leak)")
    px = df.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    return px[UNIVERSE]


def load_insample_rf(calendar: pd.DatetimeIndex, root: str = ROOT) -> pd.Series:
    """Daily risk-free rate (rate_pct/100/360), forward-filled onto `calendar`.

    Loader guard: filters to date < OOS_CUTOFF ourselves (tbill_3m.parquet spans
    the full combined history) and re-asserts the filtered max is still < cutoff.
    """
    tb = pd.read_parquet(f"{root}/data_daily/tbill_3m.parquet")
    tb["date"] = pd.to_datetime(tb["date"])
    tb = tb[tb["date"] < OOS_CUTOFF].sort_values("date")
    if tb["date"].max() >= OOS_CUTOFF:
        raise ValueError("tbill_3m filter failed -- OOS leak")
    rf = tb.set_index("date")["rate_pct"] / 100.0 / 360.0
    return rf.reindex(calendar).ffill()


def daily_excess_returns(px: pd.DataFrame, rf: pd.Series) -> pd.DataFrame:
    """Simple daily returns per ticker minus daily rf; NaN before a ticker's first obs."""
    return px.pct_change().sub(rf, axis=0)


def eligibility(px: pd.DataFrame, min_days: int = ELIGIBLE_DAYS) -> pd.DataFrame:
    """True from each ticker's `min_days`-th valid price observation onward."""
    valid = px.notna()
    return valid & (valid.cumsum() >= min_days)


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last trading day of each calendar month present in `index`."""
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby([index.year, index.month]).max().sort_values())


def ewma_vol_cov(x: pd.DataFrame, com: int = COM):
    """Annualised EWMA vol per ticker and annualised EWMA cross second-moments
    for every (i,j) pair, i<=j (MOP Eq.1 style: raw second moment, zero-mean
    assumption, recursive/adjust=False, NaNs ignored so pre-listing history
    does not contaminate the estimate), using data to and including t.
    """
    tickers = list(x.columns)
    var = (x ** 2).ewm(com=com, adjust=False, ignore_na=True).mean() * ANNUALIZATION
    sigma = np.sqrt(var)
    cols = [(tickers[a], tickers[b]) for a in range(len(tickers)) for b in range(a, len(tickers))]
    prod = pd.DataFrame({c: x[c[0]] * x[c[1]] for c in cols}, index=x.index)
    cov_pairs = prod.ewm(com=com, adjust=False, ignore_na=True).mean() * ANNUALIZATION
    return sigma, cov_pairs


def _cov_tensor(cov_pairs: pd.DataFrame, tickers: list[str]) -> np.ndarray:
    """(T, N, N) covariance tensor built from the upper-triangular pair columns."""
    n = len(tickers)
    col_of, cols = {}, []
    k = 0
    for a in range(n):
        for b in range(a, n):
            col_of[(a, b)] = col_of[(b, a)] = k
            cols.append((tickers[a], tickers[b]))
            k += 1
    arr = cov_pairs[cols].to_numpy()
    idx_map = np.array([[col_of[(a, b)] for b in range(n)] for a in range(n)])
    return arr[:, idx_map]


def _sign_lookback(x: pd.DataFrame, months: int) -> pd.DataFrame:
    window = 21 * months
    return np.sign(x.rolling(window, min_periods=window).sum())


def signals(x: pd.DataFrame, L) -> pd.DataFrame:
    """s_i,t = sign(sum of x_i over last 21*L days); COMBO = mean of the 3/6/12m signs."""
    if L == "COMBO":
        return sum(_sign_lookback(x, m) for m in (3, 6, 12)) / 3.0
    return _sign_lookback(x, int(L))


def signal_tsh(x: pd.DataFrame) -> pd.DataFrame:
    """TSH benchmark: sign of the expanding mean of x from each ticker's own first date."""
    return np.sign(x.expanding(min_periods=1).mean())


def target_weights(sig: pd.DataFrame, sigma: pd.DataFrame, cov_pairs: pd.DataFrame,
                    elig: pd.DataFrame, me: pd.DatetimeIndex):
    """Month-end target weights: 40%/sigma per-instrument scale, 1/N_t, 10% portfolio
    vol target via EWMA covariance, 3x gross cap. Returns (weights, diagnostics), both
    indexed by month-end date `me`.
    """
    tickers = list(sig.columns)
    sig_m, sigma_m, elig_m = sig.reindex(me), sigma.reindex(me), elig.reindex(me).fillna(False)
    n_elig = elig_m.sum(axis=1).astype(float)

    raw = sig_m.where(elig_m, 0.0) * (PER_INSTR_SCALE / sigma_m)
    raw = raw.div(n_elig.replace(0, np.nan), axis=0).fillna(0.0)

    cov_t = _cov_tensor(cov_pairs.reindex(me), tickers)
    var_p = np.einsum("ti,tij,tj->t", raw.to_numpy(), cov_t, raw.to_numpy())
    lam = PORT_VOL_TARGET / np.sqrt(var_p)
    w = raw.mul(lam, axis=0)

    gross = w.abs().sum(axis=1)
    cap_binding = gross > GROSS_CAP
    w = w.mul(np.where(cap_binding, GROSS_CAP / gross, 1.0), axis=0)

    diag = pd.DataFrame({"n_eligible": n_elig, "gross_pre_cap": gross,
                          "cap_binding": cap_binding, "gross_post_cap": w.abs().sum(axis=1)}, index=me)
    return w, diag


def _lagged_positions(weights: pd.DataFrame, x: pd.DataFrame):
    """Shared plumbing for simulate()/pnl_breakdown(): weights decided at month-end
    t (index) are traded at the close of t+1 and earn returns from t+2 onward.
    Returns (held_daily, target_at_exec, w_prev_at_exec, exec_dates).
    """
    dates = x.index
    tickers = list(x.columns)
    pos_of = pd.Series(np.arange(len(dates)), index=dates)

    me_pos = pos_of.reindex(weights.index)
    keep = me_pos.notna() & (me_pos.to_numpy() < len(dates) - 1)
    me_pos = me_pos[keep].astype(int)
    w_dec = weights.loc[keep[keep].index]
    exec_dates = dates[me_pos.to_numpy() + 1]

    target_at_exec = w_dec.copy()
    target_at_exec.index = exec_dates
    w_prev_at_exec = target_at_exec.shift(1).fillna(0.0)
    # missing price on the rebalance day -> keep the prior weight for that instrument
    missing = x.reindex(exec_dates)[tickers].isna()
    target_at_exec = target_at_exec.where(~missing, w_prev_at_exec)

    held = target_at_exec.reindex(dates).ffill().shift(1).fillna(0.0)
    return held, target_at_exec, w_prev_at_exec, exec_dates


def simulate(weights: pd.DataFrame, x: pd.DataFrame, cost_bp: dict | None = None,
             cost_mult: float = 1.0, borrow_annual: float = BORROW_ANNUAL,
             account: float = ACCOUNT) -> pd.DataFrame:
    """Daily $ P&L on `account`. `weights` decided at month-end t (index) are traded at
    the close of the next trading day t+1 and earn returns from t+2's return onward
    (i.e. the day-t+1 return itself, and every day up to and incl. the NEXT execution
    day, is earned by the outgoing weight). Turnover cost is charged on the execution
    day; short borrow accrues daily on whichever weight is earning that day's return
    (same lagged state, i.e. borrow also switches on t+2 -- single unified state
    variable for the book's daily economics, see report).
    """
    cost_bp = cost_bp or COST_BP
    tickers = list(x.columns)
    held, target_at_exec, w_prev_at_exec, _ = _lagged_positions(weights, x)

    turnover_cost = (target_at_exec.sub(w_prev_at_exec).abs()
                     .mul(pd.Series(cost_bp)[tickers].to_numpy() * cost_mult, axis=1)
                     .sum(axis=1)) * account
    gross_pnl = (held[tickers] * x[tickers]).sum(axis=1) * account
    short_notional = held[tickers].clip(upper=0.0).abs().sum(axis=1)
    borrow_cost = short_notional * (borrow_annual / BORROW_DAYCOUNT) * account

    turnover_daily = turnover_cost.reindex(x.index).fillna(0.0)
    net = gross_pnl - turnover_daily - borrow_cost
    return pd.DataFrame({"gross": gross_pnl, "turnover_cost": turnover_daily,
                          "borrow_cost": borrow_cost, "net": net,
                          "held_gross_lev": held[tickers].abs().sum(axis=1)}, index=x.index)


def pnl_breakdown(weights: pd.DataFrame, x: pd.DataFrame, cost_bp: dict | None = None,
                   cost_mult: float = 1.0, borrow_annual: float = BORROW_ANNUAL,
                   account: float = ACCOUNT) -> pd.DataFrame:
    """Per-instrument daily net $ P&L (gross - its share of turnover cost - its
    borrow), for asset-class / long-short attribution. Sums to simulate()'s net."""
    cost_bp = cost_bp or COST_BP
    tickers = list(x.columns)
    held, target_at_exec, w_prev_at_exec, _ = _lagged_positions(weights, x)

    turn_cost_i = (target_at_exec.sub(w_prev_at_exec).abs()
                   .mul(pd.Series(cost_bp)[tickers].to_numpy() * cost_mult, axis=1)) * account
    turn_cost_i = turn_cost_i.reindex(x.index).fillna(0.0)
    gross_i = held[tickers] * x[tickers] * account
    borrow_i = held[tickers].clip(upper=0.0).abs() * (borrow_annual / BORROW_DAYCOUNT) * account
    return gross_i - turn_cost_i - borrow_i


def sharpe(net: pd.Series) -> float:
    net = pd.Series(net, dtype=float)
    sd = net.std(ddof=1)
    if not sd or np.isnan(sd) or sd == 0:
        return float("nan")
    return float(net.mean() / sd * np.sqrt(252))


def max_drawdown(net: pd.Series) -> float:
    cum = pd.Series(net, dtype=float).cumsum()
    dd = cum - cum.cummax()
    return float(dd.min()) if len(dd) else float("nan")


def md_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    px = load_insample_prices()
    print(f"prices: {px.shape}, {px.index.min().date()}..{px.index.max().date()}")
    rf = load_insample_rf(px.index)
    x = daily_excess_returns(px, rf)
    elig = eligibility(px)
    me = month_ends(px.index)
    print(f"month-ends: {len(me)}")

    sigma, cov_pairs = ewma_vol_cov(x)
    sig = signals(x, 12)
    w, diag = target_weights(sig, sigma, cov_pairs, elig, me)
    print(f"L=12: avg N_t eligible = {diag['n_eligible'].mean():.2f}, "
          f"avg gross leverage (post-cap) = {diag['gross_post_cap'].mean():.3f}, "
          f"cap-binding share = {diag['cap_binding'].mean():.3%}")

    pnl = simulate(w, x)
    print(f"L=12 single simulate(): Sharpe = {sharpe(pnl['net']):.3f}, "
          f"net total $ = {pnl['net'].sum():,.0f}, days = {len(pnl)}")
