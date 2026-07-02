"""Liquidity pools (resting stops beyond swing extremes) and how they get taken.

Every confirmed swing high seeds a buy-side pool; every swing low a
sell-side pool.  A swing whose price sits within ``eq_tol_atr * ATR`` of a
still-intact pool additionally spawns a *merged* pool snapshot (equal
highs / equal lows — engineered liquidity) whose level is the cluster
extreme and whose confirm_index is the newest member's confirmation.

Snapshots are append-only on purpose: mutating an existing pool when a
later swing joins the cluster would rewrite what was knowable at earlier
bars and break prefix consistency (a form of lookahead).  Consumers see
every snapshot from its own confirm_index onward.

The first bar that trades through a pool's level after confirmation
resolves it:

* close back inside the level  -> "sweep"  (stop hunt / turtle soup)
* close through the level      -> "run"    (continuation)

Both classifications are knowable at that bar's close.  A pool is
considered consumed after its first take.
"""

from __future__ import annotations

import numpy as np

from ..core import BEAR, BULL, Candles, LiquidityPool, Swing, atr


def detect_liquidity_pools(
    candles: Candles,
    swings: list[Swing],
    eq_tol_atr: float = 0.25,
    atr_period: int = 14,
) -> list[LiquidityPool]:
    h, l, c = candles.high, candles.low, candles.close
    n = len(candles)
    a = atr(candles, atr_period)

    pools: list[LiquidityPool] = []
    latest: dict[int, list[LiquidityPool]] = {BULL: [], BEAR: []}  # merge candidates

    def resolve(pool: LiquidityPool) -> None:
        start = pool.confirm_index + 1
        if start >= n:
            return
        if pool.side == BULL:
            hit = np.flatnonzero(h[start:n] > pool.level)
        else:
            hit = np.flatnonzero(l[start:n] < pool.level)
        if not len(hit):
            return
        j = int(hit[0] + start)
        pool.taken_index = j
        if pool.side == BULL:
            pool.taken_kind = "sweep" if c[j] <= pool.level else "run"
        else:
            pool.taken_kind = "sweep" if c[j] >= pool.level else "run"

    for s in sorted(swings, key=lambda x: (x.confirm_index, x.index)):
        tol = eq_tol_atr * a[s.index]
        bucket = latest[s.kind]

        new = LiquidityPool(side=s.kind, level=s.price,
                            swing_indices=[s.index], confirm_index=s.confirm_index)
        merged_from: LiquidityPool | None = None
        for pool in bucket:
            intact = pool.taken_index == -1 or pool.taken_index > s.index
            if intact and abs(s.price - pool.level) <= tol:
                merged_from = pool
                break
        if merged_from is not None:
            new.swing_indices = merged_from.swing_indices + [s.index]
            new.level = (max(merged_from.level, s.price) if s.kind == BULL
                         else min(merged_from.level, s.price))
            new.confirm_index = max(merged_from.confirm_index, s.confirm_index)
            bucket.remove(merged_from)  # only the newest snapshot keeps merging
        resolve(new)
        pools.append(new)
        bucket.append(new)
        # keep the merge window small: drop candidates long since resolved
        latest[s.kind] = [p for p in bucket if p.taken_index == -1 or p.taken_index > s.index]

    pools.sort(key=lambda p: p.confirm_index)
    return pools
