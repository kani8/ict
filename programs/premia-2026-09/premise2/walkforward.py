"""Premise 2: day frame + premise test + walk-forward + null test + report
(TASK.md Steps 1, 3, 4, 5). Step 6 (no-lookahead) is test_no_lookahead.py.

make_windows/md_table are copied unchanged from premise1/walkforward.py.

Run: uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python premise2/walkforward.py
"""
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from strategy import (build_day_frame, load_insample, matched_null_legs,
                       max_drawdown, ols_hac, sharpe, simulate)

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
M_GRID = [0.75, 1.0, 1.5]
N_GRID = [14, 30, 60]
BASE_SLIP, STRESS_SLIP, FEE = 1, 2, 1.00
GATE_SHARPE, GATE_TRADES = 1.0, 800


def make_windows():
    """11 test windows 2013-07..2024-06, 3y train immediately before each. (copied from premise1)"""
    out = []
    for y in range(2013, 2024):
        test_start = pd.Timestamp(f"{y}-07-01").date()
        test_end = pd.Timestamp(f"{y + 1}-06-30").date()
        train_start = pd.Timestamp(f"{y - 3}-07-01").date()
        train_end = (pd.Timestamp(f"{y}-07-01") - pd.Timedelta(days=1)).date()
        out.append((test_start, test_end, train_start, train_end))
    return out


def md_table(rows: list[dict]) -> str:
    """(copied from premise1)"""
    if not rows:
        return ""
    cols = list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def slice_dates(df: pd.DataFrame, start, end) -> pd.DataFrame:
    return df[(df["date"] >= start) & (df["date"] <= end)].reset_index(drop=True)


def summarize(trades_df: pd.DataFrame, daily_pnl_df: pd.DataFrame) -> dict:
    """Headline stats: daily Sharpe/maxdd/net over the FULL kept-day series
    (incl. zero days), plus leg-level trade diagnostics (Step 2 requirements)."""
    n_days = len(daily_pnl_df)
    longs = trades_df[trades_df["dir"] == 1]
    shorts = trades_df[trades_df["dir"] == -1]
    flips = trades_df[trades_df["exit_reason"] == "flip"]
    hold_h = trades_df["exit_t"] - trades_df["entry_t"]
    return dict(
        sharpe=sharpe(daily_pnl_df["net"]), maxdd=max_drawdown(daily_pnl_df["net"]),
        trades=int(len(trades_df)), net_pnl=float(daily_pnl_df["net"].sum()),
        trades_per_day=float(len(trades_df) / n_days) if n_days else float("nan"),
        flips_per_day=float(len(flips) / n_days) if n_days else float("nan"),
        hit_rate=float((trades_df["net"] > 0).mean()) if len(trades_df) else float("nan"),
        mean_net_per_trade=float(trades_df["net"].mean()) if len(trades_df) else float("nan"),
        mean_hold_hours=float(hold_h.mean()) if len(hold_h) else float("nan"),
        long_sharpe=sharpe(longs["net"]), long_trades=int(len(longs)),
        short_sharpe=sharpe(shorts["net"]), short_trades=int(len(shorts)),
    )


def main():
    t0 = time.time()
    print("loading in-sample data...")
    m1 = load_insample(f"{ROOT}/data/es_1m_insample.parquet")
    h1 = load_insample(f"{ROOT}/data/es_1h_insample.parquet")
    h4 = load_insample(f"{ROOT}/data/es_4h_insample.parquet")

    print("building day frames + simulating for 9 (m,N) grid points...")
    day_frames = {(m, N): build_day_frame(m1, h1, h4, m, N) for m in M_GRID for N in N_GRID}
    skip_counts = day_frames[(1.0, 14)].attrs["skip_counts"]
    base_sim = {mn: simulate(df, BASE_SLIP, FEE) for mn, df in day_frames.items()}
    stress_sim = {mn: simulate(df, STRESS_SLIP, FEE) for mn, df in day_frames.items()}

    # --- Step 3: premise test (pooled, independent of m/N: verified identical
    # across all 9 grid points since it only needs the day-level skip set) ---
    print("running premise test...")
    ref_df = day_frames[(1.0, 14)]
    t10 = ref_df[(ref_df["t"] == 10) & ref_df["close_ok"]].copy()
    t10["r_open"] = np.log(t10["close_t"] / t10["C_prev"])
    t10["r_rest"] = np.log(t10["P16"] / t10["close_t"])
    pooled = ols_hac(t10, "r_open", "r_rest", lags=5)

    desc = ref_df[ref_df["usable"]].copy()
    desc["r_t16"] = np.log(desc["P16"] / desc["fill_open"])
    breached = desc[desc["target"].abs() == 1]
    breach_mean_bp = float((np.sign(breached["target"]) * breached["r_t16"] * 1e4).mean())
    breach_n, breach_share = int(len(breached)), float(len(breached) / len(desc))
    uncond_abs_bp = float((desc["r_t16"].abs() * 1e4).mean())

    # --- Step 4: walk-forward selection (m,N chosen by baseline train Sharpe) ---
    print("running walk-forward (9 combos x 11 windows)...")
    windows = make_windows()
    wf_rows = []
    bt_frames, bd_frames, st_frames, sd_frames = [], [], [], []
    for ts, te, trs, tre in windows:
        train_sh = {mn: sharpe(slice_dates(base_sim[mn][1], trs, tre)["net"]) for mn in day_frames}
        best_mn = max(train_sh, key=lambda mn: (train_sh[mn] if not np.isnan(train_sh[mn]) else -np.inf))
        m, N = best_mn
        b_trades, b_daily = base_sim[best_mn]
        s_trades, s_daily = stress_sim[best_mn]
        tb_t, tb_d = slice_dates(b_trades, ts, te), slice_dates(b_daily, ts, te)
        ts_t, ts_d = slice_dates(s_trades, ts, te), slice_dates(s_daily, ts, te)
        label = f"{ts.year}-{te.year}"
        for f in (tb_t, tb_d, ts_t, ts_d):
            f["test_year"] = label
        wf_rows.append(dict(test_start=ts, test_end=te, m=m, N=N,
                             train_sharpe=train_sh[best_mn], test_sharpe=sharpe(tb_d["net"]),
                             test_trades=int(len(tb_t)), test_net_pnl=float(tb_d["net"].sum())))
        bt_frames.append(tb_t); bd_frames.append(tb_d); st_frames.append(ts_t); sd_frames.append(ts_d)

    wf_windows = pd.DataFrame(wf_rows)
    stitched_bt = pd.concat(bt_frames, ignore_index=True)
    stitched_bd = pd.concat(bd_frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    stitched_st = pd.concat(st_frames, ignore_index=True)
    stitched_sd = pd.concat(sd_frames, ignore_index=True).sort_values("date").reset_index(drop=True)

    stats_base = summarize(stitched_bt, stitched_bd)
    stats_stress = summarize(stitched_st, stitched_sd)
    annual = stitched_bd.groupby("test_year")["net"].sum().reset_index().rename(columns={"net": "net_pnl"})

    # --- references: (a) fixed m=1,N=14 no-selection; (b) buy-and-hold ES ---
    print("computing references and null test...")
    overall_start, overall_end = windows[0][0], windows[-1][1]
    ref_a_trades_full, ref_a_daily_full = base_sim[(1.0, 14)]
    ref_a_daily = slice_dates(ref_a_daily_full, overall_start, overall_end)
    ref_a_trades = slice_dates(ref_a_trades_full, overall_start, overall_end)
    ref_a_stats = summarize(ref_a_trades, ref_a_daily)

    px = day_frames[(1.0, 14)][["date", "C_prev", "P16"]].drop_duplicates("date").reset_index(drop=True)
    bh_rets = []
    for ts, te, *_ in windows:
        seg = px[(px["date"] >= ts) & (px["date"] <= te)]
        bh_rets.append(np.log(seg["P16"].iloc[-1] / seg["C_prev"].iloc[0]))
    bh_rets = np.array(bh_rets)
    bh_sharpe = float(bh_rets.mean() / bh_rets.std(ddof=1))

    # --- Step 5: matched null on stitched baseline trades ---
    actual_sh, null_sh, p_value = matched_null_legs(stitched_bt, stitched_bd, BASE_SLIP, FEE)

    # --- sizing stats over stitched baseline trades ---
    median_contracts = float(stitched_bt["contracts"].median())
    cap_pct = float(stitched_bt["cap_bound"].mean()) * 100
    rounded_to_zero_n = int(stitched_bd["rounded_to_zero"].sum())

    print("writing outputs...")
    wf_windows.to_csv(f"{ROOT}/premise2/wf_windows.csv", index=False)
    stitched_bt.to_csv(f"{ROOT}/premise2/trades_wf.csv", index=False)
    stitched_bd.assign(net_stress=stitched_sd["net"].to_numpy()).to_csv(f"{ROOT}/premise2/daily_pnl_wf.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(pd.to_datetime(stitched_bd["date"]), stitched_bd["net"].cumsum(), label="walk-forward (baseline)")
    ax.plot(pd.to_datetime(ref_a_daily["date"]), ref_a_daily["net"].cumsum(), label="fixed m=1,N=14 (baseline)", alpha=0.7)
    ax.set_title("Premise 2 stitched walk-forward: cumulative net P&L ($)")
    ax.set_xlabel("date"); ax.set_ylabel("cumulative $"); ax.legend(); fig.tight_layout()
    fig.savefig(f"{ROOT}/premise2/equity_wf.png", dpi=120)

    runtime = time.time() - t0
    verdict = "PASS" if (stats_base["sharpe"] >= GATE_SHARPE and stats_base["trades"] >= GATE_TRADES) else "FAIL"
    premise_pass = "PASS" if pooled[0] > 0 and pooled[1] > 2 else "FAIL"
    wf_rows_r = [{**r, "train_sharpe": round(r["train_sharpe"], 3), "test_sharpe": round(r["test_sharpe"], 3)} for r in wf_rows]

    IMPL_CHOICES = """- sigma_t's "prior N trading days" pool is ALL candidate ET weekdays with a valid O and a valid close_t (bar n_1m>=50), independent of whether that day itself is later skipped for reasons unrelated to O/close_t (no_1600_bar, roll_crossing, day_after_early_close) -- these skips concern exit/anchor integrity, not the trustworthiness of that day's own close_t for the noise-band history.
- "instrument_id of today's bars" (roll-crossing) is read as the instrument of the earliest available hourly bar for date d (hours 9-16, back-filled), compared against the prior kept day's 16:00 bar instrument.
- An unnamed 5th skip, prev16_missing (C_prev has no valid prior 16:00 bar anywhere in history -- fires once, on the first candidate date), is added in the same spirit as premise1's Amendment-A1 precedent; not one of PREMISE_2's 4 named reasons but forced by the ffill mechanics of C_prev.
- Sizing price P in contracts=round(notional/(5*P)) is the fill price (open of bar t), i.e. sized at the actual transaction price at the flip/entry moment, per "sized at the flip time."
- A signal whose sizing rounds to zero contracts executes no leg at all (any existing position is left open unchanged); it only increments the rounded-to-zero counter -- treated as "no trade," not a flip-to-flat.
- trades_wf.csv entry_px/exit_px are raw (unadjusted) bar opens; slippage and fees are separate $ cost columns (slippage_ticks*tick*mult*2*contracts, fee_rt*contracts per leg), mirroring premise1's day-level cost convention rather than adjusting the recorded price.
- A signal with a missing fill_open (bar t open) or missing sigma_4h is treated as "no execution / hold" -- not an explicit spec case, forced by data gaps, resolved conservatively (no trade fabricated).
- Step 3's descriptive add-on (breach mean bp, count, share, unconditional mean |r|) all use the same denominator: (d,t) rows where the m=1,N=14 band is fully evaluable (close_t and sigma_t both valid), not the full 6x(kept days) row count.
- Step 5's matched null randomizes leg-level `dir` (keeping contracts/entry_px/exit_px/dates fixed) then re-aggregates to the daily series (incl. zero-net days) per rep before computing Sharpe -- adapted, not copied, from premise1's matched_null, since here the null-randomization unit (a leg) differs from the Sharpe-aggregation unit (a day).
- sigma_4h is ONE value per day d (from the [10:00,14:00) 4h bar, "known" by 14:00 ET), used to size every decision t=10..15 that day, per PREMISE_2.md/TASK.md non-negotiable #4 verbatim. This means t<14 entries are sized off same-day vol info not causally available until 14:00 -- an artifact of literally reusing P1's fixed sizing-vol timestamp, not a bug; TASK.md's no-lookahead requirement (and the prefix test) is about cross-DATE leakage, which this satisfies."""

    report = f"""# RESULTS_INSAMPLE.md

**VERDICT: {verdict}** -- stitched walk-forward baseline net Sharpe = {stats_base['sharpe']:.3f} (gate >= {GATE_SHARPE}), trades = {stats_base['trades']} (gate >= {GATE_TRADES}).

## Step 3 -- premise test (pooled in-sample, r_rest ~ r_open, HAC-5)

{md_table([dict(beta=pooled[0], t=pooled[1], r2=pooled[2], n=pooled[3])])}

Pass criterion (beta>0 and t>2): {premise_pass}

Descriptive add-on (m=1, N=14): mean of sign(breach)*ln(P16/open_t) over breached (d,t) = {breach_mean_bp:.3f} bp (n={breach_n}, share of evaluable (d,t) breached = {breach_share:.4f}); unconditional mean |ln(P16/open_t)| over the same evaluable set = {uncond_abs_bp:.3f} bp.

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

(a) fixed m=1, N=14, no walk-forward selection:

{md_table([ref_a_stats])}

(b) buy-and-hold ES, one log return per test window, annualised Sharpe: {bh_sharpe:.3f}

## Step 5 -- matched null (2000 reps, randomised leg direction)

Actual stitched baseline Sharpe = {actual_sh:.3f}; null mean = {null_sh.mean():.3f}, null sd = {null_sh.std():.3f}; one-sided p-value (fraction of null Sharpes >= actual) = {p_value:.4f}

## Skipped-day counts (by reason, mutually exclusive, priority order below)

{md_table([skip_counts])}

## Sizing stats (stitched walk-forward baseline trades)

Median contracts: {median_contracts:.1f}; cap-binding (40 MES) frequency: {cap_pct:.2f}%; rounded-to-zero count: {rounded_to_zero_n}

## Implementation choices

{IMPL_CHOICES}

## Runtime

{runtime:.1f}s (data load + 9 day-frame builds + 18 simulate() calls + walk-forward + premise test + null test + I/O).
"""
    with open(f"{ROOT}/premise2/RESULTS_INSAMPLE.md", "w") as f:
        f.write(report)

    print(f"done in {runtime:.1f}s")
    print(report)


if __name__ == "__main__":
    main()
