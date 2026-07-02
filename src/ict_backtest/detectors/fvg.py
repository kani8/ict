"""Fair Value Gap (imbalance) detection.

Bullish FVG at i: low[i+2] > high[i]  -> zone (high[i], low[i+2])
Bearish FVG at i: high[i+2] < low[i]  -> zone (high[i+2], low[i])

Knowable only once candle i+2 closes, so ``confirm_index = i + 2``.
A displacement filter (gap size relative to ATR) screens out noise gaps —
ICT emphasizes FVGs left by *impulsive* moves.
"""

from __future__ import annotations

import numpy as np

from ..core import BEAR, BULL, FVG, Candles, atr


def _first_true(mask: np.ndarray, offset: int) -> int:
    idx = np.flatnonzero(mask)
    return int(idx[0] + offset) if len(idx) else -1


def detect_fvgs(
    candles: Candles,
    min_gap_atr: float = 0.25,
    atr_period: int = 14,
) -> list[FVG]:
    h, l = candles.high, candles.low
    n = len(candles)
    if n < 3:
        return []
    a = atr(candles, atr_period)

    gaps: list[FVG] = []
    bull_mask = l[2:] > h[:-2]
    bear_mask = h[2:] < l[:-2]

    c = candles.close

    for i in np.flatnonzero(bull_mask):
        i = int(i)
        zone_lo, zone_hi = float(h[i]), float(l[i + 2])
        if zone_hi - zone_lo < min_gap_atr * a[i + 2]:
            continue
        after = i + 3
        touch = _first_true(l[after:n] <= zone_hi, after) if after < n else -1
        fill = _first_true(l[after:n] <= zone_lo, after) if after < n else -1
        invert = _first_true(c[after:n] < zone_lo, after) if after < n else -1
        invert_fail = -1
        if invert != -1 and invert + 1 < n:
            invert_fail = _first_true(c[invert + 1 : n] > zone_hi, invert + 1)
        gaps.append(FVG(index=i, low=zone_lo, high=zone_hi, direction=BULL,
                        confirm_index=i + 2, touch_index=touch, fill_index=fill,
                        invert_index=invert, invert_fail_index=invert_fail))

    for i in np.flatnonzero(bear_mask):
        i = int(i)
        zone_lo, zone_hi = float(h[i + 2]), float(l[i])
        if zone_hi - zone_lo < min_gap_atr * a[i + 2]:
            continue
        after = i + 3
        touch = _first_true(h[after:n] >= zone_lo, after) if after < n else -1
        fill = _first_true(h[after:n] >= zone_hi, after) if after < n else -1
        invert = _first_true(c[after:n] > zone_hi, after) if after < n else -1
        invert_fail = -1
        if invert != -1 and invert + 1 < n:
            invert_fail = _first_true(c[invert + 1 : n] < zone_lo, invert + 1)
        gaps.append(FVG(index=i, low=zone_lo, high=zone_hi, direction=BEAR,
                        confirm_index=i + 2, touch_index=touch, fill_index=fill,
                        invert_index=invert, invert_fail_index=invert_fail))

    gaps.sort(key=lambda g: g.index)
    return gaps
