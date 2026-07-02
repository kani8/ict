from ict_backtest.core import BEAR, BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.detectors import detect_structure, detect_swings

from conftest import make_candles


def _flat(p):
    return (p, p, p, p)


def test_bos_then_mss():
    # swing high 110 @2 (confirm 4), pullback low 100 @6 (confirm 8),
    # rally closes above 110 @10 -> bullish BOS,
    # then collapse closes below 100 @14 -> bearish MSS.
    prices = [105, 108, 110, 108, 105, 103, 100, 103, 105, 108,
              111, 112, 108, 104, 99, 98]
    candles = make_candles([_flat(p) for p in prices])
    swings = detect_swings(candles, k=2)
    events = detect_structure(candles, swings)
    assert len(events) == 2
    bos, mss = events
    assert bos.direction == BULL and bos.kind == "BOS"
    assert bos.index == 10 and bos.level == 110
    assert mss.direction == BEAR and mss.kind == "MSS"
    assert mss.level == 100


def test_structure_invariants_on_synthetic():
    candles = synthetic_candles(n=5000, seed=11)
    swings = detect_swings(candles, k=3)
    events = detect_structure(candles, swings)
    assert len(events) > 10
    swing_by_index = {(s.index, s.kind): s for s in swings}
    prev_dir = 0
    for ev in events:
        # close actually broke the level, in the stated direction
        c = candles.close[ev.index]
        assert (c > ev.level) if ev.direction == BULL else (c < ev.level)
        # the broken swing exists, was confirmed before the break bar
        s = swing_by_index[(ev.swing_index, ev.direction)]
        assert s.price == ev.level
        assert s.confirm_index <= ev.index
        # BOS continues the previous direction; MSS flips it
        if prev_dir == 0:
            assert ev.kind == "BOS"
        else:
            assert ev.kind == ("BOS" if ev.direction == prev_dir else "MSS")
        prev_dir = ev.direction
