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


# -- journey-guide features ----------------------------------------------------


def test_category_toggles():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    cons_only = _recorded(candles, CATConfig(trade_direction=False))
    assert cons_only.submissions
    assert all(o.tag == "cat_cons" for _, o in cons_only.submissions)
    assert cons_only.skip_counts["category_disabled"] > 0
    dir_only = _recorded(candles, CATConfig(trade_consolidation=False))
    assert dir_only.submissions
    assert all(o.tag == "cat_dir" for _, o in dir_only.submissions)


def test_outlier_direction_exempt():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strict = _recorded(candles, CATConfig())
    exempt = _recorded(candles, CATConfig(outlier_block_mode="direction_exempt"))
    off = _recorded(candles, CATConfig(outlier_block_mode="off"))
    # exempt admits direction entries on blocked bars; consolidation stays vetoed
    extra = [(i, o) for i, o in exempt.submissions if exempt.blocked[i]]
    assert all(o.tag == "cat_dir" for _, o in extra)
    assert len(off.submissions) >= len(exempt.submissions) >= len(strict.submissions)
    with pytest.raises(ValueError):
        CATStrategy(candles, CATConfig(outlier_block_mode="bogus"))


def test_volatility_band_filters_entries():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    banded = _recorded(candles, CATConfig(vol_ref_window=200, vol_band_low=0.9,
                                          vol_band_high=1.1))
    assert banded.skip_counts["vol_out_of_band"] > 0
    for i, _ in banded.submissions:
        ratio = banded.avg_tr[i] / banded.vol_ref[i]
        assert 0.9 <= ratio <= 1.1


def test_day_extreme_veto():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    strat = _recorded(candles, CATConfig(avoid_day_extreme_atr=1.0))
    assert strat.skip_counts["at_day_extreme"] > 0
    for i, _ in strat.submissions:
        c = candles.close[i]
        assert strat.day_high[i] - c >= strat.avg_tr[i]
        assert c - strat.day_low[i] >= strat.avg_tr[i]


def test_limit_entry_orders():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    cfg = CATConfig(entry_order="limit", limit_offset_frac=0.25, limit_expiry_bars=4)
    strat = _recorded(candles, cfg)
    assert strat.submissions
    for i, o in strat.submissions:
        assert o.type == "limit" and o.expiry_index == i + 4
        c = candles.close[i]
        # limit improves on the close: below it for longs, above for shorts
        assert (o.price < c) if o.side == BULL else (o.price > c)
        # bracket distances stay anchored to the intended fill
        assert abs(o.tp - o.price) == pytest.approx(0.5 * strat.avg_tr[i], rel=1e-9)
    with pytest.raises(ValueError):
        CATStrategy(candles, CATConfig(entry_order="bogus"))


def test_breakeven_moves_stop_to_entry():
    # ramp far enough to earn +0.5R with a bracket too wide to resolve,
    # then collapse: the breakeven stop should exit near entry, not at -1R
    close = np.concatenate([100 + 0.5 * np.arange(80.0),
                            140 + 2.0 * np.arange(20.0),
                            180 - 4.0 * np.arange(1, 21.0)])
    cfg = CATConfig(breakeven_r=0.5, bracket_frac=30.0, trade_consolidation=False)
    res, _ = run_bt(make_candles(close), cfg)
    be = [t for t in res.trades if t.reason == "sl" and abs(t.exit_price - t.entry_price)
          < 0.05 * abs(t.entry_price - t.sl)]
    assert be, "no breakeven exit happened"
    for t in be:
        assert t.r_multiple > -0.2   # nowhere near a full -1R loss


def test_max_daily_loss_and_trade_cap():
    candles, _ = synthetic_cat_regimes(n=8000, seed=5)
    capped = _recorded(candles, CATConfig(max_trades_per_day=2))
    assert capped.skip_counts["max_trades_stop"] > 0
    per_day = {}
    for i, _ in capped.submissions:
        per_day[capped.day_key[i]] = per_day.get(capped.day_key[i], 0) + 1
    assert per_day and max(per_day.values()) <= 2

    stopped = CATStrategy(candles, CATConfig(max_daily_loss_r=1.0))
    bt = Backtester(cost=CostModel(0, 0, 0))
    res = bt.run(candles, stopped)
    assert stopped.skip_counts["daily_loss_stop"] > 0
    # after the stop fires, no further entries land on that ET day
    day_r: dict = {}
    for t in res.trades:
        d = stopped.day_key[t.entry_index]
        assert day_r.get(d, 0.0) > -1.0, "entry after max daily loss was hit"
        de = stopped.day_key[t.exit_index]
        if not np.isnan(t.r_multiple):
            day_r[de] = day_r.get(de, 0.0) + t.r_multiple


# -- no-lookahead: prefix consistency ------------------------------------------


FULL_SURFACE = CATConfig(entry_order="limit", limit_offset_frac=0.1,
                         breakeven_r=0.5, max_daily_loss_r=2.0,
                         max_trades_per_day=5, vol_ref_window=200,
                         vol_band_low=0.5, vol_band_high=2.0,
                         avoid_day_extreme_atr=0.5,
                         outlier_block_mode="direction_exempt",
                         exit_on_flip=True)


@pytest.mark.parametrize("cutoff", [2000, 3500, 5000])
@pytest.mark.parametrize("cfg", [CATConfig(), FULL_SURFACE], ids=["default", "full"])
def test_prefix_consistency(cutoff, cfg):
    candles, _ = synthetic_cat_regimes(n=6000, seed=11)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)

    def subs(cs):
        strat = Recording(cs, cfg)
        bt.run(cs, strat)
        return [(i, o.side, o.type, round(o.price, 10), round(o.qty, 10),
                 round(o.sl, 10), round(o.tp, 10),
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
