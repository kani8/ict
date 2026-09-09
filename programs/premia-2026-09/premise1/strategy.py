"""Premise 1 core: daily-table construction and P&L. Pure functions, no lookahead.

Spec: ../PREMISE_1.md (frozen, incl. Amendment A1). See TASK.md for the exact
column/skip semantics. Everything here operates on ES 1h / 4h in-sample bars
only; the OOS guard lives in load_insample().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

OOS_CUTOFF = pd.Timestamp("2024-07-01", tz="America/New_York")

VOL_HORIZON = np.sqrt(5.5)   # 4h bars from 16:00 ET to next-day 15:00 ET (fixed, per PREMISE_1.md)
MES_MULT = 5.0               # $ per ES/MES index point
TICK = 0.25                  # ES/MES tick size, points
TARGET_VOL = 0.12            # annualized vol target
ACCOUNT = 100_000.0
CAP = 40                      # MES contracts


def load_insample(path: str) -> pd.DataFrame:
    """Load a parquet file, hard-guarding against any OOS leakage."""
    df = pd.read_parquet(path)
    mx = df["ts_et"].max()
    if mx >= OOS_CUTOFF:
        raise ValueError(f"{path}: ts_et.max()={mx} >= {OOS_CUTOFF} -- refusing to load (OOS boundary)")
    return df


def build_daily_table(h1: pd.DataFrame, h4: pd.DataFrame, k: float, L: int) -> pd.DataFrame:
    """One row per ET weekday date that survives all skip rules (Step 1, incl. Amendment A1).

    Skip counts (mutually exclusive, checked in this priority order: p15 ->
    p16 -> prev16 -> roll-crossing -> day-after-early-close) are attached at
    `.attrs["skip_counts"]` since dropped days produce no row.
    """
    h1 = h1.sort_values("ts_et").reset_index(drop=True).copy()
    h1["date"] = h1["ts_et"].dt.date
    h1["hour"] = h1["ts_et"].dt.hour

    dates = pd.Series(sorted(h1["date"].unique()))
    dates = dates[pd.to_datetime(dates).dt.dayofweek < 5].reset_index(drop=True)
    tbl = pd.DataFrame({"date": dates})

    b15 = h1.loc[h1.hour == 15, ["date", "open", "n_1m", "instrument_id"]].rename(
        columns={"open": "P15", "n_1m": "n15", "instrument_id": "instr15"})
    b16 = h1.loc[h1.hour == 16, ["date", "open", "n_1m", "instrument_id"]].rename(
        columns={"open": "P16", "n_1m": "n16", "instrument_id": "instr16"})
    tbl = tbl.merge(b15, on="date", how="left").merge(b16, on="date", how="left")

    # P_prev16: most recent prior date's 16:00 open. Row order is date-sorted
    # weekdays only, so shift+ffill correctly skips over weekends/holidays
    # and any date lacking a 16:00 bar, without lookahead.
    tbl["P_prev16"] = tbl["P16"].shift(1).ffill()
    tbl["instr_prev16"] = tbl["instr16"].shift(1).ffill()

    has_9to12 = set(h1.loc[h1.hour.isin([9, 10, 11, 12]), "date"])
    has_16 = set(b16["date"])
    dts = pd.to_datetime(tbl["date"])
    prev_wd = (dts - pd.to_timedelta(np.where(dts.dt.dayofweek == 0, 3, 1), unit="D")).dt.date
    day_after_early_close = pd.Series(prev_wd).isin(has_9to12).to_numpy() & ~pd.Series(prev_wd).isin(has_16).to_numpy()

    valid_p15 = tbl["P15"].notna() & (tbl["n15"] >= 50)
    valid_p16 = tbl["P16"].notna() & (tbl["n16"] >= 1)
    valid_prev16 = tbl["P_prev16"].notna()
    roll_cross = valid_prev16 & tbl["instr15"].notna() & (tbl["instr15"] != tbl["instr_prev16"])

    reason = np.select(
        [~valid_p15, ~valid_p16, ~valid_prev16, roll_cross, day_after_early_close],
        ["p15_missing_or_thin", "p16_missing", "prev16_missing", "roll_crossing", "day_after_early_close"],
        default="keep",
    )
    reason_order = ["p15_missing_or_thin", "p16_missing", "prev16_missing", "roll_crossing", "day_after_early_close"]
    vc = pd.Series(reason).value_counts().to_dict()
    skip_counts = {r: int(vc.get(r, 0)) for r in reason_order}
    skip_counts["kept"] = int(vc.get("keep", 0))
    skip_counts["candidate_weekdays"] = int(len(tbl))

    tbl = tbl.loc[reason == "keep"].reset_index(drop=True)
    tbl["r_sofar"] = np.log(tbl["P15"] / tbl["P_prev16"])
    tbl["r_trade"] = np.log(tbl["P16"] / tbl["P15"])

    # --- 4h volatility: strictly backward-looking (Step 1 subtle point) ---
    h4 = h4.sort_values("ts_et").reset_index(drop=True).copy()
    h4["date"] = h4["ts_et"].dt.date
    h4["hour"] = h4["ts_et"].dt.hour
    h4["logret"] = np.log(h4["close"] / h4["close"].shift(1))
    h4["sigma4h"] = h4["logret"].rolling(L, min_periods=L).std()
    # the "10:00" 4h bar covers [10:00,14:00) ET; its rolling std uses only
    # bars up to and including itself, i.e. only data available by 14:00,
    # strictly before the 15:00 decision.
    b10 = h4.loc[h4.hour == 10, ["date", "sigma4h"]]
    tbl = tbl.merge(b10, on="date", how="left").rename(columns={"sigma4h": "sigma_4h"})

    tbl["sigma_day"] = tbl["sigma_4h"] * VOL_HORIZON
    tbl["sigma_1h"] = tbl["sigma_4h"] / 2.0
    tbl["z"] = tbl["r_sofar"] / tbl["sigma_day"]
    tbl["dir"] = np.where(tbl["z"].abs() >= k, np.sign(tbl["z"]), 0.0)

    notional = (TARGET_VOL / np.sqrt(252) * ACCOUNT) / tbl["sigma_1h"]
    contracts_raw = np.round(notional / (MES_MULT * tbl["P15"]))
    tbl["contracts_raw"] = contracts_raw
    tbl["contracts"] = contracts_raw.clip(lower=0, upper=CAP)
    tbl["cap_bound"] = (tbl["dir"] != 0) & (contracts_raw > CAP)
    tbl["rounded_to_zero"] = (tbl["dir"] != 0) & (tbl["contracts"] == 0)
    tbl["is_trade"] = (tbl["dir"] != 0) & (tbl["contracts"] > 0)

    out = tbl[["date", "P15", "P16", "P_prev16", "r_sofar", "r_trade",
               "sigma_4h", "sigma_day", "sigma_1h", "z", "dir",
               "contracts_raw", "contracts", "cap_bound", "rounded_to_zero", "is_trade"]].reset_index(drop=True)
    out.attrs["skip_counts"] = skip_counts
    out.attrs["k"] = k
    out.attrs["L"] = L
    return out


def pnl(daily_table: pd.DataFrame, slippage_ticks: float, fee_rt: float) -> pd.DataFrame:
    """Add gross/slippage/fees/net columns. net = 0 on non-trade rows (Step 2)."""
    df = daily_table.copy()
    gross = df["dir"] * (df["P16"] - df["P15"]) * MES_MULT * df["contracts"]
    slippage = slippage_ticks * TICK * MES_MULT * 2 * df["contracts"]
    fees = fee_rt * df["contracts"]
    net = gross - slippage - fees
    trade = df["is_trade"]
    df["gross"] = np.where(trade, gross, 0.0)
    df["slippage"] = np.where(trade, slippage, 0.0)
    df["fees"] = np.where(trade, fees, 0.0)
    df["net"] = np.where(trade, net, 0.0)
    return df


def sharpe(net: pd.Series) -> float:
    """Annualized Sharpe over the full series (incl. zero/no-trade rows)."""
    net = pd.Series(net, dtype=float)
    sd = net.std(ddof=1)
    if not sd or np.isnan(sd) or sd == 0:
        return float("nan")
    return float(net.mean() / sd * np.sqrt(252))


def max_drawdown(net: pd.Series) -> float:
    """Max drawdown ($) on cumulative net P&L."""
    cum = pd.Series(net, dtype=float).cumsum()
    dd = cum - cum.cummax()
    return float(dd.min()) if len(dd) else float("nan")


def ols_hac(df: pd.DataFrame, x: str = "r_sofar", y: str = "r_trade", lags: int = 5):
    """OLS y ~ x with Newey-West HAC SE. Returns (beta, t, r2, n)."""
    import statsmodels.api as sm

    d = df[[x, y]].dropna()
    X = sm.add_constant(d[x])
    fit = sm.OLS(d[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.params[x]), float(fit.tvalues[x]), float(fit.rsquared), int(fit.nobs)


def matched_null(stitched: pd.DataFrame, slippage_ticks: float, fee_rt: float,
                  n_reps: int = 2000, seed: int = 13):
    """Step 5: randomize trade direction, recompute stitched Sharpe, n_reps times.

    Keeps dates and contract counts fixed. Returns (actual_sharpe, null_sharpes, p_value)
    where p_value = fraction of null Sharpes >= actual (one-sided).
    """
    n_total = len(stitched)
    trades = stitched.loc[stitched["is_trade"]]
    base_move = ((trades["P16"] - trades["P15"]) * MES_MULT * trades["contracts"]).to_numpy()
    cost = (slippage_ticks * TICK * MES_MULT * 2 * trades["contracts"] + fee_rt * trades["contracts"]).to_numpy()

    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_reps, len(trades)))
    net_mat = signs * base_move[None, :] - cost[None, :]
    mean_full = net_mat.sum(axis=1) / n_total
    sumsq_full = (net_mat ** 2).sum(axis=1)
    var_full = (sumsq_full - n_total * mean_full ** 2) / (n_total - 1)
    null_sharpes = mean_full / np.sqrt(var_full) * np.sqrt(252)

    actual = sharpe(stitched["net"])
    p_value = float((null_sharpes >= actual).mean())
    return actual, null_sharpes, p_value


if __name__ == "__main__":
    ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
    h1 = load_insample(f"{ROOT}/data/es_1h_insample.parquet")
    h4 = load_insample(f"{ROOT}/data/es_4h_insample.parquet")
    print(f"h1 rows={len(h1)} h4 rows={len(h4)}")
    dt = build_daily_table(h1, h4, k=0.5, L=30)
    print(dt.head())
    print("rows:", len(dt))
    print("skip_counts:", dt.attrs["skip_counts"])
    p = pnl(dt, slippage_ticks=1, fee_rt=1.00)
    print("trades:", int(p["is_trade"].sum()), "sharpe:", sharpe(p["net"]))
