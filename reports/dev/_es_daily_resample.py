"""Program T, Iter 01 — ES daily bars by resampling the existing adjusted
15m series to CME trading-day buckets.  NO re-stitch: es_15m.parquet is the
already back-adjusted continuous series; we only aggregate it to 1d.

CME equity-index Globex session: opens 17:00 CT, closes 16:00 CT next day,
maintenance break 16:00-17:00 CT.  A bar belongs to the session that *ends*
on its settlement date.  DST-safe rule: convert ts to America/Chicago, add
7h, take the calendar date -> the 17:00 CT open rolls to the next date, the
15:45 CT last bar stays on the close date.  Daily ts = midnight UTC of that
settlement date (shared convention with the CL/GC/ZN/6E stitch so the
portfolio inner-join on ts//86400 aligns across instruments).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("data/es_15m.parquet")
OUT = Path("data/es_1d.parquet")
META = Path("reports/dev/_es_1d_meta.json")
WINDOW_END = pd.Timestamp("2026-07-01").date()  # inclusive; task window end


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    df = pd.read_parquet(SRC).sort_values("ts").reset_index(drop=True)
    ct = df["ts"].dt.tz_convert("America/Chicago")
    session = (ct + pd.Timedelta(hours=7)).dt.normalize().dt.tz_localize(None).dt.date
    df["session"] = session

    # --- boundary hygiene (construction, documented; not result-patching) ---
    # (a) two lone Sunday pre-open prints (2014-05-25 16:30 CT, 2018-08-05
    #     16:45 CT) label as weekend "sessions"; real CME sessions settle
    #     Mon-Fri, so drop weekend-labeled sessions.
    # (b) the source series ends 2026-07-01 18:45 CT, an 8-bar stub of the
    #     2026-07-02 session that never reaches settlement and is past the
    #     task window end; clip to sessions <= WINDOW_END.
    sd = pd.to_datetime(pd.Series(session))
    weekend = sd.dt.weekday.to_numpy() >= 5
    out_of_window = session.to_numpy() > WINDOW_END
    dropped_weekend = sorted({str(s) for s in session[weekend]})
    dropped_oow = sorted({str(s) for s in session[out_of_window]})
    keep = ~(weekend | out_of_window)
    df = df[keep].reset_index(drop=True)

    g = df.groupby("session", sort=True)
    daily = pd.DataFrame({
        "open": g["open"].first(),
        "high": g["high"].max(),
        "low": g["low"].min(),
        "close": g["close"].last(),
        "volume": g["volume"].sum(),
    }).reset_index()
    # daily ts = midnight UTC of the settlement date (epoch seconds, integer)
    daily["ts"] = (pd.to_datetime(daily["session"]).astype("datetime64[ns]")
                   .astype(np.int64) // 10**9)
    daily = daily[["ts", "open", "high", "low", "close", "volume"]]

    # --- sanity checks ---
    n = len(daily)
    dupes = int(daily["ts"].duplicated().sum())
    ohlc_viol = int(((daily["high"] < daily[["open", "close", "low"]].max(axis=1)) |
                     (daily["low"] > daily[["open", "close", "high"]].min(axis=1))).sum())
    nonpos = int((daily[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    date0 = pd.to_datetime(daily["ts"].iloc[0], unit="s")
    date1 = pd.to_datetime(daily["ts"].iloc[-1], unit="s")

    # 20-random-day reconciliation vs raw 15m extremes (exact match)
    rng = np.random.default_rng(20100606)
    pick = rng.choice(df["session"].unique(), size=20, replace=False)
    mism = 0
    for s in pick:
        sub = df[df["session"] == s]
        o = sub["open"].iloc[0]; c = sub["close"].iloc[-1]
        hi = sub["high"].max(); lo = sub["low"].min(); vol = sub["volume"].sum()
        row = daily[daily["ts"] == (pd.Timestamp(s).value // 10**9)].iloc[0]
        if not (o == row.open and c == row.close and hi == row.high
                and lo == row.low and abs(vol - row.volume) < 1e-6):
            mism += 1
    # thin-but-legitimate sessions kept (partial data / early close)
    bars_per = g.size()
    thin_kept = {str(s): int(bars_per[s]) for s in bars_per.index if bars_per[s] < 45}

    daily.to_parquet(OUT, index=False)

    meta = {
        "generated": pd.Timestamp.now("UTC").isoformat(),
        "source": str(SRC),
        "source_sha256": sha256(SRC),
        "method": "resample es_15m -> 1d, CME session (America/Chicago +7h date), "
                  "ts=midnight-UTC settlement date; NO re-stitch",
        "rows": n,
        "date_first": str(date0.date()),
        "date_last": str(date1.date()),
        "duplicates": dupes,
        "ohlc_violations": ohlc_viol,
        "nonpositive_prices": nonpos,
        "min_close": float(daily["close"].min()),
        "max_close": float(daily["close"].max()),
        "recon_20day_mismatches": mism,
        "dropped_weekend_sessions": dropped_weekend,
        "dropped_out_of_window_sessions": dropped_oow,
        "thin_sessions_kept": thin_kept,
        "out_sha256": sha256(OUT),
    }
    META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
