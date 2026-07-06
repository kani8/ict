"""Program T, Iter 01 — daily continuous-contract stitch for CL / GC / ZN / 6E.

Generalises the ES 1m recipe (`reports/dev/_es_stitch.py`) to DAILY
resolution and to monthly-listed products.  Same protocol:

  - Source: Databento GLBX.MDP3 **ohlcv-1d**, parent symbology (e.g.
    "CL.FUT"), stype_out=instrument_id, all expiries.
  - Exclude spread instruments (symbol contains '-') before stitching.
  - Roll: lead contract by DAILY VOLUME; roll when the next contract's
    volume overtakes the front's.  Look-ahead-free: a crossover observed
    on day d moves membership to the *next trading day* (days[i+1]).
  - Back-adjust: DIFFERENCE / additive (Panama).  Newest segment offset
    0; each older segment shifted by the cumulative sum of roll gaps.
  - Volume = active contract's own volume.

Two faithful generalisations over the ES script:

  1. **Month codes.**  ES lists quarterly (H/M/U/Z); CL/GC list monthly.
     MONTHS covers all twelve CME codes so every listed contract decodes.
  2. **Contract ordering.**  The volume roll needs only the *chronological
     order* of contracts (to define each contract's successor) and the
     close-to-close gap at the crossover — not a settlement date.  CL/GC
     do not settle on the third Friday, so instead of assigning a
     third-Friday expiry we order contracts by the decoded (year, month)
     of their symbol, with the single-digit year's decade anchored to the
     contract's observed ``max_dt`` (exactly the ES decade-disambiguation,
     e.g. CLM6 = 2016 vs 2026).  This drops the equity-index-specific
     settlement assumption while keeping the identical roll logic.

Output per symbol (shared convention with data/es_1d.parquet so the
portfolio inner-join on ts//86400 aligns across all five instruments):

  data/<sym>_1d.parquet          ts = epoch SECONDS (int) of midnight-UTC
                                 session date; O/H/L/C additive-adjusted;
                                 volume = active contract's volume.
  data/<sym>_1d_raw.parquet      un-adjusted active-contract daily series
                                 (roll-continuity / offset audit).
  reports/dev/_<sym>_roll_calendar.json   every roll + contract table.
  reports/dev/_<sym>_1d_meta.json         rows, range, roll count, dupes,
                                 OHLC violations, non-positive (adjusted)
                                 flag, min/max, per-boundary residual
                                 check, last-segment offset==0 spot check,
                                 sha256s.

STATUS: staged, NOT yet run — CL/GC/ZN/6E daily data is not present
(Databento fetch is blocked; see reports/dev/T_ITER01.md).  Fill SRC_ZST
(or pass --csv) once the ohlcv-1d exports exist, then:

    uv run python reports/dev/_t01_stitch.py --sym cl --csv data/<...>.ohlcv-1d.csv.zst
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ZSTD = "/opt/homebrew/bin/zstd"

# All twelve CME month codes -> calendar month.  (ES used only H/M/U/Z.)
MONTHS = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
          "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}

# Product root length in the GLBX symbol (chars before the month code).
# ES/CL/GC/ZN are 2-char roots; 6E is also 2 chars ("6E").
ROOT_LEN = 2

# Fill after the fetch (or pass --csv on the command line).  Kept as a
# sentinel so an accidental run without data fails loud instead of silent.
SRC_ZST: dict[str, str] = {
    "cl": "",   # WTI crude  — CL.FUT ohlcv-1d
    "gc": "",   # gold       — GC.FUT ohlcv-1d
    "zn": "",   # 10y note   — ZN.FUT ohlcv-1d
    "6e": "",   # euro FX    — 6E.FUT ohlcv-1d
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_year(digits: str, max_dt: pd.Timestamp) -> int:
    """Resolve the contract year from the symbol's year digits.

    Two-digit -> 2000+n.  Single-digit -> the year in the decade of the
    contract's last observed trading day whose last digit matches, i.e.
    the same ``max_dt``-anchored disambiguation the ES stitch uses for
    ESM6 (2016) vs a truncated far-end ESM6 (2026)."""
    if len(digits) >= 2:
        return 2000 + int(digits[-2:])
    d = int(digits)
    base = (max_dt.year // 10) * 10
    cands = [base + d, base + d - 10, base + d + 10]
    return min(cands, key=lambda y: abs(y - max_dt.year))


def sort_key(symbol: str, max_dt: pd.Timestamp) -> tuple[int, int]:
    mc = symbol[ROOT_LEN]
    yr = decode_year(symbol[ROOT_LEN + 1:], max_dt)
    return (yr, MONTHS[mc])


def load_raw(csv_zst: Path) -> pd.DataFrame:
    print(f"[{time.strftime('%H:%M:%S')}] decompress+read {csv_zst.name} ...", flush=True)
    proc = subprocess.Popen([ZSTD, "-dc", str(csv_zst)], stdout=subprocess.PIPE)
    df = pd.read_csv(
        proc.stdout,
        usecols=["ts_event", "instrument_id", "open", "high", "low", "close",
                 "volume", "symbol"],
        dtype={"instrument_id": "int64", "open": "float64", "high": "float64",
               "low": "float64", "close": "float64", "volume": "int64",
               "symbol": "string"},
    )
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"zstd exited {proc.returncode}")
    print(f"  total rows read: {len(df):,}", flush=True)
    df["ts"] = pd.to_datetime(df["ts_event"], utc=True, format="ISO8601")
    return df.drop(columns=["ts_event"])


def stitch(sym: str, csv_zst: Path) -> None:
    t0 = time.time()
    df = load_raw(csv_zst)

    # --- exclude spreads --------------------------------------------------
    is_spread = df["symbol"].str.contains("-", regex=False, na=False)
    n_spread = int(is_spread.sum())
    df = df.loc[~is_spread].copy()
    print(f"  spread rows excluded: {n_spread:,}; outright rows: {len(df):,}", flush=True)

    # Daily bars: one row per (session, instrument).  ts_event is the bar's
    # UTC start; floor to the day so the session key is midnight UTC.  (To
    # verify against the real export: the settlement-date labelling must
    # match data/es_1d.parquet's midnight-UTC-of-settlement convention;
    # any mismatch is an anomaly to report, not to patch.)
    df["day"] = df["ts"].dt.floor("D")

    # --- per-contract span + chronological ordering (instrument_id keyed) --
    span = df.groupby("instrument_id").agg(
        symbol=("symbol", "first"),
        min_dt=("ts", "min"),
        max_dt=("ts", "max"),
        rows=("ts", "size"),
    ).reset_index()
    span["key"] = [sort_key(s, mx) for s, mx in zip(span["symbol"], span["max_dt"])]
    span = span.sort_values("key").reset_index(drop=True)
    print(f"  unique outright instrument_ids: {len(span)}", flush=True)

    iid_order = list(span["instrument_id"])
    successor = {iid_order[i]: iid_order[i + 1] for i in range(len(iid_order) - 1)}
    sym_of = dict(zip(span["instrument_id"], span["symbol"]))

    # --- daily volume + daily last-close per (day, instrument_id) ----------
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    dv = df.groupby(["day", "instrument_id"])["volume"].sum().to_dict()
    last_close = df.groupby(["day", "instrument_id"])["close"].last().to_dict()
    days = sorted(df["day"].unique())

    # --- seed active = max-volume contract on first day --------------------
    d0 = days[0]
    d0_contracts = [(iid, dv[(d0, iid)]) for iid in iid_order if (d0, iid) in dv]
    active = max(d0_contracts, key=lambda kv: kv[1])[0]

    # --- look-ahead-free daily-volume roll walk ----------------------------
    active_by_day: dict[pd.Timestamp, int] = {}
    rolls: list[dict] = []
    for i, d in enumerate(days):
        active_by_day[d] = active
        nxt = successor.get(active)
        if nxt is None:
            continue
        v_act = dv.get((d, active), 0)
        v_nxt = dv.get((d, nxt), 0)
        if v_nxt > v_act and v_nxt > 0 and i + 1 < len(days):
            rolls.append({
                "crossover_day": d, "effective_day": days[i + 1],
                "from_iid": int(active), "to_iid": int(nxt),
                "from_symbol": sym_of[active], "to_symbol": sym_of[nxt],
                "from_vol": int(v_act), "to_vol": int(v_nxt),
            })
            active = nxt

    # --- additive (Panama) back-adjust: newest offset 0, cumulate backward --
    for r in rolls:
        cd = r["crossover_day"]
        c_from = last_close.get((cd, r["from_iid"]))
        c_to = last_close.get((cd, r["to_iid"]))
        r["raw_gap"] = None if (c_from is None or c_to is None) else float(c_to - c_from)

    seg_offset = [0.0] * (len(rolls) + 1)
    for k in range(len(rolls) - 1, -1, -1):
        seg_offset[k] = seg_offset[k + 1] + (rolls[k]["raw_gap"] or 0.0)
    for k, r in enumerate(rolls):
        r["cum_offset_applied_to_from_segment"] = seg_offset[k]

    seg_of_day: dict[pd.Timestamp, int] = {}
    seg = 0
    roll_eff = {r["effective_day"]: i for i, r in enumerate(rolls)}
    for d in days:
        if d in roll_eff:
            seg = roll_eff[d] + 1
        seg_of_day[d] = seg

    # --- build continuous active-contract DAILY series ---------------------
    df["active_iid"] = df["day"].map(pd.Series(active_by_day))
    cont = df.loc[df["instrument_id"] == df["active_iid"]].copy()
    cont = cont.sort_values("ts", kind="stable").reset_index(drop=True)
    # one bar per session already (daily); guard against dup session rows
    cont = cont.drop_duplicates(subset="day", keep="last").reset_index(drop=True)
    off = cont["day"].map(seg_of_day).map(lambda s: seg_offset[s]).to_numpy()
    print(f"  continuous active-contract daily bars: {len(cont):,}", flush=True)

    def write(frame: pd.DataFrame, offset: np.ndarray | None, path: Path) -> None:
        add = offset if offset is not None else 0.0
        out = pd.DataFrame({
            # epoch SECONDS of midnight-UTC session date (int) — matches es_1d
            "ts": (frame["day"].astype("int64") // 10**9).to_numpy(),
            "open": frame["open"].to_numpy(float) + add,
            "high": frame["high"].to_numpy(float) + add,
            "low": frame["low"].to_numpy(float) + add,
            "close": frame["close"].to_numpy(float) + add,
            "volume": frame["volume"].to_numpy(float),
        })
        out.to_parquet(path, index=False)

    raw_path = ROOT / f"data/{sym}_1d_raw.parquet"
    adj_path = ROOT / f"data/{sym}_1d.parquet"
    write(cont, None, raw_path)
    write(cont, off, adj_path)

    # --- integrity summary (task-mandated per-instrument record) -----------
    adj = pd.read_parquet(adj_path)
    n = len(adj)
    dupes = int(adj["ts"].duplicated().sum())
    ohlc_viol = int(((adj["high"] < adj[["open", "close", "low"]].max(axis=1)) |
                     (adj["low"] > adj[["open", "close", "high"]].min(axis=1))).sum())
    nonpos = int((adj[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())

    # per-boundary residual: adjusted close of the last old-segment day and
    # the first new-segment day should differ only by the market's own
    # overnight move (the roll gap is neutralised).  We report, per roll,
    # the raw gap and confirm the cumulative offsets chain to 0 at newest.
    boundary = [{
        "roll_index": k, "effective_day": r["effective_day"].strftime("%Y-%m-%d"),
        "from_symbol": r["from_symbol"], "to_symbol": r["to_symbol"],
        "raw_gap": r["raw_gap"],
        "cum_offset_on_from_segment": r["cum_offset_applied_to_from_segment"],
    } for k, r in enumerate(rolls)]

    # front-vs-continuous spot check on the LAST segment: the newest segment
    # carries offset 0, so adjusted == raw over the final segment.
    raw = pd.read_parquet(raw_path)
    last_seg_mask = cont["day"].map(seg_of_day).to_numpy() == (len(rolls))
    last_seg_offset = float(np.unique(off[last_seg_mask])[0]) if last_seg_mask.any() else float("nan")
    last_seg_max_abs_diff = float(np.max(np.abs(
        adj.loc[last_seg_mask, "close"].to_numpy() - raw.loc[last_seg_mask, "close"].to_numpy()
    ))) if last_seg_mask.any() else float("nan")

    meta = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "symbol": sym,
        "source_csv_zst": str(csv_zst),
        "source_sha256": sha256(csv_zst),
        "n_spread_rows": n_spread,
        "rows": n,
        "date_first": str(pd.to_datetime(adj["ts"].iloc[0], unit="s").date()),
        "date_last": str(pd.to_datetime(adj["ts"].iloc[-1], unit="s").date()),
        "duplicates": dupes,
        "ohlc_violations": ohlc_viol,
        "nonpositive_adjusted_prices": nonpos,  # additive can push deep-history <=0
        "min_close": float(adj["close"].min()),
        "max_close": float(adj["close"].max()),
        "n_unique_outright_iids": int(len(span)),
        "n_rolls": len(rolls),
        "seed_active_symbol": sym_of[active_by_day[d0]],
        "final_active_symbol": sym_of[active],
        "last_segment_offset": last_seg_offset,               # must be 0.0
        "last_segment_max_abs_adj_minus_raw": last_seg_max_abs_diff,  # must be 0.0
        "boundaries": boundary,
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
                  for p in (adj_path, raw_path)},
    }
    (ROOT / f"reports/dev/_{sym}_1d_meta.json").write_text(json.dumps(meta, indent=2))
    (ROOT / f"reports/dev/_{sym}_roll_calendar.json").write_text(json.dumps({
        "n_rolls": len(rolls), "seed_day": d0.strftime("%Y-%m-%d"),
        "seed_active_symbol": sym_of[active_by_day[d0]],
        "final_active_symbol": sym_of[active],
        "rolls": [{**b} for b in boundary],
        "contracts": [{
            "instrument_id": int(row.instrument_id), "symbol": row.symbol,
            "min_dt": row.min_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "max_dt": row.max_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rows": int(row.rows),
        } for row in span.itertuples()],
    }, indent=2))
    print(f"  wrote data/{sym}_1d.parquet ({n} rows, {len(rolls)} rolls); "
          f"last-seg offset={last_seg_offset}", flush=True)
    print(f"[wall-clock {time.time() - t0:.1f}s] {sym} done", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", choices=sorted(SRC_ZST), help="single product; omit to run all")
    ap.add_argument("--csv", help="path to that product's ohlcv-1d .csv.zst (overrides SRC_ZST)")
    args = ap.parse_args()

    targets = [args.sym] if args.sym else sorted(SRC_ZST)
    for sym in targets:
        csv = args.csv if (args.csv and args.sym) else SRC_ZST[sym]
        if not csv:
            raise SystemExit(
                f"no source for {sym!r}: fill SRC_ZST[{sym!r}] or pass --sym {sym} --csv <path>. "
                "CL/GC/ZN/6E ohlcv-1d data is not present (fetch blocked)."
            )
        stitch(sym, Path(csv))


if __name__ == "__main__":
    main()
