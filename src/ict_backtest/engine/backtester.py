"""Event-driven bar backtester with pessimistic intrabar assumptions.

Accuracy rules baked in:

* Orders placed on bar i can fill no earlier than bar i+1 (decisions are
  made on closed bars only).
* Intrabar ambiguity: if a bar touches both stop and target, the stop is
  assumed to fill first ("conservative" policy — the default). Backtests
  that pass under this assumption are robust to intrabar path uncertainty.
* Gaps: exits through a gapped open fill at the open, not at the level.
* Costs: half-spread on every fill, commission per side, extra slippage
  on stop/market fills (limit fills are assumed at the limit).

The strategy interacts only through the Broker facade, which exposes no
future data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ..core import BULL, Candles


@dataclass(slots=True)
class CostModel:
    spread_bps: float = 1.0      # full spread; half paid per fill
    commission_bps: float = 2.0  # per side, on notional
    slippage_bps: float = 1.0    # on stop/market fills only

    def fill_price(self, price: float, side: int, aggressive: bool) -> float:
        adj = self.spread_bps / 2.0 + (self.slippage_bps if aggressive else 0.0)
        return price * (1.0 + side * adj / 1e4)

    def commission(self, notional: float) -> float:
        return abs(notional) * self.commission_bps / 1e4


@dataclass(slots=True)
class Order:
    side: int                 # BULL = long entry, BEAR = short entry
    qty: float
    type: str = "market"      # "market" | "limit" | "stop"
    price: float = 0.0        # limit/stop trigger price
    sl: float = 0.0
    tp: float = 0.0
    expiry_index: int = -1    # last bar index at which the order may fill
    tag: str = ""
    id: int = -1


@dataclass(slots=True)
class Position:
    side: int
    qty: float
    entry_price: float
    entry_index: int
    sl: float
    tp: float
    tag: str = ""
    entry_commission: float = 0.0


@dataclass(slots=True)
class Trade:
    side: int
    qty: float
    entry_index: int
    entry_price: float
    exit_index: int
    exit_price: float
    pnl: float                # net of costs
    r_multiple: float         # pnl / initial risk (0 risk -> nan)
    reason: str               # "sl" | "tp" | "eod" | "strategy"
    tag: str = ""

    @property
    def holding_bars(self) -> int:
        return self.exit_index - self.entry_index


class Strategy(Protocol):
    def on_bar(self, i: int, broker: "Broker") -> None: ...


class Broker:
    """Order/position facade handed to strategies. No future data escapes."""

    def __init__(self, candles: Candles, cost: CostModel, initial_equity: float) -> None:
        self._candles = candles
        self._cost = cost
        self.cash = initial_equity
        self.initial_equity = initial_equity
        self.position: Position | None = None
        self.pending: dict[int, Order] = {}
        self.trades: list[Trade] = []
        self._next_id = 0
        self._i = 0  # current bar, set by the backtester

    # -- strategy-facing API -------------------------------------------------

    @property
    def equity(self) -> float:
        if self.position is None:
            return self.cash
        p = self.position
        return self.cash + p.side * p.qty * (self._candles.close[self._i] - p.entry_price)

    def submit(self, order: Order) -> int:
        order.id = self._next_id
        self._next_id += 1
        self.pending[order.id] = order
        return order.id

    def cancel(self, order_id: int) -> None:
        self.pending.pop(order_id, None)

    def cancel_all(self) -> None:
        self.pending.clear()

    def close_position(self) -> None:
        """Market-close the open position at the next bar's open."""
        if self.position is not None:
            self._close_at_next_open = True

    _close_at_next_open: bool = False

    # -- engine internals ----------------------------------------------------

    def _exit(self, i: int, price: float, aggressive: bool, reason: str) -> None:
        p = self.position
        assert p is not None
        fill = self._cost.fill_price(price, -p.side, aggressive)
        gross = p.side * p.qty * (fill - p.entry_price)
        exit_commission = self._cost.commission(fill * p.qty)
        self.cash += gross - exit_commission
        # trade pnl carries both commissions (entry's already left the cash)
        pnl = gross - exit_commission - p.entry_commission
        risk = abs(p.entry_price - p.sl) * p.qty if p.sl > 0 else 0.0
        self.trades.append(
            Trade(side=p.side, qty=p.qty, entry_index=p.entry_index, entry_price=p.entry_price,
                  exit_index=i, exit_price=fill, pnl=pnl,
                  r_multiple=pnl / risk if risk > 0 else float("nan"),
                  reason=reason, tag=p.tag)
        )
        self.position = None

    def _enter(self, i: int, order: Order, price: float, aggressive: bool) -> None:
        fill = self._cost.fill_price(price, order.side, aggressive)
        commission = self._cost.commission(fill * order.qty)
        self.cash -= commission
        self.position = Position(side=order.side, qty=order.qty, entry_price=fill,
                                 entry_index=i, sl=order.sl, tp=order.tp, tag=order.tag,
                                 entry_commission=commission)


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: np.ndarray   # equity at each bar close
    candles: Candles
    initial_equity: float

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve[-1])

    @property
    def total_return(self) -> float:
        return self.final_equity / self.initial_equity - 1.0


class Backtester:
    def __init__(
        self,
        cost: CostModel | None = None,
        initial_equity: float = 100_000.0,
        intrabar_policy: str = "conservative",
    ) -> None:
        if intrabar_policy not in ("conservative", "optimistic"):
            raise ValueError("intrabar_policy must be 'conservative' or 'optimistic'")
        self.cost = cost or CostModel()
        self.initial_equity = initial_equity
        self.intrabar_policy = intrabar_policy

    def run(self, candles: Candles, strategy: Strategy) -> BacktestResult:
        broker = Broker(candles, self.cost, self.initial_equity)
        n = len(candles)
        o, h, l, c = candles.open, candles.high, candles.low, candles.close
        equity = np.empty(n)

        for i in range(n):
            broker._i = i
            # 1. strategy-requested market close fills at this bar's open
            if broker.position is not None and broker._close_at_next_open:
                broker._exit(i, float(o[i]), aggressive=True, reason="strategy")
                broker._close_at_next_open = False
            # 2. resolve SL/TP on an existing position
            if broker.position is not None:
                self._resolve_exits(broker, i, o[i], h[i], l[i])
            # 3. try to fill pending orders (placed on earlier bars)
            self._fill_pending(broker, i, o[i], h[i], l[i])
            # 4. a fill this bar may already be stopped/targeted this bar
            if broker.position is not None and broker.position.entry_index == i:
                self._resolve_exits(broker, i, None, h[i], l[i], entry_bar=True)
            # 5. mark to market, then let the strategy act on the closed bar
            equity[i] = broker.equity
            strategy.on_bar(i, broker)

        if broker.position is not None:
            broker._i = n - 1
            broker._exit(n - 1, float(c[-1]), aggressive=True, reason="eod")
            equity[-1] = broker.equity
        return BacktestResult(trades=broker.trades, equity_curve=equity,
                              candles=candles, initial_equity=self.initial_equity)

    # -- fill mechanics -------------------------------------------------------

    def _resolve_exits(self, broker: Broker, i: int, open_: float | None,
                       high: float, low: float, entry_bar: bool = False) -> None:
        # On the entry bar the intrabar path is unknown: under the
        # conservative policy a same-bar take-profit is never granted
        # (the touch may have happened before the fill), while a same-bar
        # stop is always honored.
        p = broker.position
        assert p is not None
        sl, tp = p.sl, p.tp
        if p.side == BULL:
            sl_hit = sl > 0 and low <= sl
            tp_hit = tp > 0 and high >= tp
            sl_gap = open_ is not None and sl > 0 and open_ <= sl
            tp_gap = open_ is not None and tp > 0 and open_ >= tp
        else:
            sl_hit = sl > 0 and high >= sl
            tp_hit = tp > 0 and low <= tp
            sl_gap = open_ is not None and sl > 0 and open_ >= sl
            tp_gap = open_ is not None and tp > 0 and open_ <= tp

        if entry_bar and self.intrabar_policy == "conservative":
            tp_hit = False
            tp_gap = False
        if sl_gap:
            broker._exit(i, open_, aggressive=True, reason="sl")
        elif tp_gap:
            broker._exit(i, open_, aggressive=False, reason="tp")
        elif sl_hit and tp_hit:
            if self.intrabar_policy == "conservative":
                broker._exit(i, sl, aggressive=True, reason="sl")
            else:
                broker._exit(i, tp, aggressive=False, reason="tp")
        elif sl_hit:
            broker._exit(i, sl, aggressive=True, reason="sl")
        elif tp_hit:
            broker._exit(i, tp, aggressive=False, reason="tp")

    def _fill_pending(self, broker: Broker, i: int, open_: float,
                      high: float, low: float) -> None:
        for oid in list(broker.pending):
            order = broker.pending[oid]
            if 0 <= order.expiry_index < i:
                del broker.pending[oid]
                continue
            if broker.position is not None:
                continue  # one position at a time
            filled = False
            if order.type == "market":
                broker._enter(i, order, open_, aggressive=True)
                filled = True
            elif order.type == "limit":
                if order.side == BULL:
                    if open_ <= order.price:
                        broker._enter(i, order, open_, aggressive=False)
                        filled = True
                    elif low <= order.price:
                        broker._enter(i, order, order.price, aggressive=False)
                        filled = True
                else:
                    if open_ >= order.price:
                        broker._enter(i, order, open_, aggressive=False)
                        filled = True
                    elif high >= order.price:
                        broker._enter(i, order, order.price, aggressive=False)
                        filled = True
            elif order.type == "stop":
                if order.side == BULL:
                    if open_ >= order.price:
                        broker._enter(i, order, open_, aggressive=True)
                        filled = True
                    elif high >= order.price:
                        broker._enter(i, order, order.price, aggressive=True)
                        filled = True
                else:
                    if open_ <= order.price:
                        broker._enter(i, order, open_, aggressive=True)
                        filled = True
                    elif low <= order.price:
                        broker._enter(i, order, order.price, aggressive=True)
                        filled = True
            if filled:
                del broker.pending[oid]
