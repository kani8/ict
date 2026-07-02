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
from ..detectors.killzones import BY_NAME, ET_BY_NAME, in_killzone
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

        if cfg.use_htf_bias:
            self.bias, self.htf_eq, self.htf_pools = self._htf_context(cfg.htf_multiplier)
        else:
            self.bias = np.zeros(len(candles), dtype=int)
            self.htf_eq = np.full(len(candles), np.nan)
            self.htf_pools = []
        self.bias2 = (self._htf_context(cfg.bias_htf2_multiplier)[0]
                      if cfg.bias_htf2_multiplier else None)
        if cfg.bias_mode == "narrative":
            # V3: the narrative engine's weighted factor vote replaces the
            # structure-direction bias (dual-TF agreement is folded into its
            # structure factors, so bias2 is redundant here)
            from .narrative import NarrativeEngine

            self.narrative = NarrativeEngine(
                candles, swing_k=cfg.swing_k,
                mtf_multiplier=cfg.htf_multiplier,
                htf_multiplier=cfg.bias_htf2_multiplier or 96,
                eq_tol_atr=cfg.eq_tol_atr, min_gap_atr=cfg.min_gap_atr,
                atr_period=cfg.atr_period, ipda_windows=cfg.ipda_windows,
                ipda_hold_days=cfg.ipda_hold_days,
                dol_lookback_days=cfg.dol_lookback_days,
                weights=cfg.narrative_weights,
                min_conviction=cfg.narrative_min_conviction,
            )
            self.bias = self.narrative.bias
            self.bias2 = None
        elif cfg.bias_mode != "structure":
            raise ValueError("bias_mode must be 'structure' or 'narrative'")

        if cfg.use_killzones:
            table = ET_BY_NAME if cfg.killzone_tz != "UTC" else BY_NAME
            zones = [table[name] for name in cfg.killzones]
            self.kz_mask = in_killzone(candles.ts, zones, cfg.killzone_tz)
        else:
            self.kz_mask = np.ones(len(candles), dtype=bool)

        if cfg.avoid_news:
            from ..data.news import blackout_mask, default_events, load_news_csv, news_day_mask

            events = (load_news_csv(cfg.news_csv) if cfg.news_csv
                      else default_events(int(candles.ts[0]),
                                          int(candles.ts[-1]) + candles.timeframe_s))
            self.news_mask = blackout_mask(candles.ts, events,
                                           cfg.news_before_min, cfg.news_after_min)
            if cfg.news_day_blackout:
                self.news_mask |= news_day_mask(candles.ts, events)
        else:
            self.news_mask = np.zeros(len(candles), dtype=bool)

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
        self._pending_poi_death: int = -1
        self._await: dict | None = None   # confirmation-mode staged setup

        # setup funnel: where candidate signals die, for over-gating diagnosis
        self.funnel = {
            "signals": 0,             # sweep-armed structure breaks considered
            "rejected_bias": 0,
            "rejected_bias2": 0,
            "rejected_discount": 0,
            "rejected_draw": 0,
            "rejected_time": 0,       # killzone or news blackout
            "staged_attempts": 0,
            "rejected_no_poi": 0,
            "rejected_ote": 0,
            "rejected_geometry": 0,   # stop/risk/qty sanity failures
            "placed_limit": 0,
            "placed_await": 0,
            "await_triggered": 0,
            "await_abandoned": 0,     # expiry, POI death, or stop violation
        }

    # ------------------------------------------------------------------

    def _htf_context(self, multiplier: int) -> tuple[np.ndarray, np.ndarray, list]:
        """Higher-timeframe judgment layer, per base bar and lookahead-safe.

        Returns ``(bias, equilibrium, pools)``:

        * bias — direction of the last completed HTF structure event;
        * equilibrium — midpoint of the HTF dealing range (most recent
          confirmed HTF swing high and low), for premium/discount gating;
        * pools — HTF liquidity pools as ``(side, level, confirm_base,
          taken_base)`` tuples, confirm/taken mapped through HTF-bar closes
          so nothing is visible before it is knowable on the base series.

        Everything an HTF bar reveals affects base bars strictly *after*
        that HTF bar's final base bar.
        """
        htf, last_base = resample(self.candles, multiplier)
        htf_swings = detect_swings(htf, self.cfg.swing_k)
        htf_events = detect_structure(htf, htf_swings)
        htf_pools = detect_liquidity_pools(htf, htf_swings, self.cfg.eq_tol_atr,
                                           self.cfg.atr_period)
        n = len(self.candles)
        bias = np.zeros(n, dtype=int)
        eq = np.full(n, np.nan)

        cur_dir = 0
        cur_eq = np.nan
        ref_hi: float | None = None
        ref_lo: float | None = None
        by_confirm = sorted(htf_swings, key=lambda s: s.confirm_index)
        si = ei = 0
        for k in range(len(htf)):
            start = int(last_base[k - 1]) + 1 if k > 0 else 0
            bias[start : int(last_base[k]) + 1] = cur_dir
            eq[start : int(last_base[k]) + 1] = cur_eq
            while si < len(by_confirm) and by_confirm[si].confirm_index <= k:
                s = by_confirm[si]
                if s.kind == BULL:
                    ref_hi = s.price
                else:
                    ref_lo = s.price
                si += 1
            while ei < len(htf_events) and htf_events[ei].index <= k:
                cur_dir = htf_events[ei].direction
                ei += 1
            if ref_hi is not None and ref_lo is not None:
                cur_eq = 0.5 * (ref_hi + ref_lo)
        if len(htf):
            bias[int(last_base[-1]) + 1 :] = cur_dir
            eq[int(last_base[-1]) + 1 :] = cur_eq

        pools = [
            (p.side, p.level, int(last_base[p.confirm_index]),
             int(last_base[p.taken_index]) if p.taken_index != -1 else -1)
            for p in htf_pools
        ]
        return bias, eq, pools

    def _draw_exists(self, direction: int, i: int) -> bool:
        """Is there an untaken HTF pool beyond price to draw toward?"""
        c = float(self.candles.close[i])
        for side, level, confirm_base, taken_base in self.htf_pools:
            if side != direction or confirm_base > i:
                continue
            if taken_base != -1 and taken_base <= i:
                continue
            if (direction == BULL and level > c) or (direction == BEAR and level < c):
                return True
        return False

    # ------------------------------------------------------------------

    def on_bar(self, i: int, broker: Broker) -> None:
        cfg = self.cfg

        # 0. a resting order whose POI zone died this bar is stale: the fill
        #    engine ran first this bar, so if the order were reachable it
        #    would already be filled — cancel the leftover
        if (self._pending_order_id is not None
                and self._pending_poi_death != -1 and i >= self._pending_poi_death):
            broker.cancel(self._pending_order_id)
            self._pending_order_id = None
            self._pending_poi_death = -1

        # 1. arm setups from sweeps confirmed at this bar
        for pool in self._sweeps_at.get(i, ()):  # pool.side BEAR = sell-side purge
            direction = BULL if pool.side == BEAR else BEAR
            wick = float(self.candles.low[i]) if direction == BULL else float(self.candles.high[i])
            self._armed.append(_ArmedSweep(direction=direction, bar=i, wick=wick))

        # drop stale sweeps
        self._armed = [a for a in self._armed if i - a.bar <= cfg.sweep_to_mss_bars]

        # 2. manage an open position (breakeven trail), nothing else while in it
        if broker.position is not None:
            if self._await is not None:
                self.funnel["await_abandoned"] += 1
                self._await = None
            self._manage(i, broker)
            return

        # 2b. confirmation mode: a staged setup waits for touch + confirming close
        if self._await is not None:
            self._process_await(i, broker)
            if broker.pending:
                return

        # 3. on a structure break in the sweep's direction, stage the entry
        for ev in self._events_at.get(i, ()):  # close-confirmed at i
            matches = [a for a in self._armed if a.direction == ev.direction]
            if not matches:
                continue
            self.funnel["signals"] += 1
            # bias-dominance gates: the HTF judgment layer must fully agree
            # before any trigger is even considered
            if cfg.use_htf_bias and self.bias[i] != ev.direction:
                self.funnel["rejected_bias"] += 1
                continue
            if self.bias2 is not None and self.bias2[i] != ev.direction:
                self.funnel["rejected_bias2"] += 1
                continue
            if cfg.require_htf_discount:
                eq = self.htf_eq[i]
                c = float(self.candles.close[i])
                if np.isnan(eq) or (ev.direction == BULL and c >= eq) \
                        or (ev.direction == BEAR and c <= eq):
                    self.funnel["rejected_discount"] += 1
                    continue
            if cfg.require_draw and not self._draw_exists(ev.direction, i):
                self.funnel["rejected_draw"] += 1
                continue
            if not self.kz_mask[i] or self.news_mask[i]:
                self.funnel["rejected_time"] += 1
                continue
            self.funnel["staged_attempts"] += 1
            sweep = max(matches, key=lambda a: a.bar)
            self._stage_entry(i, ev.direction, sweep, broker)
            self._armed = [a for a in self._armed if a.direction != ev.direction]
            break

    # ------------------------------------------------------------------

    def _manage(self, i: int, broker: Broker) -> None:
        """Move the stop to entry once the trade has run ``breakeven_r`` R."""
        cfg = self.cfg
        p = broker.position
        if cfg.breakeven_r <= 0 or p is None or p.initial_sl <= 0:
            return
        risk = abs(p.entry_price - p.initial_sl)
        if risk <= 0:
            return
        unrealized = p.side * (float(self.candles.close[i]) - p.entry_price)
        if unrealized >= cfg.breakeven_r * risk:
            if p.side == BULL and p.sl < p.entry_price:
                p.sl = p.entry_price
            elif p.side == BEAR and (p.sl > p.entry_price or p.sl == 0):
                p.sl = p.entry_price

    def _process_await(self, i: int, broker: Broker) -> None:
        """Trigger, keep, or drop the confirmation-mode setup at bar i's close."""
        a = self._await
        assert a is not None
        if i > a["expiry"] or (a["death"] != -1 and i >= a["death"]):
            self.funnel["await_abandoned"] += 1
            self._await = None
            return
        c = float(self.candles.close[i])
        direction = a["direction"]
        if direction == BULL:
            violated = c <= a["stop"]
            touched = float(self.candles.low[i]) <= a["trigger"]
            confirmed = c > a["trigger"]
        else:
            violated = c >= a["stop"]
            touched = float(self.candles.high[i]) >= a["trigger"]
            confirmed = c < a["trigger"]
        if violated:
            self.funnel["await_abandoned"] += 1
            self._await = None
            return
        if not (touched and confirmed) or self.news_mask[i]:
            return  # keep waiting

        stop = a["stop"]
        risk = (c - stop) if direction == BULL else (stop - c)
        if risk <= 0:
            self.funnel["await_abandoned"] += 1
            self._await = None
            return
        target = self._liquidity_target(direction, i, c, risk)
        equity = broker.equity
        qty = (equity * self.cfg.risk_pct / 100.0) / risk
        qty = min(qty, equity * self.cfg.max_leverage / c)
        if qty <= 0:
            self.funnel["await_abandoned"] += 1
            self._await = None
            return
        broker.submit(Order(side=direction, qty=qty, type="market",
                            sl=stop, tp=target,
                            tag=f"smc_confirm_{'long' if direction == BULL else 'short'}"))
        self.funnel["await_triggered"] += 1
        self._await = None

    # ------------------------------------------------------------------

    def _find_poi(self, direction: int, s: int, m: int) -> tuple[float, float, int] | None:
        """Freshest live POI created by the displacement leg.

        Returns ``(zone_low, zone_high, death_index)`` where ``death_index``
        is the (data-determined) bar at which the zone stops being valid —
        the FVG's full fill, or the order block's first touch or close-through
        — or -1 if that never happens.  Zones already dead at the decision
        bar ``m`` are skipped; ``death_index`` lets the caller cancel a
        resting order the moment the zone dies later (knowable only at that
        bar's close, so acting on ``i >= death_index`` is causal).
        """
        for kind in self.cfg.poi_priority:
            if kind == "ifvg":
                # inverted gap: an opposite-direction FVG that the displacement
                # leg closed through now acts as support/resistance
                cands = [g for g in self.fvgs
                         if g.direction == -direction and g.invert_index != -1
                         and s < g.invert_index <= m
                         and (g.invert_fail_index == -1 or g.invert_fail_index > m)]
                if cands:
                    g = max(cands, key=lambda g: g.invert_index)
                    return g.low, g.high, g.invert_fail_index
            elif kind == "fvg":
                cands = [g for g in self.fvgs
                         if g.direction == direction and s < g.confirm_index <= m
                         and (g.fill_index == -1 or g.fill_index > m)]
                if cands:
                    g = cands[-1]
                    return g.low, g.high, g.fill_index
            elif kind == "ob":
                cands = [b for b in self.order_blocks
                         if b.direction == direction and s <= b.created_index <= m
                         and (b.mitigated_index == -1 or b.mitigated_index > m)
                         and (b.invalidated_index == -1 or b.invalidated_index > m)]
                if cands:
                    b = cands[-1]
                    death = min(x for x in (b.mitigated_index, b.invalidated_index)
                                if x != -1) if (b.mitigated_index, b.invalidated_index) != (-1, -1) else -1
                    return b.low, b.high, death
        return None

    def _stage_entry(self, m: int, direction: int, sweep: _ArmedSweep, broker: Broker) -> None:
        cfg = self.cfg
        lo = float(np.min(self.candles.low[sweep.bar : m + 1]))
        hi = float(np.max(self.candles.high[sweep.bar : m + 1]))
        leg = hi - lo
        if leg <= 0:
            self.funnel["rejected_geometry"] += 1
            return

        poi = self._find_poi(direction, sweep.bar, m)
        if poi is None:
            self.funnel["rejected_no_poi"] += 1
            return
        poi_lo, poi_hi, poi_death = poi

        if direction == BULL:
            entry = poi_hi
            band_hi = hi - 0.62 * leg   # shallowest acceptable retrace
            band_lo = hi - 0.79 * leg
            if cfg.require_ote:
                entry = min(entry, band_hi)
                if entry < band_lo or poi_lo > band_hi:
                    self.funnel["rejected_ote"] += 1
                    return
            if cfg.require_discount and entry > lo + 0.5 * leg:
                self.funnel["rejected_ote"] += 1
                return
            stop = sweep.wick - cfg.stop_buffer_atr * self.atr[m]
            if entry <= stop:
                self.funnel["rejected_geometry"] += 1
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
                    self.funnel["rejected_ote"] += 1
                    return
            if cfg.require_discount and entry < hi - 0.5 * leg:
                self.funnel["rejected_ote"] += 1
                return
            stop = sweep.wick + cfg.stop_buffer_atr * self.atr[m]
            if entry >= stop:
                self.funnel["rejected_geometry"] += 1
                return
            risk = stop - entry
            target = self._liquidity_target(direction, m, entry, risk)

        equity = broker.equity
        qty = (equity * cfg.risk_pct / 100.0) / risk
        qty = min(qty, equity * cfg.max_leverage / entry)
        if qty <= 0:
            self.funnel["rejected_geometry"] += 1
            return

        if cfg.entry_confirmation:
            # faithful "wait for the retest + confirming close" entry: no
            # resting limit — arm a watcher that enters at market only after
            # price trades into the zone and closes back on the right side
            self._await = {
                "direction": direction,
                "trigger": entry,
                "stop": stop,
                "expiry": m + cfg.order_expiry_bars,
                "death": poi_death,
            }
            self.funnel["placed_await"] += 1
            return

        if self._pending_order_id is not None:
            broker.cancel(self._pending_order_id)
        self._pending_order_id = broker.submit(
            Order(side=direction, qty=qty, type="limit", price=entry,
                  sl=stop, tp=target, expiry_index=m + cfg.order_expiry_bars,
                  tag=f"smc_{'long' if direction == BULL else 'short'}")
        )
        self._pending_poi_death = poi_death
        self.funnel["placed_limit"] += 1

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
