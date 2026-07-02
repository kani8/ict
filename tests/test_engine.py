
import pytest

from ict_backtest.core import BEAR, BULL
from ict_backtest.engine import Backtester, CostModel, Order

from conftest import make_candles

NO_COST = CostModel(spread_bps=0.0, commission_bps=0.0, slippage_bps=0.0)


class Script:
    """Submits predefined orders at predefined bars."""

    def __init__(self, plan: dict[int, Order]):
        self.plan = plan

    def on_bar(self, i, broker):
        if i in self.plan:
            broker.submit(self.plan[i])


def test_limit_fill_no_same_bar_as_submission():
    ohlc = [
        (100, 101, 98, 100),   # 0: submit here; low touches 99 but must NOT fill
        (100, 100.5, 98.5, 99.5),  # 1: fills at 99
        (99.5, 100, 99, 99.8),
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit", price=99.0)}))
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry_index == 1
    assert t.entry_price == 99.0
    assert t.reason == "eod"


def test_conservative_policy_stops_win_ambiguous_bars():
    ohlc = [
        (100, 100, 100, 100),          # 0: submit market long, sl 95 tp 105
        (100, 100, 100, 100),          # 1: entry at open
        (100, 106, 94, 100),           # 2: touches both -> stop assumed first
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, sl=95.0, tp=105.0)}))
    t = result.trades[0]
    assert t.reason == "sl"
    assert t.exit_price == 95.0
    assert t.r_multiple == pytest.approx(-1.0)

    bt_opt = Backtester(cost=NO_COST, initial_equity=1000, intrabar_policy="optimistic")
    result = bt_opt.run(candles, Script({0: Order(side=BULL, qty=1.0, sl=95.0, tp=105.0)}))
    t = result.trades[0]
    assert t.reason == "tp"
    assert t.exit_price == 105.0


def test_gap_through_stop_fills_at_open_not_stop():
    ohlc = [
        (100, 100, 100, 100),
        (100, 100, 100, 100),   # long entry at 100
        (90, 91, 89, 90.5),     # gaps far below the 95 stop
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, sl=95.0)}))
    t = result.trades[0]
    assert t.reason == "sl"
    assert t.exit_price == 90.0  # the gapped open, not the stop level
    assert t.pnl == pytest.approx(-10.0)


def test_no_takeprofit_on_entry_bar_under_conservative_policy():
    ohlc = [
        (100, 100, 100, 100),          # submit limit buy 99, tp 101
        (100, 102, 98.5, 101.5),       # fills at 99 and touches 101 same bar
        (101.5, 101.6, 101.4, 101.5),
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(
        candles, Script({0: Order(side=BULL, qty=1.0, type="limit", price=99.0, tp=101.0)})
    )
    t = result.trades[0]
    assert t.entry_index == 1
    assert t.exit_index == 2       # tp granted only on the following bar
    assert t.reason == "tp"


def test_same_bar_stop_on_entry_bar_is_honored():
    ohlc = [
        (100, 100, 100, 100),
        (100, 100.5, 94, 95),   # fills limit 99 then stops at 96 same bar
        (95, 96, 94, 95),
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(
        candles, Script({0: Order(side=BULL, qty=1.0, type="limit", price=99.0, sl=96.0)})
    )
    t = result.trades[0]
    assert t.entry_index == 1 and t.exit_index == 1
    assert t.reason == "sl" and t.exit_price == 96.0


def test_short_side_and_costs():
    cost = CostModel(spread_bps=2.0, commission_bps=1.0, slippage_bps=0.0)
    ohlc = [
        (100, 100, 100, 100),
        (100, 100, 100, 100),   # short entry at open 100
        (90, 90, 90, 90),       # tp 90 -> gap exit at open
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=cost, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BEAR, qty=1.0, tp=90.0)}))
    t = result.trades[0]
    assert t.side == BEAR and t.reason == "tp"
    # sell entry at bid: 100 * (1 - 1bp) ; buy exit at ask: 90 * (1 + 1bp)
    assert t.entry_price == pytest.approx(100 * (1 - 1e-4))
    assert t.exit_price == pytest.approx(90 * (1 + 1e-4))
    expected_pnl = (t.entry_price - t.exit_price) - (t.entry_price + t.exit_price) * 1e-4
    assert t.pnl == pytest.approx(expected_pnl)


def test_order_expiry():
    ohlc = [(100, 100, 100, 100)] * 5 + [(100, 100, 95, 96)]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(
        candles,
        Script({0: Order(side=BULL, qty=1.0, type="limit", price=99.0, expiry_index=3)}),
    )
    assert result.trades == []  # price only reached the limit after expiry


def test_equity_curve_consistency():
    ohlc = [
        (100, 100, 100, 100),
        (100, 100, 100, 100),
        (100, 110, 100, 110),
        (110, 112, 104, 105),   # tp 111 hit intrabar
        (105, 106, 104, 105),
    ]
    candles = make_candles(ohlc)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=2.0, tp=111.0)}))
    t = result.trades[0]
    assert t.reason == "tp" and t.pnl == pytest.approx(22.0)
    assert result.equity_curve[2] == pytest.approx(1020.0)  # marked at close 110
    assert result.final_equity == pytest.approx(1022.0)
