"""Tests for the V2.1 bias-dominance gates: dual-timeframe agreement, HTF
premium/discount, draw on liquidity, and whole-news-day exclusion."""

import numpy as np
import pandas as pd

from ict_backtest.core import BEAR, BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.data.news import news_day_mask
from ict_backtest.engine import Backtester, CostModel
from ict_backtest.strategy import SMCConfig, SMCStrategy

from conftest import make_candles  # noqa: F401  (fixture support)


def _base_cfg(**kw) -> SMCConfig:
    return SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                     htf_multiplier=8, min_rr=1.0, **kw)


def test_htf_context_shapes_and_warmup():
    candles = synthetic_candles(n=4000, seed=5, base_vol=0.004)
    strat = SMCStrategy(candles, _base_cfg())
    assert len(strat.htf_eq) == len(candles)
    assert np.isnan(strat.htf_eq[0])            # no HTF swings known yet
    assert np.isfinite(strat.htf_eq[-1])        # established by the end
    assert strat.htf_pools                      # HTF pools mapped to base indices
    for side, level, confirm_base, taken_base in strat.htf_pools:
        assert side in (BULL, BEAR) and level > 0
        assert 0 <= confirm_base < len(candles)
        assert taken_base == -1 or taken_base > confirm_base


def test_draw_exists_gate():
    candles = synthetic_candles(n=1000, seed=5)
    strat = SMCStrategy(candles, _base_cfg())
    c = float(candles.close[500])
    strat.htf_pools = [(BULL, c * 1.05, 100, -1)]      # untaken pool above
    assert strat._draw_exists(BULL, 500)
    assert not strat._draw_exists(BEAR, 500)           # nothing below
    strat.htf_pools = [(BULL, c * 1.05, 100, 400)]     # already taken
    assert not strat._draw_exists(BULL, 500)
    strat.htf_pools = [(BULL, c * 1.05, 600, -1)]      # not yet confirmed
    assert not strat._draw_exists(BULL, 500)
    strat.htf_pools = [(BULL, c * 0.95, 100, -1)]      # wrong side of price
    assert not strat._draw_exists(BULL, 500)


def test_dual_timeframe_bias_gates_trades():
    candles = synthetic_candles(n=12_000, seed=13, base_vol=0.004)
    cfg = _base_cfg(bias_htf2_multiplier=24)
    strat = SMCStrategy(candles, cfg)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, strat)
    window = cfg.order_expiry_bars
    for t in result.trades:
        lo = max(0, t.entry_index - window)
        assert (strat.bias[lo : t.entry_index + 1] == t.side).any()
        assert (strat.bias2[lo : t.entry_index + 1] == t.side).any()


def test_htf_discount_gate_reduces_and_positions_trades():
    candles = synthetic_candles(n=12_000, seed=13, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    plain = bt.run(candles, SMCStrategy(candles, _base_cfg()))
    strat = SMCStrategy(candles, _base_cfg(require_htf_discount=True))
    gated = bt.run(candles, strat)
    assert 0 < len(gated.trades) <= len(plain.trades)
    window = strat.cfg.order_expiry_bars
    for t in gated.trades:
        lo = max(0, t.entry_index - window)
        eq = strat.htf_eq[lo : t.entry_index + 1]
        close = candles.close[lo : t.entry_index + 1]
        ok = ~np.isnan(eq) & ((close < eq) if t.side == BULL else (close > eq))
        assert ok.any()


def test_all_gates_together_still_trade():
    candles = synthetic_candles(n=20_000, seed=21, base_vol=0.004)
    cfg = _base_cfg(bias_htf2_multiplier=24, require_htf_discount=True,
                    require_draw=True)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, SMCStrategy(candles, cfg))
    assert len(result.trades) >= 1  # gates restrict, but not to zero


def test_news_day_mask_covers_full_et_day():
    event = int(pd.Timestamp("2024-08-02 12:30", tz="UTC").timestamp())  # 08:30 ET
    ts = np.array([
        int(pd.Timestamp("2024-08-01 23:00", tz="America/New_York").timestamp()),
        int(pd.Timestamp("2024-08-02 00:00", tz="America/New_York").timestamp()),
        int(pd.Timestamp("2024-08-02 20:00", tz="America/New_York").timestamp()),
        int(pd.Timestamp("2024-08-03 00:00", tz="America/New_York").timestamp()),
    ], dtype=np.int64)
    mask = news_day_mask(ts, [event])
    assert mask.tolist() == [False, True, True, False]


def test_v21_prefix_consistency():
    from test_no_lookahead import RecordingStrategy

    cfg = SMCConfig(swing_k=3, htf_multiplier=8, use_killzones=False,
                    require_ote=False, require_discount=False, min_rr=1.0,
                    bias_htf2_multiplier=24, require_htf_discount=True,
                    require_draw=True, avoid_news=True, news_day_blackout=True,
                    poi_priority=("ifvg", "fvg", "ob"))
    candles = synthetic_candles(n=8000, seed=31, base_vol=0.005)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    cutoff = 5000

    full = RecordingStrategy(candles, cfg)
    bt.run(candles, full)
    full_subs = [s for s in full.submissions if s[0] < cutoff]

    prefix = RecordingStrategy(candles.slice(0, cutoff), cfg)
    bt.run(candles.slice(0, cutoff), prefix)

    assert len(full_subs) > 0, "test is vacuous: no orders before the cutoff"
    assert prefix.submissions == full_subs


def test_v21_frozen_config_loads_and_runs():
    cfg = SMCConfig.from_toml("configs/v2_faithful.toml")
    assert cfg.bias_htf2_multiplier == 96
    assert cfg.require_htf_discount and cfg.require_draw and cfg.news_day_blackout
    candles = synthetic_candles(n=6000, seed=2, base_vol=0.004)
    result = Backtester(cost=CostModel(), initial_equity=100_000).run(
        candles, SMCStrategy(candles, cfg))
    assert result.final_equity > 0  # exercises the full gate stack without error
