"""Load OHLCV candles from CSV/Parquet with flexible column names."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..core import Candles

_ALIASES = {
    "ts": ("ts", "timestamp", "time", "date", "datetime", "open_time"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol", "v"),
}


def _pick(df: pd.DataFrame, key: str) -> str:
    cols = {c.lower(): c for c in df.columns}
    for alias in _ALIASES[key]:
        if alias in cols:
            return cols[alias]
    raise ValueError(f"no column found for '{key}' among {list(df.columns)}")


def candles_from_dataframe(df: pd.DataFrame, timeframe_s: int | None = None) -> Candles:
    ts_col = _pick(df, "ts")
    ts_raw = df[ts_col]
    if pd.api.types.is_numeric_dtype(ts_raw.dtype):
        # heuristics: ms vs s epochs
        vals = ts_raw.astype(np.int64).to_numpy()
        if vals.max() > 10_000_000_000:
            vals = vals // 1000
        ts = vals
    else:
        dt = pd.to_datetime(ts_raw, utc=True).astype("datetime64[ns, UTC]")
        ts = (dt.astype(np.int64) // 10**9).to_numpy()

    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    if timeframe_s is None:
        diffs = np.diff(ts)
        diffs = diffs[diffs > 0]
        if len(diffs) == 0:
            raise ValueError("cannot infer timeframe from a single bar; pass timeframe_s")
        timeframe_s = int(np.median(diffs))

    def col(key: str) -> np.ndarray:
        return df[_pick(df, key)].to_numpy(dtype=float)[order]

    try:
        volume = col("volume")
    except ValueError:
        volume = np.zeros(len(ts))

    return Candles(
        ts=ts, open=col("open"), high=col("high"), low=col("low"),
        close=col("close"), volume=volume, timeframe_s=timeframe_s,
    )


def load_candles(
    path: str | Path,
    timeframe_s: int | None = None,
    start: str | None = None,
    end: str | None = None,
) -> Candles:
    path = Path(path)
    if path.suffix in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    candles = candles_from_dataframe(df, timeframe_s)
    if start or end:
        lo = int(pd.Timestamp(start, tz="UTC").timestamp()) if start else -np.inf
        hi = int(pd.Timestamp(end, tz="UTC").timestamp()) if end else np.inf
        mask = (candles.ts >= lo) & (candles.ts < hi)
        idx = np.flatnonzero(mask)
        if len(idx) == 0:
            raise ValueError("no candles in requested date range")
        candles = candles.slice(int(idx[0]), int(idx[-1]) + 1)
    return candles
