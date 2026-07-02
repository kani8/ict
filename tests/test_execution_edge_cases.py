"""Regression tests for the two execution defects found in the 2ef571d re-audit.

1. Partial intrabar coverage must be treated as missing: a bucket with any
   absent first/middle/last sub-bar cannot prove touch order and must fall
   back to the declared policy (including on entry bars).
2. A marketable entry that gaps through its own stop/target must exit at
   the fill basis, not at the stale level (which booked phantom profit).
"""

import numpy as np
import pytest

from ict_backtest.core import BEAR, BULL, Candles
from ict_backtest.engine import Backtester, CostModel, Order

from conftest import make_candles
from test_engine import NO_COST, Script

BASE_TF = 900
SUB_TF = 300
START = 1_700_000_100 - (1_700_000_100 % BASE_TF)


def sub_candles(slots: list[tuple[int, int, tuple]]) -> Candles:
    """Sub-bars from (base_bar, slot_index, ohlc) triples; omissions = gaps."""
    slots = sorted(slots, key=lambda x: (x[0], x[1]))
    ts = np.asarray([START + b * BASE_TF + j * SUB_TF for b, j, _ in slots], np.int64)
    arr = np.asarray([bar for _, _, bar in slots], float)
    return Candles(ts=ts, open=arr[:, 0], high=arr[:, 1], low=arr[:, 2], close=arr[:, 3],
                   volume=np.ones(len(slots)), timeframe_s=SUB_TF)


FLAT = (100, 100, 100, 100)
AMBIG_BASE = [
    (100, 100, 100, 100),   # 0: submit market long, sl 95 tp 105
    (100, 100, 100, 100),   # 1: entry at open
    (100, 106, 94, 100),    # 2: touches both levels
]
# sub-bars for bar 2 that would prove tp-first — IF coverage were complete
TP_FIRST = [(2, 0, (100, 106, 99, 105)), (2, 1, (105, 105, 100, 101)),
            (2, 2, (101, 102, 94, 100))]
FULL_01 = [(b, j, FLAT) for b in (0, 1) for j in range(3)]


def _run_ambig(sub: Candles):
    candles = make_candles(AMBIG_BASE, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=sub)
    return bt.run(candles, Script({0: Order(side=BULL, qty=1.0, sl=95.0, tp=105.0)}))


def test_complete_bucket_uses_touch_order():
    t = _run_ambig(sub_candles(FULL_01 + TP_FIRST)).trades[0]
    assert t.reason == "tp"     # sanity: with full coverage the override works


@pytest.mark.parametrize("missing_slot", [0, 1, 2],
                         ids=["missing_first", "missing_middle", "missing_last"])
def test_partial_bucket_falls_back_to_policy(missing_slot):
    partial = [s for s in TP_FIRST if s[1] != missing_slot]
    t = _run_ambig(sub_candles(FULL_01 + partial)).trades[0]
    assert t.reason == "sl" and t.exit_price == 95.0


def test_auditor_repro_partial_entry_bar_does_not_suppress_stop():
    """A lone non-stopping sub-bar must not bypass the same-bar stop."""
    base = [
        (100, 100, 100, 100),
        (100, 100.5, 94, 95),   # limit 99 fills; low 94 <= stop 95
        (95, 96, 94, 95),
    ]
    sub = sub_candles([(1, 0, (100, 100.2, 98.8, 99.0))])  # first slot only
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=sub)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit",
                                              price=99.0, sl=95.0)}))
    t = result.trades[0]
    assert t.entry_index == 1 and t.exit_index == 1   # stop honored same bar
    assert t.reason == "sl"


def test_indivisible_timeframes_rejected():
    candles = make_candles(AMBIG_BASE, timeframe_s=BASE_TF, start_ts=START)
    bad = sub_candles([(0, 0, FLAT)])
    bad.timeframe_s = 400  # 900 % 400 != 0
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=bad)
    with pytest.raises(ValueError, match="multiple"):
        bt.run(candles, Script({}))


# -- gap through entry and bracket -------------------------------------------


def test_gap_through_long_entry_and_stop_books_no_phantom_profit():
    base = [
        (100, 100, 100, 100),   # submit limit buy 100, sl 95
        (90, 91, 89, 90.5),     # opens far below both limit and stop
        (90, 91, 89, 90),
    ]
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit",
                                              price=100.0, sl=95.0)}))
    t = result.trades[0]
    assert t.reason == "sl"
    assert t.entry_index == t.exit_index == 1
    assert t.exit_price == 90.0          # fill basis, not the stale 95 level
    assert t.pnl == pytest.approx(0.0)   # zero costs -> flat, never +5


def test_gap_through_short_entry_and_stop_mirrored():
    base = [
        (100, 100, 100, 100),   # submit limit sell 100, sl 105
        (110, 111, 109, 110.5),  # opens far above both limit and stop
        (110, 111, 109, 110),
    ]
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BEAR, qty=1.0, type="limit",
                                              price=100.0, sl=105.0)}))
    t = result.trades[0]
    assert t.reason == "sl"
    assert t.exit_price == 110.0
    assert t.pnl == pytest.approx(0.0)


def test_gap_born_beyond_stop_with_costs_nets_a_small_loss():
    cost = CostModel(spread_bps=2.0, commission_bps=1.0, slippage_bps=1.0)
    base = [
        (100, 100, 100, 100),
        (90, 91, 89, 90.5),
        (90, 91, 89, 90),
    ]
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=cost, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit",
                                              price=100.0, sl=95.0)}))
    t = result.trades[0]
    assert t.reason == "sl"
    assert -0.1 < t.pnl < 0.0            # round-trip costs only


def test_stop_entry_gapping_past_target_exits_at_fill_basis():
    base = [
        (100, 100, 100, 100),   # submit stop buy 102, tp 105
        (110, 111, 109, 110.5),  # opens beyond both trigger and target
        (110, 111, 109, 110),
    ]
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="stop",
                                              price=102.0, tp=105.0)}))
    t = result.trades[0]
    assert t.reason == "tp"
    assert t.exit_price == 110.0         # not the stale 105 target
    assert t.pnl == pytest.approx(0.0)
