"""Synthetic OHLCV generation for tests and null-hypothesis experiments.

Regime-switching geometric random walk with intrabar range structure.
By construction it contains no exploitable SMC edge, which makes it a
useful sanity check: a detector or strategy that "profits" reliably on
this data is leaking future information.
"""

from __future__ import annotations

import numpy as np

from ..core import Candles


def synthetic_candles(
    n: int = 20_000,
    timeframe_s: int = 900,
    start_price: float = 50_000.0,
    start_ts: int = 1_700_000_000,
    seed: int = 1,
    base_vol: float = 0.002,
    regime_persistence: float = 0.995,
    trend_strength: float = 0.0002,
) -> Candles:
    rng = np.random.default_rng(seed)
    start_ts -= start_ts % timeframe_s

    # two-state regime: drift up / drift down, occasionally flipping
    flips = rng.random(n) > regime_persistence
    regime = np.cumsum(flips) % 2
    drift = np.where(regime == 0, trend_strength, -trend_strength)
    vol = base_vol * (1.0 + 0.5 * regime)  # downtrends a bit more volatile

    rets = drift + vol * rng.standard_normal(n)
    close = start_price * np.exp(np.cumsum(rets))
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]

    body_hi = np.maximum(open_, close)
    body_lo = np.minimum(open_, close)
    wick = np.abs(rng.standard_normal(n)) * vol * close * 0.6
    high = body_hi + wick * rng.random(n)
    low = body_lo - wick * rng.random(n)
    volume = rng.lognormal(mean=0.0, sigma=0.5, size=n) * 100

    ts = start_ts + timeframe_s * np.arange(n, dtype=np.int64)
    return Candles(ts=ts, open=open_, high=high, low=low, close=close,
                   volume=volume, timeframe_s=timeframe_s)
