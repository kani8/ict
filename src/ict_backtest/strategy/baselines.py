"""Null-model strategies used to judge whether SMC adds real edge.

Two nulls with different strengths:

* ``MatchedRandomStrategy`` (the primary control) replays the audited
  strategy's *own realized trades* — same side, same stop/target distances
  in fractional terms, same risk-based sizing — at random times drawn from
  the same eligible (killzone) universe.  Holding period and exposure then
  emerge from the same exit geometry rather than being crudely averaged,
  so the only thing destroyed is the *timing signal*.  If the strategy
  cannot beat this, its entries carry no information beyond their shape.
* ``RandomStrategy`` is a simpler drift control: random entries, fixed
  holding, notional-normalized size.  It answers "does anything at this
  frequency and these hours make money here?" but is NOT exposure- or
  risk-matched to the strategy under test.
"""

from __future__ import annotations

import numpy as np

from ..core import BEAR, BULL, Candles
from ..engine import Broker, Order, Trade


class RandomStrategy:
    def __init__(
        self,
        candles: Candles,
        entry_prob: float,
        holding_bars: int,
        seed: int,
        eligible_mask: np.ndarray | None = None,
        long_prob: float = 0.5,
        risk_pct: float = 1.0,
        stop_atr: np.ndarray | None = None,
        stop_atr_mult: float = 0.0,
    ) -> None:
        self.candles = candles
        self.holding_bars = max(1, holding_bars)
        self.rng = np.random.default_rng(seed)
        self.entry_prob = entry_prob
        self.long_prob = long_prob
        self.risk_pct = risk_pct
        self.mask = eligible_mask if eligible_mask is not None else np.ones(len(candles), bool)
        self._entry_bar: int | None = None

    def on_bar(self, i: int, broker: Broker) -> None:
        if broker.position is not None:
            if self._entry_bar is None:
                self._entry_bar = broker.position.entry_index
            if i - broker.position.entry_index >= self.holding_bars:
                broker.close_position()
            return
        self._entry_bar = None
        if broker.pending:
            return
        if not self.mask[i]:
            return
        if self.rng.random() >= self.entry_prob:
            return
        direction = BULL if self.rng.random() < self.long_prob else BEAR
        price = float(self.candles.close[i])
        qty = broker.equity * self.risk_pct / 100.0 / (price * 0.01)  # notional-normalized
        broker.submit(Order(side=direction, qty=qty, type="market", tag="random"))


class MatchedRandomStrategy:
    """Replays real trade templates (side + SL/TP geometry) at random times.

    Templates come from the audited strategy's closed trades.  Each is
    scheduled at a random eligible bar; when its slot arrives and the book
    is flat, a market order goes out with the stop and target placed at the
    same *fractional* distances from price as the original trade, sized by
    the same fixed-fractional risk rule.  Slots that collide with an open
    position are taken at the next flat eligible bar, so the trade count is
    preserved.
    """

    def __init__(
        self,
        candles: Candles,
        templates: list[Trade],
        seed: int,
        eligible_mask: np.ndarray | None = None,
        risk_pct: float = 1.0,
        max_leverage: float = 5.0,
    ) -> None:
        self.candles = candles
        self.risk_pct = risk_pct
        self.max_leverage = max_leverage
        self.mask = eligible_mask if eligible_mask is not None else np.ones(len(candles), bool)

        rng = np.random.default_rng(seed)
        # (side, stop distance, target distance) as fractions of entry price
        self.templates = [
            (t.side,
             abs(t.entry_price - t.sl) / t.entry_price if t.sl > 0 else 0.0,
             abs(t.tp - t.entry_price) / t.entry_price if t.tp > 0 else 0.0)
            for t in templates
        ]
        rng.shuffle(self.templates)
        eligible = np.flatnonzero(self.mask)
        k = min(len(self.templates), len(eligible))
        self.schedule = np.sort(rng.choice(eligible, size=k, replace=False))
        self._ptr = 0

    def on_bar(self, i: int, broker: Broker) -> None:
        if broker.position is not None or broker.pending:
            return
        if self._ptr >= len(self.schedule):
            return
        if i < self.schedule[self._ptr] or not self.mask[i]:
            return
        side, stop_frac, tp_frac = self.templates[self._ptr]
        self._ptr += 1
        price = float(self.candles.close[i])
        sl = price * (1.0 - side * stop_frac) if stop_frac > 0 else 0.0
        tp = price * (1.0 + side * tp_frac) if tp_frac > 0 else 0.0
        if stop_frac > 0:
            qty = broker.equity * self.risk_pct / 100.0 / (price * stop_frac)
            qty = min(qty, broker.equity * self.max_leverage / price)
        else:
            qty = broker.equity / price
        if qty <= 0:
            return
        broker.submit(Order(side=side, qty=qty, type="market", sl=sl, tp=tp, tag="matched_null"))
