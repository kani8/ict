"""Tests for the M3 high-volume revisit study."""
import numpy as np
from ict_backtest.core import Candles
from ict_backtest.data import synthetic_candles
from ict_backtest.analytics.revisit import (
    _depart_revisit, render_revisit_table, run_revisit_study, volume_spike_mask,
)
from conftest import make_candles


def test_volume_spike_mask_detects_and_isolates():
    candles = synthetic_candles(n=1200, seed=7)
    vol = candles.volume.copy()
    vol[600] = vol.max() * 50
    vol[620] = vol.max() * 60
    vol[900] = vol.max() * 70
    c = Candles(ts=candles.ts, open=candles.open, high=candles.high,
                low=candles.low, close=candles.close, volume=vol,
                timeframe_s=candles.timeframe_s)
    mask = volume_spike_mask(c, q=0.99, trailing=300, isolation=96)
    assert mask[600] and mask[900]
    assert not mask[620]
    assert not mask[:300].any()


def test_depart_revisit_paths():
    flat = (100.0, 100.5, 99.5, 100.0)
    away = (103.0, 103.5, 102.5, 103.0)
    back = (101.0, 101.5, 99.8, 100.2)
    c1 = make_candles([flat]*3 + [away, away, back] + [away]*4)
    dep, rev = _depart_revisit(c1, 2, 8, depart_atr=1.0, atr_t=1.0)
    assert dep and rev
    c2 = make_candles([flat]*3 + [away]*7)
    dep, rev = _depart_revisit(c2, 2, 8, depart_atr=1.0, atr_t=1.0)
    assert dep and not rev
    c3 = make_candles([flat]*10)
    dep, rev = _depart_revisit(c3, 2, 8, depart_atr=1.0, atr_t=1.0)
    assert not dep and not rev


def test_run_revisit_study_structure():
    candles = synthetic_candles(n=8000, seed=11, base_vol=0.004)
    rows = run_revisit_study(candles, horizons=(96,), trailing=500, q=0.97, k=8, seed=2)
    assert len(rows) == 1
    r = rows[0]
    if r["n"] >= 5:
        assert 0.0 <= r["revisit_rate"] <= 1.0
        assert 0.0 <= r["control_rate"] <= 1.0
        assert r["ci_lo"] <= r["ratio"] <= r["ci_hi"]
    text = render_revisit_table(rows, "synthetic")
    assert "revisit" in text


def test_structureless_volume_shows_no_revisit_edge():
    """Synthetic volume is independent of price, so spike bars can't carry
    revisit information — the ratio must hover near 1.

    q=0.99 is the isolation-optimal spike quantile: with an isolation window
    of 96 bars the count of surviving isolated spikes ~ n*(1-q)*exp(-96*(1-q))
    peaks near q ≈ 1 - 1/96 ≈ 0.99, so q=0.97 starves the horizon of the
    n>=30 events this null needs. n=20_000 gives ~78 isolated events."""
    candles = synthetic_candles(n=20_000, seed=9, trend_strength=0.0)
    rows = [r for r in run_revisit_study(candles, horizons=(96,), trailing=500,
                                         q=0.99, k=10, seed=4) if r["n"] >= 30]
    assert rows
    for r in rows:
        assert 0.7 < r["ratio"] < 1.3
