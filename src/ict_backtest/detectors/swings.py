"""Fractal swing (pivot) detection with explicit confirmation lag.

A swing high at bar p requires ``k`` bars on each side, so it is only
knowable at the close of bar ``p + k``.  Detectors downstream (structure,
liquidity) inherit this lag through ``Swing.confirm_index``.

Tie handling: a pivot must be >= everything in its window and strictly
beyond the bars to its right.  Two equal extremes further than ``k`` bars
apart therefore both register — which is exactly what equal-high /
equal-low liquidity detection needs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..core import BEAR, BULL, Candles, Swing


def _pivots(values: np.ndarray, k: int, is_high: bool) -> np.ndarray:
    """Return indices p where values[p] is a k-fractal extreme."""
    s = pd.Series(values)
    window_extreme = (
        s.rolling(2 * k + 1, center=True).max() if is_high else s.rolling(2 * k + 1, center=True).min()
    ).to_numpy()
    # strictly beyond the k bars to the right (breaks ties leftward-in-window)
    right = (
        s[::-1].rolling(k).max()[::-1].shift(-1) if is_high else s[::-1].rolling(k).min()[::-1].shift(-1)
    ).to_numpy()
    if is_high:
        mask = (values == window_extreme) & (values > right)
    else:
        mask = (values == window_extreme) & (values < right)
    mask &= ~np.isnan(window_extreme)
    return np.flatnonzero(mask)


def detect_swings(candles: Candles, k: int = 3) -> list[Swing]:
    """Detect all confirmed fractal swings, sorted by pivot index.

    Each swing's ``confirm_index`` is ``index + k``.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    swings: list[Swing] = []
    for p in _pivots(candles.high, k, is_high=True):
        swings.append(Swing(index=int(p), price=float(candles.high[p]), kind=BULL, confirm_index=int(p + k)))
    for p in _pivots(candles.low, k, is_high=False):
        swings.append(Swing(index=int(p), price=float(candles.low[p]), kind=BEAR, confirm_index=int(p + k)))
    swings.sort(key=lambda s: (s.index, s.kind))
    return swings
