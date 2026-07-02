from ict_backtest.core import BEAR, BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.detectors import detect_fvgs

from conftest import make_candles


def test_bullish_fvg_zone_touch_and_fill():
    ohlc = [
        (100.0, 101.0, 99.5, 100.5),   # c0
        (100.5, 106.0, 100.4, 105.5),  # c1: displacement up
        (105.5, 107.0, 104.0, 106.5),  # c2: low 104 > c0 high 101 -> gap (101, 104)
        (106.5, 107.5, 105.0, 107.0),  # above the gap
        (107.0, 107.2, 103.0, 104.5),  # dips to 103 -> touch, not full fill
        (104.5, 105.0, 100.5, 101.0),  # dips to 100.5 -> fill
    ]
    candles = make_candles(ohlc)
    fvgs = detect_fvgs(candles, min_gap_atr=0.0)
    bulls = [g for g in fvgs if g.direction == BULL]
    assert len(bulls) == 1
    g = bulls[0]
    assert (g.low, g.high) == (101.0, 104.0)
    assert g.index == 0 and g.confirm_index == 2
    assert g.touch_index == 4
    assert g.fill_index == 5


def test_bearish_fvg():
    ohlc = [
        (100.0, 101.0, 99.0, 99.5),
        (99.5, 99.6, 94.0, 94.5),      # displacement down
        (94.5, 96.0, 93.0, 95.0),      # high 96 < c0 low 99 -> gap (96, 99)
    ]
    candles = make_candles(ohlc)
    fvgs = detect_fvgs(candles, min_gap_atr=0.0)
    bears = [g for g in fvgs if g.direction == BEAR]
    assert len(bears) == 1
    assert (bears[0].low, bears[0].high) == (96.0, 99.0)


def test_displacement_filter_rejects_small_gaps():
    candles = synthetic_candles(n=4000, seed=3)
    loose = detect_fvgs(candles, min_gap_atr=0.0)
    strict = detect_fvgs(candles, min_gap_atr=1.0)
    assert len(strict) < len(loose)
    loose_keys = {(g.index, g.direction) for g in loose}
    assert all((g.index, g.direction) in loose_keys for g in strict)


def test_gap_geometry_on_synthetic():
    candles = synthetic_candles(n=4000, seed=3)
    for g in detect_fvgs(candles, min_gap_atr=0.0):
        assert g.low < g.high
        if g.direction == BULL:
            assert candles.high[g.index] == g.low
            assert candles.low[g.index + 2] == g.high
        else:
            assert candles.low[g.index] == g.high
            assert candles.high[g.index + 2] == g.low
