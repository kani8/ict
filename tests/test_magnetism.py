"""Tests for the M1 liquidity-magnetism event study."""

import numpy as np

from ict_backtest.core import BULL, BEAR, atr as compute_atr
from ict_backtest.data import synthetic_candles
from ict_backtest.analytics.magnetism import (
    baseline_move_rate,
    pool_touch_events,
    render_magnetism_table,
    run_magnetism,
    _ratio_block_ci,
)


def test_pool_touch_events_fields():
    candles = synthetic_candles(n=5000, seed=23)
    events = pool_touch_events(candles)
    assert len(events) > 20
    confirms = [e["confirm"] for e in events]
    assert confirms == sorted(confirms)
    for e in events:
        assert e["side"] in (BULL, BEAR)
        assert e["d_atr"] > 0
        assert e["taken"] == -1 or e["taken"] > e["confirm"]


def test_baseline_move_rate_bounds_and_matching():
    candles = synthetic_candles(n=5000, seed=23)
    a = compute_atr(candles)
    events = pool_touch_events(candles)
    rng = np.random.default_rng(0)
    e = events[len(events) // 2]
    rate = baseline_move_rate(candles, e, 96, a, rng, k=25)
    assert 0.0 <= rate <= 1.0
    # tiny move -> near-certain; huge move -> near-impossible
    tiny = dict(e, d_atr=0.05)
    huge = dict(e, d_atr=50.0)
    assert baseline_move_rate(candles, tiny, 96, a, rng, k=25) >= 0.9
    assert baseline_move_rate(candles, huge, 96, a, rng, k=25) <= 0.1


def test_ratio_block_ci_detects_signal_and_null():
    rng = np.random.default_rng(1)
    touch = (rng.random(300) < 0.8).astype(float)
    base = np.full(300, 0.4)
    r, lo, hi = _ratio_block_ci(touch, base)
    assert 1.6 < r < 2.4 and lo > 1.0          # clear magnetism detected
    touch_null = (rng.random(300) < 0.4).astype(float)
    r, lo, hi = _ratio_block_ci(touch_null, base)
    assert lo <= 1.0 <= hi                     # null straddles 1


def test_run_magnetism_table_shape():
    candles = synthetic_candles(n=6000, seed=23)
    rows = run_magnetism(candles, horizons=(96,), baseline_k=8, seed=1)
    assert len(rows) == 3                      # one per distance bucket
    populated = [r for r in rows if r["n"] > 0]
    assert populated
    for r in populated:
        assert 0.0 <= r["touch_rate"] <= 1.0
        assert 0.0 <= r["baseline_rate"] <= 1.0
        assert r["ci_lo"] <= r["ratio"] <= r["ci_hi"] or np.isnan(r["ci_lo"])
    text = render_magnetism_table(rows, "synthetic")
    assert "| distance (ATR) |" in text


def test_random_walk_shows_no_strong_magnetism():
    """On drift-free synthetic data pools should not be dramatic magnets."""
    candles = synthetic_candles(n=12_000, seed=5, trend_strength=0.0)
    rows = [r for r in run_magnetism(candles, horizons=(96,), baseline_k=12, seed=3)
            if r["n"] >= 30]
    assert rows
    # ratios should hover near 1 on structureless data (loose sanity bound)
    for r in rows:
        assert 0.4 < r["ratio"] < 2.5
