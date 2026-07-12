"""CAT strategy: categorization, bracket geometry, filters, no-lookahead."""

import numpy as np
import pytest

from ict_backtest.core import BEAR, BULL, Candles
from ict_backtest.data import synthetic_cat_regimes, synthetic_candles
from ict_backtest.engine import Backtester, Broker, CostModel
from ict_backtest.strategy import CATConfig, CATStrategy
from ict_backtest.strategy.cat import (
    CAT_CONSOLIDATION,
    CAT_DIRECTION,
    CAT_NONE,
    efficiency_ratio,
)


def make_candles(close, open_=None, high=None, low=None, timeframe_s=900):
    close = np.asarray(close, dtype=float)
    n = len(close)
    if open_ is None:
        open_ = np.concatenate(([close[0]], close[:-1]))
    open_ = np.asarray(open_, dtype=float)
    high = np.maximum(open_, close) if high is None else np.asarray(high, float)
    low = np.minimum(open_, close) if low is None else np.asarray(low, float)
    ts = np.arange(n, dtype=np.int64) * timeframe_s
    return Candles(ts=ts, open=open_, high=high, low=low, close=close,
                   volume=np.ones(n), timeframe_s=timeframe_s)


# -- categorization -----------------------------------------------------------


def test_efficiency_ratio_extremes():
    ramp = np.arange(100.0)                      # straight line
    er = efficiency_ratio(ramp, 20)
    assert np.allclose(er[20:], 1.0)

    zigzag = np.array([100.0, 101.0] * 50)       # goes nowhere
    er = efficiency_ratio(zigzag, 20)
    assert np.all(er[20:] <= 0.05 + 1e-12)

    assert np.all(np.isnan(er[:20]))             # no value before the window


def test_categories_on_constructed_series():
    ramp = 100 + np.arange(60.0)
    zigzag = 100 + np.array([0.0, 1.0] * 30)
    cfg = CATConfig()
    s_dir = CATStrategy(make_candles(ramp), cfg)
    s_cons = CATStrategy(make_candles(zigzag), cfg)
    assert np.all(s_dir.category[cfg.regime_window:] == CAT_DIRECTION)
    assert np.all(s_dir.trend[cfg.regime_window:] == BULL)
    assert np.all(s_cons.category[cfg.regime_window:] == CAT_CONSOLIDATION)


def test_chaos_band_is_no_category():
    rng = np.random.default_rng(3)
    close = 100 + np.cumsum(rng.standard_normal(4000)) * 0.1
    s = CATStrategy(make_candles(close), CATConfig())
    er = s.er[~np.isnan(s.er)]
    mid = (er > 0.15) & (er < 0.40)
    cats = s.category[~np.isnan(s.er)]
    assert np.all(cats[mid] == CAT_NONE)


def test_stability_requires_consecutive_bars():
    # direction for a long stretch, then an abrupt flip to zigzag
    close = np.concatenate([100 + np.arange(60.0), 160 - np.array([0.0, 1.0] * 20)])
    cfg = CATConfig(stability_bars=4)
    s = CATStrategy(make_candles(close), cfg)
    changes = np.flatnonzero(s.category[1:] != s.category[:-1]) + 1
    for c in changes:
        assert not s.stable[c: c + cfg.stability_bars - 1].any()


def test_outlier_candle_blocks_entries():
    close = 100 + np.array([0.0, 1.0] * 40)
    close[50] = 130.0                           # one huge candle
    s = CATStrategy(make_candles(close), CATConfig(outlier_skip_bars=2))
    assert s.blocked[50] and s.blocked[51] and s.blocked[52]
    assert not s.blocked[49]


# -- trade geometry -----------------------------------------------------------


def run_bt(candles, cfg, cost=None):
    bt = Backtester(cost=cost or CostModel(spread_bps=0, commission_bps=0, slippage_bps=0))
    strat = CATStrategy(candles, cfg)
    res = bt.run(candles, strat)
    return res, strat


class Recording(CATStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submissions = []

    def on_bar(self, i, broker: Broker):
        before = broker._next_id
        super().on_bar(i, broker)
        for oid in range(before, broker._next_id):
            order = broker.pending.get(oid)
            if order is not None:
                self.submissions.append((i, order))


def _recorded(candles, cfg):
    bt = Backtester(cost=CostModel(0, 0, 0))
    strat = Recording(candles, cfg)
    bt.run(candles, strat)
    return strat


def test_consolidation_orders_target_inside_range():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strat = _recorded(candles, CATConfig())
    cons = [(i, o) for i, o in strat.submissions if o.tag == "cat_cons"]
    assert cons, "no consolidation trades on regime data — vacuous test"
    for i, o in cons:
        hi, lo = strat.range_high[i], strat.range_low[i]
        assert lo <= o.tp <= hi                     # target where price has been
        pos = (candles.close[i] - lo) / (hi - lo)
        if o.side == BULL:
            assert pos <= 1.0 - strat.cfg.avoid_extremes_frac   # no longs at the top
        else:
            assert pos >= strat.cfg.avoid_extremes_frac


def test_direction_orders_target_new_area_and_follow_trend():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strat = _recorded(candles, CATConfig())
    dirs = [(i, o) for i, o in strat.submissions if o.tag == "cat_dir"]
    assert dirs, "no direction trades on regime data — vacuous test"
    for i, o in dirs:
        assert o.side == strat.trend[i]             # with the trend, never fading
        if o.side == BULL:
            assert o.tp >= strat.range_high[i]      # a new area
            assert o.sl < candles.close[i]          # stop inside
        else:
            assert o.tp <= strat.range_low[i]
            assert o.sl > candles.close[i]


def test_one_to_one_brackets():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strat = _recorded(candles, CATConfig(rr=1.0))
    assert strat.submissions
    for i, o in strat.submissions:
        c = candles.close[i]
        assert abs(o.tp - c) == pytest.approx(abs(c - o.sl), rel=1e-9)
        assert abs(o.tp - c) == pytest.approx(0.5 * strat.avg_tr[i], rel=1e-9)


def test_no_entries_in_chaos_or_blackout():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strat = _recorded(candles, CATConfig())
    for i, _ in strat.submissions:
        assert strat.category[i] != CAT_NONE
        assert strat.stable[i]
        assert not strat.blocked[i]


def test_fade_mode_shorts_top_longs_bottom():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strat = _recorded(candles, CATConfig(consolidation_mode="fade"))
    cons = [(i, o) for i, o in strat.submissions if o.tag == "cat_cons"]
    assert cons, "no fade trades on regime data — vacuous test"
    for i, o in cons:
        hi, lo = strat.range_high[i], strat.range_low[i]
        pos = (candles.close[i] - lo) / (hi - lo)
        if o.side == BEAR:
            assert pos >= 1.0 - strat.cfg.avoid_extremes_frac   # short the top
        else:
            assert pos <= strat.cfg.avoid_extremes_frac         # long the bottom
        assert lo <= o.tp <= hi
    with pytest.raises(ValueError):
        CATStrategy(candles, CATConfig(consolidation_mode="bogus"))


def test_session_filter():
    candles = synthetic_candles(n=3000, seed=2)
    cfg = CATConfig(session_et="09:33-09:50", er_direction=0.30, er_consolidation=0.25)
    strat = CATStrategy(candles, cfg)
    assert strat.eligible_mask.sum() < len(candles)
    rec = _recorded(candles, cfg)
    for i, _ in rec.submissions:
        assert strat.eligible_mask[i]


def test_config_roundtrip(tmp_path):
    p = tmp_path / "cat.toml"
    p.write_text("[strategy]\nregime_window = 30\nrr = 1.5\nsession_et = '09:33-09:50'\n")
    cfg = CATConfig.from_toml(p)
    assert cfg.regime_window == 30 and cfg.rr == 1.5 and cfg.session_et == "09:33-09:50"
    p.write_text("[strategy]\nnot_a_key = 1\n")
    with pytest.raises(ValueError):
        CATConfig.from_toml(p)


# -- no-lookahead: prefix consistency ------------------------------------------


@pytest.mark.parametrize("cutoff", [2000, 3500, 5000])
def test_prefix_consistency(cutoff):
    candles, _ = synthetic_cat_regimes(n=6000, seed=11)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)

    def subs(cs):
        strat = Recording(cs, CATConfig())
        bt.run(cs, strat)
        return [(i, o.side, round(o.qty, 10), round(o.sl, 10), round(o.tp, 10),
                 o.expiry_index, o.tag) for i, o in strat.submissions]

    full = [s for s in subs(candles) if s[0] < cutoff]
    prefix = subs(candles.slice(0, cutoff))
    assert len(full) > 0, "test is vacuous: no orders before the cutoff"
    assert prefix == full


def test_exit_on_flip_closes_position():
    # long directional ramp that snaps into a tight zigzag: an open
    # direction trade should be closed once consolidation stabilizes
    close = np.concatenate([100 + 0.5 * np.arange(120.0),
                            160 + 0.05 * np.array([0.0, 1.0] * 60)])
    cfg = CATConfig(exit_on_flip=True, bracket_frac=50.0)  # bracket too wide to hit
    res, _ = run_bt(make_candles(close), cfg)
    flips = [t for t in res.trades if t.reason == "strategy"]
    assert flips, "no flip exit happened"
