"""Sub-bar (e.g. 1m) resolution of intrabar ambiguity.

Base bars are 900s; sub-bars 300s, three per base bar, built so that base
OHLC aggregates the sub-bars exactly.  The engine must use the observed
sub-bar touch order instead of the pessimistic assumption, and fall back
to the declared policy wherever sub-bar coverage is missing.
"""

import numpy as np
import pytest

from ict_backtest.core import BULL, Candles
from ict_backtest.engine import Backtester, Order

from conftest import make_candles
from test_engine import NO_COST, Script

BASE_TF = 900
SUB_TF = 300
START = 1_700_000_100 - (1_700_000_100 % BASE_TF)


def make_sub(sub_ohlc: list[list[tuple]], skip_base: set[int] = frozenset()) -> Candles:
    """Build sub-bar candles; sub_ohlc[i] holds the sub-bars of base bar i."""
    ts, rows = [], []
    for i, bars in enumerate(sub_ohlc):
        if i in skip_base:
            continue
        for j, bar in enumerate(bars):
            ts.append(START + i * BASE_TF + j * SUB_TF)
            rows.append(bar)
    arr = np.asarray(rows, dtype=float)
    return Candles(ts=np.asarray(ts, dtype=np.int64), open=arr[:, 0], high=arr[:, 1],
                   low=arr[:, 2], close=arr[:, 3], volume=np.ones(len(ts)),
                   timeframe_s=SUB_TF)


AMBIG_BASE = [
    (100, 100, 100, 100),   # 0: submit market long, sl 95 tp 105
    (100, 100, 100, 100),   # 1: entry at open
    (100, 106, 94, 100),    # 2: touches both levels
]
FLAT = (100, 100, 100, 100)


def _run(sub: Candles | None, policy: str = "conservative"):
    candles = make_candles(AMBIG_BASE, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar_policy=policy, intrabar=sub)
    return bt.run(candles, Script({0: Order(side=BULL, qty=1.0, sl=95.0, tp=105.0)}))


def test_subbars_show_tp_first_overrides_conservative():
    sub = make_sub([
        [FLAT] * 3,
        [FLAT] * 3,
        [(100, 106, 99, 105), (105, 105, 100, 101), (101, 102, 94, 100)],  # tp then sl
    ])
    t = _run(sub).trades[0]
    assert t.reason == "tp" and t.exit_price == 105.0


def test_subbars_show_sl_first_confirms_stop():
    sub = make_sub([
        [FLAT] * 3,
        [FLAT] * 3,
        [(100, 101, 94, 96), (96, 106, 96, 104), (104, 104, 99, 100)],  # sl then tp
    ])
    t = _run(sub).trades[0]
    assert t.reason == "sl" and t.exit_price == 95.0


def test_both_levels_in_one_subbar_falls_back_to_policy():
    sub = make_sub([
        [FLAT] * 3,
        [FLAT] * 3,
        [(100, 106, 94, 100), FLAT, FLAT],  # still ambiguous at sub level
    ])
    assert _run(sub, "conservative").trades[0].reason == "sl"
    assert _run(sub, "optimistic").trades[0].reason == "tp"


def test_missing_subbar_coverage_falls_back_to_policy():
    sub = make_sub([[FLAT] * 3, [FLAT] * 3, [FLAT] * 3], skip_base={2})
    assert _run(sub, "conservative").trades[0].reason == "sl"


def test_entry_bar_tp_granted_when_subbars_show_fill_first():
    base = [
        (100, 100, 100, 100),          # submit limit buy 99, tp 101
        (100, 102, 98.5, 101.5),       # fill and target touch in one base bar
        (101.5, 101.6, 101.4, 101.5),
    ]
    sub = make_sub([
        [FLAT] * 3,
        [(100, 100.2, 98.5, 99.0),     # fill sub-bar (low <= 99), tp not touched
         (99.0, 102, 98.9, 101.6),     # tp touched in a *later* sub-bar
         (101.6, 101.7, 101.4, 101.5)],
        [FLAT] * 3,
    ])
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=sub)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit",
                                              price=99.0, tp=101.0)}))
    t = result.trades[0]
    assert t.entry_index == 1 and t.exit_index == 1   # same-bar tp now provable
    assert t.reason == "tp"


def test_entry_bar_tp_still_denied_when_same_subbar_as_fill():
    base = [
        (100, 100, 100, 100),
        (100, 102, 98.5, 100.9),       # fill and tp touch inside one sub-bar
        (100.9, 101.6, 100.8, 101.5),  # tp cleanly hit the next bar
    ]
    sub = make_sub([
        [FLAT] * 3,
        [(100, 102, 98.5, 100.5),      # fill AND tp touch in the same sub-bar
         (100.5, 100.9, 100.3, 100.8),  # later sub-bars stay below tp
         (100.8, 100.9, 100.5, 100.9)],
        [(100.9, 101.6, 100.8, 101.5)] * 3,
    ])
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=sub)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit",
                                              price=99.0, tp=101.0)}))
    t = result.trades[0]
    assert t.entry_index == 1
    assert t.exit_index == 2 and t.reason == "tp"     # ordering unprovable -> deferred


def test_entry_bar_sl_after_fill_subbar():
    base = [
        (100, 100, 100, 100),
        (100, 100.5, 94, 95),   # limit 99 fills, then stop 96
        (95, 96, 94, 95),
    ]
    sub = make_sub([
        [FLAT] * 3,
        [(100, 100.5, 98.8, 99.0),     # fill
         (99.0, 99.2, 95.8, 96.0),     # stop touched later
         (96.0, 96.1, 94.0, 95.0)],
        [FLAT] * 3,
    ])
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=sub)
    result = bt.run(candles, Script({0: Order(side=BULL, qty=1.0, type="limit",
                                              price=99.0, sl=96.0)}))
    t = result.trades[0]
    assert t.entry_index == 1 and t.exit_index == 1
    assert t.reason == "sl" and t.exit_price == 96.0


def test_coarser_intrabar_rejected():
    candles = make_candles(AMBIG_BASE, timeframe_s=BASE_TF, start_ts=START)
    bad = make_candles([FLAT] * 3, timeframe_s=BASE_TF, start_ts=START)
    bt = Backtester(cost=NO_COST, initial_equity=1000, intrabar=bad)
    with pytest.raises(ValueError, match="finer"):
        bt.run(candles, Script({}))


def test_results_identical_without_ambiguity():
    """Sub-bar data must not change unambiguous outcomes."""
    base = [
        (100, 100, 100, 100),
        (100, 100, 100, 100),
        (100, 110, 100, 110),
        (110, 112, 104, 105),
        (105, 106, 104, 105),
    ]
    sub = make_sub([
        [FLAT] * 3, [FLAT] * 3,
        [(100, 104, 100, 104), (104, 108, 104, 108), (108, 110, 107, 110)],
        [(110, 112, 109, 111), (111, 111, 104, 105), (105, 105, 104, 105)],
        [(105, 106, 104, 105)] * 3,
    ])
    candles = make_candles(base, timeframe_s=BASE_TF, start_ts=START)
    plan = {0: Order(side=BULL, qty=2.0, tp=111.0)}
    res_plain = Backtester(cost=NO_COST, initial_equity=1000).run(candles, Script(dict(plan)))
    res_ib = Backtester(cost=NO_COST, initial_equity=1000, intrabar=sub).run(candles, Script(dict(plan)))
    assert res_plain.trades[0].exit_price == res_ib.trades[0].exit_price
    assert res_plain.final_equity == res_ib.final_equity
