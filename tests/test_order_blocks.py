from ict_backtest.core import BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.detectors import detect_order_blocks, detect_structure, detect_swings

from conftest import make_candles


def test_bullish_ob_is_last_down_candle_before_impulse():
    #                 o      h      l      c
    ohlc = [
        (104.0, 105.0, 103.0, 104.5),  # 0
        (104.5, 106.0, 104.0, 105.5),  # 1
        (105.5, 107.0, 105.0, 106.0),  # 2  swing high 107 (k=2, confirm 4)
        (106.0, 106.5, 102.0, 103.0),  # 3  red pullback
        (103.0, 103.5, 100.0, 101.0),  # 4  red pullback -> the order block
        (101.0, 105.0, 100.5, 104.5),  # 5  impulse up begins
        (104.5, 108.5, 104.0, 108.0),  # 6  closes above 107 -> bullish break
        (108.0, 109.0, 107.0, 108.5),  # 7
        (108.5, 109.5, 100.5, 102.0),  # 8  trades back into the zone -> mitigated
        (102.0, 102.5, 99.0, 99.5),    # 9  closes below zone low -> invalidated
    ]
    candles = make_candles(ohlc)
    swings = detect_swings(candles, k=2)
    events = detect_structure(candles, swings)
    assert events and events[0].direction == BULL and events[0].index == 6

    blocks = detect_order_blocks(candles, events)
    ob = blocks[0]
    assert ob.direction == BULL
    assert ob.index == 4                      # last red candle before the up-leg
    assert (ob.low, ob.high) == (100.0, 103.5)
    assert ob.created_index == 6
    assert ob.mitigated_index == 8
    assert ob.invalidated_index == 9
    assert ob.is_breaker_at(9) and not ob.is_breaker_at(8)


def test_ob_lifecycle_ordering_on_synthetic():
    candles = synthetic_candles(n=5000, seed=17)
    swings = detect_swings(candles, k=3)
    events = detect_structure(candles, swings)
    blocks = detect_order_blocks(candles, events)
    assert len(blocks) > 10
    for ob in blocks:
        assert ob.low <= ob.high
        assert ob.index <= ob.created_index
        if ob.mitigated_index != -1:
            assert ob.mitigated_index > ob.created_index
        if ob.invalidated_index != -1:
            # a close through the zone necessarily trades into it first
            assert ob.mitigated_index != -1
            assert ob.mitigated_index <= ob.invalidated_index
