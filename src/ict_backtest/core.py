"""Core data structures shared across detectors, engine, and strategies.

Design principle: every detected artifact carries a ``confirm_index`` — the
bar index at whose *close* the artifact first becomes knowable.  Consumers
(strategies) must never act on an artifact before its ``confirm_index``.
This is the primary defense against lookahead bias.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BULL = 1
BEAR = -1


@dataclass(slots=True)
class Candles:
    """Column-oriented OHLCV container backed by numpy arrays.

    ``ts`` holds UTC epoch seconds (int64). ``timeframe_s`` is the nominal
    bar duration in seconds.
    """

    ts: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    timeframe_s: int

    def __post_init__(self) -> None:
        n = len(self.ts)
        for name in ("open", "high", "low", "close", "volume"):
            if len(getattr(self, name)) != n:
                raise ValueError(f"column '{name}' length mismatch")

    def __len__(self) -> int:
        return len(self.ts)

    def slice(self, start: int, stop: int) -> "Candles":
        return Candles(
            ts=self.ts[start:stop],
            open=self.open[start:stop],
            high=self.high[start:stop],
            low=self.low[start:stop],
            close=self.close[start:stop],
            volume=self.volume[start:stop],
            timeframe_s=self.timeframe_s,
        )

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ts": pd.to_datetime(self.ts, unit="s", utc=True),
                "open": self.open,
                "high": self.high,
                "low": self.low,
                "close": self.close,
                "volume": self.volume,
            }
        )


def atr(candles: Candles, period: int = 14) -> np.ndarray:
    """Wilder-smoothed Average True Range, aligned 1:1 with the candles.

    Value at index i uses data up to and including bar i (no lookahead).
    The first bar's TR is its own high-low range.
    """
    h, l, c = candles.high, candles.low, candles.close
    tr = np.empty(len(candles))
    tr[0] = h[0] - l[0]
    prev_close = c[:-1]
    tr[1:] = np.maximum(
        h[1:] - l[1:],
        np.maximum(np.abs(h[1:] - prev_close), np.abs(l[1:] - prev_close)),
    )
    # Wilder smoothing == EWM with alpha = 1/period, adjust=False
    return pd.Series(tr).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy()


def resample(candles: Candles, multiplier: int) -> tuple[Candles, np.ndarray]:
    """Aggregate base-timeframe candles into a higher timeframe.

    Buckets are aligned to wall-clock boundaries of the target timeframe
    (``ts - ts % htf_seconds``), so a 4h bar starts at 00/04/08... UTC.

    Returns ``(htf_candles, last_base_index)`` where ``last_base_index[k]``
    is the index of the final base bar inside HTF bar k.  An HTF artifact
    confirmed at HTF bar k is only knowable at base bar
    ``last_base_index[k]`` — use that for confirm-index mapping.
    """
    if multiplier < 1:
        raise ValueError("multiplier must be >= 1")
    htf_s = candles.timeframe_s * multiplier
    bucket = candles.ts - (candles.ts % htf_s)
    # bucket is non-decreasing; find group boundaries
    change = np.flatnonzero(np.diff(bucket)) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [len(candles)]))  # exclusive

    k = len(starts)
    o = np.empty(k)
    h = np.empty(k)
    l = np.empty(k)
    c = np.empty(k)
    v = np.empty(k)
    ts = np.empty(k, dtype=np.int64)
    last_base = np.empty(k, dtype=np.int64)
    for j in range(k):
        s, e = starts[j], ends[j]
        ts[j] = bucket[s]
        o[j] = candles.open[s]
        h[j] = candles.high[s:e].max()
        l[j] = candles.low[s:e].min()
        c[j] = candles.close[e - 1]
        v[j] = candles.volume[s:e].sum()
        last_base[j] = e - 1
    htf = Candles(ts=ts, open=o, high=h, low=l, close=c, volume=v, timeframe_s=htf_s)
    return htf, last_base


# ---------------------------------------------------------------------------
# Detected artifacts
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Swing:
    """A confirmed fractal pivot. ``kind`` is BULL for swing high, BEAR for low."""

    index: int
    price: float
    kind: int
    confirm_index: int


@dataclass(slots=True)
class StructureEvent:
    """A close-confirmed break of a prior swing.

    ``kind`` is "BOS" (with-trend continuation) or "MSS" (against-trend
    shift, a.k.a. CHoCH). ``direction`` is BULL when a swing high was broken
    upward, BEAR when a swing low was broken downward. Confirmed at the
    close of ``index``.
    """

    index: int
    direction: int
    kind: str
    level: float
    swing_index: int

    @property
    def confirm_index(self) -> int:
        return self.index


@dataclass(slots=True)
class OrderBlock:
    """Last counter-trend candle before the impulse that broke structure.

    ``direction`` BULL means a bullish OB (demand zone, last down candle
    before an up-leg). ``created_index`` is the structure-break bar — the
    zone is only tradeable from there on. ``invalidated_index`` is the first
    bar whose close violates the zone; from that bar on the zone acts as a
    breaker in the opposite direction.  -1 sentinels mean "never happened
    within the data".
    """

    index: int
    low: float
    high: float
    direction: int
    created_index: int
    mitigated_index: int = -1
    invalidated_index: int = -1

    def is_breaker_at(self, i: int) -> bool:
        return 0 <= self.invalidated_index <= i


@dataclass(slots=True)
class FVG:
    """Three-candle imbalance. Zone is (low, high) in price terms.

    Bullish FVG: gap between high[i] and low[i+2] under current price.
    ``confirm_index`` = i+2. ``touch_index`` is the first later bar that
    trades back into the zone; ``fill_index`` the first bar that fully
    closes the gap (zone consumed). -1 sentinels mean "never".
    """

    index: int
    low: float
    high: float
    direction: int
    confirm_index: int
    touch_index: int = -1
    fill_index: int = -1


@dataclass(slots=True)
class LiquidityPool:
    """Cluster of resting stops beyond a swing extreme.

    ``side`` BULL = buy-side liquidity above swing high(s); BEAR = sell-side
    below swing low(s). Equal highs/lows within tolerance merge into one
    pool (``swing_indices`` lists the members, ``level`` the extreme).

    ``taken_index``/``taken_kind`` record the first bar that trades through
    the level: a "sweep" (close back inside — stop hunt) or a "run" (close
    through — continuation). Both are knowable at that bar's close.
    """

    side: int
    level: float
    swing_indices: list[int] = field(default_factory=list)
    confirm_index: int = 0
    taken_index: int = -1
    taken_kind: str | None = None

    @property
    def is_equal_cluster(self) -> bool:
        return len(self.swing_indices) > 1
