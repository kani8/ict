"""Tests for the Study-V3 narrative engine."""

import numpy as np
import pytest

from ict_backtest.core import BEAR, BULL, Candles
from ict_backtest.data import synthetic_candles
from ict_backtest.engine import Backtester, CostModel
from ict_backtest.strategy import SMCConfig, SMCStrategy
from ict_backtest.strategy.narrative import (
    NarrativeEngine,
    _broadcast,
    _dol_states,
    _ipda_states,
)

from conftest import make_candles


def _daily(prices: list[float]) -> Candles:
    ohlc = [(p, p * 1.001, p * 0.999, p) for p in prices]
    return make_candles(ohlc, timeframe_s=86_400)


def test_broadcast_visibility_rule():
    last_base = np.array([2, 5, 8], dtype=np.int64)
    states = np.array([1.0, -1.0, 1.0])
    out = _broadcast(11, last_base, states)
    # bucket 0 (bars 0-2) sees nothing yet; bucket 1 sees state after bucket 0
    assert out[:3].tolist() == [0.0, 0.0, 0.0]
    assert out[3:6].tolist() == [1.0, 1.0, 1.0]
    assert out[6:9].tolist() == [-1.0, -1.0, -1.0]
    assert out[9:].tolist() == [1.0, 1.0]      # after last bucket: final state


def test_ipda_expansion_and_sweep_recovery():
    flat = [100.0] * 25
    breakout = _daily(flat + [103.0, 103.5])           # closes above 20d high
    states = _ipda_states(breakout, windows=(20,), hold_days=10)
    assert states[25] == BULL and states[26] == BULL

    breakdown = _daily(flat + [97.0])                  # closes below 20d low
    assert _ipda_states(breakdown, (20,), 10)[25] == BEAR

    # sweep of the 20d low with a close back above it -> bullish reversal
    ohlc = [(100, 100.1, 99.9, 100.0)] * 25 + [(100, 100.2, 98.0, 100.05)]
    sweep = make_candles(ohlc, timeframe_s=86_400)
    assert _ipda_states(sweep, (20,), 10)[25] == BULL

    # sweep of the 20d high with a close back below -> bearish reversal
    ohlc = [(100, 100.1, 99.9, 100.0)] * 25 + [(100, 102.0, 99.9, 99.95)]
    sweep_hi = make_candles(ohlc, timeframe_s=86_400)
    assert _ipda_states(sweep_hi, (20,), 10)[25] == BEAR


def test_ipda_hold_expires():
    flat = [100.0] * 25
    series = _daily(flat + [103.0] + [103.0] * 15)     # one event, then quiet
    states = _ipda_states(series, windows=(20,), hold_days=5)
    assert states[25] == BULL
    assert states[31] == 0.0                           # ttl exhausted


def test_ipda_multi_window_grades_by_horizon_agreement():
    # break after 65 flat bars: all of 20/40/60 agree -> full-strength vote
    late_break = _daily([100.0] * 65 + [103.0])
    states = _ipda_states(late_break, windows=(20, 40, 60), hold_days=10)
    assert states[65] == pytest.approx(1.0)
    # break after only 25 bars: 40/60-day windows abstain -> graded vote
    early_break = _daily([100.0] * 25 + [103.0])
    states = _ipda_states(early_break, windows=(20, 40, 60), hold_days=10)
    assert states[25] == pytest.approx(1.0 / 3.0)


def test_dol_states_signs():
    up = synthetic_candles(n=3000, seed=9, base_vol=0.004)
    from ict_backtest.core import resample
    daily, _ = resample(up, 96)
    states = _dol_states(daily, swing_k=3, eq_tol_atr=0.25,
                         min_gap_atr=0.0, atr_period=14)
    assert len(states) == len(daily)
    assert np.all(states >= -1.0) and np.all(states <= 1.0)
    assert np.any(states != 0.0)


def test_dol_recency_window_excludes_stale_liquidity():
    # a lone swing low early on, then a long steady rally away from it:
    # with a short lookback the stale sell-side pool must stop counting
    prices = [100, 99, 95, 99, 100] + [100 + 0.2 * i for i in range(120)]
    daily = _daily(prices)
    short = _dol_states(daily, swing_k=2, eq_tol_atr=0.0,
                        min_gap_atr=10.0, atr_period=14, lookback=30)
    long_ = _dol_states(daily, swing_k=2, eq_tol_atr=0.0,
                        min_gap_atr=10.0, atr_period=14, lookback=10_000)
    assert long_[-1] < 0.0     # stale pool below still drags the unbounded score
    assert short[-1] >= long_[-1]
    assert short[-1] == 0.0    # nothing recent below, nothing above -> abstain


def test_engine_score_and_conviction():
    candles = synthetic_candles(n=20_000, seed=11, base_vol=0.004)
    eng = NarrativeEngine(candles, mtf_multiplier=8, htf_multiplier=32,
                          min_conviction=0.5)
    assert len(eng.score) == len(candles)
    assert np.all(np.abs(eng.score) <= 1.0 + 1e-12)
    # conviction thresholding: bias only where the vote is decisive
    assert np.all((eng.bias != 0) == (np.abs(eng.score) >= 0.5))
    assert (eng.bias == 0).any()               # abstention actually happens
    assert (eng.bias != 0).any()               # ...but not always
    assert set(eng.factors) == set(NarrativeEngine.FACTORS)
    assert "struct_wk" in eng.factors and len(eng.factors["struct_wk"]) == len(candles)
    with pytest.raises(ValueError):
        NarrativeEngine(candles, weights=(0.0,) * 5)
    with pytest.raises(ValueError):
        NarrativeEngine(candles, weights=(1.0,) * 4)   # wrong length


def test_strategy_narrative_mode_gates_trades():
    candles = synthetic_candles(n=20_000, seed=21, base_vol=0.005)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, bias_htf2_multiplier=32, min_rr=1.0,
                    bias_mode="narrative", narrative_min_conviction=0.25)
    strat = SMCStrategy(candles, cfg)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, strat)
    assert len(result.trades) >= 1
    window = cfg.order_expiry_bars
    for t in result.trades:
        lo = max(0, t.entry_index - window)
        assert (strat.bias[lo : t.entry_index + 1] == t.side).any()


def test_funnel_accounting():
    candles = synthetic_candles(n=20_000, seed=21, base_vol=0.005)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, min_rr=1.0)
    strat = SMCStrategy(candles, cfg)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, strat)
    f = strat.funnel
    rejections = (f["rejected_bias"] + f["rejected_bias2"] + f["rejected_discount"]
                  + f["rejected_draw"] + f["rejected_time"])
    assert f["signals"] == rejections + f["staged_attempts"]
    assert f["staged_attempts"] == (f["rejected_no_poi"] + f["rejected_ote"]
                                    + f["rejected_geometry"] + f["placed_limit"]
                                    + f["placed_await"])
    assert f["signals"] > 0 and f["placed_limit"] > 0
    assert f["placed_limit"] >= len(result.trades)  # some orders expire unfilled


def test_underpowered_result_is_labeled():
    from ict_backtest.analytics import compute_metrics, matched_baseline_test, render_report
    from ict_backtest.engine import BacktestResult

    candles = synthetic_candles(n=8000, seed=13, base_vol=0.004)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, min_rr=1.0)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    full = bt.run(candles, SMCStrategy(candles, cfg))
    assert len(full.trades) >= 3
    small = BacktestResult(trades=full.trades[:2], equity_curve=full.equity_curve,
                           candles=candles, initial_equity=full.initial_equity)
    baseline = matched_baseline_test(candles, small, bt, n_sims=50)
    assert baseline.n_sims == 0
    assert "underpowered" in baseline.note
    report = render_report(small, compute_metrics(small), baseline)
    assert "underpowered, not evidence" in report
    assert "null test skipped" in report


def test_await_abandonment_subreasons_sum():
    candles = synthetic_candles(n=20_000, seed=21, base_vol=0.005)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, min_rr=1.0, entry_confirmation=True)
    strat = SMCStrategy(candles, cfg)
    Backtester(cost=CostModel(), initial_equity=100_000).run(candles, strat)
    f = strat.funnel
    assert f["placed_await"] > 0
    assert f["await_abandoned"] == (f["await_expired"] + f["await_violated"]
                                    + f["await_displaced"])


def test_forward_return_table_separates_crafted_regimes():
    import numpy as np
    from ict_backtest.analytics import forward_return_table, render_forward_table

    # 400 bars drifting up, then 400 drifting down, labeled correctly
    up = [100 * (1.001 ** i) for i in range(400)]
    down = [up[-1] * (0.999 ** i) for i in range(400)]
    prices = up + down
    candles = make_candles([(p, p, p, p) for p in prices])
    states = np.array([1] * 400 + [-1] * 400)
    rows = forward_return_table(candles, states, horizon_bars=50)
    by_state = {r["state"]: r for r in rows}
    assert by_state[1.0]["mean_fwd_logret"] > 0 > by_state[-1.0]["mean_fwd_logret"]
    assert by_state[1.0]["t_stat"] > 2.0 and by_state[-1.0]["t_stat"] < -2.0
    # non-overlapping sampling: 750 usable bars / 50 step = 15 samples total
    assert sum(r["n"] for r in rows) == 15
    text = render_forward_table(rows, "crafted")
    assert "| +1 |" in text and "| -1 |" in text

    with pytest.raises(ValueError):
        forward_return_table(candles, states[:100], horizon_bars=50)
    with pytest.raises(ValueError):
        forward_return_table(candles, states, horizon_bars=10_000)


def test_bias_mode_validation():
    candles = synthetic_candles(n=2000, seed=1)
    with pytest.raises(ValueError, match="bias_mode"):
        SMCStrategy(candles, SMCConfig(bias_mode="vibes"))


def test_narrative_prefix_consistency():
    from test_no_lookahead import RecordingStrategy

    cfg = SMCConfig(swing_k=3, htf_multiplier=8, bias_htf2_multiplier=32,
                    use_killzones=False, require_ote=False, require_discount=False,
                    min_rr=1.0, bias_mode="narrative", narrative_min_conviction=0.25,
                    poi_priority=("ifvg", "fvg", "ob"))
    candles = synthetic_candles(n=10_000, seed=33, base_vol=0.005)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    cutoff = 6000

    full = RecordingStrategy(candles, cfg)
    bt.run(candles, full)
    full_subs = [s for s in full.submissions if s[0] < cutoff]

    prefix = RecordingStrategy(candles.slice(0, cutoff), cfg)
    bt.run(candles.slice(0, cutoff), prefix)

    assert len(full_subs) > 0, "test is vacuous: no orders before the cutoff"
    assert prefix.submissions == full_subs


def test_v3_frozen_config_loads_and_runs():
    cfg = SMCConfig.from_toml("configs/v3_origin.toml")
    assert cfg.bias_mode == "narrative"
    assert cfg.narrative_weights == (1.0,) * 5
    assert cfg.ipda_windows == (20, 40, 60)
    candles = synthetic_candles(n=12_000, seed=4, base_vol=0.004)
    result = Backtester(cost=CostModel(), initial_equity=100_000).run(
        candles, SMCStrategy(candles, cfg))
    assert result.final_equity > 0
