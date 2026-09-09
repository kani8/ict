#!/usr/bin/env python3
"""
Build a daily dataset for a fixed 20-ticker multi-asset ETF universe.
Run: uv run --with pandas --with pyarrow --with yfinance python build_daily.py

Data-hygiene job only: download, long+wide parquet, in-sample/OOS split,
3m T-bill series, and data_daily/VALIDATION.md. No momentum/trend/Sharpe.
"""
import time
import urllib.request
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

import os

ROOT = Path(__file__).resolve().parent
# Optional overrides so the same hygiene job can build other fixed universes
# (PREMISE_6 breadth set): ETF_OUT=data_breadth ETF_UNIVERSE=SPY,QQQ,... .
OUT = ROOT / os.environ.get("ETF_OUT", "data_daily")
OUT.mkdir(exist_ok=True)

START, END_EXCL = "2003-01-01", "2026-07-02"   # yfinance end is exclusive -> include 2026-07-01
SPLIT = pd.Timestamp("2024-07-01").date()
UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ",    # equities
            "TLT", "IEF", "LQD", "HYG", "TIP",           # bonds
            "GLD", "SLV", "USO", "DBC",                  # commodities
            "UUP", "FXE", "FXY", "FXA",                  # currencies
            "VNQ"]                                       # real estate
if os.environ.get("ETF_UNIVERSE"):
    UNIVERSE = [t.strip() for t in os.environ["ETF_UNIVERSE"].split(",") if t.strip()]
else:
    assert len(UNIVERSE) == 20
T0 = time.time()


def log(msg):
    print(f"[{time.time()-T0:7.1f}s] {msg}", flush=True)


RENAME = {"Open": "open", "High": "high", "Low": "low", "Close": "close",
          "Adj Close": "adj_close", "Volume": "volume", "Dividends": "dividend"}
KEEP = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume", "dividend"]


def fetch(ticker):
    df = yf.download(ticker, start=START, end=END_EXCL, auto_adjust=False, actions=True, progress=False)
    if df is None or df.empty:
        raise ValueError("no data returned")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=RENAME).reset_index().rename(columns={"Date": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["ticker"] = ticker
    if "dividend" not in df.columns:
        df["dividend"] = 0.0
    return df[KEEP]


def fetch_tbill():
    try:
        req = urllib.request.Request("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3",
                                      headers={"User-Agent": "curl/8.0"})
        raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        t = pd.read_csv(StringIO(raw))
        t.columns = ["date", "rate_pct"]
        t["date"] = pd.to_datetime(t["date"]).dt.date
        t["rate_pct"] = pd.to_numeric(t["rate_pct"], errors="coerce")
        t = t.dropna(subset=["rate_pct"])
        t = t[t["date"] >= pd.to_datetime(START).date()]
        if t.empty:
            raise ValueError("FRED returned no usable numeric rows")
        return t.sort_values("date").reset_index(drop=True), "FRED DTB3"
    except Exception as e:
        log(f"FRED fetch failed ({e}); falling back to yfinance ^IRX ...")
    try:
        t = fetch("^IRX")[["date", "close"]].rename(columns={"close": "rate_pct"}).dropna()
        if t.empty:
            raise ValueError("^IRX returned no rows")
        return t.sort_values("date").reset_index(drop=True), "yfinance ^IRX"
    except Exception as e:
        log(f"^IRX fetch also failed ({e})")
        return None, None


# ---- step 1: download universe -------------------------------------------
log(f"downloading {len(UNIVERSE)} tickers, {START} .. 2026-07-01 inclusive (auto_adjust=False, actions=True) ...")
dl_t0 = time.time()
frames, failed = [], []
for tkr in UNIVERSE:
    try:
        d = fetch(tkr)
        frames.append(d)
        log(f"  {tkr:>5}: {len(d):5,} rows  {d['date'].min()} .. {d['date'].max()}")
    except Exception as e:
        failed.append(tkr)
        log(f"  {tkr:>5}: FAILED -- {e}")
dl_elapsed = time.time() - dl_t0
if failed:
    log(f"WARNING: {len(failed)} ticker(s) failed to download: {failed} -- NOT substituted, per spec")

long_df = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)
log(f"long frame: {len(long_df):,} rows across {long_df['ticker'].nunique()} tickers")
long_df.to_parquet(OUT / "etf_daily.parquet", index=False)

adj_wide = long_df.pivot(index="date", columns="ticker", values="adj_close").sort_index()
close_wide = long_df.pivot(index="date", columns="ticker", values="close").sort_index()
adj_wide.to_parquet(OUT / "adj_close_wide.parquet")
close_wide.to_parquet(OUT / "close_wide.parquet")

# ---- step 2: first valid date ---------------------------------------------
first_valid = (long_df.dropna(subset=["close"]).groupby("ticker")["date"].min()
               .rename("first_valid_date").reset_index())
first_valid.to_csv(OUT / "first_valid_date.csv", index=False)
log(f"wrote first_valid_date.csv ({len(first_valid)} tickers)")

# ---- step 3: in-sample / OOS split (OOS is LOCKED) -------------------------
ins = long_df[long_df["date"] < SPLIT].reset_index(drop=True)
oos = long_df[long_df["date"] >= SPLIT].reset_index(drop=True)
ins.to_parquet(OUT / "etf_daily_insample.parquet", index=False)
oos.to_parquet(OUT / "etf_daily_oos.parquet", index=False)
adj_wide[adj_wide.index < SPLIT].to_parquet(OUT / "adj_close_wide_insample.parquet")
adj_wide[adj_wide.index >= SPLIT].to_parquet(OUT / "adj_close_wide_oos.parquet")
close_wide[close_wide.index < SPLIT].to_parquet(OUT / "close_wide_insample.parquet")
close_wide[close_wide.index >= SPLIT].to_parquet(OUT / "close_wide_oos.parquet")
log(f"split at {SPLIT}: in-sample {len(ins):,} rows, OOS {len(oos):,} rows (LOCKED -- counts only)")

# ---- step 4: 3-month T-bill -------------------------------------------------
log("fetching 3m T-bill rate ...")
tbill, tbill_src = fetch_tbill()
if tbill is not None:
    tbill.to_parquet(OUT / "tbill_3m.parquet", index=False)
    log(f"tbill_3m.parquet: {len(tbill):,} rows from {tbill_src}")
else:
    log("T-BILL FETCH FAILED: both FRED and ^IRX unreachable -- tbill_3m.parquet NOT written")

# ---- step 5: validation ------------------------------------------------------
log("running validation checks ...")
spy_ins_dates = set(ins.loc[ins["ticker"] == "SPY", "date"])
lines = ["# VALIDATION.md", "",
         f"Universe: {len(UNIVERSE)} tickers. Failed downloads: {failed if failed else 'none'}.",
         f"3m T-bill source: {tbill_src if tbill_src else 'FAILED (FRED and ^IRX both unreachable)'}.", "",
         "## Per-ticker in-sample (date < 2024-07-01) summary", "",
         "| ticker | first date | last in-sample date | in-sample rows | gaps vs SPY calendar | "
         "max abs adj return | date of max | days abs(ret)>15% |",
         "|---|---|---|---|---|---|---|---|"]

big_moves_all, ratio_violations = [], []
for tkr in UNIVERSE:
    if tkr in failed:
        lines.append(f"| {tkr} | -- | -- | -- | -- | -- | -- | -- |")
        continue
    g = ins[ins["ticker"] == tkr].sort_values("date").reset_index(drop=True)
    first_date, last_date, n_rows = g["date"].min(), g["date"].max(), len(g)
    spy_in_range = {dd for dd in spy_ins_dates if first_date <= dd <= last_date}
    gap_count = len(spy_in_range - set(g["date"]))

    ret = g["adj_close"].pct_change()
    if ret.notna().any():
        idx_max = ret.abs().idxmax()
        max_ret, max_ret_date = ret.abs().loc[idx_max], g["date"].loc[idx_max]
    else:
        max_ret, max_ret_date = float("nan"), None
    big = g.loc[ret.abs() > 0.15, ["date"]].copy()
    big["ret"] = ret[ret.abs() > 0.15]
    for _, r in big.iterrows():
        big_moves_all.append((tkr, r["date"], r["ret"]))
    lines.append(f"| {tkr} | {first_date} | {last_date} | {n_rows:,} | {gap_count} | "
                 f"{max_ret:.2%} | {max_ret_date} | {len(big)} |")

    ratio = (g["adj_close"] / g["close"]).to_numpy()
    rel_diff = np.diff(ratio) / ratio[:-1]   # relative step; float rounding noise tops out ~2e-6
    for vi in np.where(rel_diff < -1e-4)[0]:
        ratio_violations.append((tkr, g["date"].iloc[vi + 1], ratio[vi], ratio[vi + 1]))

lines += ["", "## Days with |adjusted daily return| > 15%", ""]
if big_moves_all:
    lines += ["| ticker | date | return |", "|---|---|---|"]
    lines += [f"| {tkr} | {d} | {r:.2%} |" for tkr, d, r in sorted(big_moves_all, key=lambda x: (x[0], x[1]))]
else:
    lines.append("None found.")

lines += ["", "## adj_close/close ratio monotonicity (must be non-decreasing forward in time; "
              "a decrease flags a dividend/split-adjustment inconsistency)", ""]
if ratio_violations:
    lines += [f"{len(ratio_violations)} violation(s) found:", "",
              "| ticker | date | ratio before | ratio after |", "|---|---|---|---|"]
    lines += [f"| {tkr} | {d} | {b:.6f} | {a:.6f} |" for tkr, d, b, a in ratio_violations[:50]]
    if len(ratio_violations) > 50:
        lines.append(f"... and {len(ratio_violations) - 50} more.")
else:
    lines.append("None found -- adjustments are dividend/split-consistent for all tickers.")

lines += ["", "## SPY vs IVV sanity check (IVV is a one-off pull, not part of the saved universe)", ""]
try:
    ivv_ins = fetch("IVV").query("date < @SPLIT").sort_values("date")
    spy_ins = ins[ins["ticker"] == "SPY"].sort_values("date")
    merged = pd.merge(spy_ins[["date", "adj_close"]], ivv_ins[["date", "adj_close"]],
                       on="date", suffixes=("_spy", "_ivv"))
    corr = merged["adj_close_spy"].pct_change().corr(merged["adj_close_ivv"].pct_change())
    status = "PASS" if corr >= 0.97 else "FAIL"
    lines.append(f"Correlation of SPY vs IVV in-sample daily adjusted returns "
                 f"({len(merged):,} overlapping days, {merged['date'].min()} .. {merged['date'].max()}): "
                 f"{corr:.4f} ({status}, threshold 0.97).")
except Exception as e:
    lines.append(f"Could not pull IVV for sanity check: {e}")

total_elapsed = time.time() - T0
lines += ["", "## Timing", "",
          f"- Universe download time ({len(UNIVERSE)} tickers): {dl_elapsed:.1f}s",
          f"- Total script wall time (download + T-bill + IVV sanity + validation): {total_elapsed:.1f}s"]
(OUT / "VALIDATION.md").write_text("\n".join(lines) + "\n")
log(f"done in {total_elapsed:.1f}s -- wrote {OUT}/VALIDATION.md")
