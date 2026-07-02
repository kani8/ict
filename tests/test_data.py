import numpy as np
import pandas as pd
import pytest

from ict_backtest.core import atr, resample
from ict_backtest.data import load_candles, synthetic_candles
from ict_backtest.data.fetch import save_candles


def test_loader_roundtrip(tmp_path):
    candles = synthetic_candles(n=500, seed=2)
    for name in ("data.csv", "data.parquet"):
        path = tmp_path / name
        save_candles(candles, path)
        loaded = load_candles(path)
        assert len(loaded) == 500
        assert loaded.timeframe_s == candles.timeframe_s
        np.testing.assert_allclose(loaded.close, candles.close, rtol=1e-9)
        np.testing.assert_array_equal(loaded.ts, candles.ts)


def test_loader_date_filter(tmp_path):
    candles = synthetic_candles(n=1000, seed=2)
    path = tmp_path / "data.parquet"
    save_candles(candles, path)
    start = pd.Timestamp(candles.ts[100], unit="s", tz="UTC").isoformat()
    end = pd.Timestamp(candles.ts[200], unit="s", tz="UTC").isoformat()
    loaded = load_candles(path, start=start, end=end)
    assert len(loaded) == 100
    assert loaded.ts[0] == candles.ts[100]


def test_resample_aggregation():
    candles = synthetic_candles(n=997, timeframe_s=900, seed=4)  # deliberately ragged
    htf, last_base = resample(candles, 4)
    assert htf.timeframe_s == 3600
    # spot-check an interior bucket
    k = 5
    mask = (candles.ts >= htf.ts[k]) & (candles.ts < htf.ts[k] + 3600)
    idx = np.flatnonzero(mask)
    assert htf.open[k] == candles.open[idx[0]]
    assert htf.close[k] == candles.close[idx[-1]]
    assert htf.high[k] == candles.high[idx].max()
    assert htf.low[k] == candles.low[idx].min()
    assert htf.volume[k] == pytest.approx(candles.volume[idx].sum())
    assert last_base[k] == idx[-1]
    # mapping is strictly increasing and ends at the final bar
    assert np.all(np.diff(last_base) > 0)
    assert last_base[-1] == len(candles) - 1


def test_atr_positive_and_prefix_consistent():
    candles = synthetic_candles(n=400, seed=6)
    full = atr(candles)
    assert np.all(full > 0)
    prefix = atr(candles.slice(0, 200))
    np.testing.assert_allclose(prefix, full[:200], rtol=1e-12)
