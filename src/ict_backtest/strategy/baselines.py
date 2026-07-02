"""Null-model strategies used to judge whether SMC adds real edge.

RandomStrategy enters at random eligible bars (same killzone universe as
the strategy under test), holds for a fixed number of bars, and exits at
market.  Running it many times with different seeds yields the null
distribution for "a strategy that trades this often, this long, at these
times, with no signal".
"""

from __future__ import annotations

import numpy as np

from ..core import BEAR, BULL, Candles
from ..engine import Broker, Order


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
