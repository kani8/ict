"""Tests for the Study-V2 faithfulness features: inversion FVGs, DST-correct
killzones, news blackouts, confirmation entries, and breakeven management."""

import numpy as np
import pandas as pd
import pytest

from ict_backtest.core import BEAR, BULL, FVG
from ict_backtest.data import synthetic_candles
from ict_backtest.data.news import (
    blackout_mask,
    default_events,
    fomc_events,
    load_news_csv,
    nfp_events,
)
from ict_backtest.detectors import detect_fvgs
from ict_backtest.detectors.killzones import ET_BY_NAME, in_killzone
from ict_backtest.engine import Backtester, Broker, CostModel, Order
from ict_backtest.strategy import SMCConfig, SMCStrategy

from conftest import make_candles


# -- FVG inversion ------------------------------------------------------------


def test_bearish_fvg_inversion_and_failure():
    ohlc = [
        (100.0, 101.0, 99.0, 99.5),    # 0
        (99.5, 99.6, 94.0, 94.5),      # 1 displacement down
        (94.5, 96.0, 93.0, 95.0),      # 2 bearish FVG zone (96, 99)
        (95.0, 95.5, 94.0, 95.0),      # 3
        (95.0, 100.5, 94.8, 100.0),    # 4 closes above 99 -> inverts bullish
        (100.0, 100.5, 97.0, 98.0),    # 5 retest into the inverted gap
        (98.0, 98.5, 94.0, 95.0),      # 6 closes below 96 -> inversion fails
    ]
    candles = make_candles(ohlc)
    g = [g for g in detect_fvgs(candles, min_gap_atr=0.0) if g.direction == BEAR][0]
    assert (g.low, g.high) == (96.0, 99.0)
    assert g.invert_index == 4
    assert g.invert_fail_index == 6


def test_bullish_fvg_inversion():
    ohlc = [
        (100.0, 101.0, 99.5, 100.5),
        (100.5, 106.0, 100.4, 105.5),
        (105.5, 107.0, 104.0, 106.5),  # bullish FVG (101, 104)
        (106.5, 107.0, 105.0, 106.0),
        (106.0, 106.5, 100.0, 100.5),  # closes below 101 -> inverts bearish
    ]
    candles = make_candles(ohlc)
    g = [g for g in detect_fvgs(candles, min_gap_atr=0.0) if g.direction == BULL][0]
    assert g.invert_index == 4
    assert g.invert_fail_index == -1


def test_find_poi_ifvg():
    candles = synthetic_candles(n=500, seed=1)
    strat = SMCStrategy(candles, SMCConfig(use_killzones=False))
    strat.cfg = SMCConfig(poi_priority=("ifvg",))
    strat.order_blocks = []
    strat.fvgs = [
        FVG(index=90, low=99.0, high=100.0, direction=BEAR, confirm_index=92,
            invert_index=96, invert_fail_index=120),   # inverted bullish in-leg
        FVG(index=91, low=98.0, high=98.5, direction=BEAR, confirm_index=93,
            invert_index=-1),                           # never inverted
    ]
    poi = strat._find_poi(BULL, 94, 100)
    assert poi == (99.0, 100.0, 120)
    assert strat._find_poi(BULL, 94, 125) is None      # inversion already failed
    assert strat._find_poi(BEAR, 94, 100) is None      # wrong direction


# -- DST-correct killzones ------------------------------------------------------


def test_et_killzone_dst_correctness():
    ny = ET_BY_NAME["new_york"]  # 07:00-09:00 ET
    winter = int(pd.Timestamp("2024-01-10 07:30", tz="America/New_York").timestamp())
    summer = int(pd.Timestamp("2024-07-10 07:30", tz="America/New_York").timestamp())
    ts = np.array([winter, summer], dtype=np.int64)
    mask = in_killzone(ts, [ny], tz="America/New_York")
    assert mask.all()
    # in UTC terms the two differ by an hour (12:30 vs 11:30 UTC): a fixed
    # 12:00-14:00 UTC window would misclassify the summer bar
    utc_hours = (ts % 86400) / 3600
    assert utc_hours[0] == pytest.approx(12.5)
    assert utc_hours[1] == pytest.approx(11.5)


# -- news calendar --------------------------------------------------------------


def test_nfp_first_fridays_dst_aware():
    start = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())
    end = int(pd.Timestamp("2024-12-31", tz="UTC").timestamp())
    events = nfp_events(start, end)
    assert len(events) == 12
    jan = pd.Timestamp(events[0], unit="s", tz="UTC")
    aug = pd.Timestamp(events[7], unit="s", tz="UTC")
    assert jan.strftime("%Y-%m-%d %H:%M") == "2024-01-05 13:30"  # EST
    assert aug.strftime("%Y-%m-%d %H:%M") == "2024-08-02 12:30"  # EDT


def test_fomc_events_in_range():
    start = int(pd.Timestamp("2023-01-01", tz="UTC").timestamp())
    end = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
    events = fomc_events(start, end)
    assert len(events) == 24  # 8 meetings/year x 3 years


def test_blackout_mask_window():
    event = int(pd.Timestamp("2024-08-02 12:30", tz="UTC").timestamp())
    ts = event + np.array([-31, -30, -1, 0, 59, 60]) * 60
    mask = blackout_mask(ts.astype(np.int64), [event], before_min=30, after_min=60)
    assert mask.tolist() == [False, True, True, True, True, False]


def test_news_csv_loader(tmp_path):
    p = tmp_path / "cal.csv"
    p.write_text("datetime,impact\n2024-08-02T12:30:00Z,high\n2024-09-06T12:30:00Z,high\n")
    events = load_news_csv(p)
    assert len(events) == 2
    assert events[0] == int(pd.Timestamp("2024-08-02 12:30", tz="UTC").timestamp())


def test_news_csv_impact_filter(tmp_path):
    p = tmp_path / "cal.csv"
    p.write_text(
        "datetime,impact,event\n"
        "2024-08-02T12:30:00Z,High,NFP\n"
        "2024-08-05T14:00:00Z,medium,speech\n"
        "2024-08-14T12:30:00Z,HIGH,CPI\n"
    )
    assert len(load_news_csv(p)) == 3                            # no filter: all
    events = load_news_csv(p, impact_filter=("high",))           # case-insensitive
    assert len(events) == 2
    assert events[1] == int(pd.Timestamp("2024-08-14 12:30", tz="UTC").timestamp())


def test_default_events_sorted_and_merged():
    start = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())
    end = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp())
    events = default_events(start, end)
    assert events == sorted(events)
    assert len(events) == 12 + 8   # NFP + FOMC


# -- confirmation entries --------------------------------------------------------


def _strategy_with_await(direction, trigger, stop, expiry=10_000, death=-1):
    candles = synthetic_candles(n=600, seed=3)
    cfg = SMCConfig(use_killzones=False, entry_confirmation=True)
    strat = SMCStrategy(candles, cfg)
    strat._await = {"direction": direction, "trigger": trigger, "stop": stop,
                    "expiry": expiry, "death": death}
    broker = Broker(candles, CostModel(), 100_000.0)
    return strat, broker, candles


def test_confirmation_triggers_on_touch_and_close_back():
    strat, broker, candles = _strategy_with_await(BULL, trigger=0.0, stop=0.0)
    # pick a bar and derive trigger/stop from it so touch+confirm hold
    i = 300
    strat._await["trigger"] = float(candles.low[i]) + 1e-9
    strat._await["stop"] = float(candles.low[i]) * 0.95
    strat._process_await(i, broker)
    assert len(broker.pending) == 1
    order = next(iter(broker.pending.values()))
    assert order.type == "market" and order.side == BULL
    assert order.sl == pytest.approx(float(candles.low[i]) * 0.95)
    assert order.tp > float(candles.close[i])
    assert strat._await is None


def test_confirmation_keeps_waiting_without_touch():
    strat, broker, candles = _strategy_with_await(BULL, trigger=0.0, stop=0.0)
    i = 300
    strat._await["trigger"] = float(candles.low[i]) - 1.0   # never touched
    strat._await["stop"] = float(candles.low[i]) * 0.9
    strat._process_await(i, broker)
    assert broker.pending == {}
    assert strat._await is not None


def test_confirmation_dropped_on_violation_expiry_and_death():
    strat, broker, candles = _strategy_with_await(BULL, trigger=1.0, stop=1e12)
    strat._process_await(300, broker)                       # close <= stop
    assert strat._await is None and broker.pending == {}

    strat, broker, _ = _strategy_with_await(BULL, trigger=1.0, stop=0.5, expiry=299)
    strat._process_await(300, broker)                       # expired
    assert strat._await is None

    strat, broker, _ = _strategy_with_await(BULL, trigger=1.0, stop=0.5, death=300)
    strat._process_await(300, broker)                       # POI died
    assert strat._await is None


def test_confirmation_mode_end_to_end_produces_market_entries():
    candles = synthetic_candles(n=10_000, seed=13, base_vol=0.004)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, min_rr=1.0, entry_confirmation=True,
                    poi_priority=("ifvg", "fvg", "ob"))
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, SMCStrategy(candles, cfg))
    assert len(result.trades) >= 3
    assert all(t.tag.startswith("smc_confirm") for t in result.trades)


# -- breakeven management ---------------------------------------------------------


def test_breakeven_moves_stop_to_entry_and_r_uses_initial_risk():
    ohlc = [
        (100, 100, 100, 100),   # submit market long, sl 95 (risk 5)
        (100, 100, 100, 100),   # entry at open 100
        (100, 106, 100, 105.5), # +1.1R close -> strategy should move sl to 100
        (105, 105.5, 99, 99.5), # falls back through entry -> stopped at 100
    ]
    candles = make_candles(ohlc)

    class BEStrategy:
        def __init__(self, cfg):
            self.cfg = cfg
            self.candles = candles

        def on_bar(self, i, broker):
            if i == 0:
                broker.submit(Order(side=BULL, qty=1.0, sl=95.0, tp=0.0))
            SMCStrategy._manage(self, i, broker)

    bt = Backtester(cost=CostModel(0, 0, 0), initial_equity=1000)
    result = bt.run(candles, BEStrategy(SMCConfig(breakeven_r=1.0)))
    t = result.trades[0]
    assert t.reason == "sl"
    assert t.exit_price == pytest.approx(100.0)       # breakeven, not 95
    assert t.pnl == pytest.approx(0.0)
    assert t.sl == pytest.approx(95.0)                # trade records initial stop
    assert t.r_multiple == pytest.approx(0.0)         # risk basis = initial 5


# -- lookahead safety of the V2 path ----------------------------------------------


def test_v2_prefix_consistency():
    from test_no_lookahead import RecordingStrategy

    cfg = SMCConfig(swing_k=3, htf_multiplier=8, use_killzones=False,
                    require_ote=False, require_discount=False, min_rr=1.0,
                    poi_priority=("ifvg", "fvg", "ob"), entry_confirmation=True,
                    breakeven_r=1.0, avoid_news=True)
    candles = synthetic_candles(n=6000, seed=99, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    cutoff = 3500

    full = RecordingStrategy(candles, cfg)
    bt.run(candles, full)
    full_subs = [s for s in full.submissions if s[0] < cutoff]

    prefix = RecordingStrategy(candles.slice(0, cutoff), cfg)
    bt.run(candles.slice(0, cutoff), prefix)

    assert len(full_subs) > 0
    assert prefix.submissions == full_subs
