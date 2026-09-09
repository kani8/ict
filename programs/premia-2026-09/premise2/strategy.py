"""Premise 2 core: (date, decision-hour) frame construction and simulation.

Spec: ../PREMISE_2.md (frozen). See TASK.md for the exact rule/skip semantics.
load_insample/sharpe/max_drawdown/ols_hac are copied UNCHANGED from
premise1/strategy.py (see PREMISE_2 TASK.md: "reuse ... by importing or
copying"). Everything else (build_day_frame, simulate, matched_null_legs) is
new, adapted to the per-leg / per-(date,t) structure of this premise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

OOS_CUTOFF = pd.Timestamp("2024-07-01", tz="America/New_York")
MES_MULT = 5.0                # $ per ES/MES index point
TICK = 0.25                   # ES/MES tick size, points
TARGET_VOL = 0.12             # annualized vol target
ACCOUNT = 100_000.0
CAP = 40                       # MES contracts
SIGMA4H_WINDOW = 30            # fixed a priori (sizing vol), NOT the N grid
DECISION_HOURS = [10, 11, 12, 13, 14, 15]


def load_insample(path: str) -> pd.DataFrame:
    """Load a parquet file, hard-guarding against any OOS leakage. (copied from premise1)"""
    df = pd.read_parquet(path)
    mx = df["ts_et"].max()
    if mx >= OOS_CUTOFF:
        raise ValueError(f"{path}: ts_et.max()={mx} >= {OOS_CUTOFF} -- refusing to load (OOS boundary)")
    return df


def sharpe(net: pd.Series) -> float:
    """Annualized Sharpe over the full series (incl. zero/no-trade rows). (copied from premise1)"""
    net = pd.Series(net, dtype=float)
    sd = net.std(ddof=1)
    if not sd or np.isnan(sd) or sd == 0:
        return float("nan")
    return float(net.mean() / sd * np.sqrt(252))


def max_drawdown(net: pd.Series) -> float:
    """Max drawdown ($) on cumulative net P&L. (copied from premise1)"""
    cum = pd.Series(net, dtype=float).cumsum()
    dd = cum - cum.cummax()
    return float(dd.min()) if len(dd) else float("nan")


def ols_hac(df: pd.DataFrame, x: str, y: str, lags: int = 5):
    """OLS y ~ x with Newey-West HAC SE. Returns (beta, t, r2, n). (copied from premise1)"""
    import statsmodels.api as sm

    d = df[[x, y]].dropna()
    X = sm.add_constant(d[x])
    fit = sm.OLS(d[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.params[x]), float(fit.tvalues[x]), float(fit.rsquared), int(fit.nobs)


def build_day_frame(m1: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, m: float, N: int) -> pd.DataFrame:
    """One row per (date, t) for t in DECISION_HOURS, for every date that survives
    the day-level skips. Carries O, C_prev, P16, close_t, fill_open (open of bar
    [t,t+1)), sigma_t, sigma_4h, Upper_t/Lower_t, target, and validity flags.
    """
    h1 = h1.sort_values("ts_et").reset_index(drop=True).copy()
    h1["date"] = h1["ts_et"].dt.date
    h1["hour"] = h1["ts_et"].dt.hour

    dates = pd.Series(sorted(h1["date"].unique()))
    dates = dates[pd.to_datetime(dates).dt.dayofweek < 5].reset_index(drop=True)
    uni = pd.DataFrame({"date": dates})

    o930 = m1.loc[(m1["ts_et"].dt.hour == 9) & (m1["ts_et"].dt.minute == 30)].copy()
    o930["date"] = o930["ts_et"].dt.date
    o930 = o930[["date", "open"]].drop_duplicates("date").rename(columns={"open": "O"})
    uni = uni.merge(o930, on="date", how="left")

    for h in range(9, 17):
        b = h1.loc[h1.hour == h, ["date", "open", "close", "n_1m", "instrument_id"]].rename(
            columns={"open": f"open_{h}", "close": f"close_{h}", "n_1m": f"n1m_{h}", "instrument_id": f"instr_{h}"})
        uni = uni.merge(b, on="date", how="left")

    instr_cols = [f"instr_{h}" for h in range(9, 17)]
    uni["instr_today"] = uni[instr_cols].bfill(axis=1).iloc[:, 0]
    uni["P16"] = uni["open_16"]
    uni["C_prev"] = uni["P16"].shift(1).ffill()
    uni["instr_prev16"] = uni["instr_16"].shift(1).ffill()

    has_9to12 = set(h1.loc[h1.hour.isin([9, 10, 11, 12]), "date"])
    has_16 = set(uni.loc[uni["open_16"].notna(), "date"])
    dts = pd.to_datetime(uni["date"])
    prev_wd = (dts - pd.to_timedelta(np.where(dts.dt.dayofweek == 0, 3, 1), unit="D")).dt.date
    day_after_early_close = pd.Series(prev_wd).isin(has_9to12).to_numpy() & ~pd.Series(prev_wd).isin(has_16).to_numpy()

    valid_O = uni["O"].notna()
    valid_p16 = uni["open_16"].notna()
    valid_prev16 = uni["C_prev"].notna()
    roll_cross = valid_prev16 & uni["instr_today"].notna() & (uni["instr_today"] != uni["instr_prev16"])

    reason = np.select(
        [~valid_O, ~valid_p16, ~valid_prev16, roll_cross, day_after_early_close],
        ["no_0930_bar", "no_1600_bar", "prev16_missing", "roll_crossing", "day_after_early_close"],
        default="keep",
    )
    reason_order = ["no_0930_bar", "no_1600_bar", "prev16_missing", "roll_crossing", "day_after_early_close"]
    vc = pd.Series(reason).value_counts().to_dict()
    skip_counts = {r: int(vc.get(r, 0)) for r in reason_order}
    skip_counts["kept"] = int(vc.get("keep", 0))
    skip_counts["candidate_weekdays"] = int(len(uni))

    # --- sigma_4h: fixed 30-bar rolling std of 4h log returns, value as of the
    # [10:00,14:00) 4h bar (ends by 14:00 ET, strictly before any decision uses it).
    h4 = h4.sort_values("ts_et").reset_index(drop=True).copy()
    h4["date"] = h4["ts_et"].dt.date
    h4["logret"] = np.log(h4["close"] / h4["close"].shift(1))
    h4["sigma4h"] = h4["logret"].rolling(SIGMA4H_WINDOW, min_periods=SIGMA4H_WINDOW).std()
    b10 = h4.loc[h4["ts_et"].dt.hour == 10, ["date", "sigma4h"]]
    uni = uni.merge(b10, on="date", how="left").rename(columns={"sigma4h": "sigma_4h"})

    # --- sigma_t per decision hour: mean of prior N valid |close_{d-i,t}/O_{d-i}-1|,
    # over ALL candidate weekdays with a valid O and a valid close at t (independent
    # of whether that day survives the unrelated skips above -- see report notes).
    for t in DECISION_HOURS:
        hc = t - 1
        ok = uni["O"].notna() & uni[f"close_{hc}"].notna() & uni[f"n1m_{hc}"].fillna(0).ge(50)
        val = np.where(ok, (uni[f"close_{hc}"] / uni["O"] - 1).abs(), np.nan)
        comp = pd.DataFrame({"date": uni["date"], "val": val}).dropna().sort_values("date")
        comp["roll"] = comp["val"].rolling(N, min_periods=N).mean()
        left = pd.DataFrame({"date": pd.to_datetime(uni["date"])})
        right = comp[["date", "roll"]].assign(date=pd.to_datetime(comp["date"]))
        sig = pd.merge_asof(left, right, on="date", direction="backward", allow_exact_matches=False)["roll"]
        uni[f"sigma_{t}"] = sig.to_numpy()

    uni["sigma_any_nan"] = uni[[f"sigma_{t}" for t in DECISION_HOURS]].isna().any(axis=1)

    kept = uni.loc[reason == "keep"].reset_index(drop=True)

    frames = []
    for t in DECISION_HOURS:
        cols = ["date", "O", "C_prev", "P16", "sigma_4h", "sigma_any_nan",
                f"open_{t}", f"close_{t-1}", f"n1m_{t-1}", f"sigma_{t}"]
        sub = kept[cols].rename(columns={f"open_{t}": "fill_open", f"close_{t-1}": "close_t",
                                          f"n1m_{t-1}": "n1m_dec", f"sigma_{t}": "sigma_t"})
        sub["t"] = t
        frames.append(sub)
    day_frame = pd.concat(frames, ignore_index=True).sort_values(["date", "t"]).reset_index(drop=True)

    day_frame["close_ok"] = day_frame["close_t"].notna() & day_frame["n1m_dec"].fillna(0).ge(50)
    day_frame["band_ok"] = day_frame["sigma_t"].notna() & ~day_frame["sigma_any_nan"]
    day_frame["usable"] = day_frame["close_ok"] & day_frame["band_ok"]

    anchor_hi = np.maximum(day_frame["O"], day_frame["C_prev"])
    anchor_lo = np.minimum(day_frame["O"], day_frame["C_prev"])
    day_frame["Upper_t"] = anchor_hi * (1 + m * day_frame["sigma_t"])
    day_frame["Lower_t"] = anchor_lo * (1 - m * day_frame["sigma_t"])

    target = pd.Series(np.nan, index=day_frame.index)
    u = day_frame["usable"]
    target.loc[u & (day_frame["close_t"] > day_frame["Upper_t"])] = 1.0
    target.loc[u & (day_frame["close_t"] < day_frame["Lower_t"])] = -1.0
    day_frame["target"] = target

    day_frame.attrs["skip_counts"] = skip_counts
    day_frame.attrs["m"] = m
    day_frame.attrs["N"] = N
    return day_frame


def simulate(day_frame: pd.DataFrame, slippage_ticks: float, fee_rt: float):
    """Step 2 state machine. Returns (trades_df, daily_pnl_df); one trades row
    per closed leg, daily_pnl_df has one row per kept date (0 net on no-trade days).
    """
    df = day_frame.sort_values(["date", "t"]).reset_index(drop=True)
    trades, daily_net, daily_rtz, daily_sig = [], {}, {}, {}

    def leg_row(date, entry_t, exit_t, direction, contracts, entry_px, exit_px, reason, cap_flag):
        gross = direction * (exit_px - entry_px) * MES_MULT * contracts
        slip = slippage_ticks * TICK * MES_MULT * 2 * contracts
        fees = fee_rt * contracts
        net = gross - slip - fees
        daily_net[date] = daily_net.get(date, 0.0) + net
        return dict(date=date, entry_t=entry_t, exit_t=exit_t, dir=direction, contracts=contracts,
                    entry_px=entry_px, exit_px=exit_px, gross=gross, slippage=slip, fees=fees,
                    net=net, exit_reason=reason, cap_bound=cap_flag)

    for date, g in df.groupby("date", sort=False):
        daily_net.setdefault(date, 0.0)
        daily_rtz.setdefault(date, 0)
        daily_sig.setdefault(date, 0)
        pos_dir = pos_contracts = 0.0
        pos_entry_px = pos_entry_t = pos_cap = None
        for _, row in g.iterrows():
            tgt = row["target"]
            if pd.isna(tgt) or tgt == pos_dir:
                continue
            fill = row["fill_open"]
            if pd.isna(fill) or pd.isna(row["sigma_4h"]):
                continue  # can't execute or size without a fill price / sigma_4h -- hold (conservative)
            daily_sig[date] += 1
            h_rem = 16 - row["t"]
            sigma_hold = row["sigma_4h"] * np.sqrt(h_rem / 4.0)
            if not sigma_hold > 0:
                continue
            notional = (TARGET_VOL / np.sqrt(252) * ACCOUNT) / sigma_hold
            raw = notional / (MES_MULT * fill)
            cap_flag = raw > CAP
            contracts = float(np.clip(np.round(raw), 0, CAP))
            if contracts == 0:
                daily_rtz[date] += 1
                continue  # rounds to zero -- no execution, position unchanged
            if pos_dir != 0:
                trades.append(leg_row(date, pos_entry_t, row["t"], pos_dir, pos_contracts,
                                       pos_entry_px, fill, "flip", pos_cap))
            pos_dir, pos_contracts, pos_entry_px, pos_entry_t, pos_cap = tgt, contracts, fill, row["t"], cap_flag
        if pos_dir != 0:
            trades.append(leg_row(date, pos_entry_t, 16, pos_dir, pos_contracts,
                                   pos_entry_px, g["P16"].iloc[0], "close", pos_cap))

    trades_df = pd.DataFrame(trades)
    daily_pnl_df = pd.DataFrame({
        "date": list(daily_net), "net": list(daily_net.values()),
        "rounded_to_zero": [daily_rtz[d] for d in daily_net], "n_signals": [daily_sig[d] for d in daily_net],
    }).sort_values("date").reset_index(drop=True)
    return trades_df, daily_pnl_df


def matched_null_legs(trades_df: pd.DataFrame, daily_pnl_df: pd.DataFrame,
                       slippage_ticks: float, fee_rt: float, n_reps: int = 2000, seed: int = 13):
    """Step 5: randomize `dir` per leg (dates/times/contracts/prices fixed),
    recompute stitched daily Sharpe, n_reps times. One-sided p = P(null >= actual).
    Adapted from premise1.matched_null's numpy vectorization to leg-level data.
    """
    all_days = np.array(sorted(daily_pnl_df["date"]))
    n_days = len(all_days)
    day_pos = np.searchsorted(all_days, trades_df["date"].to_numpy())

    base_move = ((trades_df["exit_px"] - trades_df["entry_px"]) * MES_MULT * trades_df["contracts"]).to_numpy()
    cost = (slippage_ticks * TICK * MES_MULT * 2 * trades_df["contracts"] + fee_rt * trades_df["contracts"]).to_numpy()

    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_reps, len(trades_df)))
    net_leg = signs * base_move[None, :] - cost[None, :]

    daily_null = np.zeros((n_reps, n_days))
    for r in range(n_reps):
        daily_null[r] = np.bincount(day_pos, weights=net_leg[r], minlength=n_days)

    mean_full = daily_null.mean(axis=1)
    var_full = daily_null.var(axis=1, ddof=1)
    null_sharpes = mean_full / np.sqrt(var_full) * np.sqrt(252)

    actual = sharpe(daily_pnl_df["net"])
    p_value = float((null_sharpes >= actual).mean())
    return actual, null_sharpes, p_value


if __name__ == "__main__":
    ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
    print("loading in-sample data...")
    m1 = load_insample(f"{ROOT}/data/es_1m_insample.parquet")
    h1 = load_insample(f"{ROOT}/data/es_1h_insample.parquet")
    h4 = load_insample(f"{ROOT}/data/es_4h_insample.parquet")
    print(f"m1 rows={len(m1)} h1 rows={len(h1)} h4 rows={len(h4)}")

    df = build_day_frame(m1, h1, h4, m=1.0, N=14)
    print(df.head(12))
    print("rows:", len(df), "  dates:", df["date"].nunique())
    print("skip_counts:", df.attrs["skip_counts"])
    share = float((df["target"].abs() == 1).mean())
    print(f"share of (d,t) rows with a +-1 target at m=1,N=14: {share:.4f}  (n breached={int((df['target'].abs()==1).sum())} of {len(df)})")

    print("running first simulate() pass (baseline costs)...")
    trades_df, daily_pnl_df = simulate(df, slippage_ticks=1, fee_rt=1.00)
    print("trades:", len(trades_df), " days:", len(daily_pnl_df), " sharpe:", sharpe(daily_pnl_df["net"]))
    print(trades_df.head())
