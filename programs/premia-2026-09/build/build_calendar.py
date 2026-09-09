#!/usr/bin/env python3
"""
Build ES session/calendar hygiene tables: outright settles panel, continuous
front-contract daily view, trading-day calendar, and FOMC announcement dates.
Run: uv run --with pandas --with pyarrow --with numpy --with zstandard --with requests --with lxml python build_calendar.py
Hygiene only: coverage counts + unconditional sanity checks (HARD RULE 1). No
returns-vs-calendar, no regressions, no P&L. Reuses build_data.py's raw-file
parsing (spread filter, ET session_date shift rule) and data/rolls.csv (its
already-validated front-contract roll schedule). Never writes under data/.
"""
import bisect
import re
import time
from pathlib import Path
import numpy as np
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parent
RAW = ROOT / "glbx-mdp3-20100606-20260701.ohlcv-1m.csv.zst"
OUT = ROOT / "data_calendar"
OUT.mkdir(exist_ok=True)
ET = "America/New_York"
SPLIT = pd.Timestamp("2024-07-01").date()
T0 = time.time()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
def log(m):
    print(f"[{time.time()-T0:7.1f}s] {m}", flush=True)
def mnum(name):
    return next(i for i, m in enumerate(MONTHS, 1) if m.startswith(name[:3]))  # handles "Apr"/"April" alike
# ============================================================= ES settles / front series
log("loading raw csv.zst (reusing build_data.py's spread filter + ET session_date rule) ...")
df = pd.read_csv(RAW, compression="zstd", usecols=["ts_event", "instrument_id", "symbol", "close", "volume"],
                  dtype={"instrument_id": "int64", "close": "float64", "volume": "int64", "symbol": "str"})
df = df.loc[~df["symbol"].str.contains("-")].copy()   # outright contracts only, same rule as build_data.py
df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
df["ts_et"] = df["ts_event"].dt.tz_convert(ET)
naive = df["ts_et"].dt.tz_localize(None)
cal_date = naive.dt.normalize()
df["session_date"] = np.where(naive.dt.hour >= 18, (cal_date + pd.Timedelta(days=1)).dt.date, cal_date.dt.date)
df["cal_date"] = cal_date.dt.date
df["hour"] = naive.dt.hour + naive.dt.minute / 60.0
log(f"{len(df):,} outright 1m rows, {df['instrument_id'].nunique()} instruments")
symbol_by_id = df.groupby("instrument_id")["symbol"].first()
log("settles (last bar ts_et<16:00 ET) + day_volume (prev 18:00 ET -> 16:00 ET) ...")
day_bars = df[df["hour"] < 16]
settle_idx = day_bars.groupby(["cal_date", "instrument_id"])["ts_et"].idxmax()
settles = (day_bars.loc[settle_idx, ["cal_date", "instrument_id", "ts_et", "close"]]
           .rename(columns={"cal_date": "date", "ts_et": "settle_ts_et", "close": "settle"}))
in_window = ~((naive.dt.date.to_numpy() == df["session_date"].to_numpy()) & (df["hour"] >= 16))
vol = (df.loc[in_window].groupby(["session_date", "instrument_id"])["volume"].sum()
       .rename("day_volume").reset_index().rename(columns={"session_date": "date"}))
es_settles = settles.merge(vol, on=["date", "instrument_id"], how="outer")
es_settles = es_settles[es_settles["day_volume"].fillna(0) > 0].copy()
es_settles["symbol"] = es_settles["instrument_id"].map(symbol_by_id)
n_no_settle = int(es_settles["settle"].isna().sum())
log(f"{len(es_settles):,} (date,instrument) rows kept (day_volume>0); {n_no_settle} have no pre-16:00 bar")
log("assigning front/next_id from data/rolls.csv (schedule already validated by build_data.py) ...")
rolls = pd.read_csv(ROOT / "data" / "rolls.csv")
rolls["roll_start_utc"] = pd.to_datetime(rolls["roll_session_start_utc"], utc=True)
# roll_session_start_utc = 18:00 ET the day before the new front's first session -> +6h/ET gives that date
rolls["front_start_date"] = rolls["roll_start_utc"].dt.tz_convert(ET).apply(lambda t: (t + pd.Timedelta(hours=6)).date())
rolls = rolls.sort_values("front_start_date").reset_index(drop=True)
succ = dict(zip(rolls["from_instrument_id"], rolls["to_instrument_id"]))
boundaries, front_chain = rolls["front_start_date"].tolist(), [rolls["from_instrument_id"].iloc[0]] + rolls["to_instrument_id"].tolist()
def front_on(d):
    return front_chain[bisect.bisect_right(boundaries, d)]
uniq_dates = sorted(es_settles["date"].unique())
front_lookup = pd.Series({d: front_on(d) for d in uniq_dates})
next_lookup = front_lookup.map(succ)  # NaN for the current front -- no later roll observed yet
es_settles["is_front"] = es_settles["instrument_id"].to_numpy() == es_settles["date"].map(front_lookup).to_numpy()
es_settles["next_id"] = es_settles["date"].map(next_lookup)
es_settles = es_settles[["date", "instrument_id", "symbol", "settle", "settle_ts_et", "day_volume",
                          "is_front", "next_id"]].sort_values(["date", "instrument_id"]).reset_index(drop=True)
log("building es_daily_front (front settle + prior-front same-contract settle) ...")
front_rows = es_settles[es_settles["is_front"]].sort_values("date").reset_index(drop=True)
front_rows["prev_front_id"] = front_rows["instrument_id"].shift(1)
prev_lookup = front_rows[["date", "prev_front_id"]].rename(columns={"prev_front_id": "instrument_id"})
prev_settle = prev_lookup.merge(es_settles[["date", "instrument_id", "settle"]], on=["date", "instrument_id"], how="left")
es_daily_front = pd.DataFrame({
    "date": front_rows["date"], "front_id": front_rows["instrument_id"], "front_settle": front_rows["settle"],
    "prev_front_id": front_rows["prev_front_id"], "prev_front_settle_today": prev_settle["settle"].to_numpy()})
n_prev_nan = int(es_daily_front["prev_front_settle_today"].isna().sum())
log(f"{len(es_daily_front):,} trading days; {n_prev_nan} with prev_front_settle_today NaN (incl. first date)")
log("building trading_days.csv ...")
td = pd.DataFrame({"date": sorted(es_daily_front["date"].unique())})
td["date_ts"] = pd.to_datetime(td["date"])
grp = td.groupby([td["date_ts"].dt.year, td["date_ts"].dt.month])["date"]
td["tdom"], td["n_td_month"] = grp.cumcount() + 1, grp.transform("size")
td["tdom_from_end"] = td["n_td_month"] - td["tdom"]
td["weekday"] = td["date_ts"].dt.day_name()
pm_bars = set(df.loc[(df["hour"] >= 13.5) & (df["hour"] < 16), "cal_date"].unique())
td["early_close"] = ~td["date"].isin(pm_bars)
td = td.drop(columns="date_ts")
log("writing es_settles / es_daily_front / trading_days (full + in-sample/OOS split) ...")
for name, d in [("es_settles", es_settles), ("es_daily_front", es_daily_front)]:
    ins, oos = d[d["date"] < SPLIT].reset_index(drop=True), d[d["date"] >= SPLIT].reset_index(drop=True)
    ins.to_parquet(OUT / f"{name}_insample.parquet", index=False)
    oos.to_parquet(OUT / f"{name}_oos.parquet", index=False)
    log(f"  {name}: insample {len(ins):,} rows, oos {len(oos):,} rows")
td.to_csv(OUT / "trading_days.csv", index=False)
log(f"trading_days.csv: {len(td):,} rows, {td['date'].min()}..{td['date'].max()} (calendar -- NOT split)")
# ============================================================================ FOMC dates
log("fetching FOMC announcement dates from federalreserve.gov ...")
budget = {"used": 0.0, "limit": 600.0}
def fetch(url):
    if budget["used"] >= budget["limit"]:
        log(f"  SKIP (network budget exhausted): {url}")
        return None
    t0 = time.time()
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log(f"  FETCH FAILED {url}: {e}")
        return None
    finally:
        budget["used"] += time.time() - t0
def parse_phrase(month_part, day_part, year):
    months, nums = month_part.split("/"), re.findall(r"\d+", day_part)
    if len(months) == 2:
        m1, m2, d1, d2 = months[0], months[1], nums[0], nums[1]
    else:
        m1 = m2 = months[0]
        d1, d2 = nums[0], (nums[1] if len(nums) > 1 else nums[0])
    return (pd.Timestamp(year=year, month=mnum(m1), day=int(d1)).date(),
            pd.Timestamp(year=year, month=mnum(m2), day=int(d2)).date())
H5_RE = re.compile(r'<h5[^>]*>\s*([A-Za-z]+(?:/[A-Za-z]+)?)\s+(\d+(?:\s*-\s*\d+)?)\s*'
                    r'(?:\(([^)]+)\))?\s*(Meeting|Conference Call)?\s*-\s*(\d{4})\s*</h5>')
RELEASED_RE = re.compile(r'Statement</a>\s*\(Released\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\)')
YEAR_RE = re.compile(r'<a id="\d+">(\d{4}) FOMC Meetings</a>')
MD_RE = re.compile(r'fomc-meeting__month[^"]*"><strong>([^<]+)</strong></div>\s*'
                    r'<div class="fomc-meeting__date[^"]*">([^<]+)</div>')
def parse_historical(html):
    rows = []
    for m in H5_RE.finditer(html):
        month_part, day_part, qualifier, kind, year = m.groups()
        year = int(year)
        if qualifier and "notation vote" in qualifier:
            continue
        start, end = parse_phrase(month_part, day_part, year)
        cancelled = bool(qualifier and "cancelled" in qualifier)
        scheduled = not cancelled and not (qualifier and "unscheduled" in qualifier) and kind != "Conference Call"
        notes = [qualifier] if qualifier else []
        if kind == "Conference Call":
            notes.append("conference call")
        announce = None if cancelled else end
        if not cancelled:
            rm = RELEASED_RE.search(html[m.end():m.end() + 2000])
            if rm:
                mon, day, yy = rm.groups()
                announce = pd.Timestamp(year=int(yy), month=mnum(mon), day=int(day)).date()
                notes.append(f"statement released {announce}, after meeting end")
        rows.append(dict(announce_date=announce, meeting_start=start, meeting_end=end,
                          scheduled=scheduled, notes="; ".join(notes)))
    return rows
def parse_live(html):
    rows = []
    heads = [(int(m.group(1)), m.start()) for m in YEAR_RE.finditer(html)] + [(None, len(html))]
    for i in range(len(heads) - 1):
        year, s = heads[i]
        for month_part, date_part in MD_RE.findall(html[s:heads[i + 1][1]]):
            if "notation vote" in date_part:
                continue
            unscheduled = "unscheduled" in date_part.lower()
            start, end = parse_phrase(month_part, re.sub(r"\*|\([^)]*\)", "", date_part).strip(), year)
            rows.append(dict(announce_date=end, meeting_start=start, meeting_end=end,
                              scheduled=not unscheduled, notes="SEP meeting" if "*" in date_part else ""))
    return rows
fomc_rows, fomc_gaps, live_years = [], [], set()
live_html = fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
if live_html:
    live_rows = parse_live(live_html)
    fomc_rows += live_rows
    live_years = {r["meeting_end"].year for r in live_rows}
    log(f"  live calendar page: years {sorted(live_years)}, {len(live_rows)} meetings")
else:
    fomc_gaps.append("fomccalendars.htm unreachable")
for y in [y for y in range(2009, 2021) if y not in live_years]:
    html = fetch(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm")
    if html is None:
        fomc_gaps.append(f"{y}: fetch failed")
        continue
    rows = parse_historical(html)
    fomc_gaps.append(f"{y}: parsed 0 meetings") if not rows else fomc_rows.extend(rows)
if fomc_rows:
    fomc_df = pd.DataFrame(fomc_rows)
    fomc_df = fomc_df[(fomc_df["meeting_start"] >= pd.Timestamp("2009-01-01").date()) &
                       (fomc_df["meeting_end"] <= pd.Timestamp("2026-12-31").date())]
    fomc_df = fomc_df.sort_values("meeting_end").reset_index(drop=True)
    fomc_df.to_csv(OUT / "fomc_dates.csv", index=False)
    log(f"fomc_dates.csv: {len(fomc_df):,} rows, {fomc_df['meeting_end'].min()}..{fomc_df['meeting_end'].max()}")
else:
    fomc_df = pd.DataFrame(columns=["announce_date", "meeting_start", "meeting_end", "scheduled", "notes"])
    log("FOMC FETCH TOTAL FAILURE -- fomc_dates.csv not written")
if fomc_gaps:
    log(f"FOMC gaps: {fomc_gaps}")
# =================================================================== VALIDATION.md (in-sample only)
log("running validation (in-sample, date < 2024-07-01) ...")
es_ins = es_settles[es_settles["date"] < SPLIT]
front_ins = es_daily_front[es_daily_front["date"] < SPLIT].sort_values("date").reset_index(drop=True)
yr = pd.to_datetime(front_ins["date"]).dt.year
L = ["# VALIDATION.md (calendar hygiene, in-sample only: date < 2024-07-01)", "",
     "## Trading dates per year vs. dates with a front settle", "", "| year | trading dates | with front settle |", "|---|---|---|"]
L += [f"| {y} | {len(g)} | {g['front_settle'].notna().sum()} |" for y, g in front_ins.groupby(yr)]
multi = es_ins.groupby("date")["instrument_id"].nunique()
L += ["", f"## Dates with >1 active (day_volume>0) contract: {int((multi > 1).sum())} (expect ~2 per roll)"]
td_ins = td[td["date"] < SPLIT]
ec = td_ins[td_ins["early_close"]]
L += ["", f"## Early-close dates in-sample: {len(ec)}", "", "| year | early closes |", "|---|---|"]
L += [f"| {y} | {len(g)} |" for y, g in ec.groupby(pd.to_datetime(ec['date']).dt.year)]
nan_prev = front_ins[front_ins["prev_front_settle_today"].isna()]
L += ["", f"## prev_front_settle_today NaN in-sample: {len(nan_prev)}" +
      (f" (dates: {', '.join(str(d) for d in nan_prev['date'])})" if len(nan_prev) else "")]
rolls_ins = rolls[rolls["front_start_date"] < SPLIT]
tfe = td.set_index("date").loc[rolls_ins["front_start_date"], "tdom_from_end"]
L += ["", f"## Rolls in-sample: {len(rolls_ins)}",
      f"- tdom_from_end on first post-roll date: min={int(tfe.min())}, median={tfe.median():.1f}, "
      f"max={int(tfe.max())} (mid-month sanity for quarterly rolls)"]
if len(fomc_df):
    fdy = pd.to_datetime(fomc_df["meeting_end"]).dt.year
    sched_by_year = fomc_df[fomc_df["scheduled"]].groupby(fdy[fomc_df["scheduled"]]).size()
    L += ["", "## FOMC scheduled meetings per year", "", "| year | scheduled |", "|---|---|"]
    L += [f"| {y} | {n} |" for y, n in sched_by_year.items()]
    off = sched_by_year[(sched_by_year.index >= 2009) & (sched_by_year.index <= 2025) & (sched_by_year != 8)]
    L.append(f"- Years 2009-2025 with count != 8: {dict(off) if len(off) else 'none'}")
else:
    L += ["", "## FOMC scheduled meetings per year", "", "FETCH FAILED -- see FOMC gaps note below."]
if fomc_gaps:
    L.append(f"- FOMC fetch gaps: {fomc_gaps}")
L += ["", "## First/last dates per file", "", "| file | first | last |", "|---|---|---|",
      f"| es_settles_insample | {es_ins['date'].min()} | {es_ins['date'].max()} |",
      f"| es_daily_front_insample | {front_ins['date'].min()} | {front_ins['date'].max()} |",
      f"| trading_days.csv (full) | {td['date'].min()} | {td['date'].max()} |",
      f"| fomc_dates.csv | {fomc_df['meeting_end'].min() if len(fomc_df) else '--'} | "
      f"{fomc_df['meeting_end'].max() if len(fomc_df) else '--'} |"]
sc = front_ins.set_index("date")
same_contract_ret = (sc["prev_front_settle_today"] / sc["front_settle"].shift(1) - 1).dropna()
mx = same_contract_ret.abs().idxmax()
L += ["", "## Unconditional same-contract |daily return| sanity (hygiene check, not a strategy statistic)", "",
      f"Max |return| = {same_contract_ret.abs().max():.4%} on {mx}."]
L += ["", "## Interpretation notes", "",
      "- `day_volume` sums 1m volume strictly in (prev-day 18:00 ET, this-day 16:00 ET]; the small 16:00-18:00 "
      "ET post-settle leg is excluded from every day's day_volume (build_data.py's full 24h session_date window "
      "instead folds that leg into the same date).",
      "- `next_id` is session-level: the instrument_id data/rolls.csv's chain says becomes front after the "
      "CURRENT front's own next roll (successor of front_id(date)); NaN for the latest front (no successor yet).",
      "- Front/roll assignment is read directly from the already-validated data/rolls.csv, not recomputed.",
      "- FOMC: 'Conference Call' entries and 2020's unscheduled Mar 2/Mar 15 calls are scheduled=False; the "
      "2020 Mar 17-18 slot (cancelled, superseded by those calls) is kept with scheduled=False, empty "
      "announce_date -- why 2020 shows <8 scheduled meetings. '(notation vote)' rows are excluded entirely.",
      "- announce_date = last day of the meeting, unless the source page states the statement was released "
      "later (e.g. 2020-03-02 meeting -> announced 2020-03-03).",
      f"- Network budget for FOMC fetches: {budget['used']:.0f}s used of {budget['limit']:.0f}s cap."]
(OUT / "VALIDATION.md").write_text("\n".join(L) + "\n")
log(f"done in {time.time()-T0:.1f}s -- wrote data_calendar/VALIDATION.md")
