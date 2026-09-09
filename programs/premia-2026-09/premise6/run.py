"""Premise 6 CLI: premise test, fixed-rule L=12 class-balanced simulation,
benchmarks, sensitivity table, permutation test, no-lookahead test, gate.
Run: uv run --with pandas --with pyarrow --with numpy --with statsmodels
     --with matplotlib python premise6/run.py   (from ROOT)
"""
from __future__ import annotations

import io
import os
import time
from contextlib import redirect_stdout

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import permtest as pm
import test_no_lookahead as tnl
from strategy import (ASSET_CLASS, COST_BP, UNIVERSE, class_balanced_weights,
                       load_insample_prices, load_insample_rf, p3)

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
FULLSPAN_START, FULLSPAN_END = pd.Timestamp("2007-07-01"), pd.Timestamp("2024-06-28")
STITCH_START, STITCH_END = pd.Timestamp("2010-07-01"), pd.Timestamp("2024-06-30")
GATE_SHARPE = 0.5
N_PERM = 500


def test_years():
    """14 Jul->Jun (start,end) pairs, 2010-07..2024-06; no train windows needed
    (L=12 fixed). Minimal copy of premise3/walkforward.py:make_windows()."""
    return [(pd.Timestamp(f"{y}-07-01"), pd.Timestamp(f"{y + 1}-06-30")) for y in range(2010, 2024)]


def ols_cluster(panel, xcol="xvar", ycol="y", cluster="month"):
    """Copied verbatim from premise3/walkforward.py (generic, no P3 globals)."""
    import statsmodels.api as sm
    d = panel[[xcol, ycol, cluster]].dropna()
    X = sm.add_constant(d[xcol])
    fit = sm.OLS(d[ycol], X).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})
    return float(fit.params[xcol]), float(fit.tvalues[xcol]), float(fit.rsquared), int(fit.nobs)


def summarize(pnl):
    """Copied verbatim from premise3/walkforward.py (generic)."""
    years = (pnl.index[-1] - pnl.index[0]).days / 365.25
    ann_ret = pnl["net"].sum() / p3.ACCOUNT / years if years else float("nan")
    return dict(sharpe=p3.sharpe(pnl["net"]), ann_return=ann_ret,
                ann_vol=float(pnl["net"].std(ddof=1) * np.sqrt(252) / p3.ACCOUNT),
                maxdd_pct=p3.max_drawdown(pnl["net"]) / p3.ACCOUNT,
                avg_gross_lev=float(pnl["held_gross_lev"].mean()))


def premise_panel(x, sigma, elig, me):
    """y = next-month excess return/sigma_i,t; xvar = sign(prior 252d sum).
    Adapted from premise3/walkforward.py:premise_panel with this premise's
    own 5-class ASSET_CLASS (P3's hardcodes its own 20-name one)."""
    next_ret = x.cumsum().reindex(me).diff().shift(-1)
    sig12 = p3.signals(x, 12).reindex(me)
    sigma_m, elig_m = sigma.reindex(me), elig.reindex(me)
    frames = [pd.DataFrame({"month": me, "ticker": t, "asset_class": ASSET_CLASS[t],
                             "y": (next_ret[t] / sigma_m[t]).to_numpy(),
                             "xvar": sig12[t].to_numpy(), "eligible": elig_m[t].to_numpy()})
              for t in x.columns]
    panel = pd.concat(frames, ignore_index=True)
    return panel[panel["eligible"] & panel["xvar"].notna() & panel["y"].notna()]


def fixed_pnl(x, elig, me, sigma, cov_pairs, cost_mult=1.0):
    sig = p3.signals(x, 12)
    w, diag = class_balanced_weights(sig, sigma, cov_pairs, elig, me)
    return w, diag, p3.simulate(w, x, cost_bp=COST_BP, cost_mult=cost_mult)


def leg_split(w, x):
    held, tgt_e, prev_e, _ = p3._lagged_positions(w, x)
    brk = p3.pnl_breakdown(w, x, cost_bp=COST_BP)
    tickers = list(x.columns)
    long_pnl = brk.where(held[tickers] > 0, 0.0).sum(axis=1)
    short_pnl = brk.where(held[tickers] < 0, 0.0).sum(axis=1)
    return long_pnl, short_pnl, brk, held, tgt_e, prev_e


def annual_turnover(w, x, start, end, n_years=14):
    _, tgt_e, prev_e, _ = p3._lagged_positions(w, x)
    return float(tgt_e.sub(prev_e).abs().sum(axis=1).loc[start:end].sum()) / n_years


def bench_pnl(sig, x, elig, me, sigma, cov_pairs):
    w, diag = class_balanced_weights(sig, sigma, cov_pairs, elig, me)
    return p3.simulate(w, x, cost_bp=COST_BP), diag


def bench_fixed(x, weight_map):
    me_ = p3.month_ends(x.index)
    w = pd.DataFrame(0.0, index=me_, columns=list(x.columns))
    for t, v in weight_map.items():
        w[t] = v
    return p3.simulate(w, x, cost_bp=COST_BP)


def main():
    t0 = time.time()
    print("loading in-sample data (guarded: refuses any date >= 2024-07-01)...")
    px = load_insample_prices()
    rf = load_insample_rf(px.index)
    x = p3.daily_excess_returns(px, rf)
    elig = p3.eligibility(px)
    me = p3.month_ends(px.index)
    perm_cutoff = px.notna().idxmax().max()
    print(f"  prices {px.shape}, {px.index.min().date()}..{px.index.max().date()}, "
          f"{len(me)} month-ends, perm cutoff (first day all 38 listed) = {perm_cutoff.date()}")

    print("Step 1: premise test (pooled monthly panel, cluster by month, L=12)...")
    sigma, cov_pairs = p3.ewma_vol_cov(x)
    panel = premise_panel(x, sigma, elig, me)
    beta, tstat, r2, n = ols_cluster(panel)
    premise_pass = "PASS" if tstat > 2 else "FAIL"
    class_rows = []
    for cls in sorted(set(ASSET_CLASS.values())):
        b, t, r, nn = ols_cluster(panel[panel["asset_class"] == cls])
        class_rows.append(dict(asset_class=cls, beta=b, t=t, r2=r, n=nn))

    print("Step 2: fixed rule (L=12, class-balanced), full span + stitched...")
    w, diag, pnl_base = fixed_pnl(x, elig, me, sigma, cov_pairs, cost_mult=1.0)
    pnl_stress = p3.simulate(w, x, cost_bp=COST_BP, cost_mult=1.5)
    full_base, full_stress = pnl_base.loc[FULLSPAN_START:FULLSPAN_END], pnl_stress.loc[FULLSPAN_START:FULLSPAN_END]
    stit_base, stit_stress = pnl_base.loc[STITCH_START:STITCH_END], pnl_stress.loc[STITCH_START:STITCH_END]
    span_rows = [{**summarize(full_base), "span": "full 2007-07..2024-06", "regime": "baseline"},
                 {**summarize(full_stress), "span": "full 2007-07..2024-06", "regime": "stress x1.5"},
                 {**summarize(stit_base), "span": "stitched 2010-07..2024-06", "regime": "baseline"},
                 {**summarize(stit_stress), "span": "stitched 2010-07..2024-06", "regime": "stress x1.5"}]
    cap_binding_pct = float(diag.loc[STITCH_START:STITCH_END, "cap_binding"].mean()) * 100
    turnover = annual_turnover(w, x, STITCH_START, STITCH_END)
    long_pnl, short_pnl, brk, held, _, _ = leg_split(w, x)
    long_short_rows = [dict(leg="long", sharpe=p3.sharpe(long_pnl.loc[STITCH_START:STITCH_END]),
                             total_pnl=float(long_pnl.loc[STITCH_START:STITCH_END].sum())),
                       dict(leg="short", sharpe=p3.sharpe(short_pnl.loc[STITCH_START:STITCH_END]),
                            total_pnl=float(short_pnl.loc[STITCH_START:STITCH_END].sum()))]
    class_pnl = brk.loc[STITCH_START:STITCH_END].T.groupby(pd.Series(ASSET_CLASS)).sum().T.sum()
    class_pnl_rows = [dict(asset_class=k, total_pnl=float(v)) for k, v in class_pnl.items()]
    yr_rows = []
    for ts, te in test_years():
        seg = stit_base.loc[ts:te]["net"]
        yr_rows.append(dict(test_year=ts.year, net_pnl=float(seg.sum()), sharpe=p3.sharpe(seg)))
    pos_years = int(sum(1 for r in yr_rows if r["net_pnl"] > 0))

    print("Step 3: benchmarks (TSH, class-balanced risk parity, 60/40, SPY B&H)...")
    tsh_pnl, _ = bench_pnl(p3.signal_tsh(x), x, elig, me, sigma, cov_pairs)
    rp_pnl, _ = bench_pnl(pd.DataFrame(1.0, index=x.index, columns=x.columns), x, elig, me, sigma, cov_pairs)
    tsh_pnl, rp_pnl = tsh_pnl.loc[STITCH_START:STITCH_END], rp_pnl.loc[STITCH_START:STITCH_END]
    bh6040_pnl = bench_fixed(x, {"SPY": 0.6, "IEF": 0.4}).loc[STITCH_START:STITCH_END]
    spy_pnl = bench_fixed(x, {"SPY": 1.0}).loc[STITCH_START:STITCH_END]
    bench_rows = []
    for name, p in [("TSMOM (fixed L=12, class-bal.)", stit_base), ("TSH", tsh_pnl), ("risk_parity", rp_pnl),
                    ("60/40 SPY-IEF", bh6040_pnl), ("SPY B&H", spy_pnl)]:
        s = summarize(p)
        s["name"] = name
        s["corr_vs_leg"] = float(p["net"].corr(stit_base["net"]))
        s["corr_vs_SPY"] = float(p["net"].corr(spy_pnl["net"]))
        bench_rows.append({k: s[k] for k in ["name", "sharpe", "ann_return", "ann_vol", "maxdd_pct",
                                              "corr_vs_leg", "corr_vs_SPY"]})
    tsh_sharpe = summarize(tsh_pnl)["sharpe"]

    def _net_col(df):
        # each premise's own script names its net-pnl column; try the likely candidates
        for c in ("net", "leg_net", "net_pnl"):
            if c in df.columns:
                return c
        return None

    cross_corr = {}
    p3wf = pd.read_csv(f"{ROOT}/premise3/daily_pnl_wf.csv", index_col=0, parse_dates=True)
    cross_corr["premise3"] = float(stit_base["net"].corr(p3wf[_net_col(p3wf)].reindex(stit_base.index)))
    for k in (4, 5):
        fp = f"{ROOT}/premise{k}/daily_pnl.csv"
        col = None
        if os.path.exists(fp):
            pk = pd.read_csv(fp, index_col=0, parse_dates=True)
            col = _net_col(pk)
        cross_corr[f"premise{k}"] = (float(stit_base["net"].corr(pk[col].reindex(stit_base.index)))
                                      if col else None)

    print("Step 4: sensitivity table (L x weighting, stitched Sharpe, report-only)...")
    sens_rows = []
    for L in [6, 12, "COMBO"]:
        sig_L = p3.signals(x, L)
        for scheme in ["class_balanced", "1/N"]:
            if scheme == "class_balanced":
                w_s, _ = class_balanced_weights(sig_L, sigma, cov_pairs, elig, me)
            else:
                w_s, _ = p3.target_weights(sig_L, sigma, cov_pairs, elig, me)
            pnl_s = p3.simulate(w_s, x, cost_bp=COST_BP)["net"].loc[STITCH_START:STITCH_END]
            sens_rows.append(dict(L=str(L), weighting=scheme, stitched_sharpe=p3.sharpe(pnl_s),
                                   is_rule=(L == 12 and scheme == "class_balanced")))
    pd.DataFrame(sens_rows).to_csv(f"{ROOT}/premise6/sensitivity.csv", index=False)

    print(f"Step 5: permutation test ({N_PERM} day-shuffle reps, full pipeline)...")
    real_sh, null_sh, p_perm = pm.run_permutation_test(x, elig, me, perm_cutoff, n_reps=N_PERM)

    print("Step 6: no-lookahead test...")
    buf = io.StringIO()
    with redirect_stdout(buf):
        tnl.run()
    nolookahead_out = buf.getvalue()
    print(nolookahead_out.strip().splitlines()[-1])

    stitched_sh = summarize(stit_base)["sharpe"]
    gate_a = stitched_sh >= GATE_SHARPE
    gate_b = stitched_sh > tsh_sharpe
    gate_c = pos_years >= 8
    gate_d = p_perm < 0.05
    verdict = "PASS" if (gate_a and gate_b and gate_c and gate_d) else "FAIL"

    print("writing outputs...")
    daily_pnl = pnl_base.loc[FULLSPAN_START:FULLSPAN_END].copy()
    daily_pnl["stitched"] = (daily_pnl.index >= STITCH_START) & (daily_pnl.index <= STITCH_END)
    daily_pnl.to_csv(f"{ROOT}/premise6/daily_pnl.csv")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(stit_base.index, stit_base["net"].cumsum(), label="TSMOM (L=12, class-bal.)")
    ax.plot(tsh_pnl.index, tsh_pnl["net"].cumsum(), label="TSH", alpha=0.8)
    ax.plot(rp_pnl.index, rp_pnl["net"].cumsum(), label="class-bal. risk parity", alpha=0.8)
    ax.plot(bh6040_pnl.index, bh6040_pnl["net"].cumsum(), label="60/40 SPY/IEF", alpha=0.8)
    ax.plot(spy_pnl.index, spy_pnl["net"].cumsum(), label="SPY B&H", alpha=0.8)
    ax.set_title("Premise 6 stitched: cumulative net P&L ($, $100k book)")
    ax.set_xlabel("date"); ax.set_ylabel("cumulative $"); ax.legend(); fig.tight_layout()
    fig.savefig(f"{ROOT}/premise6/equity.png", dpi=120)

    runtime = time.time() - t0
    IMPL_CHOICES = f"""- **Sensitivity-table count vs PREMISE_6.md:** TASK.md Step 4 specifies the full cross-product {{L=6,12,COMBO}} x {{class-balanced,1/N}} (6 cells); PREMISE_6.md's prose says "four extra numbers." The literal cross-product yields 6 cells, one of which (L=12, class-balanced) is the rule itself already reported in Step 2, leaving 5 "extra," not 4. Followed TASK.md literally (all 6 cells computed and reported; the rule cell flagged) as the more precise and directly-governing instruction; PREMISE_6.md's "four" is treated as loose prose, not a constraint on which cells to compute -- most conservative reading, changes nothing (report-only table).
- **Permutation cutoff:** "first day all 38 are listed" computed from the price panel (`px.notna().idxmax().max()`) = {perm_cutoff.date()} (EMB), analogous to P3's PERM_CUTOFF being HYG's first-listed date, not the first date of a complete *excess-return* cross-section (which would be one trading day later, since pct_change's first observation is NaN); this matches P3's own convention exactly.
- **permtest.py / test_no_lookahead.py reimplemented, not imported:** premise3/permtest.py hardcodes a 20-name PERM_CUTOFF and itself does `from strategy import ...`, which would resolve against *this premise's* strategy.py (same generic module name) if premise3/permtest.py were dynamically loaded here, silently pulling in the wrong `target_weights`/`GRID`/etc. Both files were rewritten as minimal, faithful ports of P3's logic (same day-shuffle / prefix-consistency approach), parametrised on this premise's own universe, cutoff and class-balanced weights; see strategy.py's module docstring.
- **Class-balanced weights on non-eligible-but-zero-signal instruments:** `n_c(i),t` and `C_t` are computed from eligibility only (not signal sign), so a class with eligible instruments whose signal is exactly 0 still counts toward `C_t` and dilutes other classes' share -- read directly off the PREMISE_6.md formula, which conditions the raw weight (not the class-count) on `s_i,t`.
- **60/40 and SPY B&H** are not run through the class-balance/vol-target/cap machinery (P3's convention, restated in PREMISE_6.md's benchmark section): fixed monthly target weights, same 1-day-lag execution/turnover-cost mechanics, uniform 5bp (both SPY and IEF are already 5bp in this premise's own COST_BP).
- **Cross-premise correlation:** looks for the sibling's daily net-P&L column under any of "net"/"leg_net"/"net_pnl" (each premise's own script names it differently; premise5's, produced concurrently with this run, uses "leg_net") and reports "n/a" if the file or a recognisable column is missing.
- All other conventions (EWMA vol/cov COM=60, eligibility on the 261st valid price, execution at close t+1, missing price -> prior weight, 252-day/12-month sign lookback, borrow 1%/yr /360, 5bp/10bp cost table, 3x gross cap, 10% vol target) are P3's, imported unchanged via `strategy.p3`.
- **Code budget:** TASK.md's "~200 new lines" was not met (actual: see line counts below). All core math (excess returns, EWMA vol/cov, signals/TSH, simulate/pnl_breakdown, sharpe/max_drawdown, P3's 1/N target_weights) is imported unchanged; the new code is (i) the ~35-line class-balanced weight formula itself, and (ii) orchestration/reporting for 7 TASK.md steps (premise test, full+stitched fixed-rule sim, 4 benchmarks, a 6-cell sensitivity grid, permutation test, no-lookahead test, cross-premise correlations, gate) that could not be imported from premise3/walkforward.py as-is because its helpers close over P3's own hardcoded 20-name UNIVERSE/ASSET_CLASS globals and it self-imports a module literally named "strategy" (which would resolve to this premise's own file, not P3's, if dynamically loaded here -- see strategy.py's docstring). Most of the excess line count is one-line-per-table-row report plumbing, not new strategy logic."""

    def fmt_corr(k):
        v = cross_corr[k]
        return f"{v:.4f}" if v is not None else "n/a"

    report = f"""# RESULTS_INSAMPLE.md

**VERDICT: {verdict}** -- stitched net Sharpe = {stitched_sh:.3f} (gate a: >= {GATE_SHARPE} -> {gate_a}); TSMOM {'>' if gate_b else '<='} TSH ({tsh_sharpe:.3f}) (gate b: {gate_b}); positive test years = {pos_years}/14 (gate c: >=8 -> {gate_c}); permutation p = {p_perm:.4f} (gate d: <0.05 -> {gate_d}).

## Step 1 -- premise test (pooled monthly panel, x_i,t+1/sigma_i,t ~ sign(prior 252d sum), cluster by month, 38 ETFs)
{p3.md_table([dict(beta=beta, t=tstat, r2=r2, n=n)])}
Pass criterion (t > 2): {premise_pass}. Per-asset-class:
{p3.md_table(class_rows)}
## Step 2 -- fixed rule (L=12, class-balanced): full span vs stitched, baseline vs stress (1.5x costs)
{p3.md_table(span_rows)}
Cap-binding share (stitched): {cap_binding_pct:.2f}%. Annual turnover (sum|dw|/14y, stitched): {turnover:.3f}. Long vs short leg (stitched):
{p3.md_table(long_short_rows)}
Per-asset-class P&L, stitched ($):
{p3.md_table(class_pnl_rows)}
P&L and Sharpe by test year, stitched ($):
{p3.md_table([{**r, "net_pnl": round(r["net_pnl"])} for r in yr_rows])}
## Step 3 -- benchmarks (stitched, same universe/class balance/sizing/costs)
{p3.md_table(bench_rows)}
Correlation of the leg's stitched daily net P&L with: premise3 = {fmt_corr('premise3')}, premise4 = {fmt_corr('premise4')}, premise5 = {fmt_corr('premise5')}.
## Step 4 -- sensitivity table (report only; changes nothing; L=12/class-balanced is the rule)
{p3.md_table([{**r, "stitched_sharpe": round(r["stitched_sharpe"], 4)} for r in sens_rows])}
## Step 5 -- permutation test ({N_PERM} day-shuffle reps, full pipeline, cutoff={perm_cutoff.date()})
Real stitched Sharpe = {real_sh:.4f}; null mean = {null_sh.mean():.4f}, null sd = {null_sh.std():.4f}; one-sided p (share >= real) = {p_perm:.4f}
## Step 6 -- no-lookahead test (L=12, class-balanced)
```
{nolookahead_out.strip()}
```
## Step 7 -- gate (report only)
(a) stitched Sharpe >= 0.5: {stitched_sh:.3f} -> {gate_a}. (b) TSMOM > TSH: {stitched_sh:.3f} vs {tsh_sharpe:.3f} -> {gate_b}. (c) >=8/14 positive years: {pos_years}/14 -> {gate_c}. (d) p<0.05: {p_perm:.4f} -> {gate_d}. **Verdict: {verdict}** (PASS requires all four).
## Implementation choices
{IMPL_CHOICES}
## Runtime
{runtime:.1f}s total (data load, premise test, fixed-rule sim x2 cost regimes, benchmarks x4, 6-cell sensitivity grid, {N_PERM}-rep permutation test, no-lookahead test, I/O).
"""
    with open(f"{ROOT}/premise6/RESULTS_INSAMPLE.md", "w") as f:
        f.write(report)
    print(f"done in {runtime:.1f}s")
    print(report)


if __name__ == "__main__":
    main()
