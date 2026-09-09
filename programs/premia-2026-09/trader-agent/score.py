#!/usr/bin/env python3
"""Trail B scorer. Resolves expired ledger calls against yfinance daily bars,
appends to resolved.csv (append-only, never re-resolves a row), and writes
SCORECARD.md. See PLAYBOOK.md for the rules this implements.

Run: uv run --with pandas --with yfinance --with numpy python trader-agent/score.py
"""
import argparse, os
from datetime import date, timedelta
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None

MULT = {"ES=F": (5.0, 0.25), "NQ=F": (2.0, 0.25)}  # instrument -> (multiplier, tick)
HORIZON_N = {"1d": 1, "5d": 5}
RESOLVED_COLS = ["date", "instrument", "call", "horizon", "conviction", "hype", "entry",
                 "invalidation", "target", "size", "exit_date", "exit_price", "stopped",
                 "pnl", "p", "brier", "correct", "resolved_at"]

def classify(call, size):
    call = str(call).strip().lower()
    try:
        sz = float(size)
    except Exception:
        sz = 0.0
    if call in ("long", "short") and sz > 0:
        return "entered"
    if call == "flat":
        return "flat"
    return "watch"

def get_history(ticker, start, cache, notes):
    if ticker in cache:
        return cache[ticker]
    df = None
    if yf is not None:
        try:
            df = yf.download(ticker, start=(start - timedelta(days=5)).isoformat(),
                              end=(date.today() + timedelta(days=1)).isoformat(),
                              interval="1d", progress=False, auto_adjust=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is None or df.empty:
                df = None
        except Exception as e:
            notes.append(f"yfinance fetch failed for {ticker}: {e}")
            df = None
    if df is not None:
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.normalize()
    cache[ticker] = df
    return df

def resolve_row(row, cache, notes):
    """Return a resolved dict, or None if not yet resolvable / data missing."""
    inst, call, horizon = row["instrument"], str(row["call"]).lower(), str(row["horizon"]).strip()
    n = HORIZON_N.get(horizon)
    if n is None:
        notes.append(f"{row['date']} {inst}: unknown horizon '{horizon}', skipping")
        return None
    try:
        call_date = pd.to_datetime(row["date"]).normalize()
        entry, invalidation, size = float(row["entry"]), float(row["invalidation"]), float(row["size"])
    except Exception:
        notes.append(f"{row['date']} {inst}: missing entry/invalidation/size, skipping")
        return None
    df = get_history(inst, call_date.date(), cache, notes)
    if df is None:
        notes.append(f"{row['date']} {inst}: no price data available, skipping")
        return None
    bars = df[df["Date"] >= call_date].sort_values("Date").reset_index(drop=True)
    if bars.empty:
        notes.append(f"{row['date']} {inst}: no bars on/after call date, skipping")
        return None
    direction = 1 if call == "long" else -1
    exit_date = exit_price = stopped = None
    last_idx = min(n, len(bars) - 1)
    for i in range(0, last_idx + 1):
        lo, hi = bars.loc[i, "Low"], bars.loc[i, "High"]
        hit = (lo <= invalidation) if direction == 1 else (hi >= invalidation)
        if hit:
            exit_date, exit_price, stopped = bars.loc[i, "Date"], invalidation, True
            break
    if exit_date is None:
        if len(bars) < n + 1:
            return None  # horizon hasn't elapsed yet and no stop hit
        exit_date, exit_price, stopped = bars.loc[n, "Date"], float(bars.loc[n, "Close"]), False
    mult, tick = MULT.get(inst, (1.0, None))
    if inst in MULT:
        cost = 1.00 * size + tick * mult * size * 2
    else:
        cost = 0.005 * size * 2
    pnl = direction * (exit_price - entry) * size * mult - cost
    conviction = float(row["conviction"])
    p = 0.5 + 0.08 * conviction
    correct = pnl > 0
    brier = (p - (1.0 if correct else 0.0)) ** 2
    return {"date": row["date"], "instrument": inst, "call": call, "horizon": horizon,
            "conviction": conviction, "hype": row.get("hype"), "entry": entry,
            "invalidation": invalidation, "target": row.get("target"), "size": size,
            "exit_date": exit_date.date().isoformat(), "exit_price": exit_price,
            "stopped": stopped, "pnl": pnl, "p": p, "brier": brier, "correct": correct,
            "resolved_at": date.today().isoformat()}

def bootstrap_ci(values, reps=1000, alpha=0.10, seed=7):
    if len(values) == 0:
        return None, None
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    means = [rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(reps)]
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return lo, hi

def sharpe_and_drawdown(resolved):
    if resolved.empty:
        return float("nan"), float("nan")
    calls = pd.to_datetime(resolved["date"])
    exits = pd.to_datetime(resolved["exit_date"])
    idx = pd.bdate_range(calls.min(), exits.max())
    daily = pd.Series(0.0, index=idx)
    for d, p in zip(exits, resolved["pnl"]):
        d = pd.Timestamp(d).normalize()
        if d in daily.index:
            daily[d] += p
    sharpe = float("nan")
    if daily.std(ddof=1) > 0:
        sharpe = daily.mean() / daily.std(ddof=1) * (252 ** 0.5)
    cum = daily.cumsum()
    dd = (cum - cum.cummax()).min()
    return sharpe, dd

def table(df, by):
    if df.empty:
        return "_no resolved calls yet_\n"
    g = df.groupby(by).agg(n=("pnl", "size"), hit_rate=("correct", "mean"),
                            mean_pnl=("pnl", "mean")).reset_index()
    lines = [f"| {by} | n | hit rate | mean P&L |", "|---|---|---|---|"]
    for _, r in g.iterrows():
        lines.append(f"| {r[by]} | {int(r['n'])} | {r['hit_rate']:.0%} | ${r['mean_pnl']:.2f} |")
    return "\n".join(lines) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=None)
    args = ap.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ledger_path = args.ledger or os.path.join(script_dir, "ledger.csv")
    out_dir = os.path.dirname(os.path.abspath(ledger_path))
    resolved_path = os.path.join(out_dir, "resolved.csv")
    scorecard_path = os.path.join(out_dir, "SCORECARD.md")

    ledger = pd.read_csv(ledger_path, dtype=str).fillna("")
    ledger["_class"] = [classify(c, s) for c, s in zip(ledger["call"], ledger["size"])]
    counts = ledger["_class"].value_counts().to_dict()

    prior = pd.read_csv(resolved_path) if os.path.exists(resolved_path) else pd.DataFrame(columns=RESOLVED_COLS)
    prior_keys = set(prior["date"].astype(str) + "|" + prior["instrument"].astype(str) + "|" + prior["call"].astype(str))

    notes, cache, new_rows = [], {}, []
    for _, row in ledger[ledger["_class"] == "entered"].iterrows():
        key = f"{row['date']}|{row['instrument']}|{row['call']}"
        if key in prior_keys:
            continue
        res = resolve_row(row, cache, notes)
        if res is not None:
            new_rows.append(res)

    if new_rows:
        new_df = pd.DataFrame(new_rows)[RESOLVED_COLS]
        header = not os.path.exists(resolved_path)
        new_df.to_csv(resolved_path, mode="a", header=header, index=False)

    resolved = pd.read_csv(resolved_path) if os.path.exists(resolved_path) else pd.DataFrame(columns=RESOLVED_COLS)
    if not resolved.empty:
        resolved["correct"] = resolved["correct"].astype(str).str.lower().isin(["true", "1"])

    lines = ["# SCORECARD (Trail B)", "", f"Generated: {date.today().isoformat()}", "",
              f"Calls logged — entered: {counts.get('entered', 0)}, watch: {counts.get('watch', 0)}, "
              f"flat: {counts.get('flat', 0)}", f"Resolved calls: {len(resolved)}", ""]

    if resolved.empty:
        lines.append("**No calls have been resolved yet.** Nothing to score.")
    else:
        hit_rate = resolved["correct"].mean()
        brier_mean = resolved["brier"].astype(float).mean()
        lo, hi = bootstrap_ci(resolved["brier"].astype(float).tolist())
        pnl_total = resolved["pnl"].astype(float).sum()
        sharpe, mdd = sharpe_and_drawdown(resolved)
        lines += [
            f"- Hit rate: {hit_rate:.1%}",
            f"- Mean Brier: {brier_mean:.4f}  (90% bootstrap CI: [{lo:.4f}, {hi:.4f}], n=1000 reps)",
            f"- Cumulative paper P&L: ${pnl_total:,.2f}",
            f"- Daily-P&L Sharpe (annualised): {sharpe:.2f}",
            f"- Max drawdown: ${mdd:,.2f}", "",
            "## By conviction", table(resolved, "conviction"), "## By hype", table(resolved, "hype"),
            "## By instrument", table(resolved, "instrument"), "## By horizon", table(resolved, "horizon"),
            "## Stop rule (PLAYBOOK.md)",
        ]
        first_date = pd.to_datetime(ledger["date"]).min()
        days_elapsed = (pd.Timestamp(date.today()) - first_date).days if pd.notna(first_date) else 0
        ci_excludes = hi < 0.25 if hi is not None else False
        lines += [
            f"- Resolved non-flat calls: {len(resolved)} / 60",
            f"- Days since first ledger entry: {days_elapsed} / 180",
            f"- Brier 90% CI excludes 0.25: {ci_excludes} (CI=[{lo:.4f},{hi:.4f}])",
            f"- Sharpe >= 0.5: {sharpe >= 0.5 if sharpe == sharpe else False} (Sharpe={sharpe:.2f})",
            f"- Stop triggered: {(len(resolved) >= 60 or days_elapsed >= 180) and (not ci_excludes or (sharpe == sharpe and sharpe < 0.5))}",
        ]
    if notes:
        lines += ["", "## Notes (skipped/unresolvable rows)"] + [f"- {n}" for n in notes]

    with open(scorecard_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {resolved_path} ({len(resolved)} resolved) and {scorecard_path}")
    if notes:
        print(f"{len(notes)} note(s) — see SCORECARD.md")

if __name__ == "__main__":
    main()
