"""Premise 1: premise test + walk-forward + null test + report (TASK.md steps 2-5).

Run: uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python premise1/walkforward.py
"""
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from strategy import (build_daily_table, load_insample, matched_null,
                       max_drawdown, ols_hac, pnl, sharpe)

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
K_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
L_GRID = [18, 30, 60]
BASE_SLIP, STRESS_SLIP, FEE = 1, 2, 1.00
GATE_SHARPE, GATE_TRADES = 1.0, 800


def make_windows():
    """11 test windows 2013-07..2024-06, 3y train immediately before each."""
    out = []
    for y in range(2013, 2024):
        test_start = pd.Timestamp(f"{y}-07-01").date()
        test_end = pd.Timestamp(f"{y + 1}-06-30").date()
        train_start = pd.Timestamp(f"{y - 3}-07-01").date()
        train_end = (pd.Timestamp(f"{y}-07-01") - pd.Timedelta(days=1)).date()
        out.append((test_start, test_end, train_start, train_end))
    return out


def summarize(df: pd.DataFrame) -> dict:
    """Headline stats on a (baseline- or stress-costed) daily pnl frame."""
    trades = df[df["is_trade"]]
    longs, shorts = trades[trades["dir"] == 1], trades[trades["dir"] == -1]
    return dict(
        sharpe=sharpe(df["net"]), maxdd=max_drawdown(df["net"]),
        trades=int(len(trades)), net_pnl=float(df["net"].sum()),
        hit_rate=float((trades["net"] > 0).mean()) if len(trades) else float("nan"),
        mean_net_per_trade=float(trades["net"].mean()) if len(trades) else float("nan"),
        mean_abs_z_traded=float(trades["z"].abs().mean()) if len(trades) else float("nan"),
        long_sharpe=sharpe(longs["net"]), long_trades=int(len(longs)),
        short_sharpe=sharpe(shorts["net"]), short_trades=int(len(shorts)),
    )


def md_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main():
    t0 = time.time()
    print("loading in-sample data...")
    h1 = load_insample(f"{ROOT}/data/es_1h_insample.parquet")
    h4 = load_insample(f"{ROOT}/data/es_4h_insample.parquet")

    print("building daily tables for 15 (k,L) grid points...")
    raw = {(k, L): build_daily_table(h1, h4, k, L) for k in K_GRID for L in L_GRID}
    base_pnl = {kl: pnl(df, BASE_SLIP, FEE) for kl, df in raw.items()}
    skip_counts = raw[(0.0, 30)].attrs["skip_counts"]

    # --- Step 3: premise test (pooled, k irrelevant, L=30 for z terciles) ---
    print("running premise test...")
    premise_tbl = raw[(0.0, 30)]
    pooled = ols_hac(premise_tbl)
    tercile_rows = []
    zt = premise_tbl.dropna(subset=["z"]).copy()
    zt["tercile"] = pd.qcut(zt["z"].abs(), 3, labels=["low", "mid", "high"])
    for name in ["low", "mid", "high"]:
        b, t, r2, n = ols_hac(zt[zt["tercile"] == name])
        tercile_rows.append(dict(tercile=name, beta=b, t=t, r2=r2, n=n))
    always_long_mean = float(premise_tbl["r_trade"].mean())

    # --- Step 4: walk-forward selection (k,L chosen by baseline train Sharpe) ---
    print("running walk-forward grid (15 combos x 11 windows)...")
    windows = make_windows()
    wf_rows, base_frames, stress_frames = [], [], []
    for ts, te, trs, tre in windows:
        train_sh = {}
        for kl, df in base_pnl.items():
            seg = df[(df["date"] >= trs) & (df["date"] <= tre)]
            train_sh[kl] = sharpe(seg["net"])
        best_kl = max(train_sh, key=lambda kl: (train_sh[kl] if not np.isnan(train_sh[kl]) else -np.inf))
        k, L = best_kl
        test_base = base_pnl[best_kl]
        test_base = test_base[(test_base["date"] >= ts) & (test_base["date"] <= te)].copy()
        test_stress = pnl(raw[best_kl], STRESS_SLIP, FEE)
        test_stress = test_stress[(test_stress["date"] >= ts) & (test_stress["date"] <= te)].copy()
        label = f"{ts.year}-{te.year}"
        test_base["test_year"], test_stress["test_year"] = label, label
        wf_rows.append(dict(test_start=ts, test_end=te, k=k, L=L,
                             train_sharpe=train_sh[best_kl], test_sharpe=sharpe(test_base["net"]),
                             test_trades=int(test_base["is_trade"].sum()), test_net_pnl=float(test_base["net"].sum())))
        base_frames.append(test_base)
        stress_frames.append(test_stress)

    wf_windows = pd.DataFrame(wf_rows)
    stitched_base = pd.concat(base_frames).sort_values("date").reset_index(drop=True)
    stitched_stress = pd.concat(stress_frames).sort_values("date").reset_index(drop=True)

    stats_base = summarize(stitched_base)
    stats_stress = summarize(stitched_stress)
    annual = stitched_base.groupby("test_year")["net"].sum().reset_index().rename(columns={"net": "net_pnl"})

    # --- references: (a) fixed k=0,L=30 no-selection; (b) buy-and-hold ES ---
    print("computing references and null test...")
    overall_start, overall_end = windows[0][0], windows[-1][1]
    ref_a_full = base_pnl[(0.0, 30)]
    ref_a = ref_a_full[(ref_a_full["date"] >= overall_start) & (ref_a_full["date"] <= overall_end)]
    ref_a_stats = summarize(ref_a)

    px = raw[(0.0, 30)][["date", "P_prev16", "P16"]]
    bh_rets = []
    for ts, te, *_ in windows:
        seg = px[(px["date"] >= ts) & (px["date"] <= te)]
        bh_rets.append(np.log(seg["P16"].iloc[-1] / seg["P_prev16"].iloc[0]))
    bh_rets = np.array(bh_rets)
    bh_sharpe = float(bh_rets.mean() / bh_rets.std(ddof=1))

    # --- Step 5: matched null on stitched baseline trade list ---
    actual_sh, null_sh, p_value = matched_null(stitched_base, BASE_SLIP, FEE)

    # --- sizing stats over stitched baseline trades ---
    trades_all = stitched_base[stitched_base["is_trade"]]
    median_contracts = float(trades_all["contracts"].median())
    cap_pct = float(trades_all["cap_bound"].mean()) * 100
    rounded_to_zero_n = int((stitched_base["rounded_to_zero"]).sum())

    # --- outputs ---
    print("writing outputs...")
    wf_windows.to_csv(f"{ROOT}/premise1/wf_windows.csv", index=False)
    trades_all.to_csv(f"{ROOT}/premise1/trades_wf.csv", index=False)
    stitched_base.assign(net_stress=stitched_stress["net"].to_numpy()).to_csv(
        f"{ROOT}/premise1/daily_pnl_wf.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(pd.to_datetime(stitched_base["date"]), stitched_base["net"].cumsum(), label="walk-forward (baseline)")
    ax.plot(pd.to_datetime(ref_a["date"]), ref_a["net"].cumsum(), label="fixed k=0,L=30 (baseline)", alpha=0.7)
    ax.set_title("Premise 1 stitched walk-forward: cumulative net P&L ($)")
    ax.set_xlabel("date"); ax.set_ylabel("cumulative $"); ax.legend(); fig.tight_layout()
    fig.savefig(f"{ROOT}/premise1/equity_wf.png", dpi=120)

    runtime = time.time() - t0
    verdict = "PASS" if (stats_base["sharpe"] >= GATE_SHARPE and stats_base["trades"] >= GATE_TRADES) else "FAIL"
    premise_pass = "PASS" if pooled[0] > 0 and pooled[1] > 2 else "FAIL"
    wf_rows_r = [{**r, "train_sharpe": round(r["train_sharpe"], 3), "test_sharpe": round(r["test_sharpe"], 3)} for r in wf_rows]

    IMPL_CHOICES = """- sigma_day = sigma_4h * sqrt(5.5) used literally as the fixed constant given in the spec (not the 'actual count of 4h bars' alternative PREMISE_1.md offers as an option).
- Skip reasons are made mutually exclusive by checking in this priority order so counts sum exactly to the candidate-weekday count: p15_missing_or_thin, p16_missing, prev16_missing, roll_crossing, day_after_early_close.
- Rows with insufficient 4h history for L (sigma_4h NaN) are NOT counted as a skipped day: the daily-table row is kept (r_sofar/r_trade are still valid), z is NaN, and dir/contracts resolve to 0/no-trade, contributing a legitimate zero-P&L day to Sharpe -- consistent with 'Sharpe over the full daily series including zero days'.
- Amendment A1(ii) ('day after an early close') is implemented exactly as the mechanical rule in TASK.md (prior weekday has a 9-12 ET bar but no 16:00 bar), with no day-of-week or holiday special-casing; this also fires after full-closure holidays with a partial overnight Globex print (e.g. Thanksgiving), not just classic 13:00 half-days -- see report notes.
- Buy-and-hold reference per window = ln(P16 of the window's last kept date / P_prev16 of the window's first kept date) -- the most literal close-to-close return spanning exactly the test window (using the same 16:00 cash-close convention as the rest of the strategy).
- Walk-forward (k,L) is selected once per window using the baseline daily table build/cost; the stress-cost stitched result reruns pnl() with slippage_ticks=2 on the SAME selected (k,L) and SAME dir/contracts per window (costs are not part of selection).
- Matched-null p-value is reported as the raw fraction of 2000 null Sharpes >= actual, with no add-one continuity correction (not specified in the task).
- ICT repo's matched_baseline_test/random_baseline_test were not reused: their interface is built around ict_backtest.engine Candles/Backtester/BacktestResult objects and a stop/target trade-template null, which does not fit this two-fills-per-trade, direction-only vectorised strategy; step 5 is instead ~15 lines of numpy directly on the stitched pnl frame.
- hit_rate, mean_net_per_trade, mean_abs_z_traded and long/short Sharpe are diagnostic sub-statistics computed over trade days only for that subset (not zero-padded); long/short Sharpe still uses the same mean/std*sqrt(252) annualisation as the full-series headline Sharpe, for comparability, even though trade days are a sparser, irregular subset of the calendar."""

    report = f"""# RESULTS_INSAMPLE.md

**VERDICT: {verdict}** -- stitched walk-forward baseline net Sharpe = {stats_base['sharpe']:.3f} (gate >= {GATE_SHARPE}), trades = {stats_base['trades']} (gate >= {GATE_TRADES}).

## Step 3 -- premise test (pooled in-sample, r_trade ~ r_sofar, HAC-5)

{md_table([dict(beta=pooled[0], t=pooled[1], r2=pooled[2], n=pooled[3])])}

Pass criterion (beta>0 and t>2): {premise_pass}

Terciles of |z| (L=30, descriptive):

{md_table(tercile_rows)}

Always-long mean r_trade (context): {always_long_mean:.6f}

## Step 4 -- walk-forward window table

{md_table(wf_rows_r)}

## Stitched metrics

Baseline (1 tick slip, $1 fee):

{md_table([stats_base])}

Stress (2 tick slip, $1 fee):

{md_table([stats_stress])}

Annual net P&L by test year (baseline):

{md_table(annual.to_dict("records"))}

## References (context only, same stitched period)

(a) fixed k=0, L=30, no walk-forward selection:

{md_table([ref_a_stats])}

(b) buy-and-hold ES, one log return per test window, annualised Sharpe: {bh_sharpe:.3f}

## Step 5 -- matched null (2000 reps, randomised trade direction)

Actual stitched baseline Sharpe = {actual_sh:.3f}; null mean = {null_sh.mean():.3f}, null sd = {null_sh.std():.3f}; one-sided p-value (fraction of null Sharpes >= actual) = {p_value:.4f}

## Skipped-day counts (by reason, mutually exclusive, priority order below)

{md_table([skip_counts])}

## Sizing stats (stitched walk-forward baseline trades)

Median contracts: {median_contracts:.1f}; cap-binding (40 MES) frequency: {cap_pct:.2f}%; rounded-to-zero count: {rounded_to_zero_n}

## Implementation choices

{IMPL_CHOICES}

## Runtime

{runtime:.1f}s (data load + 15 daily-table builds + full walk-forward + premise test + null test + I/O).
"""
    with open(f"{ROOT}/premise1/RESULTS_INSAMPLE.md", "w") as f:
        f.write(report)

    print(f"done in {runtime:.1f}s")
    print(report)


if __name__ == "__main__":
    main()
