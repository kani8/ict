"""The composed Smart Money Concepts strategy.

Trade sequence (the canonical ICT "2022 model" flow):

1. **Bias** — higher-timeframe structure direction (last HTF BOS/MSS),
   mapped back to base bars through HTF-close confirm indices.
2. **Sweep** — a liquidity pool *against* the bias is purged and price
   closes back inside (stop hunt).  Sell-side sweep arms a long setup,
   buy-side sweep arms a short.
3. **Shift** — a base-timeframe structure break in the bias direction
   within ``sweep_to_mss_bars`` of the sweep confirms displacement.
4. **Retrace entry** — limit order at the FVG (or order block) left by the
   displacement leg, required to sit in the OTE band (62-79% retracement)
   and on the discount/premium side of the leg.
5. **Risk** — stop beyond the sweep wick plus an ATR buffer; target the
   nearest opposing liquidity pool offering at least ``min_rr``, else a
   fixed ``default_rr`` multiple.  Fixed fractional position sizing.

Everything the strategy reads is gated by confirm indices computed by the
detectors, so no decision uses information from the future.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core import BEAR, BULL, Candles, atr, resample
from ..detectors import (
    detect_fvgs,
    detect_liquidity_pools,
    detect_order_blocks,
    detect_structure,
    detect_swings,
)
from ..detectors.killzones import BY_NAME, in_killzone
from ..engine import Broker, Order
from .config import SMCConfig


@dataclass(slots=True)
class _ArmedSweep:
    direction: int      # trade direction this sweep arms (BULL after sell-side sweep)
    bar: int            # bar at which the sweep resolved (close-confirmed)
    wick: float         # sweep extreme (low of the purge bar for longs)


class SMCStrategy:
    def __init__(self, candles: Candles, config: SMCConfig | None = None) -> None:
        self.cfg = config or SMCConfig()
        self.candles = candles
        cfg = self.cfg

        self.atr = atr(candles, cfg.atr_period)
        swings = detect_swings(candles, cfg.swing_k)
        self.events = detect_structure(candles, swings)
        self.order_blocks = detect_order_blocks(candles, self.events, cfg.max_leg_bars)
        self.fvgs = detect_fvgs(candles, cfg.min_gap_atr, cfg.atr_period)
        self.pools = detect_liquidity_pools(candles, swings, cfg.eq_tol_atr, cfg.atr_period)

        self.bias = self._compute_bias() if cfg.use_htf_bias else np.zeros(len(candles), dtype=int)

        if cfg.use_killzones:
            zones = [BY_NAME[name] for name in cfg.killzones]
            self.kz_mask = in_killzone(candles.ts, zones)
        else:
            self.kz_mask = np.ones(len(candles), dtype=bool)

        # per-bar lookups
        self._sweeps_at: dict[int, list] = {}
        for p in self.pools:
            if p.taken_kind == "sweep":
                self._sweeps_at.setdefault(p.taken_index, []).append(p)
        self._events_at: dict[int, list] = {}
        for ev in self.events:
            self._events_at.setdefault(ev.index, []).append(ev)

        self._armed: list[_ArmedSweep] = []
        self._pending_order_id: int | None = None

    # ------------------------------------------------------------------

    def _compute_bias(self) -> np.ndarray:
        """Direction of the last completed HTF structure event, per base bar."""
        htf, last_base = resample(self.candles, self.cfg.htf_multiplier)
        htf_swings = detect_swings(htf, self.cfg.swing_k)
        htf_events = detect_structure(htf, htf_swings)
        bias = np.zeros(len(self.candles), dtype=int)
        current = 0
        ei = 0
        for k in range(len(htf)):
            start = int(last_base[k - 1]) + 1 if k > 0 else 0
            bias[start : int(last_base[k]) + 1] = current
            # events on HTF bar k become known at that bar's close -> affect
            # base bars strictly after last_base[k]
            while ei < len(htf_events) and htf_events[ei].index <= k:
                current = htf_events[ei].direction
                ei += 1
        if len(htf):
            bias[int(last_base[-1]) + 1 :] = current
        return bias

    # ------------------------------------------------------------------

    def on_bar(self, i: int, broker: Broker) -> None:
        cfg = self.cfg

        # 1. arm setups from sweeps confirmed at this bar
        for pool in self._sweeps_at.get(i, ()):  # pool.side BEAR = sell-side purge
            direction = BULL if pool.side == BEAR else BEAR
            wick = float(self.candles.low[i]) if direction == BULL else float(self.candles.high[i])
            self._armed.append(_ArmedSweep(direction=direction, bar=i, wick=wick))

        # drop stale sweeps
        self._armed = [a for a in self._armed if i - a.bar <= cfg.sweep_to_mss_bars]

        # 2. on a structure break in the sweep's direction, stage the entry
        if broker.position is not None:
            return
        for ev in self._events_at.get(i, ()):  # close-confirmed at i
            matches = [a for a in self._armed if a.direction == ev.direction]
            if not matches:
                continue
            if cfg.use_htf_bias and self.bias[i] != ev.direction:
                continue
            if not self.kz_mask[i]:
                continue
            sweep = max(matches, key=lambda a: a.bar)
            self._stage_entry(i, ev.direction, sweep, broker)
            self._armed = [a for a in self._armed if a.direction != ev.direction]
            break

    # ------------------------------------------------------------------

    def _find_poi(self, direction: int, s: int, m: int) -> tuple[float, float] | None:
        """Zone (low, high) of the freshest POI created by the displacement leg."""
        for kind in self.cfg.poi_priority:
            if kind == "fvg":
                cands = [g for g in self.fvgs
                         if g.direction == direction and s < g.confirm_index <= m
                         and (g.fill_index == -1 or g.fill_index > m)]
                if cands:
                    g = cands[-1]
                    return g.low, g.high
            elif kind == "ob":
                cands = [b for b in self.order_blocks
                         if b.direction == direction and s <= b.created_index <= m]
                if cands:
                    b = cands[-1]
                    return b.low, b.high
        return None

    def _stage_entry(self, m: int, direction: int, sweep: _ArmedSweep, broker: Broker) -> None:
        cfg = self.cfg
        lo = float(np.min(self.candles.low[sweep.bar : m + 1]))
        hi = float(np.max(self.candles.high[sweep.bar : m + 1]))
        leg = hi - lo
        if leg <= 0:
            return

        poi = self._find_poi(direction, sweep.bar, m)
        if poi is None:
            return
        poi_lo, poi_hi = poi

        if direction == BULL:
            entry = poi_hi
            band_hi = hi - 0.62 * leg   # shallowest acceptable retrace
            band_lo = hi - 0.79 * leg
            if cfg.require_ote:
                entry = min(entry, band_hi)
                if entry < band_lo or poi_lo > band_hi:
                    return
            if cfg.require_discount and entry > lo + 0.5 * leg:
                return
            stop = sweep.wick - cfg.stop_buffer_atr * self.atr[m]
            if entry <= stop:
                return
            risk = entry - stop
            target = self._liquidity_target(direction, m, entry, risk)
        else:
            entry = poi_lo
            band_lo = lo + 0.62 * leg
            band_hi = lo + 0.79 * leg
            if cfg.require_ote:
                entry = max(entry, band_lo)
                if entry > band_hi or poi_hi < band_lo:
                    return
            if cfg.require_discount and entry < hi - 0.5 * leg:
                return
            stop = sweep.wick + cfg.stop_buffer_atr * self.atr[m]
            if entry >= stop:
                return
            risk = stop - entry
            target = self._liquidity_target(direction, m, entry, risk)

        equity = broker.equity
        qty = (equity * cfg.risk_pct / 100.0) / risk
        qty = min(qty, equity * cfg.max_leverage / entry)
        if qty <= 0:
            return

        if self._pending_order_id is not None:
            broker.cancel(self._pending_order_id)
        self._pending_order_id = broker.submit(
            Order(side=direction, qty=qty, type="limit", price=entry,
                  sl=stop, tp=target, expiry_index=m + cfg.order_expiry_bars,
                  tag=f"smc_{'long' if direction == BULL else 'short'}")
        )

    def _liquidity_target(self, direction: int, m: int, entry: float, risk: float) -> float:
        """Nearest live opposing liquidity pool offering >= min_rr, else fixed R."""
        cfg = self.cfg
        if direction == BULL:
            levels = sorted(
                p.level for p in self.pools
                if p.side == BULL and p.confirm_index <= m and p.level > entry
                and (p.taken_index == -1 or p.taken_index > m)
            )
            for level in levels:
                if (level - entry) / risk >= cfg.min_rr:
                    return level
            return entry + cfg.default_rr * risk
        levels = sorted(
            (p.level for p in self.pools
             if p.side == BEAR and p.confirm_index <= m and p.level < entry
             and (p.taken_index == -1 or p.taken_index > m)),
            reverse=True,
        )
        for level in levels:
            if (entry - level) / risk >= cfg.min_rr:
                return level
        return entry - cfg.default_rr * risk
