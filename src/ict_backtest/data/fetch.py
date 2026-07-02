"""Fetch historical klines from Binance's public REST API (no key needed).

Requires the ``fetch`` extra (``pip install ict-backtest[fetch]``).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import Candles

_INTERVAL_S = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "8h": 28800,
    "12h": 43200, "1d": 86400,
}

_ENDPOINTS = (
    "https://api.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
)


def fetch_binance(
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    start: str = "2023-01-01",
    end: str | None = None,
    pause_s: float = 0.15,
) -> Candles:
    import requests

    if interval not in _INTERVAL_S:
        raise ValueError(f"interval must be one of {sorted(_INTERVAL_S)}")
    tf = _INTERVAL_S[interval]
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000) if end else int(time.time() * 1000)

    rows: list[list] = []
    cursor = start_ms
    session = requests.Session()
    while cursor < end_ms:
        params = {"symbol": symbol, "interval": interval, "startTime": cursor,
                  "endTime": end_ms, "limit": 1000}
        last_err: Exception | None = None
        for url in _ENDPOINTS:
            try:
                resp = session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                batch = resp.json()
                break
            except Exception as e:  # noqa: BLE001 - try next endpoint
                last_err = e
        else:
            raise RuntimeError(f"all Binance endpoints failed: {last_err}")
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + tf * 1000
        time.sleep(pause_s)

    if not rows:
        raise RuntimeError("no data returned")
    arr = np.array(rows, dtype=object)
    ts = arr[:, 0].astype(np.int64) // 1000
    uniq = np.unique(ts, return_index=True)[1]
    return Candles(
        ts=ts[uniq],
        open=arr[uniq, 1].astype(float),
        high=arr[uniq, 2].astype(float),
        low=arr[uniq, 3].astype(float),
        close=arr[uniq, 4].astype(float),
        volume=arr[uniq, 5].astype(float),
        timeframe_s=tf,
    )


def save_candles(candles: Candles, path: str | Path) -> None:
    df = candles.to_dataframe()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix in (".parquet", ".pq"):
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
