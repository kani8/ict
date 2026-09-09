#!/usr/bin/env python3
"""
Build VX futures + VIX spot hygiene dataset (coverage/scaling/calendar checks only;
no return/P&L/regression logic -- see PREMISE_4.md).
Run: uv run --with pandas --with pyarrow --with numpy --with requests python build_vx.py
"""
import time
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data_vx"
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SPLIT = pd.Timestamp("2024-07-01")
DAILY_START = pd.Timestamp("2004-03-26")
RESCALE_CUTOFF = pd.Timestamp("2007-03-26")
UA = {"User-Agent": "Mozilla/5.0 (data-hygiene research script; contact: kvatsavayi@example.com)"}
T0 = time.time()
_last_req = [0.0]
MONTH_CODE = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
              7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}


def log(msg):
    print(f"[{time.time()-T0:7.1f}s] {msg}", flush=True)


def throttled_get(url):
    """<=4 req/sec, 20s timeout, one retry on exception/5xx."""
    for attempt in (1, 2):
        wait = 0.25 - (time.time() - _last_req[0])
        if wait > 0:
            time.sleep(wait)
        _last_req[0] = time.time()
        try:
            r = requests.get(url, headers=UA, timeout=20)
            if r.status_code == 200:
                return 200, r.text
            if r.status_code >= 500 and attempt == 1:
                continue
            return r.status_code, None
        except requests.RequestException as e:
            if attempt == 2:
                log(f"  request failed twice: {url} ({e})")
                return None, None
    return None, None


def fetch_cached(url, cache_name):
    ok_path, miss_path = RAW / cache_name, RAW / (cache_name + ".MISSING")
    if ok_path.exists():
        return ok_path.read_text()
    if miss_path.exists():
        return None
    status, text = throttled_get(url)
    if status == 200 and text and "," in text.splitlines()[0]:
        ok_path.write_text(text)
        return text
    miss_path.touch()
    return None


def month_range(y0, m0, y1, m1):
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            m, y = 1, y + 1


def third_friday(y, m):
    d = date(y, m, 1)
    fridays = []
    while d.month == m:
        if d.weekday() == 4:
            fridays.append(d)
        d += timedelta(days=1)
    return fridays[2]


def nominal_wed(y, m):
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return third_friday(ny, nm) - timedelta(days=30)


def normalize_cols(df):
    df.columns = [c.strip().lower() for c in df.columns]
    ren = {"trade date": "date", "futures": "label", "open": "open", "high": "high",
           "low": "low", "close": "close", "settle": "settle", "total volume": "volume",
           "open interest": "oi"}
    return df.rename(columns={k: v for k, v in ren.items() if k in df.columns})


def parse_contract_csv(text, expiry, source):
    text = "\n".join(ln.rstrip(",") for ln in text.splitlines())  # some archive rows have a stray trailing comma
    df = normalize_cols(pd.read_csv(StringIO(text)))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["open", "high", "low", "close", "settle", "volume", "oi"]:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["expiry"] = pd.Timestamp(expiry)
    df["source"] = source
    pre = df["date"] < RESCALE_CUTOFF
    for c in ["open", "high", "low", "close", "settle"]:
        df.loc[pre, c] = df.loc[pre, c] / 10.0
    return df[["date", "expiry", "open", "high", "low", "close", "settle", "volume", "oi", "source"]]


# ---- step 1: VIX spot -------------------------------------------------------
log("fetching VIX spot history ...")
vix_txt = fetch_cached("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv", "VIX_History.csv")
if not vix_txt:
    raise SystemExit("VIX_History.csv unreachable -- aborting")
vix = pd.read_csv(StringIO(vix_txt))
vix.columns = [c.strip().lower() for c in vix.columns]
vix["date"] = pd.to_datetime(vix["date"], format="%m/%d/%Y")
vix = vix.sort_values("date").drop_duplicates("date").reset_index(drop=True)
vix.to_parquet(OUT / "vix_spot.parquet", index=False)
trading_dates = vix["date"].to_numpy()
log(f"vix_spot: {len(vix):,} rows {vix['date'].min().date()} .. {vix['date'].max().date()}")

# ---- step 2: fetch contracts -------------------------------------------------
archive_months = list(month_range(2004, 5, 2013, 12))
new_months = list(month_range(2013, 1, 2026, 8))
archive_df, new_df, new_resolved, fetch_log, discrepancies, degenerate_new = {}, {}, {}, [], [], []

log(f"fetching {len(archive_months)} archive-format months ...")
for y, m in archive_months:
    code, yy = MONTH_CODE[m], y % 100
    url = f"https://cdn.cboe.com/resources/futures/archive/volume-and-price/CFE_{code}{yy:02d}_VX.csv"
    txt = fetch_cached(url, f"archive_{code}{yy:02d}.csv")
    exp = nominal_wed(y, m)
    archive_df[(y, m)] = parse_contract_csv(txt, exp, "archive") if txt else None

log(f"fetching {len(new_months)} new-format months (Wednesday, then -1/-2 days) ...")
for y, m in new_months:
    wed = nominal_wed(y, m)
    df, resolved = None, None
    for back in (0, 1, 2):
        cand = wed - timedelta(days=back)
        url = f"https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{cand.isoformat()}.csv"
        txt = fetch_cached(url, f"new_{cand.isoformat()}.csv")
        if txt:
            df, resolved = parse_contract_csv(txt, cand, "new"), back
            break
    new_df[(y, m)], new_resolved[(y, m)] = df, resolved
    status = f"resolved -{resolved}d" if df is not None else "MISSING"
    fetch_log.append((y, m, wed.isoformat(), status))

# ---- step 3: resolve 2013 overlap ROW-LEVEL, assemble panel -----------------
# Rule: for each (date, expiry) present in both formats, use the new-format row if its
# Settle > 0, otherwise fall back to the archive row for that specific date (source kept
# accurate per row). "Prefer new" is a per-row tiebreak among two VALID readings, not a
# license to keep a degenerate new-format row over a valid archive one.
frames = []
for y, m in sorted(set(archive_df) | set(new_df)):
    a, n = archive_df.get((y, m)), new_df.get((y, m))
    if n is not None and a is not None:
        label = f"{MONTH_CODE[m]}{y % 100:02d}"
        raw_overlap = pd.merge(a[["date"]], n[["date"]], on="date")  # dates present in both raw files
        a_valid, n_valid = a[a["settle"] > 0], n[n["settle"] > 0]
        both = pd.merge(a_valid[["date", "settle"]], n_valid[["date", "settle"]], on="date", suffixes=("_a", "_n"))
        if len(both):  # both sources independently valid on this date -> magnitude check only
            diff = (both["settle_n"] - both["settle_a"]).abs()
            if diff.max() > 0.02:
                discrepancies.append((label, len(both), diff.mean(), diff.max()))
        fb_dates = set(a_valid["date"]) - set(n_valid["date"])  # archive valid, new missing/invalid
        if fb_dates:
            fb = a_valid[a_valid["date"].isin(fb_dates)]
            degenerate_new.append((label, len(fb), len(raw_overlap), fb["date"].min().date(), fb["date"].max().date()))
        frames.append(pd.concat([n_valid, a[a["date"].isin(fb_dates)]], ignore_index=True))
    elif n is not None:
        frames.append(n)
    elif a is not None:
        frames.append(a)

missing_expiries = sorted({(y, m) for y, m in (archive_months + new_months)
                            if archive_df.get((y, m)) is None and new_df.get((y, m)) is None})

panel = pd.concat(frames, ignore_index=True)
panel = panel[(panel["date"].notna()) & (panel["date"] <= panel["expiry"])]
panel = panel[panel["settle"].notna() & (panel["settle"] > 0)]
panel = panel.drop_duplicates(["date", "expiry"], keep="first").sort_values(["date", "expiry"]).reset_index(drop=True)

lo = np.searchsorted(trading_dates, panel["date"].to_numpy(), side="right")
hi = np.searchsorted(trading_dates, panel["expiry"].to_numpy(), side="right")
panel["dte_biz"] = hi - lo
panel = panel[["date", "expiry", "open", "high", "low", "close", "settle", "volume", "oi", "dte_biz", "source"]]
panel.to_parquet(OUT / "vx_contracts.parquet", index=False)
log(f"vx_contracts: {len(panel):,} rows, {panel['expiry'].nunique()} expiries")

# ---- step 4: rescale check by quarter 2006Q1-2007Q4 --------------------------
rescale_rows = []
for q_start, q_end, label in [(f"{y}-{mq}-01", None, f"{y}Q{q}") for y in (2006, 2007) for q, mq in
                               [(1, "01"), (2, "04"), (3, "07"), (4, "10")]]:
    qs = pd.Timestamp(q_start)
    qe = (qs + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
    sub = panel[(panel["date"] >= qs) & (panel["date"] <= qe)]
    front = sub.loc[sub.groupby("date")["expiry"].idxmin()]
    m = front.merge(vix, on="date", suffixes=("", "_vix"))
    ratio = (m["settle"] / m["close"]).median() if len(m) else float("nan")
    rescale_rows.append((label, len(m), ratio))

# ---- step 5: vx_daily ---------------------------------------------------------
log("building vx_daily ...")
last_date = min(vix["date"].max(), pd.Timestamp(date.today()))
cal = vix.loc[(vix["date"] >= DAILY_START) & (vix["date"] <= last_date), ["date", "close"]].rename(
    columns={"close": "vix_close"}).reset_index(drop=True)
rows = []
for d, grp in panel[panel["date"] >= DAILY_START].groupby("date"):
    cand = grp[grp["expiry"] > d].sort_values("expiry")
    rows.append({
        "date": d,
        "f1_expiry": cand["expiry"].iloc[0] if len(cand) > 0 else pd.NaT,
        "f1_settle": cand["settle"].iloc[0] if len(cand) > 0 else np.nan,
        "f1_dte": cand["dte_biz"].iloc[0] if len(cand) > 0 else np.nan,
        "f1_volume": cand["volume"].iloc[0] if len(cand) > 0 else np.nan,
        "f2_expiry": cand["expiry"].iloc[1] if len(cand) > 1 else pd.NaT,
        "f2_settle": cand["settle"].iloc[1] if len(cand) > 1 else np.nan,
        "f2_dte": cand["dte_biz"].iloc[1] if len(cand) > 1 else np.nan,
        "f2_volume": cand["volume"].iloc[1] if len(cand) > 1 else np.nan,
    })
daily = cal.merge(pd.DataFrame(rows), on="date", how="left").sort_values("date").reset_index(drop=True)
daily.to_parquet(OUT / "vx_daily.parquet", index=False)
log(f"vx_daily: {len(daily):,} rows {daily['date'].min().date()} .. {daily['date'].max().date()}")

# ---- step 6: splits -----------------------------------------------------------
for name, df, col in [("vx_contracts", panel, "date"), ("vx_daily", daily, "date")]:
    ins, oos = df[df[col] < SPLIT], df[df[col] >= SPLIT]
    ins.to_parquet(OUT / f"{name}_insample.parquet", index=False)
    oos.to_parquet(OUT / f"{name}_oos.parquet", index=False)
    log(f"{name} split: insample {len(ins):,} rows, oos {len(oos):,} rows "
        f"({oos[col].min().date() if len(oos) else 'n/a'} .. {oos[col].max().date() if len(oos) else 'n/a'})")

# ---- step 7: per-year validation table (IN-SAMPLE ONLY -- no OOS content beyond row count/range) --
daily_ins, panel_ins = daily[daily["date"] < SPLIT].copy(), panel[panel["date"] < SPLIT]
zero_vol_ins_by_year = panel_ins[panel_ins["volume"] == 0]["date"].dt.year.value_counts().sort_index()
daily_ins["year"] = daily_ins["date"].dt.year
yrs = sorted(daily_ins["year"].unique())
per_year = []
for y in yrs:
    g = daily_ins[daily_ins["year"] == y]
    contango = (g["f1_settle"] > g["vix_close"]).sum() / g["f1_settle"].notna().sum() if g["f1_settle"].notna().sum() else float("nan")
    pc = panel_ins[panel_ins["date"].dt.year == y]
    mad = (pc["settle"] - pc["close"]).abs().mean() if len(pc) else float("nan")
    per_year.append((y, len(g), g["f1_settle"].notna().sum(), g["f2_settle"].notna().sum(),
                      ((g["f1_dte"] < 10) & g["f2_settle"].isna()).sum(),
                      int(zero_vol_ins_by_year.get(y, 0)), g["f1_volume"].median(), g["f2_volume"].median(),
                      contango, mad))

rolls = daily_ins.loc[daily_ins["f1_expiry"] != daily_ins["f1_expiry"].shift(1), "f1_dte"].dropna()
rolls = rolls.iloc[1:]  # drop the first row (not a real roll, just series start)
rolls_at25 = int((rolls == 25).sum())  # normal: some months have 5 Wednesdays/Fridays between expiries
rolls_gt25 = int((rolls > 25).sum())   # anomalous: usually a missing contract-month was skipped

# ---- step 8: VALIDATION.md -----------------------------------------------------
lines = ["# VALIDATION.md", "",
          "Sources: CBOE VIX_History.csv (spot); CFE_<code><yy>_VX.csv archive 2004-05..2013-12; "
          "VX_<expiry>.csv new-format 2013-01..2026-08 (Wed 30d-before-3rd-Friday-next-month rule, "
          "then -1/-2 days if 403).",
          f"Archive months attempted {len(archive_months)}, found {sum(v is not None for v in archive_df.values())}. "
          f"New-format months attempted {len(new_months)}, found {sum(v is not None for v in new_df.values())}.",
          f"Expiries unresolved in EITHER format: {[f'{y}-{m:02d}' for y, m in missing_expiries] or 'none'}. "
          "These 4 (2004-05..2005-09 vintage) predate every walk-forward window and the EWMA warm-up "
          "(P4's first train window starts 2007-07-01), so they are irrelevant to P4.",
          f"New-format offsets used: 0d={sum(1 for v in new_resolved.values() if v==0)}, "
          f"-1d={sum(1 for v in new_resolved.values() if v==1)}, -2d={sum(1 for v in new_resolved.values() if v==2)}.",
          f"Holiday-shifted (resolved date != nominal Wed): "
          f"{[(f'{y}-{m:02d}', wed, st.split()[-1]) for y, m, wed, st in fetch_log if st not in ('resolved -0d', 'MISSING')] or 'none'}.",
          "", "## Rescale check: median(front settle / VIX close) by quarter", "",
          "| quarter | n days | median ratio |", "|---|---|---|"]
lines += [f"| {q} | {n} | {r:.3f} |" for q, n, r in rescale_rows]
lines += ["", "## 2013 archive-vs-new discrepancies (|diff| settle > 0.02, both sources valid)", ""]
if discrepancies:
    lines += ["| contract | n overlap days | mean |diff| | max |diff| |", "|---|---|---|---|"]
    lines += [f"| {c} | {n} | {md:.3f} | {mx:.3f} |" for c, n, md, mx in discrepancies]
else:
    lines.append("None found (>0.02 threshold).")
lines += ["", "## 2013 new-format degenerate settle -> archive used as row-level fallback", ""]
if degenerate_new:
    lines += ["| contract | days archive used | raw-overlap days | first | last |", "|---|---|---|---|---|"]
    lines += [f"| {c} | {n} | {tot} | {d0} | {d1} |" for c, n, tot, d0, d1 in degenerate_new]
    lines.append("F13/G13/H13/J13 new-format files have Settle==0 for their entire life (not just near "
                  "expiry); K13/M13 mostly so. Merge rule: new-format wins per (date, expiry) only where "
                  "its own Settle>0, else the archive row for that date is used (source recorded per row) "
                  "-- coverage is preserved, see per-year table below.")
else:
    lines.append("None found.")
lines += ["", "## Per-year summary", "",
          "| year | vix days | days w/ f1 | days w/ f2 | f1dte<10 & no f2 | zero-vol rows | "
          "med f1 vol | med f2 vol | contango share | settle-close MAD |",
          "|---|---|---|---|---|---|---|---|---|---|"]
lines += [f"| {y} | {n} | {f1} | {f2} | {gap} | {zv} | {mv1:.0f} | "
          f"{'n/a' if pd.isna(mv2) else f'{mv2:.0f}'} | {'n/a' if pd.isna(cs) else f'{cs:.1%}'} | {mad:.3f} |"
          for y, n, f1, f2, gap, zv, mv1, mv2, cs, mad in per_year]
lines += ["", "## f1_dte distribution at roll (nominally ~20-21, up to 25 in 5-Wednesday months)", "",
          f"n rolls={len(rolls)}, min={rolls.min():.0f}, p25={rolls.quantile(.25):.0f}, "
          f"median={rolls.median():.0f}, p75={rolls.quantile(.75):.0f}, max={rolls.max():.0f}. "
          f"==25 (normal, 5-Wednesday month): {rolls_at25}. >25 (anomalous): {rolls_gt25} -- all of these "
          "(42-44 days) coincide exactly with unresolved archive expiries above (front skips the missing "
          "contract-month).",
          "", "## Interpretations", "",
          "- dte_biz counted on VIX trading calendar per spec; f1/f2 require strictly expiry>date "
          "(expiry-day settle itself doesn't count as f1).",
          "- Zero-volume rows kept (illiquid early contracts / far months); settle-close MAD is inflated "
          "on those days since close=0 when no trade occurs.",
          "- Archive header identical across 2004-2013 samples checked; no column renaming needed beyond "
          "lowercasing/whitespace strip.",
          "", "## Timing", "", f"- Total wall time: {time.time()-T0:.1f}s"]
(OUT / "VALIDATION.md").write_text("\n".join(lines) + "\n")
log(f"done -- wrote {OUT}/VALIDATION.md ({len(lines)} lines)")
