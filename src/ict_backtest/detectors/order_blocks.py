"""Order block detection anchored to structure breaks.

For each bullish StructureEvent we locate the origin of the impulse leg
(the lowest low between the broken swing's formation and the break bar)
and mark the last down-close candle in that leg as the bullish order
block; mirrored for bearish events.  The zone becomes tradeable at the
break bar (``created_index``), never earlier.

Lifecycle (all data-determined, path-independent — safe to precompute):
* mitigated_index   — first later bar that trades back into the zone
* invalidated_index — first later bar that *closes* through the zone;
                      from then on the zone is a breaker for the
                      opposite direction.
"""

from __future__ import annotations

import numpy as np

from ..core import BULL, Candles, OrderBlock, StructureEvent


def _first_true(mask: np.ndarray, offset: int) -> int:
    idx = np.flatnonzero(mask)
    return int(idx[0] + offset) if len(idx) else -1


def detect_order_blocks(
    candles: Candles,
    events: list[StructureEvent],
    max_leg_bars: int = 100,
) -> list[OrderBlock]:
    o, h, l, c = candles.open, candles.high, candles.low, candles.close
    n = len(candles)
    blocks: list[OrderBlock] = []

    for ev in events:
        b = ev.index
        start = max(0, b - max_leg_bars, ev.swing_index)
        if ev.direction == BULL:
            origin = start + int(np.argmin(l[start : b + 1]))
            # last down-close candle in [origin, b); fall back to the origin bar
            cand = [j for j in range(origin, b) if c[j] < o[j]]
            ob_idx = cand[-1] if cand else origin
            zone_lo, zone_hi = float(l[ob_idx]), float(h[ob_idx])
            after = b + 1
            mitigated = _first_true(l[after:n] <= zone_hi, after) if after < n else -1
            invalidated = _first_true(c[after:n] < zone_lo, after) if after < n else -1
        else:
            origin = start + int(np.argmax(h[start : b + 1]))
            cand = [j for j in range(origin, b) if c[j] > o[j]]
            ob_idx = cand[-1] if cand else origin
            zone_lo, zone_hi = float(l[ob_idx]), float(h[ob_idx])
            after = b + 1
            mitigated = _first_true(h[after:n] >= zone_lo, after) if after < n else -1
            invalidated = _first_true(c[after:n] > zone_hi, after) if after < n else -1

        blocks.append(
            OrderBlock(
                index=ob_idx,
                low=zone_lo,
                high=zone_hi,
                direction=ev.direction,
                created_index=b,
                mitigated_index=mitigated,
                invalidated_index=invalidated,
            )
        )
    return blocks
