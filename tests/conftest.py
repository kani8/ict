import numpy as np
import pytest

from ict_backtest.core import Candles


def make_candles(ohlc: list[tuple[float, float, float, float]],
                 timeframe_s: int = 900, start_ts: int = 1_700_000_100) -> Candles:
    """Build Candles from (open, high, low, close) tuples."""
    start_ts -= start_ts % timeframe_s
    arr = np.asarray(ohlc, dtype=float)
    n = len(arr)
    return Candles(
        ts=start_ts + timeframe_s * np.arange(n, dtype=np.int64),
        open=arr[:, 0], high=arr[:, 1], low=arr[:, 2], close=arr[:, 3],
        volume=np.ones(n), timeframe_s=timeframe_s,
    )


@pytest.fixture
def make():
    return make_candles
