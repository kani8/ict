"""Premise 4: premise test + fixed-rule + stitched calendar + benchmarks +
sensitivity + permutation + no-lookahead + report.

Run: uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python premise4/run.py
"""
from __future__ import annotations

import io
import time
from contextlib import redirect_stdout

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

import permtest as pt
import test_no_lookahead as tnl
from strategy import (ACCOUNT, THETA_FIXED, THETA_GRID, held_series,
                       load_insample, max_drawdown, md_table, positions,
                       roll_flag, sharpe, simulate, size)

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
STITCH_START, STITCH_END = pd.Timestamp("2010-07-01"), pd.Timestamp("2024-06-30")
GATE_SHARPE = 0.5
N_PERM = 500
PERM_SEED = 42


def test_years():
    return [(pd.Timestamp(f"{y}-07-01"), pd.Timestamp(f"{y + 1}-06-30")) for y in range(2010, 2024)]


def build(held, F, rday, theta, ticks=1):
    pos = positions(held["roll"], theta)
    w, cap = size(pos, held["ret_next"])
    pnl = simulate(w, held["ret_next"], F, rday, ticks=ticks)
    df = pnl.copy()
    df.index = held["date"].to_numpy()
    df["pos"] = pos.to_numpy()
    df["active_pos"] = df["pos"].shift(2)
    df["cap_binding"] = cap.to_numpy()
    return df


def summarize(df):
    net = df["net"]
    years = (df.index[-1] - df.index[0]).days / 365.25
    return dict(sharpe=sharpe(net), ann_return=float(net.sum() / ACCOUNT / years),
                ann_vol=float(net.std(ddof=1) * np.sqrt(252) / ACCOUNT),
                maxdd_pct=float(max_drawdown(net) / ACCOUNT),
                worst_day_pct=float(net.min() / ACCOUNT),
                time_in_mkt=float((df["active_pos"] != 0).mean()))


def ols_nw(y, x, lags):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    X = sm.add_constant(d["x"])
    fit = sm.OLS(d["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return dict(beta=float(fit.params["x"]), t=float(fit.tvalues["x"]),
                r2=float(fit.rsquared), n=int(fit.nobs))


def fwd21(ret_next: pd.Series) -> pd.Series:
    """21-trading-day forward compounded return starting at t (r[t]..r[t+20]).
    NaN (no-settle) days filled 0 for compounding only -- ~35/5116 rows, documented."""
    r = ret_next.fillna(0.0)
    cp = (1 + r).cumprod()
    base = cp.shift(1).fillna(1.0)
    return cp.shift(-20) / base - 1.0


def main():
    t0 = time.time()
    print("loading in-sample data (guarded: refuses any date >= 2024-07-01)...")
    vd, vc, spy = load_insample()
    held = held_series(vd, vc)
    rday = roll_flag(held)
    F = held["settle"]
    first_valid = held["date"][held["ret_next"].notna().cumsum() >= 60].iloc[0]
    fullspan_end = held["date"].max()
    print(f"  held rows={len(held)}, rolls={int(rday.sum())}, nan ret_next={held['ret_next'].isna().sum()}, "
          f"first_valid={first_valid.date()}, fullspan_end={fullspan_end.date()}")

    print("Step 1: premise test (roll_t -> next-day return, NW-5; 21d-fwd NW-21; contango/backw halves)...")
    span = held["date"] >= first_valid
    daily = ols_nw(held["ret_next"].where(span), held["roll"].where(span), 5)
    f21 = ols_nw(fwd21(held["ret_next"]).where(span), held["roll"].where(span), 21)
    d_sample = pd.DataFrame({"roll": held["roll"], "ret_next": held["ret_next"]}).where(span).dropna()
    contango = ols_nw(d_sample.loc[d_sample.roll > 0, "ret_next"], d_sample.loc[d_sample.roll > 0, "roll"], 5)
    backw = ols_nw(d_sample.loc[d_sample.roll < 0, "ret_next"], d_sample.loc[d_sample.roll < 0, "roll"], 5)
    premise_pass = "PASS" if daily["t"] < -2 else "FAIL"

    print("Step 2: fixed rule (theta=0.0050), full span...")
    df_fixed = build(held, F, rday, THETA_FIXED, ticks=1)
    fs = df_fixed.loc[first_valid:fullspan_end]
    fs_stats = summarize(fs)
    trades_yr = float((fs["pos"].diff().fillna(0) != 0).sum() / ((fs.index[-1] - fs.index[0]).days / 365.25))
    roll_cost_share = float(fs["roll_cost"].sum() / fs["turnover_cost"].sum())

    print("Step 3: stitched calendar, 1 tick vs 2 ticks, legs, per-test-year, cap-binding...")
    st = df_fixed.loc[STITCH_START:STITCH_END]
    df_fixed2 = build(held, F, rday, THETA_FIXED, ticks=2)
    st2 = df_fixed2.loc[STITCH_START:STITCH_END]
    st_stats1, st_stats2 = summarize(st), summarize(st2)
    long_pnl = st["net"].where(st["active_pos"] > 0, 0.0)
    short_pnl = st["net"].where(st["active_pos"] < 0, 0.0)
    leg_rows = [dict(leg="long", sharpe=sharpe(long_pnl), total_pnl=float(long_pnl.sum())),
                dict(leg="short", sharpe=sharpe(short_pnl), total_pnl=float(short_pnl.sum()))]
    cap_binding_pct = float(st["cap_binding"].mean()) * 100
    year_rows = []
    for ts, te in test_years():
        seg = st.loc[ts:te]
        year_rows.append(dict(test_year=f"{ts.year}-{te.year}", net_pnl=float(seg["net"].sum()),
                               sharpe=sharpe(seg["net"])))
    pos_years = int(sum(1 for r in year_rows if r["net_pnl"] > 0))

    print("Step 4: benchmarks (always-short/-long, SPY B&H) + correlations...")
    bench = {}
    for name, s_const in [("always-short", -1.0), ("always-long", 1.0)]:
        pos_const = pd.Series(s_const, index=held.index)
        w_c, _ = size(pos_const, held["ret_next"])
        pnl_c = simulate(w_c, held["ret_next"], F, rday, ticks=1)
        pnl_c.index = held["date"].to_numpy()
        pnl_c["active_pos"] = pd.Series(pos_const.to_numpy(), index=pnl_c.index).shift(2)
        bench[name] = pnl_c.loc[STITCH_START:STITCH_END]
    always_short, always_long = bench["always-short"], bench["always-long"]
    spy_ret = spy.pct_change().reindex(st.index)
    spy_pnl = pd.DataFrame({"net": spy_ret * ACCOUNT, "active_pos": 1.0}, index=st.index)
    bench_rows = []
    for name, d in [("timed (theta=0.0050)", st), ("always-short", always_short),
                    ("always-long", always_long), ("SPY B&H", spy_pnl)]:
        s = summarize(d)
        s["name"] = name
        bench_rows.append({k: s[k] for k in ["name", "sharpe", "ann_return", "maxdd_pct", "worst_day_pct"]})
    corr_spy = float(st["net"].corr(spy_pnl["net"]))
    p3 = pd.read_csv(f"{ROOT}/premise3/daily_pnl_wf.csv", parse_dates=["date"]).set_index("date")["net"]
    common = st["net"].index.intersection(p3.index)
    corr_p3 = float(st["net"].loc[common].corr(p3.loc[common]))

    print("Step 5: sensitivity table (theta grid, full-span + stitched + per-test-year Sharpe)...")
    sens_rows = []
    for th in THETA_GRID:
        d = build(held, F, rday, th, ticks=1)
        row = dict(theta=th, fixed_choice=(th == THETA_FIXED),
                   full_span_sharpe=sharpe(d.loc[first_valid:fullspan_end, "net"]),
                   stitched_sharpe=sharpe(d.loc[STITCH_START:STITCH_END, "net"]))
        for ts, te in test_years():
            row[f"y{ts.year}"] = sharpe(d.loc[ts:te, "net"])
        sens_rows.append(row)
    sens_df = pd.DataFrame(sens_rows)
    sens_df.to_csv(f"{ROOT}/premise4/sensitivity.csv", index=False)

    print(f"Step 6: permutation test ({N_PERM} reps, seed={PERM_SEED})...")
    mask = ((held["date"] >= STITCH_START) & (held["date"] <= STITCH_END)).to_numpy()
    pos_fixed = positions(held["roll"], THETA_FIXED)
    real_sh, null_sh, p_perm = pt.permutation_test(held["ret_next"], pos_fixed, F, rday, mask,
                                                    n_reps=N_PERM, seed=PERM_SEED)

    print("Step 7: no-lookahead test...")
    buf = io.StringIO()
    with redirect_stdout(buf):
        tnl.run()
    nolookahead_out = buf.getvalue()
    print(nolookahead_out.strip().splitlines()[-1])

    gate_a = st_stats1["sharpe"] >= GATE_SHARPE
    gate_b = st_stats1["sharpe"] > sharpe(always_short["net"])
    gate_c = pos_years >= 8
    gate_d = p_perm < 0.05
    verdict = "PASS" if (gate_a and gate_b and gate_c and gate_d) else "FAIL"

    print("writing outputs...")
    out = df_fixed.copy()
    out["stitched"] = (out.index >= STITCH_START) & (out.index <= STITCH_END)
    out.to_csv(f"{ROOT}/premise4/daily_pnl.csv", index_label="date")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(st.index, st["net"].cumsum(), label="timed (theta=0.0050)")
    ax.plot(always_short.index, always_short["net"].cumsum(), label="always-short", alpha=0.8)
    ax.plot(always_long.index, always_long["net"].cumsum(), label="always-long", alpha=0.8)
    ax.plot(spy_pnl.index, spy_pnl["net"].cumsum(), label="SPY B&H", alpha=0.8)
    ax.set_title("Premise 4 stitched calendar: cumulative net P&L ($, $100k book)")
    ax.set_xlabel("date"); ax.set_ylabel("cumulative $"); ax.legend(); fig.tight_layout()
    fig.savefig(f"{ROOT}/premise4/equity.png", dpi=120)

    runtime = time.time() - t0
    IMPL = """- vix_spot.parquet is read and guarded (Hard Rule 1) and cross-checked equal to vx_daily's own `vix_close` on every overlapping date (0 mismatches) then not reused: `held_series(vx_daily, contracts)`'s signature (per TASK.md) takes no vix_spot argument, and vx_daily.vix_close IS spot VIX close.
- ret_next(t) is looked up in `vx_contracts` at (t+1, held_expiry(t)), not vx_daily's own f1/f2 columns at t+1 -- on a roll day the outgoing contract is no longer f1 or f2 the next day, so only the raw per-expiry contracts table has its price.
- **EWMA sigma lookahead fix**: sigma_t must use only returns realized by t. Since `ret_next` is indexed by its START date (t -> t+1, per the held-series spec), sigma_t = EWMA(ret_next.shift(1)) -- using ret_next unshifted would leak t+1's settle into the weight decided at t. Caught by design intent of the no-lookahead test.
- Roll-day cost: `simulate()`'s signature is extended with a `roll_day` flag beyond TASK.md's suggested (weights,ret,F,ticks) -- required to distinguish "close+reopen full notional" (roll day) from "trade |Delta notional|" (normal day); TASK.md's own cost description needs this flag, its suggested signature just omitted it. Both legs of a roll are costed at the post-roll contract's own settle (F_t), a simplification since the spec gives one F_t, not separate outgoing/incoming prices.
- 21-day-forward regression: NaN (no-VX-settle) days' return treated as 0 for compounding only (~35/5116 rows); the daily regression and P&L never do this (NaN stays NaN, position carried, per VALIDATION.md).
- "First valid date" = the date by which >=60 non-null ret_next have accumulated since inception (2004-03-26); used as the start of the full-span reporting window (Steps 1-2) and the sensitivity table's full-span column. The state machine/EWMA itself runs continuously from inception (no truncation upstream) -- only the reporting window is trimmed.
- Time-in-market uses the 2-day-lagged active position (what is actually earning that day's P&L), not the raw same-day decided `pos`. Trades/yr = count of days `pos` changes (entry/exit/flip), divided by span years.
- Always-short/-long benchmarks are constant s_t in {-1,+1} with no state machine or NaN-carry logic (trivial by construction); same sizing/cost/roll machinery otherwise. SPY B&H is a pure 100%-weight daily-return series, no cost (context only, per spec)."""

    report = f"""# RESULTS_INSAMPLE.md

**VERDICT: {verdict}** -- stitched net Sharpe (1 tick) = {st_stats1['sharpe']:.3f} (gate a >= {GATE_SHARPE}: {gate_a}); timed {'>' if gate_b else '<='} always-short Sharpe ({sharpe(always_short['net']):.3f}) (gate b: {gate_b}); positive test years = {pos_years}/14 (gate c >= 8: {gate_c}); permutation p = {p_perm:.4f} (gate d < 0.05: {gate_d}).

## Step 1 -- premise test (roll_t -> next-day held-contract return, NW-5 lags; span {first_valid.date()}..{fullspan_end.date()})
{md_table([daily])}
Pass (daily t < -2): {premise_pass}. 21-day-forward (overlapping, NW-21):
{md_table([f21])}
Contango half (roll>0) / backwardation half (roll<0), daily NW-5:
{md_table([{**contango, "half": "contango"}, {**backw, "half": "backwardation"}])}

## Step 2 -- fixed rule (theta=0.0050), full span {first_valid.date()}..{fullspan_end.date()}
{md_table([fs_stats])}
trades/yr = {trades_yr:.2f}. Roll-cost share of total cost = {roll_cost_share:.2%}.

## Step 3 -- stitched calendar {STITCH_START.date()}..{STITCH_END.date()}
Baseline (1 tick) vs stress (2 ticks):
{md_table([{**st_stats1, "regime": "1 tick"}, {**st_stats2, "regime": "2 ticks"}])}
Cap-binding share of days: {cap_binding_pct:.4f}% (expect 0). Long vs short leg:
{md_table(leg_rows)}
P&L and Sharpe by test year (Jul->Jun):
{md_table(year_rows)}

## Step 4 -- benchmarks (same stitched calendar, sizing, costs, rolls)
{md_table(bench_rows)}
corr(timed daily net $, SPY daily $) = {corr_spy:.3f}. corr(timed, premise3 stitched net $) = {corr_p3:.3f} (n={len(common)} overlapping days).

## Step 5 -- sensitivity table (theta grid; full sensitivity.csv has per-test-year columns too)
{md_table([{k: r[k] for k in ["theta", "fixed_choice", "full_span_sharpe", "stitched_sharpe"]} for r in sens_rows])}
This table changes nothing (theta = 0.0050 is fixed regardless of rank here).

## Step 6 -- permutation test ({N_PERM} reps, seed={PERM_SEED}, stitched calendar)
Real Sharpe = {real_sh:.4f}, null mean = {null_sh.mean():.4f}, null sd = {null_sh.std():.4f}, p (share >= real) = {p_perm:.4f}

## Step 7 -- no-lookahead test (theta = 0.0050)
```
{nolookahead_out.strip()}
```
## Implementation choices
{IMPL}
## Runtime
{runtime:.1f}s total (data load+guards, held-series build, premise regressions, fixed-rule full-span + stitched (2 cost regimes), benchmarks, 4-theta sensitivity, {N_PERM}-rep permutation, no-lookahead test, I/O).
"""
    with open(f"{ROOT}/premise4/RESULTS_INSAMPLE.md", "w") as f:
        f.write(report)
    print(f"done in {runtime:.1f}s")
    print(report)


if __name__ == "__main__":
    main()
