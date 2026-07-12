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


def synthetic_cat_regimes(
    n: int = 20_000,
    timeframe_s: int = 900,
    start_price: float = 5_000.0,
    start_ts: int = 1_700_000_000,
    seed: int = 1,
    base_vol: float = 0.0012,
    cons_mean_bars: int = 160,
    dir_mean_bars: int = 80,
    cons_reversion: float = 0.08,
    dir_drift: float = 0.0006,
) -> tuple[Candles, np.ndarray]:
    """Alternating consolidation / direction regimes, by construction.

    The world the CAT (categorical trading) approach claims as its edge:
    consolidation segments are an Ornstein-Uhlenbeck pull toward the
    level where the segment started (price "stays where it has been"),
    direction segments carry a persistent drift with random sign (price
    "goes to a new area").  Segment lengths are geometric with the given
    means.

    Returns ``(candles, labels)`` with ``labels[i]`` 1 = direction,
    2 = consolidation for bar i — ground truth for classifier
    diagnostics, never an input to any strategy.

    A strategy whose consolidation/direction mechanics are implemented
    correctly should extract edge here; the same strategy on
    ``synthetic_candles(trend_strength=0)`` (a pure random walk) should
    not.  Passing both is a calibration of the mechanics, not evidence
    about any real market.
    """
    rng = np.random.default_rng(seed)
    start_ts -= start_ts % timeframe_s

    labels = np.empty(n, dtype=np.int8)
    logp = np.empty(n)
    x = np.log(start_price)
    i = 0
    in_cons = True
    while i < n:
        mean_len = cons_mean_bars if in_cons else dir_mean_bars
        seg = min(n - i, max(5, int(rng.geometric(1.0 / mean_len))))
        if in_cons:
            anchor = x
            for j in range(i, i + seg):
                x += cons_reversion * (anchor - x) + base_vol * rng.standard_normal()
                logp[j] = x
                labels[j] = 2
        else:
            drift = dir_drift * (1 if rng.random() < 0.5 else -1)
            for j in range(i, i + seg):
                x += drift + base_vol * rng.standard_normal()
                logp[j] = x
                labels[j] = 1
        i += seg
        in_cons = not in_cons

    close = np.exp(logp)
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]
    body_hi = np.maximum(open_, close)
    body_lo = np.minimum(open_, close)
    wick = np.abs(rng.standard_normal(n)) * base_vol * close * 0.6
    high = body_hi + wick * rng.random(n)
    low = body_lo - wick * rng.random(n)
    volume = rng.lognormal(mean=0.0, sigma=0.5, size=n) * 100

    ts = start_ts + timeframe_s * np.arange(n, dtype=np.int64)
    candles = Candles(ts=ts, open=open_, high=high, low=low, close=close,
                      volume=volume, timeframe_s=timeframe_s)
    return candles, labels
