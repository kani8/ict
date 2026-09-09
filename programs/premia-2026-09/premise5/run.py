"""Premise 5: premise test + fixed-rule leg + benchmarks + sensitivity + null test.

Run: uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python premise5/run.py
"""
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

import permtest as pt
import strategy as s

ROOT = s.ROOT
STITCH_START, STITCH_END = pd.Timestamp("2010-07-01"), pd.Timestamp("2024-06-30")
GATE_SHARPE = 0.5
N_PERM = 500
VARIANTS = ["XS", "TS", "BOTH"]


def test_year_windows():
    return [(pd.Timestamp(f"{y}-07-01"), pd.Timestamp(f"{y + 1}-06-30")) for y in range(2010, 2024)]


def ols_cluster(panel, xcol, ycol, cluster):
    d = panel[[xcol, ycol, cluster]].dropna()
    X = sm.add_constant(d[xcol])
    fit = sm.OLS(d[ycol], X).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})
    return float(fit.params[xcol]), float(fit.tvalues[xcol]), float(fit.rsquared), int(fit.nobs)


def ols_nw(d, xcol, ycol, lags=3):
    d = d[[xcol, ycol]].dropna()
    X = sm.add_constant(d[xcol])
    fit = sm.OLS(d[ycol], X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.params[xcol]), float(fit.tvalues[xcol]), float(fit.rsquared), int(fit.nobs)


def fx_premise_panel(x, sigma, carry, me):
    next_ret = x[s.FX].cumsum().reindex(me).diff().shift(-1)
    sigma_m = sigma.reindex(me)
    frames = [pd.DataFrame({"month": me, "ticker": t,
                             "y": (next_ret[t] / sigma_m[t]).to_numpy(),
                             "carry": carry[t].to_numpy()}) for t in s.FX]
    panel = pd.concat(frames, ignore_index=True)
    return panel[panel["carry"].notna() & panel["y"].notna()]


def bond_premise_data(x, sigma, yields, me):
    next_ret = x[s.BONDS].cumsum().reindex(me).diff().shift(-1)
    sigma_m = sigma.reindex(me)
    dgs10, dgs20, dtb3 = (s._asof(yields[c], me) for c in ("DGS10", "DGS20", "DTB3"))
    spread = pd.DataFrame({"IEF": dgs10 - dtb3, "TLT": dgs20 - dtb3}, index=me)
    return {j: pd.DataFrame({"y": (next_ret[j] / sigma_m[j]).to_numpy(),
                              "spread": spread[j].to_numpy()}, index=me).dropna() for j in s.BONDS}


def summarize(net: pd.Series, gross: pd.Series | None = None) -> dict:
    years = (net.index[-1] - net.index[0]).days / 365.25
    out = dict(sharpe=s.sharpe(net), ann_return=float(net.sum() / s.ACCOUNT / years) if years else float("nan"),
               ann_vol=float(net.std(ddof=1) * np.sqrt(252) / s.ACCOUNT),
               maxdd_pct=float(s.max_drawdown(net) / s.ACCOUNT))
    if gross is not None:
        out["avg_gross_lev"] = float(gross.mean())
    return out


def annual_turnover(w: pd.DataFrame, x: pd.DataFrame, start, end, years: float) -> float:
    _, tgt, prev, _ = s._lagged_positions(w, x)
    turn = tgt.sub(prev).abs().sum(axis=1)
    return float(turn.loc[start:end].sum() / years)


def test_year_sharpes(net: pd.Series, windows) -> list[float]:
    return [s.sharpe(net.loc[a:b]) for a, b in windows]


def long_short_fx(w_fx, x, cost_mult=1.0):
    held, *_ = s._lagged_positions(w_fx, x[s.FX])
    brk = s.pnl_breakdown(w_fx, x[s.FX], cost_bp={t: s.COST_BP[t] for t in s.FX}, cost_mult=cost_mult)
    long_pnl = brk.where(held[s.FX] > 0, 0.0).sum(axis=1)
    short_pnl = brk.where(held[s.FX] < 0, 0.0).sum(axis=1)
    return long_pnl, short_pnl


def main():
    t0 = time.time()
    print("loading in-sample carry data (guarded: refuses any date >= 2024-07-01)...")
    px = s.load_insample_etf_prices()
    rf = s.load_insample_rf(px.index)
    x = s.daily_excess_returns(px, rf)
    me = s.month_ends(px.index)
    rates, yields = s.load_rates_monthly(), s.load_yields_daily()
    carry, missing, used_fwd = s.fx_carry(rates, me)
    bsig = s.bond_signal(yields, me)
    sigma, cov_pairs = s.ewma_vol_cov(x)
    sigma_m = sigma.reindex(me)

    elig_me = me[px.notna().reindex(me).all(axis=1)]
    FULLSPAN_START, FULLSPAN_END = elig_me.min(), me.max()
    print(f"  prices {px.shape}, {px.index.min().date()}..{px.index.max().date()}; "
          f"full span {FULLSPAN_START.date()}..{FULLSPAN_END.date()} ({len(elig_me)} month-ends)")

    print("Step 1: premise test (FX pooled panel cluster-by-month; bonds per-ETF Newey-West 3 lags)...")
    fx_panel = fx_premise_panel(x, sigma, carry, me)
    fx_beta, fx_t, fx_r2, fx_n = ols_cluster(fx_panel, "carry", "y", "month")
    bond_data = bond_premise_data(x, sigma, yields, me)
    bond_rows = []
    for j in s.BONDS:
        b, t, r2, n = ols_nw(bond_data[j], "spread", "y", lags=3)
        bond_rows.append(dict(etf=j, beta=b, t=t, r2=r2, n=n))
    ief_t = bond_rows[0]["t"]
    premise_pass = "PASS" if (fx_t > 2 and ief_t > 2) else "FAIL"

    print("Step 2/3: fixed rule (XS), full span + stitched, baseline & stress costs...")
    fx_raw = {v: s.fx_weights(carry, v) for v in VARIANTS}
    bond_raw = s.bond_weights(bsig, sigma_m)
    leg_base = s.build_leg(x, fx_raw["XS"], bond_raw, cov_pairs, cost_mult=1.0)
    leg_stress = s.build_leg(x, fx_raw["XS"], bond_raw, cov_pairs, cost_mult=1.5)

    full_years = (FULLSPAN_END - FULLSPAN_START).days / 365.25
    fullspan_rows = []
    for name, net, gross in [("leg", leg_base["leg_net"], leg_base["leg_gross"]),
                              ("FX sleeve", leg_base["fx"]["pnl"]["net"], leg_base["fx"]["pnl"]["held_gross_lev"]),
                              ("bond sleeve", leg_base["bond"]["pnl"]["net"], leg_base["bond"]["pnl"]["held_gross_lev"])]:
        seg, gseg = net.loc[FULLSPAN_START:FULLSPAN_END], gross.loc[FULLSPAN_START:FULLSPAN_END]
        fullspan_rows.append({"sleeve": name, **summarize(seg, gseg)})
    fx_turn_full = annual_turnover(leg_base["fx"]["w"], x, FULLSPAN_START, FULLSPAN_END, full_years)
    bond_turn_full = annual_turnover(leg_base["bond"]["w"], x, FULLSPAN_START, FULLSPAN_END, full_years)
    cap_fx_full = float(leg_base["fx"]["diag"]["cap_binding"].loc[FULLSPAN_START:FULLSPAN_END].mean()) * 100
    cap_bd_full = float(leg_base["bond"]["diag"]["cap_binding"].loc[FULLSPAN_START:FULLSPAN_END].mean()) * 100

    windows = test_year_windows()
    stitch_years = 14.0
    stitched_rows = []
    for name, leg in [("baseline", leg_base), ("stress x1.5", leg_stress)]:
        seg, gseg = leg["leg_net"].loc[STITCH_START:STITCH_END], leg["leg_gross"].loc[STITCH_START:STITCH_END]
        stitched_rows.append({"regime": name, **summarize(seg, gseg)})
    sleeve_stitch_rows = []
    for name, pnlkey in [("FX sleeve", "fx"), ("bond sleeve", "bond")]:
        net = leg_base[pnlkey]["pnl"]["net"].loc[STITCH_START:STITCH_END]
        sleeve_stitch_rows.append({"sleeve": name, "sharpe": s.sharpe(net), "total_pnl": float(net.sum())})
    fx_turn_stitch = annual_turnover(leg_base["fx"]["w"], x, STITCH_START, STITCH_END, stitch_years)
    bond_turn_stitch = annual_turnover(leg_base["bond"]["w"], x, STITCH_START, STITCH_END, stitch_years)
    cap_fx_stitch = float(leg_base["fx"]["diag"]["cap_binding"].loc[STITCH_START:STITCH_END].mean()) * 100
    cap_bd_stitch = float(leg_base["bond"]["diag"]["cap_binding"].loc[STITCH_START:STITCH_END].mean()) * 100

    long_pnl, short_pnl = long_short_fx(leg_base["fx"]["w"], x)
    long_pnl, short_pnl = long_pnl.loc[STITCH_START:STITCH_END], short_pnl.loc[STITCH_START:STITCH_END]
    long_short_rows = [dict(leg="FX long", sharpe=s.sharpe(long_pnl), total_pnl=float(long_pnl.sum())),
                        dict(leg="FX short", sharpe=s.sharpe(short_pnl), total_pnl=float(short_pnl.sum()))]

    ty_sharpes = test_year_sharpes(leg_base["leg_net"], windows)
    pos_years = int(sum(sh > 0 for sh in ty_sharpes if not np.isnan(sh)))
    annual_rows = [{"test_year": a.year, "net_pnl": float(leg_base["leg_net"].loc[a:b].sum()),
                     "sharpe": ty_sharpes[i]} for i, (a, b) in enumerate(windows)]

    miss_full = float(missing.loc[FULLSPAN_START:FULLSPAN_END].to_numpy().mean()) * 100
    cf_full = float(used_fwd.loc[FULLSPAN_START:FULLSPAN_END].to_numpy().mean()) * 100
    miss_stitch = float(missing.loc[STITCH_START:STITCH_END].to_numpy().mean()) * 100
    cf_stitch = float(used_fwd.loc[STITCH_START:STITCH_END].to_numpy().mean()) * 100

    print("Step 4: benchmarks (FX/bond/leg no-signal, SPY B&H), correlations...")
    fx_ns_raw = pd.DataFrame(1.0 / 6, index=me, columns=s.FX)
    bond_ns_sig = pd.DataFrame(1.0, index=me, columns=s.BONDS)
    bond_ns_raw = s.bond_weights(bond_ns_sig, sigma_m)
    leg_ns = s.build_leg(x, fx_ns_raw, bond_ns_raw, cov_pairs, cost_mult=1.0)

    spy_px = s.load_spy().to_frame("SPY")
    spy_rf = s.load_insample_rf(spy_px.index)
    x_spy = s.daily_excess_returns(spy_px, spy_rf)
    me_spy = s.month_ends(spy_px.index)
    w_spy = pd.DataFrame(1.0, index=me_spy, columns=["SPY"])
    spy_pnl = s.simulate(w_spy, x_spy, cost_bp={"SPY": 0.0005})["net"]

    def _corr(a, b):
        d = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
        return float(d["a"].corr(d["b"])) if len(d) > 2 else float("nan")

    leg_stitch = leg_base["leg_net"].loc[STITCH_START:STITCH_END]
    bench_rows = []
    for name, net in [("leg (XS, fixed)", leg_stitch),
                       ("FX no-signal (eq-wt long 6)", leg_ns["fx"]["pnl"]["net"].loc[STITCH_START:STITCH_END]),
                       ("bond no-signal (always long)", leg_ns["bond"]["pnl"]["net"].loc[STITCH_START:STITCH_END]),
                       ("leg no-signal", leg_ns["leg_net"].loc[STITCH_START:STITCH_END]),
                       ("SPY B&H", spy_pnl.loc[STITCH_START:STITCH_END])]:
        bench_rows.append({"name": name, **summarize(net), "corr_vs_leg": _corr(net, leg_stitch)})
    gate_b = s.sharpe(leg_stitch) > s.sharpe(leg_ns["leg_net"].loc[STITCH_START:STITCH_END])

    p3wf_path = f"{ROOT}/premise3/daily_pnl_wf.csv"
    p4_path = f"{ROOT}/premise4/daily_pnl.csv"
    extra_corr = []
    try:
        p3wf = pd.read_csv(p3wf_path, index_col=0, parse_dates=True)["net"]
        extra_corr.append(("premise3 (daily_pnl_wf.csv)", _corr(leg_stitch, p3wf)))
    except FileNotFoundError:
        extra_corr.append(("premise3 (daily_pnl_wf.csv)", None))
    try:
        p4 = pd.read_csv(p4_path, index_col=0, parse_dates=True)["net"]
        extra_corr.append(("premise4 (daily_pnl.csv)", _corr(leg_stitch, p4)))
    except FileNotFoundError:
        extra_corr.append(("premise4 (daily_pnl.csv)", None))

    print("Step 5: sensitivity table (XS fixed; TS/BOTH sensitivity-only)...")
    sens_rows = []
    sens_csv_rows = []
    for v in VARIANTS:
        leg_v = leg_base if v == "XS" else s.build_leg(x, fx_raw[v], bond_raw, cov_pairs, cost_mult=1.0)
        full_sh = s.sharpe(leg_v["leg_net"].loc[FULLSPAN_START:FULLSPAN_END])
        stitch_sh = s.sharpe(leg_v["leg_net"].loc[STITCH_START:STITCH_END])
        ty = test_year_sharpes(leg_v["leg_net"], windows)
        sens_rows.append({"variant": v + (" (fixed)" if v == "XS" else ""),
                           "full_span_sharpe": full_sh, "stitched_sharpe": stitch_sh})
        row = {"variant": v, "full_span_sharpe": full_sh, "stitched_sharpe": stitch_sh}
        row.update({f"test_{a.year}": ty[i] for i, (a, b) in enumerate(windows)})
        sens_csv_rows.append(row)
    pd.DataFrame(sens_csv_rows).to_csv(f"{ROOT}/premise5/sensitivity.csv", index=False)
    ty_table_rows = [{"test_year": windows[i][0].year,
                       **{v: round(s.sharpe(
                           (leg_base if v == "XS" else s.build_leg(x, fx_raw[v], bond_raw, cov_pairs))["leg_net"]
                           .loc[windows[i][0]:windows[i][1]]), 3) for v in VARIANTS}}
                      for i in range(len(windows))]

    print(f"Step 6: permutation test ({N_PERM} reps, exogenous-signal scheme, stitched calendar)...")
    real_sh, null_sh, p_perm = pt.run_permutation(x, fx_raw["XS"], bsig, me, STITCH_START, STITCH_END,
                                                   N_PERM, seed=5)

    print("Step 7: no-lookahead test...")
    import io
    from contextlib import redirect_stdout
    import test_no_lookahead as tnl
    buf = io.StringIO()
    with redirect_stdout(buf):
        tnl.run()
    nolookahead_out = buf.getvalue()
    print(nolookahead_out.strip().splitlines()[-1])

    gate_a = s.sharpe(leg_stitch) >= GATE_SHARPE
    gate_c = pos_years >= 8
    gate_d = p_perm < 0.05
    verdict = "PASS" if (gate_a and gate_b and gate_c and gate_d) else "FAIL"

    print("writing outputs...")
    full_out = pd.DataFrame({"fx_net": leg_base["fx"]["pnl"]["net"], "bond_net": leg_base["bond"]["pnl"]["net"],
                              "leg_net": leg_base["leg_net"]}).loc[FULLSPAN_START:FULLSPAN_END]
    full_out["stitched"] = (full_out.index >= STITCH_START) & (full_out.index <= STITCH_END)
    full_out.to_csv(f"{ROOT}/premise5/daily_pnl.csv")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(leg_stitch.index, leg_stitch.cumsum(), label="leg (XS carry, fixed)")
    ax.plot(leg_ns["leg_net"].loc[STITCH_START:STITCH_END].index,
            leg_ns["leg_net"].loc[STITCH_START:STITCH_END].cumsum(), label="leg no-signal", alpha=0.8)
    ax.plot(spy_pnl.loc[STITCH_START:STITCH_END].index, spy_pnl.loc[STITCH_START:STITCH_END].cumsum(),
            label="SPY B&H", alpha=0.8)
    ax.set_title("Premise 5 stitched calendar: cumulative net P&L ($, $100k book)")
    ax.set_xlabel("date"); ax.set_ylabel("cumulative $"); ax.legend(); fig.tight_layout()
    fig.savefig(f"{ROOT}/premise5/equity.png", dpi=120)

    runtime = time.time() - t0
    IMPL_CHOICES = f"""- Step 1 premise-test panel spans each instrument's OWN available history (sigma_i,t is NaN, so dropna() excludes, before that name's own first listed price), not the all-8-simultaneously-eligible FULLSPAN_START used for Steps 2/3's leg reporting -- more data-inclusive, and the same per-instrument-eligibility convention premise3 used for its pooled panel. FX panel N=1294 = ~216 avg eligible months/currency x 6; bond N=233 (IEF/TLT both trade since 2005-01, so ~all 234 month-ends minus the final month's shift(-1) edge).
- Eligibility ("first month-end with all 8 instruments eligible"): purely price-listing based (no P3-style N-day warm-up threshold -- PREMISE_5.md defines none); FULLSPAN_START = {FULLSPAN_START.date()} (the month-end after FXY, the last-listed name, appears on 2007-02-13). Pre-FULLSPAN_START month-ends (2005-01..2007-01) still get FX rank/sign weights computed (carry only needs rate data, which predates every ETF listing) but the resulting sizing lambda is NaN whenever the 6x6 FX covariance sub-block is not yet fully populated (not all 6 names trading); verified this never leaks into the reported span -- `simulate()`'s skipna sum silently drops the untradable pre-listing contribution and by FULLSPAN_START itself the covariance block is fully populated (0 NaNs in leg_net from FULLSPAN_START onward, checked directly).
- Missing-rate rule (Amendment A2): implemented as carry-forward per currency (incl. USD) on a monthly grid, `ffill(limit=6)`; a currency's rate is "still missing" only if no observation exists within the trailing 6 months. carry_i(t) is NaN (-> weight 0 that FX name that month, via the `avail` mask in `fx_weights`) if EITHER the foreign or the USD rate is still-missing at lag month m-1 (USD is common to all six carries, so a USD gap zeroes every FX name that month). In-sample this triggers exactly once: USD's one gap>1mo (2020-04, per VALIDATION.md) is recovered by the 6-month carry-forward, so it is a "used carry-forward" event, never a "still-missing" (weight-0) event, for all six names simultaneously -- see the Step 3 line below.
- XS with missing names generalises `rank(carry)-3.5` to `rank(carry)-(n_avail+1)/2` over the currencies with a defined carry that month (reduces to the literal formula when all 6 are available, which is true for all but the one recovered-via-carry-forward month above); Sigma|w|=1 renormalised over the available subset. TS keeps the spec's fixed `/6` denominator (no renormalisation) per the literal formula; a zeroed name simply reduces TS's gross that month. BOTH always renormalises to Sigma|w|=1 after averaging. Since missing-rate events are (documented above) never a weight-0 event in-sample, none of this generalisation is actually exercised on live signal values in-sample.
- Leg = 1/2 x FX-sleeve $P&L + 1/2 x bond-sleeve $P&L, each sleeve run through its own independent EWMA-covariance lambda scaling (its own 6x6 or 2x2 sub-block of the joint 8x8 EWMA covariance) and its own 3x gross cap, each simulated on a $100k book with its own turnover/borrow costs -- mathematically identical to a single simulate() call on the concatenated (0.5x FX w, 0.5x bond w) weight matrix on one $100k book, since turnover cost, borrow cost and gross P&L are all linear in weights. Leg avg gross leverage / annual turnover reported as the same 1/2-1/2 combination; the leg itself is not re-capped after combination (only each sleeve is), so "cap-binding %" is reported per sleeve, not for the leg row.
- Bond premise test: per-ETF simple time series (not pooled/clustered) of `x_j,t+1/sigma_j,t` on the raw spread `y_j,t - bill_t` (not its sign), Newey-West 3 lags, per PREMISE_5.md Step 1 wording; gate uses IEF only (TLT reported alongside).
- FX/bond no-signal benchmarks use the SAME EWMA covariance (from the realised 8-instrument excess-return panel) and the same 3x cap machinery as the timed sleeves; SPY B&H uses a fixed weight of 1.0, 5bp cost, run through the same 1-day-lag `simulate()` for internal consistency (mirrors the P3/P4 SPY benchmark convention).
- Permutation test (Step 6): only the daily excess-return matrix is shuffled (dates >= 2007-02-13, the first day all 8 names are listed); the FX rank weights (`fx_raw`, a function of carry only) are literally invariant to the permutation and computed once; the bond sleeve's per-instrument 0.40/sigma scaling depends on EWMA vol, so sigma/cov and the bond raw weights ARE recomputed on each permuted panel, exactly as PREMISE_5.md's "recompute vol/cov, weights, costs, P&L" specifies.
- Correlation vs premise3/premise4: premise3's `daily_pnl_wf.csv` is present and used; premise4 has not been run yet in this workspace (`{p4_path}` does not exist), so that correlation is reported as "not available" rather than fabricated."""

    report = f"""# RESULTS_INSAMPLE.md

**VERDICT: {verdict}** -- stitched leg net Sharpe = {s.sharpe(leg_stitch):.3f} (gate a >= {GATE_SHARPE}: {gate_a}); leg {'>' if gate_b else '<='} leg-no-signal Sharpe ({s.sharpe(leg_ns['leg_net'].loc[STITCH_START:STITCH_END]):.3f}) (gate b: {gate_b}); positive test years = {pos_years}/14 (gate c >=8: {gate_c}); permutation p={p_perm:.4f} (gate d <0.05: {gate_d}). FX variant fixed at XS (Amendment A1); TS/BOTH below are sensitivity-only.

## Step 1 -- premise test
FX pooled monthly panel (x_i,t+1/sigma_i,t ~ carry_i,t, %-pts, cluster by month):
{s.md_table([dict(beta=fx_beta, t=fx_t, r2=fx_r2, n=fx_n)])}
Bonds (x_j,t+1/sigma_j,t ~ y_j,t-bill_t, per ETF, Newey-West 3 lags):
{s.md_table(bond_rows)}
Pass (FX t>2 AND IEF t>2): {premise_pass}
## Step 2 -- fixed rule, full span ({FULLSPAN_START.date()}..{FULLSPAN_END.date()})
{s.md_table(fullspan_rows)}
FX annual turnover: {fx_turn_full:.3f}; bond annual turnover: {bond_turn_full:.3f}. Cap-binding %: FX {cap_fx_full:.2f}%, bonds {cap_bd_full:.2f}%.
Missing-rate rate (share of FX-name-months): still-missing (weight 0) = {miss_full:.3f}%, used carry-forward = {cf_full:.3f}%.
## Step 3 -- stitched calendar ({STITCH_START.date()}..{STITCH_END.date()})
Leg, baseline vs 1.5x costs:
{s.md_table(stitched_rows)}
Sleeve Sharpes (stitched):
{s.md_table(sleeve_stitch_rows)}
FX annual turnover: {fx_turn_stitch:.3f}; bond annual turnover: {bond_turn_stitch:.3f}. Cap-binding %: FX {cap_fx_stitch:.2f}%, bonds {cap_bd_stitch:.2f}%.
FX long vs short contribution:
{s.md_table(long_short_rows)}
P&L and Sharpe by test year:
{s.md_table([{**r, "net_pnl": round(r["net_pnl"], 0), "sharpe": round(r["sharpe"], 3) if not np.isnan(r["sharpe"]) else r["sharpe"]} for r in annual_rows])}
Missing-rate rate (stitched): still-missing = {miss_stitch:.3f}%, used carry-forward = {cf_stitch:.3f}%.
## Step 4 -- benchmarks (stitched calendar)
{s.md_table([{k: v for k, v in r.items()} for r in bench_rows])}
Additional correlations of the leg with: {", ".join(f"{name}={('n/a' if v is None else format(v, '.4f'))}" for name, v in extra_corr)}.
## Step 5 -- sensitivity (FX variant; XS is the fixed rule, TS/BOTH sensitivity-only, changes nothing)
{s.md_table(sens_rows)}
Per-test-year leg Sharpe by variant:
{s.md_table(ty_table_rows)}
## Step 6 -- permutation test ({N_PERM} reps, exogenous-signal scheme, stitched calendar)
Real Sharpe = {real_sh:.4f}; null mean = {null_sh.mean():.4f}, null sd = {null_sh.std():.4f}; p (share >= real) = {p_perm:.4f}
## Step 7 -- no-lookahead test
```
{nolookahead_out.strip()}
```
## Implementation choices
{IMPL_CHOICES}
## Runtime
{runtime:.1f}s total (data load, premise test, full-span + stitched fixed-rule leg, benchmarks, {N_PERM}-rep permutation test, sensitivity table, no-lookahead test, I/O).
"""
    with open(f"{ROOT}/premise5/RESULTS_INSAMPLE.md", "w") as f:
        f.write(report)

    print(f"done in {runtime:.1f}s")
    print(report)


if __name__ == "__main__":
    main()
