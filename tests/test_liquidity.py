from ict_backtest.core import BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.detectors import detect_liquidity_pools, detect_swings

from conftest import make_candles


def _flat(p):
    return (p, p, p, p)


def test_sweep_vs_run_classification():
    # swing high 105 @2 (k=2, confirm 4); bar 6 wicks above and closes back
    # below -> sweep.  Later swing high 106 @9; bar 13 closes through -> run.
    ohlc = [
        _flat(100), _flat(103), _flat(105), _flat(103), _flat(101),   # 0-4
        (101, 102, 100, 101.5),                                       # 5
        (101.5, 105.8, 101.0, 103.0),                                 # 6 sweep of 105
        (103, 104, 102, 103.5),                                       # 7
        (103.5, 105.5, 103.0, 105.0),                                 # 8
        (105.0, 106.0, 104.5, 105.5),                                 # 9 swing high 106
        (105.5, 105.6, 104.0, 104.5),                                 # 10
        (104.5, 105.0, 103.5, 104.0),                                 # 11
        (104.0, 105.5, 103.8, 105.2),                                 # 12
        (105.2, 107.5, 105.0, 107.2),                                 # 13 run through 106
    ]
    candles = make_candles(ohlc)
    swings = detect_swings(candles, k=2)
    pools = detect_liquidity_pools(candles, swings, eq_tol_atr=0.0)
    buy_side = [p for p in pools if p.side == BULL]
    levels = {p.level: p for p in buy_side}
    assert 105.0 in levels and 106.0 in levels
    swept = levels[105.0]
    assert swept.taken_index == 6 and swept.taken_kind == "sweep"
    ran = levels[106.0]
    assert ran.taken_index == 13 and ran.taken_kind == "run"


def test_equal_highs_merge_into_cluster():
    # second equal high sits just *below* the first: if it poked above, it
    # would take the pool out instead of building the cluster
    prices = [100, 101, 105.1, 100, 99, 98, 99, 100, 105, 100, 99, 98, 97, 96]
    candles = make_candles([_flat(p) for p in prices])
    swings = detect_swings(candles, k=2)
    pools = detect_liquidity_pools(candles, swings, eq_tol_atr=1.0)  # generous tol
    clusters = [p for p in pools if p.side == BULL and p.is_equal_cluster]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.swing_indices == [2, 8]
    assert cluster.level == 105.1
    assert cluster.confirm_index == 10
    # the append-only single-member snapshot must still exist (causality)
    singles = [p for p in pools if p.side == BULL and p.swing_indices == [2]]
    assert len(singles) == 1


def test_pool_invariants_on_synthetic():
    candles = synthetic_candles(n=4000, seed=23)
    swings = detect_swings(candles, k=3)
    pools = detect_liquidity_pools(candles, swings)
    assert len(pools) > 20
    for p in pools:
        if p.taken_index == -1:
            assert p.taken_kind is None
            continue
        assert p.taken_index > p.confirm_index
        bar_h = candles.high[p.taken_index]
        bar_l = candles.low[p.taken_index]
        bar_c = candles.close[p.taken_index]
        if p.side == BULL:
            assert bar_h > p.level
            assert (p.taken_kind == "sweep") == (bar_c <= p.level)
        else:
            assert bar_l < p.level
            assert (p.taken_kind == "sweep") == (bar_c >= p.level)
