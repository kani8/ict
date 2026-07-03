"""Tests for the M2 post-sweep event study."""

import numpy as np

from ict_backtest.data import synthetic_candles
from ict_backtest.analytics.sweep_study import (
    _realized_vol,
    render_sweep_tables,
    run_sweep_study,
    sweep_events,
)

from conftest import make_candles


def test_sweep_events_fields_and_prediction_signs():
    candles = synthetic_candles(n=6000, seed=23)
    events = sweep_events(candles)
    assert len(events) > 20
    assert {e["kind"] for e in events} <= {"sweep", "run"}
    for e in events:
        if e["kind"] == "sweep":
            assert e["predicted"] == -e["side"]   # purge reverses
        else:
            assert e["predicted"] == e["side"]    # run continues
    ts = [e["t"] for e in events]
    assert ts == sorted(ts)


def test_realized_vol_detects_regime_shift():
    rng = np.random.default_rng(0)
    quiet = 100 * np.exp(np.cumsum(0.0005 * rng.standard_normal(300)))
    loud = quiet[-1] * np.exp(np.cumsum(0.005 * rng.standard_normal(300)))
    close = np.concatenate([quiet, loud])
    ohlc = [(c, c, c, c) for c in close]
    candles = make_candles(ohlc)
    before = _realized_vol(candles.close, 300 - 96, 300)
    after = _realized_vol(candles.close, 300, 300 + 96)
    assert after / before > 3.0


def test_run_sweep_study_structure():
    candles = synthetic_candles(n=8000, seed=23, base_vol=0.004)
    result = run_sweep_study(candles, seed=1)
    assert result["n_events"] > 20
    assert len(result["direction"]) == 4      # {sweep, run} x {96, 384}
    assert len(result["vol"]) == 2            # {sweep, run}
    for r in result["direction"]:
        if r["n"] >= 5:
            assert r["ci_lo"] <= r["mean_signed"] <= r["ci_hi"]
    for r in result["vol"]:
        if r["n"] >= 5:
            assert r["event_expansion"] > 0 and r["control_expansion"] > 0
            assert r["ci_lo"] <= r["ratio"] <= r["ci_hi"]
    text = render_sweep_tables(result, "synthetic")
    assert "Direction" in text and "Volatility expansion" in text


def test_no_direction_signal_on_structureless_data():
    """Drift-free random-walk sweeps should not show a strong directional edge."""
    candles = synthetic_candles(n=12_000, seed=5, trend_strength=0.0)
    rows = [r for r in run_sweep_study(candles, seed=3)["direction"] if r["n"] >= 30]
    assert rows
    for r in rows:
        # signed mean should be small relative to any plausible bar-scale move
        assert abs(r["mean_signed"]) < 0.05
