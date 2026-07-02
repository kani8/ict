"""Tests for the fixes prompted by the 2026-07 real-market audit:

1. POI selection must skip order blocks already mitigated/invalidated at
   the decision bar, and resting orders must be cancelled when their POI
   zone dies.
2. The matched null must reproduce the strategy's trade templates (side,
   stop/target geometry, count) at randomized times.
3. Block bootstrap for dependence-aware CIs.
"""

import numpy as np
import pytest

from ict_backtest.core import BULL, FVG, OrderBlock
from ict_backtest.data import synthetic_candles
from ict_backtest.engine import Backtester, Broker, CostModel, Order
from ict_backtest.analytics import matched_baseline_test
from ict_backtest.analytics.significance import block_bootstrap_ci
from ict_backtest.strategy import MatchedRandomStrategy, SMCConfig, SMCStrategy


def _strategy(n=3000, seed=99):
    candles = synthetic_candles(n=n, seed=seed, base_vol=0.004)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, min_rr=1.0)
    return SMCStrategy(candles, cfg), candles


# -- 1. OB lifecycle in POI selection ---------------------------------------


def test_find_poi_skips_dead_order_blocks():
    strat, _ = _strategy()
    strat.cfg = SMCConfig(poi_priority=("ob",))
    strat.fvgs = []
    live = OrderBlock(index=90, low=99.0, high=100.0, direction=BULL,
                      created_index=95, mitigated_index=-1, invalidated_index=-1)
    mitigated = OrderBlock(index=96, low=100.0, high=101.0, direction=BULL,
                           created_index=98, mitigated_index=99, invalidated_index=-1)
    invalidated = OrderBlock(index=97, low=101.0, high=102.0, direction=BULL,
                             created_index=99, mitigated_index=100, invalidated_index=100)
    strat.order_blocks = [live, mitigated, invalidated]

    # at m=100 both later (fresher) blocks are dead -> the live one wins
    poi = strat._find_poi(BULL, 90, 100)
    assert poi is not None
    assert (poi[0], poi[1]) == (99.0, 100.0)
    assert poi[2] == -1

    # before their deaths, the freshest block is eligible and reports its death
    poi = strat._find_poi(BULL, 90, 98)
    assert (poi[0], poi[1]) == (100.0, 101.0)
    assert poi[2] == 99


def test_find_poi_death_index_for_fvg():
    strat, _ = _strategy()
    strat.cfg = SMCConfig(poi_priority=("fvg",))
    strat.fvgs = [FVG(index=93, low=99.0, high=100.0, direction=BULL,
                      confirm_index=95, touch_index=101, fill_index=120)]
    strat.order_blocks = []
    poi = strat._find_poi(BULL, 90, 100)
    assert (poi[0], poi[1]) == (99.0, 100.0)
    assert poi[2] == 120           # cancel-at index = full fill
    assert strat._find_poi(BULL, 90, 125) is None  # dead at decision time


def test_pending_order_cancelled_when_poi_dies():
    strat, candles = _strategy()
    broker = Broker(candles, CostModel(), 100_000.0)
    oid = broker.submit(Order(side=BULL, qty=1.0, type="limit", price=1.0))
    strat._pending_order_id = oid
    strat._pending_poi_death = 500

    broker._i = 499
    strat.on_bar(499, broker)
    assert oid in broker.pending      # zone still alive

    broker._i = 500
    strat.on_bar(500, broker)
    assert oid not in broker.pending  # zone died this bar -> stale order gone
    assert strat._pending_order_id is None


# -- 2. matched null ----------------------------------------------------------


def _run_smc():
    strat, candles = _strategy(n=8000, seed=13)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    return candles, bt, bt.run(candles, strat)


def test_matched_null_preserves_trade_templates():
    candles, bt, result = _run_smc()
    assert len(result.trades) >= 5
    null = MatchedRandomStrategy(candles, result.trades, seed=1)
    res = bt.run(candles, null)
    assert len(res.trades) == len(result.trades)
    # side mix and fractional stop geometry are preserved as multisets
    real_sides = sorted(t.side for t in result.trades)
    null_sides = sorted(t.side for t in res.trades)
    assert null_sides == real_sides
    real_fracs = sorted(round(abs(t.entry_price - t.sl) / t.entry_price, 4)
                        for t in result.trades)
    null_fracs = sorted(round(abs(t.entry_price - t.sl) / t.entry_price, 4)
                        for t in res.trades)
    np.testing.assert_allclose(null_fracs, real_fracs, rtol=0.15)


def test_matched_null_randomizes_timing():
    candles, bt, result = _run_smc()
    r1 = bt.run(candles, MatchedRandomStrategy(candles, result.trades, seed=1))
    r2 = bt.run(candles, MatchedRandomStrategy(candles, result.trades, seed=2))
    assert [t.entry_index for t in r1.trades] != [t.entry_index for t in r2.trades]


def test_matched_baseline_test_diagnostics():
    candles, bt, result = _run_smc()
    test = matched_baseline_test(candles, result, bt, n_sims=10)
    assert 0.0 < test.p_value <= 1.0
    assert test.kind == "matched"
    d = test.diagnostics
    assert d["strategy_trades"] == len(result.trades)
    assert d["null_mean_trades"] == pytest.approx(len(result.trades), rel=0.1)
    assert d["null_mean_exposure_pct"] > 0
    # holding emerges from the same geometry -> same order of magnitude
    assert 0.2 < d["null_mean_holding_bars"] / max(d["strategy_mean_holding_bars"], 1e-9) < 5.0


# -- 3. block bootstrap -------------------------------------------------------


def test_block_bootstrap_signs_and_blocklen():
    rng = np.random.default_rng(0)
    mean, lo, hi, b = block_bootstrap_ci(np.ones(100) + 0.1 * rng.standard_normal(100))
    assert lo > 0 and b == round(100 ** (1 / 3))
    mean, lo, hi, b = block_bootstrap_ci(rng.standard_normal(300) * 2)
    assert lo < 0 < hi


def test_block_bootstrap_widens_ci_under_dependence():
    """Clustered data must yield a wider CI than the IID bootstrap claims."""
    from ict_backtest.analytics import bootstrap_ci
    rng = np.random.default_rng(3)
    # strongly autocorrelated: long runs of good and bad regimes
    regimes = np.repeat(rng.standard_normal(20), 15)
    x = regimes + 0.1 * rng.standard_normal(len(regimes))
    _, ilo, ihi = bootstrap_ci(x, seed=5)
    _, blo, bhi, b = block_bootstrap_ci(x, block_len=15, seed=5)
    assert (bhi - blo) > (ihi - ilo) * 1.3


def test_block_bootstrap_small_samples():
    mean, lo, hi, b = block_bootstrap_ci([1.0])
    assert mean == 1.0
    mean, lo, hi, b = block_bootstrap_ci([])
    assert (mean, lo, hi, b) == (0.0, 0.0, 0.0, 0)


def test_trades_record_initial_geometry():
    _, _, result = _run_smc()
    for t in result.trades:
        assert t.sl > 0 and t.tp > 0
        if t.side == BULL:
            assert t.sl < t.entry_price < t.tp
        else:
            assert t.tp < t.entry_price < t.sl
