
from ict_backtest.core import BEAR, BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.detectors import detect_swings

from conftest import make_candles


def _flat(price: float) -> tuple[float, float, float, float]:
    return (price, price, price, price)


def test_single_pivot_high_and_confirmation_lag():
    prices = [100, 101, 102, 110, 102, 101, 100, 99, 98]
    candles = make_candles([_flat(p) for p in prices])
    swings = detect_swings(candles, k=2)
    highs = [s for s in swings if s.kind == BULL]
    assert len(highs) == 1
    assert highs[0].index == 3
    assert highs[0].price == 110
    assert highs[0].confirm_index == 5


def test_single_pivot_low():
    prices = [100, 99, 98, 90, 98, 99, 100, 101, 102]
    candles = make_candles([_flat(p) for p in prices])
    swings = detect_swings(candles, k=2)
    lows = [s for s in swings if s.kind == BEAR]
    assert len(lows) == 1
    assert lows[0].index == 3
    assert lows[0].price == 90


def test_equal_highs_far_apart_both_detected():
    prices = [100, 101, 105, 100, 99, 98, 99, 100, 105, 100, 99, 98]
    candles = make_candles([_flat(p) for p in prices])
    swings = detect_swings(candles, k=2)
    highs = [s for s in swings if s.kind == BULL]
    assert [s.index for s in highs] == [2, 8]
    assert all(s.price == 105 for s in highs)


def test_pivot_is_window_extreme_on_synthetic():
    candles = synthetic_candles(n=3000, seed=5)
    k = 3
    for s in detect_swings(candles, k=k):
        lo, hi = s.index - k, s.index + k + 1
        window = candles.high[lo:hi] if s.kind == BULL else candles.low[lo:hi]
        extreme = window.max() if s.kind == BULL else window.min()
        assert s.price == extreme
        assert s.confirm_index == s.index + k
        assert lo >= 0 and hi <= len(candles)
