"""The gold-standard lookahead test: prefix consistency.

Every decision made at bar i may only depend on bars 0..i.  Therefore a
strategy run on candles[:K] must submit *exactly* the same orders at bars
< K as the same strategy run on the full series.  Any divergence means
some artifact or decision leaked information from the future.
"""

import pytest

from ict_backtest.data import synthetic_candles
from ict_backtest.engine import Backtester, Broker, CostModel
from ict_backtest.strategy import SMCConfig, SMCStrategy


class RecordingStrategy(SMCStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submissions: list[tuple] = []

    def on_bar(self, i, broker: Broker):
        before = broker._next_id
        super().on_bar(i, broker)
        for oid in range(before, broker._next_id):
            order = broker.pending.get(oid)
            if order is not None:
                self.submissions.append(
                    (i, order.side, round(order.price, 10), round(order.qty, 10),
                     round(order.sl, 10), round(order.tp, 10), order.expiry_index)
                )


CONFIG = SMCConfig(
    swing_k=3,
    htf_multiplier=8,
    use_killzones=False,   # widest decision surface = strictest test
    require_ote=False,
    require_discount=False,
    use_htf_bias=True,
    min_rr=1.0,
)


@pytest.mark.parametrize("cutoff", [2000, 3500, 5000])
def test_prefix_consistency(cutoff):
    candles = synthetic_candles(n=6000, seed=99, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)

    full = RecordingStrategy(candles, CONFIG)
    bt.run(candles, full)
    full_subs = [s for s in full.submissions if s[0] < cutoff]

    prefix = RecordingStrategy(candles.slice(0, cutoff), CONFIG)
    bt.run(candles.slice(0, cutoff), prefix)

    assert len(full_subs) > 0, "test is vacuous: no orders before the cutoff"
    assert prefix.submissions == full_subs


def test_trades_match_on_prefix():
    """Closed trades before the cutoff must be identical as well."""
    candles = synthetic_candles(n=6000, seed=7, base_vol=0.004)
    cutoff = 4000
    bt = Backtester(cost=CostModel(), initial_equity=100_000)

    res_full = bt.run(candles, SMCStrategy(candles, CONFIG))
    res_prefix = bt.run(candles.slice(0, cutoff), SMCStrategy(candles.slice(0, cutoff), CONFIG))

    def key(t):
        return (t.entry_index, t.exit_index, t.side, round(t.entry_price, 8),
                round(t.exit_price, 8), round(t.pnl, 6), t.reason)

    full_closed = [key(t) for t in res_full.trades if t.exit_index < cutoff - 1]
    prefix_closed = [key(t) for t in res_prefix.trades if t.exit_index < cutoff - 1]
    assert len(full_closed) > 0
    assert prefix_closed == full_closed
