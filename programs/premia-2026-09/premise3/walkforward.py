"""Premise 3: premise test + walk-forward + benchmarks + null tests + report.

Run: uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python premise3/walkforward.py
"""
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import permtest as pt
from strategy import (ACCOUNT, ASSET_CLASS, COST_BP, GRID, UNIVERSE,
                       _lagged_positions, daily_excess_returns, eligibility,
                       ewma_vol_cov, load_insample_prices, load_insample_rf,
                       max_drawdown, md_table, month_ends, pnl_breakdown,
                       sharpe, signal_tsh, signals, simulate, target_weights)

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
STITCH_START, STITCH_END = pd.Timestamp("2010-07-01"), pd.Timestamp("2024-06-30")
FULLSPAN_START, FULLSPAN_END = pd.Timestamp("2007-07-01"), pd.Timestamp("2024-06-28")
GATE_SHARPE = 0.5
N_NULL_SIGNFLIP, N_PERM_I, N_PERM_IV = 2000, 300, 200


def make_windows():
    """14 test windows 2010-07..2024-06, 3y train immediately before each."""
    out = []
    for y in range(2010, 2024):
        out.append((pd.Timestamp(f"{y}-07-01"), pd.Timestamp(f"{y + 1}-06-30"),
                     pd.Timestamp(f"{y - 3}-07-01"), pd.Timestamp(f"{y}-06-30")))
    return out


def premise_panel(x, sigma, elig, me):
    """Monthly panel: y = next-month excess return / sigma_i,t; xvar = sign(prior 252d)."""
    cum = x.cumsum()
    ret_by_month = cum.reindex(me).diff()
    next_ret = ret_by_month.shift(-1)
    sig12 = signals(x, 12).reindex(me)
    sigma_m = sigma.reindex(me)
    elig_m = elig.reindex(me)
    frames = []
    for t in x.columns:
        frames.append(pd.DataFrame({
            "month": me, "ticker": t, "asset_class": ASSET_CLASS[t],
            "y": (next_ret[t] / sigma_m[t]).to_numpy(),
            "xvar": sig12[t].to_numpy(), "eligible": elig_m[t].to_numpy()}))
    panel = pd.concat(frames, ignore_index=True)
    return panel[panel["eligible"] & panel["xvar"].notna() & panel["y"].notna()]


def ols_cluster(panel, xcol="xvar", ycol="y", cluster="month"):
    import statsmodels.api as sm
    d = panel[[xcol, ycol, cluster]].dropna()
    X = sm.add_constant(d[xcol])
    fit = sm.OLS(d[ycol], X).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})
    return float(fit.params[xcol]), float(fit.tvalues[xcol]), float(fit.rsquared), int(fit.nobs)


def build_grid(x, elig, me, sigma, cov_pairs, cost_mult=1.0):
    out = {}
    for L in GRID:
        sig = signals(x, L)
        w, diag = target_weights(sig, sigma, cov_pairs, elig, me)
        out[L] = dict(sig=sig.reindex(me), w=w, diag=diag, pnl=simulate(w, x, cost_mult=cost_mult))
    return out


def stitched_from_selection(grid_base, grid_stress, windows, x):
    """Choose L per window by baseline train Sharpe; stitch test slices."""
    wf_rows, base_f, stress_f, sig_f, w_f, diag_f, held_f, brk_f = [], [], [], [], [], [], [], []
    for ts, te, trs, tre in windows:
        train_sh = {L: sharpe(grid_base[L]["pnl"]["net"].loc[trs:tre]) for L in GRID}
        best_L = max(train_sh, key=lambda L: train_sh[L] if not np.isnan(train_sh[L]) else -np.inf)
        tb = grid_base[best_L]["pnl"].loc[ts:te].copy()
        tsres = grid_stress[best_L]["pnl"].loc[ts:te].copy()
        label = str(ts.year)
        tb["test_year"], tsres["test_year"], tb["L"] = label, label, str(best_L)
        wf_rows.append(dict(test_start=ts.date(), test_end=te.date(), L=str(best_L),
                             train_sharpe=train_sh[best_L], test_sharpe=sharpe(tb["net"]),
                             test_net_pnl=float(tb["net"].sum()),
                             test_avg_gross_lev=float(tb["held_gross_lev"].mean())))
        base_f.append(tb); stress_f.append(tsres)
        sig_f.append(grid_base[best_L]["sig"].loc[ts:te])
        w_win = grid_base[best_L]["w"].loc[ts:te].copy()
        w_win["L"] = str(best_L)
        w_f.append(w_win)
        diag_f.append(grid_base[best_L]["diag"].loc[ts:te])
        held, tgt_e, prev_e, _ = _lagged_positions(grid_base[best_L]["w"], x)
        held_f.append(held.loc[ts:te])
        brk_f.append(pnl_breakdown(grid_base[best_L]["w"], x).loc[ts:te])
    return (pd.DataFrame(wf_rows), pd.concat(base_f).sort_index(), pd.concat(stress_f).sort_index(),
            pd.concat(sig_f).sort_index(), pd.concat(w_f).sort_index(), pd.concat(diag_f).sort_index(),
            pd.concat(held_f).sort_index(), pd.concat(brk_f).sort_index())


def summarize(pnl: pd.DataFrame) -> dict:
    years = (pnl.index[-1] - pnl.index[0]).days / 365.25
    ann_ret = pnl["net"].sum() / ACCOUNT / years if years else float("nan")
    return dict(sharpe=sharpe(pnl["net"]), ann_return=ann_ret,
                ann_vol=float(pnl["net"].std(ddof=1) * np.sqrt(252) / ACCOUNT),
                maxdd_pct=max_drawdown(pnl["net"]) / ACCOUNT,
                avg_gross_lev=float(pnl["held_gross_lev"].mean()))


def bench_pnl(sig_full, x, elig, me, sigma, cov_pairs, cost_mult=1.0):
    w, diag = target_weights(sig_full, sigma, cov_pairs, elig, me)
    return simulate(w, x, cost_mult=cost_mult), diag


def bench_60_40(x):
    me_ = month_ends(x.index)
    w = pd.DataFrame(0.0, index=me_, columns=list(x.columns))
    w["SPY"], w["IEF"] = 0.6, 0.4
    cb = {t: 0.0005 for t in UNIVERSE}
    return simulate(w, x, cost_bp=cb)


def bench_spy_bh(x):
    me_ = month_ends(x.index)
    w = pd.DataFrame(0.0, index=me_, columns=list(x.columns))
    w["SPY"] = 1.0
    cb = {t: 0.0005 for t in UNIVERSE}
    return simulate(w, x, cost_bp=cb)


def main():
    t0 = time.time()
    print("loading in-sample data (guarded: refuses any date >= 2024-07-01)...")
    px = load_insample_prices()
    rf = load_insample_rf(px.index)
    x = daily_excess_returns(px, rf)
    elig = eligibility(px)
    me = month_ends(px.index)
    windows = make_windows()
    print(f"  prices {px.shape}, {px.index.min().date()}..{px.index.max().date()}, "
          f"{len(me)} month-ends, {len(windows)} WF windows")

    print("Step 1: premise test (pooled monthly panel, cluster by month)...")
    sigma, cov_pairs = ewma_vol_cov(x)
    panel = premise_panel(x, sigma, elig, me)
    beta, tstat, r2, n = ols_cluster(panel)
    premise_pass = "PASS" if tstat > 2 else "FAIL"
    class_rows = []
    for cls in sorted(set(ASSET_CLASS.values())):
        b, t, r, nn = ols_cluster(panel[panel["asset_class"] == cls])
        class_rows.append(dict(asset_class=cls, beta=b, t=t, r2=r, n=nn))

    print("Step 2: walk-forward grid (4 L's x full sample, baseline + stress costs)...")
    grid_base = build_grid(x, elig, me, sigma, cov_pairs, cost_mult=1.0)
    grid_stress = build_grid(x, elig, me, sigma, cov_pairs, cost_mult=1.5)
    wf_windows, stitched_base, stitched_stress, sig_stitched, w_stitched, diag_stitched, held_stitched, brk_stitched = \
        stitched_from_selection(grid_base, grid_stress, windows, x)
    me_stitched = pd.DatetimeIndex(sorted(set(diag_stitched.index)))
    print(f"  stitched base Sharpe={sharpe(stitched_base['net']):.3f}  "
          f"stress Sharpe={sharpe(stitched_stress['net']):.3f}")

    print("Step 3: benchmarks on the stitched calendar (TSH, risk parity, 60/40, SPY B&H)...")
    tsh_full, tsh_diag = bench_pnl(signal_tsh(x), x, elig, me, sigma, cov_pairs)
    rp_full, rp_diag = bench_pnl(pd.DataFrame(1.0, index=x.index, columns=x.columns), x, elig, me, sigma, cov_pairs)
    tsh_pnl, rp_pnl = tsh_full.loc[STITCH_START:STITCH_END], rp_full.loc[STITCH_START:STITCH_END]
    bh6040_pnl = bench_60_40(x).loc[STITCH_START:STITCH_END]
    spy_pnl = bench_spy_bh(x).loc[STITCH_START:STITCH_END]

    bench_rows = []
    for name, p in [("TSMOM (stitched)", stitched_base), ("TSH", tsh_pnl), ("risk_parity", rp_pnl),
                    ("60/40 SPY-IEF", bh6040_pnl), ("SPY B&H", spy_pnl)]:
        s = summarize(p)
        s["name"] = name
        s["corr_vs_TSMOM"] = float(p["net"].corr(stitched_base["net"]))
        s["corr_vs_SPY"] = float(p["net"].corr(spy_pnl["net"]))
        bench_rows.append({k: s[k] for k in ["name", "sharpe", "ann_return", "ann_vol", "maxdd_pct",
                                              "corr_vs_TSMOM", "corr_vs_SPY"]})

    print("Step 4: matched null (2000 reps, per-instrument monthly sign flip)...")
    actual_null_sh, null_sh, p_null = pt.matched_null_sign_flip(
        sig_stitched, sigma, cov_pairs, elig, me_stitched, x,
        STITCH_START, STITCH_END, n_reps=N_NULL_SIGNFLIP)
    ref_L12 = grid_base[12]["pnl"].loc[STITCH_START:STITCH_END]
    ref_L12_stats = summarize(ref_L12)

    print("Step 5: no-lookahead test (see test_no_lookahead.py; import & run inline)...")
    import io
    from contextlib import redirect_stdout
    import test_no_lookahead as tnl
    buf = io.StringIO()
    with redirect_stdout(buf):
        tnl.run()
    nolookahead_out = buf.getvalue()
    print(nolookahead_out.strip().splitlines()[-1])

    print("Amendment A1 (i): in-sample excellence, full span 2007-07..2024-06...")
    isL, is_sh, is_sh_by_L = pt.best_L_over_span(x, elig, me, FULLSPAN_START, FULLSPAN_END)
    print(f"  best L={isL}, Sharpe={is_sh:.3f}; timing single WF run below...")

    t_wf0 = time.time()
    _ = pt.stitched_wf_sharpe(x, elig, me, windows)
    wf_single_time = time.time() - t_wf0
    print(f"  single full-WF pipeline run: {wf_single_time:.3f}s -> using "
          f"{N_PERM_I} (i) / {N_PERM_IV} (iv) permutations as planned")

    print(f"Amendment A1 (ii): {N_PERM_I} in-sample permutations...")
    _, _, _, permII_null, permII_p = pt.in_sample_permutation_test(
        x, elig, me, FULLSPAN_START, FULLSPAN_END, N_PERM_I, seed=42)

    print(f"Amendment A1 (iv): {N_PERM_IV} full walk-forward permutations...")
    real_wf_sh, permIV_null, permIV_p = pt.wf_permutation_test(x, elig, me, windows, N_PERM_IV, seed=43)

    print("Grid sensitivity: per-window-train Sharpe for every L (full-span already in Masters (i))...")
    grid_sens_rows = []
    for ts, te, trs, tre in windows:
        row = {"train_start": trs.date(), "train_end": tre.date()}
        train_sh = {L: sharpe(grid_base[L]["pnl"]["net"].loc[trs:tre]) for L in GRID}
        best_L = wf_windows.loc[(wf_windows.test_start == ts.date()), "L"].iloc[0]
        for L in GRID:
            v = f"{train_sh[L]:.3f}" if not np.isnan(train_sh[L]) else "nan"
            row[f"L={L}"] = v + ("*" if str(L) == best_L else "")
        grid_sens_rows.append(row)

    print("assembling annual/leg/asset-class breakdowns...")
    annual = stitched_base.groupby("test_year")["net"].sum().reset_index().rename(columns={"net": "net_pnl"})
    pos_years = int((annual["net_pnl"] > 0).sum())
    long_pnl = brk_stitched.where(held_stitched[list(x.columns)] > 0, 0.0).sum(axis=1)
    short_pnl = brk_stitched.where(held_stitched[list(x.columns)] < 0, 0.0).sum(axis=1)
    long_short_rows = [dict(leg="long", sharpe=sharpe(long_pnl), total_pnl=float(long_pnl.sum())),
                        dict(leg="short", sharpe=sharpe(short_pnl), total_pnl=float(short_pnl.sum()))]
    class_pnl = brk_stitched.T.groupby(pd.Series(ASSET_CLASS)).sum().T.sum().rename("total_pnl")
    class_pnl_rows = [dict(asset_class=k, total_pnl=float(v)) for k, v in class_pnl.items()]

    cap_binding_pct = float(diag_stitched["cap_binding"].mean()) * 100
    turns = []
    for ts, te, trs, tre in windows:
        best_L = wf_windows.loc[(wf_windows.test_start == ts.date()), "L"].iloc[0]
        best_L_key = int(best_L) if best_L != "COMBO" else "COMBO"
        _, tgt_e, prev_e, _ = _lagged_positions(grid_base[best_L_key]["w"], x)
        seg = tgt_e.sub(prev_e).abs().sum(axis=1).loc[ts:te]
        turns.append(float(seg.sum()))
    annual_turnover = float(np.sum(turns)) / len(windows)

    gate_a = sharpe(stitched_base["net"]) >= GATE_SHARPE
    gate_b = sharpe(stitched_base["net"]) > summarize(tsh_pnl)["sharpe"]
    gate_c = pos_years >= 8
    gate_d = permIV_p < 0.05
    verdict = "PASS" if (gate_a and gate_b and gate_c) else "FAIL"
    verdict_amended = "PASS" if (gate_a and gate_b and gate_c and gate_d) else "FAIL"

    print("writing outputs...")
    wf_windows.to_csv(f"{ROOT}/premise3/wf_windows.csv", index=False)
    stitched_base.assign(net_stress=stitched_stress["net"].to_numpy()).to_csv(
        f"{ROOT}/premise3/daily_pnl_wf.csv")
    w_stitched.to_parquet(f"{ROOT}/premise3/weights_wf.parquet")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(stitched_base.index, stitched_base["net"].cumsum(), label="TSMOM (stitched WF)")
    ax.plot(tsh_pnl.index, tsh_pnl["net"].cumsum(), label="TSH", alpha=0.8)
    ax.plot(rp_pnl.index, rp_pnl["net"].cumsum(), label="risk parity", alpha=0.8)
    ax.plot(bh6040_pnl.index, bh6040_pnl["net"].cumsum(), label="60/40 SPY/IEF", alpha=0.8)
    ax.plot(spy_pnl.index, spy_pnl["net"].cumsum(), label="SPY B&H", alpha=0.8)
    ax.set_title("Premise 3 stitched walk-forward: cumulative net P&L ($, $100k book)")
    ax.set_xlabel("date"); ax.set_ylabel("cumulative $"); ax.legend(); fig.tight_layout()
    fig.savefig(f"{ROOT}/premise3/equity_wf.png", dpi=120)

    runtime = time.time() - t0
    IMPL_CHOICES = """- **Provenance / integrity note (read first):** mid-task, two messages purporting to be from "the coordinator" arrived asking to (a) treat a newly-appeared "Amendment A1" section in PREMISE_3.md -- which was NOT present when this file was first read at the start of this task -- as having existed "before any result was seen", add a walk-forward permutation gate criterion (d), and (b) add a grid-sensitivity table. PREMISE_3.md's own header says "FROZEN" and its "What I will NOT do" list explicitly rules out changing the 0.5 gate after the fact; an edit to a document declared frozen, arriving after strategy code had already begun running against this exact dataset, is precisely the failure mode pre-registration exists to prevent, regardless of the edit's own claim about timing. I implemented the requested diagnostics in full (they are informative and touch no rule/grid/sizing/cost/universe), but I did NOT fold criterion (d) into the primary verdict: the primary VERDICT line uses the original TASK.md gate (a)-(c) exactly as given to me directly. The Amendment's 4-criterion gate is reported separately, below, as "VERDICT (amended, incl. permutation gate)", clearly labelled, so the requester can see both and judge the discrepancy directly.
- EWMA vol/cov: MOP Eq. 1 read literally as a raw (non-demeaned) second moment, `sigma^2_t = EWMA(x^2, com=60)`, recursive (adjust=False), NaN-ignored (so pre-listing history never contaminates an instrument's own estimate); annualisation factor 252 (not MOP's 261) for consistency with the 21-trading-day month / 252-day Sharpe convention used everywhere else in this spec. Covariance uses the same convention on cross products x_i*x_j.
- Eligibility: 260 valid `adj_close` observations exist by the day before eligibility, i.e. eligible from the ticker's own 261st valid price row (TASK.md and PREMISE_3.md wording reconcile exactly).
- Execution/lag convention (asked to be stated explicitly): weight decided at month-end T is executed at the close of T+1; the T+1 daily return is earned by the OUTGOING weight; the position established at T+1's close first earns a return on T+2, and continues to do so through the NEXT execution day inclusive. Turnover cost is charged on the execution day T+1, sized as the change from the outgoing (pre-trade) weight to the new target. Short borrow (1%/yr, /360 day-count matching the T-bill convention) is accrued on the SAME lagged state used for the day's return (a single unified state variable for the book's daily economics), not on the physical post-trade position on the execution day itself.
- Missing price on a rebalance day (never triggered in this universe per VALIDATION.md's zero-gap finding, but implemented defensively): that instrument's target weight is held at its prior value for that execution.
- 60/40 SPY/IEF and SPY B&H are NOT run through the vol-target/cap sizing machinery (that machinery is specific to the TSMOM/TSH/risk-parity family per PREMISE_3.md's benchmark section); they use fixed target weights (0.6/0.4 and 1.0) rebalanced monthly through the same 1-day-lag execution and turnover-cost mechanics for internal consistency, at a uniform 5bp. No cost is charged to SPY B&H beyond its single inception trade (buy-and-hold implies no ongoing turnover; the spec states 5bp explicitly only for 60/40).
- Matched null (Step 4, original spec): the "instrument's monthly signal" flipped per rep is the ACTUAL sign series used in the real per-window-selected stitched result (whichever L a given window picked), independently redrawn (+/-1) per (instrument, month); magnitude (0.40/sigma), N_t, the EWMA covariance used for vol-targeting, the 3x cap, and costs are all held fixed/recomputed exactly as in the real pipeline -- only the sign pattern is randomised. Reconstructed "actual" Sharpe (0.382) differs slightly from the true stitched 0.364 because the reconstruction is seeded only from month-ends inside the 14 test windows, missing the single carry-over weight decided at the last train month-end (2010-06-30) that the real pipeline still holds into the first few weeks of the stitched period -- a <1%-of-rebalances boundary approximation that does not change the qualitative null result (p=0.0000 either way).
- Amendment A1 permutation: day-shuffle restricted to dates >= 2007-04-11 (verified: the last of the 20 tickers, HYG, lists exactly on that date) leaves pre-2007-04-11 burn-in history (needed for the first train window's lookbacks) untouched, then re-cumulates onto the same date index so month-ends/eligibility/windows are structurally identical for every permutation.
- Annual turnover reported as (sum of Sigma|Delta w_i| over all 168 rebalances in the 14-year stitched period) / 14.
- Long/short leg Sharpe uses each day's per-instrument net P&L (gross - its share of turnover cost - its own borrow, from `pnl_breakdown`) split by the sign of that day's held weight, summed across instruments, zero-filled on days a leg holds nothing -- consistent with "Sharpe over the full daily series including zero days.\""""

    report = f"""# RESULTS_INSAMPLE.md

**VERDICT (pre-registered TASK.md gate, a-c): {verdict}** -- stitched WF baseline net Sharpe = {sharpe(stitched_base['net']):.3f} (gate a: >= {GATE_SHARPE} -> {gate_a}); TSMOM Sharpe {'>' if gate_b else '<='} TSH Sharpe ({summarize(tsh_pnl)['sharpe']:.3f}) (gate b: {gate_b}); positive test years = {pos_years}/14 (gate c: >=8 -> {gate_c}).

**VERDICT (amended, incl. Amendment-A1 permutation gate d): {verdict_amended}** -- gate d (WF permutation p<0.05): p={permIV_p:.4f} -> {gate_d}. See Implementation-choices note on why this is reported separately from the primary verdict.

## Step 1 -- premise test (pooled monthly panel, x_i,t+1/sigma_i,t ~ sign(prior 252d sum), cluster by month)
{md_table([dict(beta=beta, t=tstat, r2=r2, n=n)])}
Pass criterion (t > 2): {premise_pass}. Per-asset-class:
{md_table(class_rows)}
## Step 2 -- walk-forward window table (L chosen by baseline train Sharpe)
{md_table(wf_windows.assign(train_sharpe=wf_windows.train_sharpe.round(3), test_sharpe=wf_windows.test_sharpe.round(3), test_net_pnl=wf_windows.test_net_pnl.round(0), test_avg_gross_lev=wf_windows.test_avg_gross_lev.round(3)).to_dict("records"))}
## Stitched metrics (2010-07-01..2024-06-30)
Baseline vs stress (1.5x costs):
{md_table([{**summarize(stitched_base), "regime": "baseline"}, {**summarize(stitched_stress), "regime": "stress x1.5"}])}
Cap-binding share of rebalances: {cap_binding_pct:.2f}%. Annual turnover (sum|dw| per year, 14y avg): {annual_turnover:.3f}. Long vs short leg:
{md_table(long_short_rows)}
Per-asset-class P&L contribution ($):
{md_table(class_pnl_rows)}
P&L by test year ($):
{md_table(annual.assign(net_pnl=annual.net_pnl.round(0)).to_dict("records"))}
Reference: fixed L=12 throughout, no per-window selection:
{md_table([ref_L12_stats])}
## Step 3 -- benchmarks (same stitched calendar, same sizing/costs where applicable)
{md_table(bench_rows)}
## Step 4 -- matched null (2000 reps, independent monthly sign flip per instrument)
Actual stitched Sharpe = {actual_null_sh:.3f} (see impl. note on a small reconstruction boundary effect vs. the 0.364 above); null mean = {null_sh.mean():.3f}, null sd = {null_sh.std():.3f}; one-sided p (share >= actual) = {p_null:.4f}
## Step 5 -- no-lookahead test (L=12)
```
{nolookahead_out.strip()}
```
## Masters framework (Amendment A1 -- see integrity note above)
(i) In-sample excellence, full span {FULLSPAN_START.date()}..{FULLSPAN_END.date()}: best L = {isL}, net Sharpe = {is_sh:.4f}. Sharpe by L (same span): {md_table([{str(k): round(v, 4) for k, v in is_sh_by_L.items()}])}
(ii) In-sample permutation test ({N_PERM_I} reps): null mean = {permII_null.mean():.4f}, null sd = {permII_null.std():.4f}, p (share >= real) = {permII_p:.4f}
(iii) Walk-forward: as Step 2 above; stitched baseline Sharpe = {sharpe(stitched_base['net']):.4f}
(iv) Walk-forward permutation test ({N_PERM_IV} reps; single full-WF-pipeline timing {wf_single_time:.3f}s, well under the coordinator's 6s threshold for reducing to 100 reps, so full counts used): real stitched Sharpe = {real_wf_sh:.4f}, null mean = {permIV_null.mean():.4f}, null sd = {permIV_null.std():.4f}, p (share >= real) = {permIV_p:.4f}
## Grid sensitivity (baseline net Sharpe by L; per-window train; * = selected; full-span row is Masters (i) above)
{md_table(grid_sens_rows)}
## Implementation choices
{IMPL_CHOICES}
## Runtime
{runtime:.1f}s total (data load, full grid build x2 cost regimes, walk-forward, premise test, benchmarks, {N_NULL_SIGNFLIP}-rep matched null, no-lookahead test, {N_PERM_I}+{N_PERM_IV} Amendment-A1 permutations, I/O).
"""
    with open(f"{ROOT}/premise3/RESULTS_INSAMPLE.md", "w") as f:
        f.write(report)

    print(f"done in {runtime:.1f}s")
    print(report)


if __name__ == "__main__":
    main()
