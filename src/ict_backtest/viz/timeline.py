"""Narrative timeline: the strategy's state machine, recorded bar by bar.

Runs the *real* SMCStrategy through the *real* Backtester and captures what
the strategy knew and intended at each bar close — bias, conviction, armed
sweeps, resting orders, awaits, open positions — as human-readable status
change-points. This is the data behind the UI's "we are bullish, waiting
for a structure break" box, and because it comes from the same code path
as the backtests, it can't drift from reality.
"""

from __future__ import annotations

from ..core import BULL, Candles
from ..engine import Backtester, Broker, CostModel
from ..strategy import SMCConfig, SMCStrategy


def _fmt(x: float) -> str:
    return f"{x:,.6g}"


class _Recorder(SMCStrategy):
    def __init__(self, candles: Candles, config: SMCConfig) -> None:
        super().__init__(candles, config)
        self.status_points: list[tuple[int, str]] = []
        self._last_status = ""

    def _status(self, i: int, broker: Broker) -> str:
        p = broker.position
        if p is not None:
            side = "LONG" if p.side == BULL else "SHORT"
            return f"{side} open — SL {_fmt(p.sl)} · TP {_fmt(p.tp)}"
        if self._await is not None:
            a = self._await
            side = "long" if a["direction"] == BULL else "short"
            return (f"Awaiting retest ({side}) — trigger {_fmt(a['trigger'])}, "
                    f"stop {_fmt(a['stop'])}, expires bar {a['expiry']}")
        if broker.pending:
            o = next(iter(broker.pending.values()))
            side = "long" if o.side == BULL else "short"
            return f"Resting limit ({side}) @ {_fmt(o.price)} — SL {_fmt(o.sl)} · TP {_fmt(o.tp)}"
        if self._armed:
            dirs = {a.direction for a in self._armed}
            parts = []
            if BULL in dirs:
                parts.append("sell-side swept — waiting for bullish structure break")
            if -BULL in dirs:
                parts.append("buy-side swept — waiting for bearish structure break")
            return "Armed: " + "; ".join(parts)
        b = int(self.bias[i])
        if b == BULL:
            return "Bullish narrative — hunting a sell-side sweep"
        if b == -BULL:
            return "Bearish narrative — hunting a buy-side sweep"
        return "No conviction — standing aside"

    def on_bar(self, i: int, broker: Broker) -> None:
        super().on_bar(i, broker)
        status = self._status(i, broker)
        if status != self._last_status:
            self.status_points.append((i, status))
            self._last_status = status


def build_timeline(candles: Candles, config: SMCConfig,
                   cost: CostModel | None = None) -> dict:
    """Backtest replay -> {bias, score, factors, status, trades, funnel}."""
    strat = _Recorder(candles, config)
    bt = Backtester(cost=cost or CostModel(), initial_equity=100_000.0)
    result = bt.run(candles, strat)

    out: dict = {
        "bias": [int(b) for b in strat.bias],
        "status": [[i, s] for i, s in strat.status_points],
        "trades": [
            [t.entry_index, t.exit_index, int(t.side),
             round(t.entry_price, 6), round(t.exit_price, 6),
             round(t.sl, 6), round(t.tp, 6),
             round(t.r_multiple, 3) if t.r_multiple == t.r_multiple else 0.0,
             round(t.pnl, 2), t.reason]
            for t in result.trades
        ],
        "funnel": strat.funnel,
    }
    if getattr(strat, "narrative", None) is not None:
        out["score"] = [round(float(s), 4) for s in strat.narrative.score]
        out["factors"] = {
            name: [round(float(v), 3) for v in arr]
            for name, arr in strat.narrative.factors.items()
        }
    else:
        out["score"] = [float(b) for b in strat.bias]
        out["factors"] = {}
    return out
