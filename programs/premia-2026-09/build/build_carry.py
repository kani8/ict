#!/usr/bin/env python3
"""
Build the carry dataset: 6 FX-trust + 2 bond ETFs, FRED 3m interbank rates
(monthly, 7 currencies), FRED daily yields (DGS10/DGS20/DTB3).
Hygiene job only -- no return statistic conditioned on carry or yields.
Run: uv run --with pandas --with pyarrow --with numpy --with yfinance --with requests python build_carry.py
"""
import time
import urllib.error
import urllib.request
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data_carry"
OUT.mkdir(exist_ok=True)

START, END_EXCL = "2005-01-01", "2026-07-02"   # yfinance end is exclusive -> include 2026-07-01
SPLIT = pd.Timestamp("2024-07-01").date()
ETF_UNIVERSE = ["FXE", "FXY", "FXA", "FXB", "FXC", "FXF", "IEF", "TLT"]
RATE_IDS = {"USD": "IR3TIB01USM156N", "EUR": "IR3TIB01EZM156N", "JPY": "IR3TIB01JPM156N",
            "AUD": "IR3TIB01AUM156N", "GBP": "IR3TIB01GBM156N", "CAD": "IR3TIB01CAM156N",
            "CHF": "IR3TIB01CHM156N"}
RATE_ID_ALTS = {"IR3TIB01EZM156N": "IR3TIB01XMM156N"}   # euro-area spelling ambiguity, per spec
YIELD_IDS = ["DGS10", "DGS20", "DTB3"]
T0 = time.time()
BUDGET_S = 600  # stop if FRED/Yahoo unreachable for >10 min total

def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)

def check_budget(tag):
    if time.time() - T0 > BUDGET_S:
        raise SystemExit(f"STOPPING: exceeded {BUDGET_S}s budget at '{tag}'")

RENAME = {"Open": "open", "High": "high", "Low": "low", "Close": "close",
          "Adj Close": "adj_close", "Volume": "volume", "Dividends": "dividend"}
KEEP = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume", "dividend"]

def fetch_etf(ticker):
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

def fetch_fred_csv(series_id, timeout=20):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
    df = pd.read_csv(StringIO(raw))
    df.columns = ["dt", "val"]
    return df

def fetch_rate_series(ccy, series_id, notes):
    try:
        df = fetch_fred_csv(series_id)
    except urllib.error.HTTPError as e:
        if e.code == 404 and series_id in RATE_ID_ALTS:
            alt = RATE_ID_ALTS[series_id]
            notes.append(f"{series_id} 404'd; retried alternate spelling {alt}")
            df = fetch_fred_csv(alt)
        else:
            notes.append(f"{series_id} FAILED ({e}); {ccy} omitted")
            return None
    df["dt"] = pd.to_datetime(df["dt"]).dt.date
    df["val"] = pd.to_numeric(df["val"], errors="coerce")
    n_before = len(df)
    df = df.dropna(subset=["val"]).sort_values("dt").reset_index(drop=True)
    if n_before - len(df):
        notes.append(f"{ccy} ({series_id}): dropped {n_before - len(df)} non-numeric '.' row(s)")
    return pd.DataFrame({"month": df["dt"], "ccy": ccy, "rate_pct": df["val"]})

def fetch_yield_series(series_id):
    df = fetch_fred_csv(series_id)
    df["dt"] = pd.to_datetime(df["dt"]).dt.date
    df["val"] = pd.to_numeric(df["val"], errors="coerce")   # '.' -> NaN, NOT forward-filled
    return pd.DataFrame({"date": df["dt"], "series": series_id, "pct": df["val"]})

# ---- 1: ETF universe --------------------------------------------------------
log(f"downloading {len(ETF_UNIVERSE)} ETFs, {START} .. 2026-07-01 inclusive (auto_adjust=False) ...")
frames, failed = [], []
for tkr in ETF_UNIVERSE:
    check_budget("etf download")
    try:
        d = fetch_etf(tkr)
        frames.append(d)
        log(f"  {tkr:>4}: {len(d):5,} rows  {d['date'].min()} .. {d['date'].max()}")
    except Exception as e:
        failed.append(tkr)
        log(f"  {tkr:>4}: FAILED -- {e}")
if failed:
    log(f"WARNING: {failed} failed to download -- NOT substituted")
long_df = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)
long_df.to_parquet(OUT / "etf_daily.parquet", index=False)
adj_wide = long_df.pivot(index="date", columns="ticker", values="adj_close").sort_index()
close_wide = long_df.pivot(index="date", columns="ticker", values="close").sort_index()
adj_wide.to_parquet(OUT / "adj_close_wide.parquet")
close_wide.to_parquet(OUT / "close_wide.parquet")
first_valid = (long_df.dropna(subset=["close"]).groupby("ticker")["date"].min()
               .rename("first_valid_date").reset_index())
first_valid.to_csv(OUT / "first_valid_date.csv", index=False)
ins = long_df[long_df["date"] < SPLIT].reset_index(drop=True)
oos = long_df[long_df["date"] >= SPLIT].reset_index(drop=True)
ins.to_parquet(OUT / "etf_daily_insample.parquet", index=False)
oos.to_parquet(OUT / "etf_daily_oos.parquet", index=False)
log(f"split at {SPLIT}: in-sample {len(ins):,} rows, OOS {len(oos):,} rows")

# ---- 2: FRED monthly 3m interbank rates -------------------------------------
log("fetching FRED 3m interbank rates (monthly) ...")
rate_notes, rate_frames = [], []
for ccy, sid in RATE_IDS.items():
    check_budget("rates fetch")
    r = fetch_rate_series(ccy, sid, rate_notes)
    if r is not None:
        rate_frames.append(r)
        log(f"  {ccy} ({sid}): {len(r):,} obs, {r['month'].min()} .. {r['month'].max()}")
rates_df = pd.concat(rate_frames, ignore_index=True) if rate_frames else pd.DataFrame(columns=["month", "ccy", "rate_pct"])
rates_df.to_parquet(OUT / "rates_3m_monthly.parquet", index=False)

# ---- 3: FRED daily yields ----------------------------------------------------
log("fetching FRED daily yields (DGS10, DGS20, DTB3) ...")
yield_frames, yield_notes = [], []
for sid in YIELD_IDS:
    check_budget("yields fetch")
    try:
        y = fetch_yield_series(sid)
        yield_frames.append(y)
        log(f"  {sid}: {len(y):,} rows, {y['date'].min()} .. {y['date'].max()}, NaN={y['pct'].isna().sum()}")
    except Exception as e:
        yield_notes.append(f"{sid} FAILED ({e})")
        log(f"  {sid}: FAILED -- {e}")
yields_df = pd.concat(yield_frames, ignore_index=True) if yield_frames else pd.DataFrame(columns=["date", "series", "pct"])
yields_df.to_parquet(OUT / "yields_daily.parquet", index=False)

# ---- 4: validation ------------------------------------------------------------
log("running validation checks ...")
union_calendar = set(ins["date"]) | set(oos["date"])
lines = ["# VALIDATION.md (data_carry)", "",
         f"Universe: {ETF_UNIVERSE}. Failed downloads: {failed if failed else 'none'}. "
         "Rates/yields are NOT split into in-sample/OOS (they are signals; consumer filters by date).", "",
         "## Per-ticker ETF summary (full 2005-01-01..2026-07-01 span)", "",
         "| ticker | first | last | rows | missing vs union calendar | zero-vol days | |ret|>8% count |",
         "|---|---|---|---|---|---|---|"]
big_moves, div_rows, ratio_viol = [], [], []
for tkr in ETF_UNIVERSE:
    if tkr in failed:
        lines.append(f"| {tkr} | -- | -- | -- | -- | -- | -- |")
        continue
    g = long_df[long_df["ticker"] == tkr].sort_values("date").reset_index(drop=True)
    first_d, last_d, n = g["date"].min(), g["date"].max(), len(g)
    cal_in_range = {d for d in union_calendar if first_d <= d <= last_d}
    missing = len(cal_in_range - set(g["date"]))
    zero_vol = int((g["volume"] == 0).sum())
    ret = g["close"].pct_change()
    big = ret[ret.abs() > 0.08]
    for idx in big.index:
        big_moves.append((tkr, g["date"].loc[idx], big.loc[idx]))
    lines.append(f"| {tkr} | {first_d} | {last_d} | {n:,} | {missing} | {zero_vol} | {len(big)} |")
    ratio = (g["adj_close"] / g["close"]).to_numpy()
    rel = np.diff(ratio) / ratio[:-1]
    for vi in np.where(rel < -1e-4)[0]:
        ratio_viol.append(tkr)
    g["year"] = pd.to_datetime(g["date"]).dt.year
    yr_counts = g[g["dividend"] > 0].groupby("year").size()
    zero_yrs = sorted(set(g["year"].unique()) - set(yr_counts.index))
    div_rows.append((tkr, int((g["dividend"] > 0).sum()), len(zero_yrs), len(yr_counts)))

lines += ["", "## Days with |daily close return| > 8%", ""]
if big_moves:
    lines += ["| ticker | date | ret |", "|---|---|---|"]
    for tkr, d, r in sorted(big_moves, key=lambda x: (x[0], x[1]))[:20]:
        lines.append(f"| {tkr} | {d} | {r:.2%} |")
    if len(big_moves) > 20:
        lines.append(f"... and {len(big_moves) - 20} more.")
else:
    lines.append("None found.")
lines += ["", "## adj_close/close ratio monotonicity", ""]
lines.append("None found -- all tickers consistent." if not ratio_viol
             else f"Violations in: {sorted(set(ratio_viol))}.")
lines += ["", "## Dividend event counts by year (income-component sanity check)", "",
          "| ticker | total div events | years w/ 0 events | years w/ >=1 event |", "|---|---|---|---|"]
lines += [f"| {t} | {tot} | {z} | {nz} |" for t, tot, z, nz in div_rows]
lines.append("FX trusts (FXE/FXY/FXA/FXB/FXC/FXF) pay monthly income tied to the foreign deposit rate; "
             "expect years-w/-0 to cluster in the 2010-2021 near-zero-rate era.")
lines += ["", "## FRED 3m interbank rates (monthly)", "",
          "| ccy | series | first | last | count | gap>1mo | last<2026-06-01 |", "|---|---|---|---|---|---|---|"]
for ccy, sid in RATE_IDS.items():
    sub = rates_df[rates_df["ccy"] == ccy].sort_values("month")
    if sub.empty:
        lines.append(f"| {ccy} | {sid} | -- | -- | 0 | -- | -- |")
        continue
    months = pd.to_datetime(sub["month"])
    gaps = (months.diff().dt.days > 45).sum()
    last = sub["month"].max()
    flag = "YES (discontinuation risk)" if last < pd.Timestamp("2026-06-01").date() else "no"
    lines.append(f"| {ccy} | {sid} | {sub['month'].min()} | {last} | {len(sub)} | {gaps} | {flag} |")
if rate_notes:
    lines += [""] + [f"- {n}" for n in rate_notes]
lines += ["", "## FRED daily yields", "", "| series | first | last | rows | NaN count |", "|---|---|---|---|---|"]
for sid in YIELD_IDS:
    sub = yields_df[yields_df["series"] == sid]
    if sub.empty:
        lines.append(f"| {sid} | -- | -- | 0 | -- |")
        continue
    lines.append(f"| {sid} | {sub['date'].min()} | {sub['date'].max()} | {len(sub):,} | {int(sub['pct'].isna().sum())} |")
if yield_notes:
    lines += [""] + [f"- {n}" for n in yield_notes]
lines += ["", "## Notes / interpretations",
          "- Big-move threshold is |daily close return| > 8% (not adjusted close), per spec.",
          "- Monthly rate 'gap>1mo' = any month-to-month step exceeding 45 days.",
          "- OOS ETF split (>= 2024-07-01): "
          f"{len(oos):,} rows, {oos['date'].min() if len(oos) else '--'} .. {oos['date'].max() if len(oos) else '--'} "
          "(counts/range only, per spec)."]
(OUT / "VALIDATION.md").write_text("\n".join(lines) + "\n")
log(f"done in {time.time() - T0:.1f}s -- wrote {OUT}/VALIDATION.md")
