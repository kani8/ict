"""Market-structure tracking: Break of Structure / Market Structure Shift.

Walks the bars once, revealing swings only at their confirm_index, and
emits a StructureEvent whenever a close breaks the most recent confirmed,
unbroken swing:

* break in the direction of the prevailing trend  -> "BOS"
* break against the prevailing trend (CHoCH)       -> "MSS"

The first break of the series (trend unknown) is labeled "BOS".
Events are close-confirmed, so ``confirm_index == index``.
"""

from __future__ import annotations

from ..core import BEAR, BULL, Candles, StructureEvent, Swing


def detect_structure(candles: Candles, swings: list[Swing]) -> list[StructureEvent]:
    events: list[StructureEvent] = []
    by_confirm = sorted(swings, key=lambda s: s.confirm_index)
    si = 0
    ref_high: Swing | None = None
    ref_low: Swing | None = None
    trend = 0

    n = len(candles)
    close = candles.close
    for i in range(n):
        # reveal swings confirmed at this bar's close
        while si < len(by_confirm) and by_confirm[si].confirm_index <= i:
            s = by_confirm[si]
            if s.kind == BULL:
                ref_high = s
            else:
                ref_low = s
            si += 1

        c = close[i]
        if ref_high is not None and c > ref_high.price:
            kind = "MSS" if trend == BEAR else "BOS"
            events.append(
                StructureEvent(index=i, direction=BULL, kind=kind,
                               level=ref_high.price, swing_index=ref_high.index)
            )
            trend = BULL
            ref_high = None
        if ref_low is not None and c < ref_low.price:
            kind = "MSS" if trend == BULL else "BOS"
            events.append(
                StructureEvent(index=i, direction=BEAR, kind=kind,
                               level=ref_low.price, swing_index=ref_low.index)
            )
            trend = BEAR
            ref_low = None
    return events
