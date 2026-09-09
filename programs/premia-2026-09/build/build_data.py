#!/usr/bin/env python3
"""
Build a continuous ES futures 1m/1h/4h dataset from raw Databento GLBX.MDP3 data.
Run: uv run --with pandas --with pyarrow --with zstandard python build_data.py

Strict data-hygiene job: filters spreads, derives expiries, computes a
volume-crossover roll schedule, builds a continuous UNADJUSTED front-contract
series, resamples it, splits in-sample/OOS, and writes data/VALIDATION.md.
"""
import bisect
import calendar
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "glbx-mdp3-20100606-20260701.ohlcv-1m.csv.zst"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

ET = "America/New_York"
MONTH_CODE = {"H": 3, "M": 6, "U": 9, "Z": 12}
SPLIT_ET = pd.Timestamp("2024-07-01 00:00:00", tz=ET)
T0 = time.time()


def log(msg):
    print(f"[{time.time()-T0:7.1f}s] {msg}", flush=True)


def third_friday_utc(year, month):
    cal = calendar.monthcalendar(year, month)
    day = [w[calendar.FRIDAY] for w in cal if w[calendar.FRIDAY]][2]
    return pd.Timestamp(year=year, month=month, day=day, hour=9, minute=30, tz=ET).tz_convert("UTC")


def compute_expiry(symbol, first_ts):
    month, d = MONTH_CODE[symbol[2]], int(symbol[3])
    for y in range(2000, 2046):
        if y % 10 != d:
            continue
        exp = third_friday_utc(y, month)
        if exp > first_ts:
            return exp
    raise ValueError(f"no expiry candidate found for {symbol}")


# ---------------------------------------------------------------- load & filter
log("loading raw csv.zst ...")
df = pd.read_csv(RAW, compression="zstd",
                  usecols=["ts_event", "instrument_id", "open", "high", "low", "close", "volume", "symbol"],
                  dtype={"instrument_id": "int64", "open": "float64", "high": "float64", "low": "float64",
                         "close": "float64", "volume": "int64", "symbol": "str"})
log(f"loaded {len(df):,} rows, {df['symbol'].nunique()} distinct symbols")

is_spread = df["symbol"].str.contains("-")
n_outright_syms = df.loc[~is_spread, "symbol"].nunique()
if n_outright_syms != 40:
    raise SystemExit(f"STOP: expected 40 outright symbols, found {n_outright_syms}. Contradicts stated facts.")
df = df.loc[~is_spread].copy()
log(f"dropped {is_spread.sum():,} spread rows; {len(df):,} outright rows remain")

df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
df = df.sort_values("ts_event").reset_index(drop=True)
df["ts_et"] = df["ts_event"].dt.tz_convert(ET)
naive_et = df["ts_et"].dt.tz_localize(None)
d0 = naive_et.dt.normalize()
df["session_date"] = np.where(naive_et.dt.hour >= 18, (d0 + pd.Timedelta(days=1)).dt.date, d0.dt.date)

# ---------------------------------------------------------------- per-instrument expiry
log("deriving expiry per instrument_id ...")
inst = df.groupby("instrument_id").agg(symbol=("symbol", "first"), nsym=("symbol", "nunique"),
                                        first_ts=("ts_event", "min"), last_ts=("ts_event", "max")).reset_index()
if (inst["nsym"] != 1).any():
    raise SystemExit("STOP: an instrument_id maps to more than one symbol string.")
inst["expiry_utc"] = [compute_expiry(s, t) for s, t in zip(inst["symbol"], inst["first_ts"])]
inst["expiry_date"] = inst["expiry_utc"].dt.tz_convert(ET).dt.date
bad = inst[inst["last_ts"] > inst["expiry_utc"]]
if len(bad):
    raise SystemExit(f"STOP: {len(bad)} instruments trade past their computed expiry:\n{bad}")
inst = inst.sort_values("expiry_utc").reset_index(drop=True)
inst["chain_idx"] = np.arange(len(inst))
log(f"{len(inst)} outright instruments; expiries {inst['expiry_date'].min()} .. {inst['expiry_date'].max()}; "
    f"0 last-bar-after-expiry violations")

id_to_chain = dict(zip(inst["instrument_id"], inst["chain_idx"]))
chain_to_id = dict(zip(inst["chain_idx"], inst["instrument_id"]))
expiry_by_id = dict(zip(inst["instrument_id"], inst["expiry_date"]))
symbol_by_id = dict(zip(inst["instrument_id"], inst["symbol"]))

# ---------------------------------------------------------------- session volumes & roll schedule
log("computing per-session per-instrument volume ...")
sess_vol = df.groupby(["session_date", "instrument_id"])["volume"].sum().unstack(fill_value=0)
sessions = sorted(sess_vol.index)
log(f"{len(sessions)} sessions, {sessions[0]} .. {sessions[-1]}")


def session_open_utc(session_date):
    return (pd.Timestamp(session_date, tz=ET) - pd.Timedelta(hours=6)).tz_convert("UTC")  # prior day 18:00 ET


def session_before(date_obj):
    idx = bisect.bisect_left(sessions, date_obj)
    return sessions[idx - 1] if idx > 0 else None


log("running roll rule (volume crossover, next-quarterly cap, forced pre-expiry roll) ...")
front = sess_vol.loc[sessions[0]].idxmax()
front_per_session, rolls = [], []
sbe = session_before(expiry_by_id[front])
for i, s in enumerate(sessions):
    front_per_session.append(front)
    if i == len(sessions) - 1:
        break
    fc = id_to_chain[front]
    if fc + 1 >= len(inst):
        continue
    next_q = chain_to_id[fc + 1]
    front_vol, next_vol = sess_vol.at[s, front], sess_vol.at[s, next_q]
    forced = s == sbe
    if next_vol > front_vol or forced:
        nxt_session = sessions[i + 1]
        rolls.append(dict(roll_session_start_utc=session_open_utc(nxt_session), roll_session_date=nxt_session,
                           from_instrument_id=front, from_symbol=symbol_by_id[front],
                           to_instrument_id=next_q, to_symbol=symbol_by_id[next_q],
                           forced=forced and not (next_vol > front_vol)))
        front = next_q
        sbe = session_before(expiry_by_id[front])

rolls_df = pd.DataFrame(rolls)
assert (rolls_df["from_instrument_id"].map(id_to_chain) + 1 == rolls_df["to_instrument_id"].map(id_to_chain)).all()
log(f"{len(rolls_df)} rolls computed ({rolls_df['forced'].sum()} forced pre-expiry, "
    f"{(~rolls_df['forced']).sum()} volume-triggered)")
rolls_df[["roll_session_start_utc", "from_instrument_id", "from_symbol", "to_instrument_id", "to_symbol"]] \
    .to_csv(OUT / "rolls.csv", index=False)

# ---------------------------------------------------------------- continuous 1m front series
log("assembling continuous front-contract 1m series ...")
session_front = pd.DataFrame({"session_date": sessions, "front_instrument_id": front_per_session})
merged = df.merge(session_front, on="session_date", how="left")
es1m = merged.loc[merged["instrument_id"] == merged["front_instrument_id"],
                   ["ts_event", "ts_et", "instrument_id", "symbol", "open", "high", "low", "close", "volume"]]
es1m = es1m.rename(columns={"ts_event": "ts_utc"}).sort_values("ts_utc").reset_index(drop=True)
log(f"continuous 1m series: {len(es1m):,} bars, {es1m['instrument_id'].nunique()} distinct front instruments")


def resample(bars, freq):
    naive = bars["ts_et"].dt.tz_localize(None)
    if freq == "1h":
        key = naive.dt.floor("h")
    else:
        key = (naive - pd.Timedelta(hours=2)).dt.floor("4h") + pd.Timedelta(hours=2)
    g = bars.groupby(key, sort=True)
    out = pd.DataFrame({"ts_utc": g["ts_utc"].min(), "open": g["open"].first(), "high": g["high"].max(),
                         "low": g["low"].min(), "close": g["close"].last(), "volume": g["volume"].sum(),
                         "n_1m": g.size(), "instrument_id": g["instrument_id"].last()}).reset_index(drop=True)
    out["ts_et"] = out["ts_utc"].dt.tz_convert(ET)
    return out[["ts_et", "ts_utc", "instrument_id", "open", "high", "low", "close", "volume", "n_1m"]]


log("resampling to 1h and 4h ...")
es1h = resample(es1m, "1h")
es4h = resample(es1m, "4h")

log("writing parquet files (combined + insample/oos split) ...")
files_written = {}
for name, d in [("es_1m", es1m), ("es_1h", es1h), ("es_4h", es4h)]:
    ts_col = d["ts_et"]
    combo, ins, oos = d, d[ts_col < SPLIT_ET], d[ts_col >= SPLIT_ET]
    for suffix, part in [("", combo), ("_insample", ins), ("_oos", oos)]:
        path = OUT / f"{name}{suffix}.parquet"
        part.reset_index(drop=True).to_parquet(path, engine="pyarrow", index=False)
        files_written[path.name] = len(part)
log("OOS files written to data/*_oos.parquet -- LOCKED, do not read until final testing.")

# ---------------------------------------------------------------- validation checks
log("running validation checks ...")
condition = {c["date"]: c["condition"] for c in json.load(open(ROOT / "condition.json"))}

days_before_expiry = (pd.to_datetime(rolls_df["from_instrument_id"].map(expiry_by_id)) -
                       pd.to_datetime(rolls_df["roll_session_date"])).dt.days

rth = es1h[(es1h["ts_et"].dt.weekday < 5) & (es1h["ts_et"].dt.hour.between(9, 15))].copy()
gaps = rth[rth["n_1m"] < 30].copy()
gaps["date"] = gaps["ts_et"].dt.date.astype(str)
gaps["condition"] = gaps["date"].map(condition).fillna("not in condition.json")

close = es1m["close"]
ret = close.pct_change()
big_moves = es1m.loc[ret.abs() > 0.05, ["ts_utc", "instrument_id", "close"]].copy()
big_moves["ret"] = ret[ret.abs() > 0.05]

switch = es1m["instrument_id"] != es1m["instrument_id"].shift(1)
switch_pos = np.flatnonzero(switch.to_numpy())[1:]  # skip row 0 (not a real roll)
jumps = []
for p in switch_pos:
    frm, to = es1m.iloc[p - 1], es1m.iloc[p]
    jumps.append(dict(ts=to["ts_utc"], from_sym=frm["symbol"], to_sym=to["symbol"],
                       from_close=frm["close"], to_open=to["open"], jump=abs(to["open"] - frm["close"])))
jumps_df = pd.DataFrame(jumps).sort_values("jump", ascending=False)
if len(switch_pos) != len(rolls_df):
    log(f"WARNING: {len(switch_pos)} instrument transitions in es_1m vs {len(rolls_df)} rolls -- mismatch!")

per_year = es1h.groupby(es1h["ts_et"].dt.year).size()
earliest5 = inst.sort_values("expiry_date").head(5)[["instrument_id", "symbol", "expiry_date"]]
latest5 = inst.sort_values("expiry_date").tail(5)[["instrument_id", "symbol", "expiry_date"]]

# ---------------------------------------------------------------- write VALIDATION.md
lines = ["# VALIDATION.md", "", "## Row counts per file", "", "| file | rows |", "|---|---|"]
lines += [f"| rolls.csv | {len(rolls_df)} |"] + [f"| {k} | {v:,} |" for k, v in files_written.items()]
lines += ["", "## Per-year 1h bar counts (combined es_1h)", "", "| year | 1h bars |", "|---|---|"]
lines += [f"| {y} | {n:,} |" for y, n in per_year.items()]
lines += ["", f"## Distinct instruments used as front: {es1m['instrument_id'].nunique()}", "",
          "## Roll table summary", "",
          f"- count: {len(rolls_df)}", f"- forced (pre-expiry) rolls: {int(rolls_df['forced'].sum())}",
          f"- days-before-expiry: min={days_before_expiry.min()}, median={days_before_expiry.median():.1f}, "
          f"max={days_before_expiry.max()}", "",
          "## RTH-hour (09:30-16:00 ET weekdays) 1h windows with n_1m < 30", ""]
if gaps.empty:
    lines.append("None found.")
else:
    lines += ["| date | hour ET | n_1m | instrument | condition.json |", "|---|---|---|---|---|"]
    for _, r in gaps.sort_values("ts_et").iterrows():
        lines.append(f"| {r['date']} | {r['ts_et'].hour:02d}:00 | {r['n_1m']} | {r['instrument_id']} | {r['condition']} |")
lines += ["", "## 1-min return check on continuous close (|return| > 5%)", ""]
if big_moves.empty:
    lines.append(f"None found. Max |1-min return| observed: {ret.abs().max():.4%}")
else:
    lines += ["| ts_utc | instrument_id | close | return |", "|---|---|---|---|"]
    for _, r in big_moves.iterrows():
        lines.append(f"| {r['ts_utc']} | {r['instrument_id']} | {r['close']} | {r['ret']:.4%} |")
lines += ["", "## Largest absolute price jump across a roll (from-close vs to-open)", ""]
if jumps_df.empty:
    lines.append("No rolls to check.")
else:
    top = jumps_df.iloc[0]
    lines.append(f"Largest: {top['jump']:.2f} pts at {top['ts']} ({top['from_sym']} close {top['from_close']} -> "
                 f"{top['to_sym']} open {top['to_open']})")
    lines.append(f"Median jump across all {len(jumps_df)} rolls: {jumps_df['jump'].median():.2f} pts")
lines += ["", "## Instrument expiry mapping (5 earliest, 5 latest) -- for eyeballing", "",
          "| instrument_id | symbol | expiry_date |", "|---|---|---|"]
for _, r in pd.concat([earliest5, latest5]).iterrows():
    lines.append(f"| {r['instrument_id']} | {r['symbol']} | {r['expiry_date']} |")
weekday_counts = pd.to_datetime(rolls_df["roll_session_date"]).dt.day_name().value_counts().to_dict()
lines += ["", "## Notes", "",
          "- Prices are UNADJUSTED across rolls (no back-adjustment), per spec.",
          f"- Roll timing is tightly clustered at {int(days_before_expiry.min())}-{int(days_before_expiry.max())} "
          f"days before expiry (effective sessions fall on {weekday_counts}), i.e. Mon/Tue of expiry week. "
          "Spot-checked against raw per-session volume for the first roll (ESM0->ESU0, instrument_id 6640/26714): "
          "next-quarter volume genuinely overtakes front on the Friday 7 calendar days before expiry, but the "
          "rule only rolls at the START of the FOLLOWING session, which is the Monday after the weekend -- "
          "hence the effective roll lands 3-4 days before expiry, not a bug.",
          "- Wall-clock (ET) resampling floors on tz-naive local time; the one ambiguous DST fall-back "
          "hour/year is not specially disambiguated, but it falls in CME's weekly Sunday closure so no "
          "real bars are affected.",
          "- OOS files (*_oos.parquet) are locked -- do not read until final testing."]
(OUT / "VALIDATION.md").write_text("\n".join(lines) + "\n")
log(f"done in {time.time()-T0:.1f}s -- wrote data/VALIDATION.md and {len(files_written)} parquet files")
