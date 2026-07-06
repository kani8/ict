"""Program S: session table, study battery, and session strategies.

The synthetic fixtures build 15m bars at explicit America/New_York wall
times, so anchor arithmetic, DST handling, and early-close exclusion are
exercised against known prices.
"""

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from ict_backtest.analytics.session_study import (
    fomc_rows,
    ibs_rows,
    intraday_momentum_rows,
    orb_rows,
    overnight_rows,
    run_session_battery,
    render_session_battery,
    session_table,
)
from ict_backtest.core import BULL, BEAR, Candles
from ict_backtest.data import synthetic_candles
from ict_backtest.engine import Backtester, Broker, CostModel
from ict_backtest.strategy import (
    IntradayMomentumStrategy,
    OpeningRangeBreakoutStrategy,
    SessionConfig,
)

ET = ZoneInfo("America/New_York")
ZERO_COST = CostModel(spread_bps=0.0, commission_bps=0.0, slippage_bps=0.0)


def make_session_candles(days: list[tuple[str, dict[int, tuple], int]]) -> Candles:
    """Bars at explicit ET wall times.

    ``days`` items: (date "YYYY-MM-DD", {minute_of_day: (o,h,l,c)}, last_minute)
    where bars run every 15 minutes from 09:30 through ``last_minute``
    inclusive; explicit OHLC overrides the flat default (100,100,100,100).
    """
    ts, o, h, low, c = [], [], [], [], []
    for date, overrides, last_minute in days:
        y, mo, d = map(int, date.split("-"))
        for minute in range(570, last_minute + 1, 15):
            wall = pd.Timestamp(year=y, month=mo, day=d, hour=minute // 60,
                                minute=minute % 60, tz=ET)
            ts.append(int(wall.timestamp()))
            bar = overrides.get(minute, (100.0, 100.0, 100.0, 100.0))
            o.append(bar[0])
            h.append(bar[1])
            low.append(bar[2])
            c.append(bar[3])
    return Candles(ts=np.array(ts, dtype=np.int64), open=np.array(o), high=np.array(h),
                   low=np.array(low), close=np.array(c), volume=np.ones(len(ts)),
                   timeframe_s=900)


def flat_day(date: str, last_minute: int = 960) -> tuple[str, dict, int]:
    return (date, {}, last_minute)


# ---------------------------------------------------------------------------
# session_table
# ---------------------------------------------------------------------------


def test_session_table_anchors_and_exclusion():
    candles = make_session_candles([
        ("2024-01-02", {570: (100, 101, 99, 100.5), 585: (100.5, 102, 100, 101),
                        825: (101, 101, 101, 101), 915: (101, 101, 101, 102),
                        930: (102, 103, 102, 102.5), 945: (102.5, 104, 102, 103)}, 960),
        ("2024-01-03", {}, 780),                       # early close: no 15:15+ bars
        flat_day("2024-01-04"),
    ])
    t = session_table(candles)
    assert list(t["day"]) == [20240102, 20240104]      # early-close day dropped
    row = t.iloc[0]
    assert row["open_0930"] == 100.0
    assert row["p_1000"] == 101.0
    assert row["p_1530"] == 102.0
    assert row["close_1600"] == 103.0
    assert row["or_high"] == 102.0 and row["or_low"] == 99.0
    assert row["r_last"] == pytest.approx(np.log(103.0 / 102.0))
    # second included row chains prev_close across the dropped session
    assert t.iloc[1]["prev_close"] == 103.0
    assert t.iloc[1]["day_gap"] == 2


def test_session_table_rejects_non_15m():
    candles = synthetic_candles(n=100, timeframe_s=3600)
    with pytest.raises(ValueError):
        session_table(candles)


# ---------------------------------------------------------------------------
# study battery
# ---------------------------------------------------------------------------


def _battery_candles(n_days: int = 40) -> Candles:
    """Deterministic multi-day sessions with mild upward drift into the close."""
    rng = np.random.default_rng(3)
    days = []
    base = 100.0
    dates = pd.bdate_range("2024-01-02", periods=n_days, tz=ET)
    for date in dates:
        overrides = {}
        px = base
        for minute in range(570, 961, 15):
            step = rng.normal(0, 0.2) + (0.05 if minute >= 930 else 0.0)
            o_, c_ = px, px + step
            overrides[minute] = (o_, max(o_, c_) + 0.05, min(o_, c_) - 0.05, c_)
            px = c_
        days.append((date.strftime("%Y-%m-%d"), overrides, 960))
        base = px + rng.normal(0, 0.3)
    return make_session_candles(days)


def test_battery_runs_and_renders():
    candles = _battery_candles()
    fomc = [int(pd.Timestamp("2024-01-31 14:00", tz=ET).timestamp())]
    result = run_session_battery(candles, fomc_ts=fomc)
    assert result["n_sessions"] == 40
    assert {r["predictor"] for r in result["s1_intraday_momentum"]} == {"fh", "rod", "both"}
    assert len(result["s4_ibs"]) == 6                  # 5 quintiles + spread
    text = render_session_battery(result, "synthetic")
    assert "S1 intraday momentum" in text and "S3 pre-FOMC" in text


def test_study_functions_shapes():
    table = session_table(_battery_candles())
    assert len(intraday_momentum_rows(table)) == 12    # 3 predictors x (all + 3 terciles)
    assert [r["subset"] for r in orb_rows(table, _battery_candles())] == ["all", "narrow_range"]
    assert [r["subset"] for r in overnight_rows(table)] == ["overnight", "intraday"]
    fomc = [int(pd.Timestamp("2024-01-10 14:00", tz=ET).timestamp())]
    rows = fomc_rows(table, fomc)
    assert rows[0]["subset"] == "fomc_days" and rows[0]["n"] <= 1 + 4  # <5 -> nan mean
    assert ibs_rows(table)[-1]["subset"] == "q1_minus_q5"


# ---------------------------------------------------------------------------
# IntradayMomentumStrategy
# ---------------------------------------------------------------------------


def up_day(date: str, lift: float) -> tuple[str, dict, int]:
    """A session whose price sits ``lift`` above 100 from 10:00 onward."""
    overrides = {}
    for minute in range(570, 961, 15):
        px = 100.0 if minute < 585 else 100.0 + lift
        overrides[minute] = (px, px + 0.01, px - 0.01, px)
    return (date, overrides, 960)


def test_intraday_momentum_enters_long_and_exits_at_close():
    candles = make_session_candles([flat_day("2024-01-02"), up_day("2024-01-03", 2.0)])
    bt = Backtester(cost=ZERO_COST)
    strat = IntradayMomentumStrategy(candles, SessionConfig(im_predictor="both"))
    result = bt.run(candles, strat)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.side == BULL and trade.tag == "im_last30"
    minute = strat.minute
    assert minute[trade.entry_index] == 930            # fills at the 15:30 bar open
    assert minute[trade.exit_index] == 960             # flat at the 16:00 bar open
    assert trade.reason == "strategy"


def test_intraday_momentum_short_on_down_day():
    candles = make_session_candles([flat_day("2024-01-02"), up_day("2024-01-03", -2.0)])
    result = Backtester(cost=ZERO_COST).run(
        candles, IntradayMomentumStrategy(candles, SessionConfig()))
    assert len(result.trades) == 1 and result.trades[0].side == BEAR


def test_intraday_momentum_disagreement_blocks_both_mode():
    # first half hour down, rest of day up -> "both" stands aside, "rod" trades
    overrides = {}
    for minute in range(570, 961, 15):
        px = 99.0 if minute == 585 else (101.0 if minute >= 600 else 100.0)
        overrides[minute] = (px, px + 0.01, px - 0.01, px)
    candles = make_session_candles([flat_day("2024-01-02"),
                                    ("2024-01-03", overrides, 960)])
    both = Backtester(cost=ZERO_COST).run(
        candles, IntradayMomentumStrategy(candles, SessionConfig(im_predictor="both")))
    rod = Backtester(cost=ZERO_COST).run(
        candles, IntradayMomentumStrategy(candles, SessionConfig(im_predictor="rod")))
    assert len(both.trades) == 0
    assert len(rod.trades) == 1 and rod.trades[0].side == BULL


def test_intraday_momentum_needs_prior_close():
    candles = make_session_candles([up_day("2024-01-03", 2.0)])
    result = Backtester(cost=ZERO_COST).run(
        candles, IntradayMomentumStrategy(candles, SessionConfig()))
    assert result.trades == []                          # no prev close -> no signal


# ---------------------------------------------------------------------------
# OpeningRangeBreakoutStrategy
# ---------------------------------------------------------------------------


def breakout_day(date: str) -> tuple[str, dict, int]:
    """Up first bar, 99-101 opening range, upside break at 11:00."""
    overrides = {}
    for minute in range(570, 961, 15):
        if minute == 570:
            overrides[minute] = (100.0, 101.0, 99.0, 100.8)   # up bar -> long bias
        elif minute == 585:
            overrides[minute] = (100.8, 100.9, 100.0, 100.2)
        elif minute == 660:                                    # 11:00 breakout bar
            overrides[minute] = (100.5, 102.0, 100.4, 101.8)
        elif minute > 660:
            overrides[minute] = (101.8, 101.9, 101.7, 101.8)
        else:
            overrides[minute] = (100.3, 100.6, 100.1, 100.4)
    return (date, overrides, 960)


def test_orb_enters_on_stop_and_exits_at_close():
    candles = make_session_candles([breakout_day("2024-01-03")])
    strat = OpeningRangeBreakoutStrategy(candles, SessionConfig())
    result = Backtester(cost=ZERO_COST).run(candles, strat)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.side == BULL and trade.tag == "orb30"
    assert trade.entry_price == pytest.approx(101.0)   # the opening-range high
    assert trade.sl == pytest.approx(99.0)             # opposite extreme
    assert strat.minute[trade.entry_index] == 660
    assert strat.minute[trade.exit_index] == 960
    assert trade.reason == "strategy"


def test_orb_range_filter_blocks_trade():
    candles = make_session_candles([breakout_day("2024-01-03")])
    cfg = SessionConfig(orb_max_range_atr=0.1)         # 2.0 range >> 0.1 ATRs
    result = Backtester(cost=ZERO_COST).run(
        candles, OpeningRangeBreakoutStrategy(candles, cfg))
    assert result.trades == []


def test_orb_no_breakout_no_trade():
    candles = make_session_candles([flat_day("2024-01-03")])
    result = Backtester(cost=ZERO_COST).run(
        candles, OpeningRangeBreakoutStrategy(candles, SessionConfig()))
    assert result.trades == []


def test_orb_unfilled_entry_cancelled_at_cutoff():
    # breakout happens at 15:15, after the 15:00 cutoff -> order already gone
    overrides = {}
    for minute in range(570, 961, 15):
        if minute == 570:
            overrides[minute] = (100.0, 101.0, 99.0, 100.8)
        elif minute == 915:
            overrides[minute] = (100.5, 102.0, 100.4, 101.8)   # too late to fill
        else:
            overrides[minute] = (100.3, 100.6, 100.1, 100.4)
    candles = make_session_candles([("2024-01-03", overrides, 960)])
    result = Backtester(cost=ZERO_COST).run(
        candles, OpeningRangeBreakoutStrategy(candles, SessionConfig()))
    assert result.trades == []


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


def test_session_config_from_toml(tmp_path):
    path = tmp_path / "s.toml"
    path.write_text("[session]\nim_predictor = \"rod\"\norb_stop_mode = \"atr\"\n")
    cfg = SessionConfig.from_toml(path)
    assert cfg.im_predictor == "rod" and cfg.orb_stop_mode == "atr"
    path.write_text("[session]\nnot_a_key = 1\n")
    with pytest.raises(ValueError):
        SessionConfig.from_toml(path)


# ---------------------------------------------------------------------------
# no-lookahead: prefix consistency (the gold-standard test)
# ---------------------------------------------------------------------------


class _RecordingMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submissions: list[tuple] = []

    def on_bar(self, i, broker: Broker):
        before = broker._next_id
        super().on_bar(i, broker)
        for oid in range(before, broker._next_id):
            order = broker.pending.get(oid)
            if order is not None:
                self.submissions.append(
                    (i, order.side, round(order.price, 10), round(order.qty, 10),
                     round(order.sl, 10), round(order.tp, 10), order.expiry_index)
                )


class RecordingIM(_RecordingMixin, IntradayMomentumStrategy):
    pass


class RecordingORB(_RecordingMixin, OpeningRangeBreakoutStrategy):
    pass


@pytest.mark.parametrize("cls", [RecordingIM, RecordingORB])
@pytest.mark.parametrize("cutoff", [2500, 4000])
def test_prefix_consistency_sessions(cls, cutoff):
    # 24/7 synthetic 15m bars: every ET day is a complete session
    candles = synthetic_candles(n=6000, seed=11, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)

    full = cls(candles)
    bt.run(candles, full)
    full_subs = [s for s in full.submissions if s[0] < cutoff]

    prefix = cls(candles.slice(0, cutoff))
    bt.run(candles.slice(0, cutoff), prefix)

    assert len(full_subs) > 0, "test is vacuous: no orders before the cutoff"
    assert prefix.submissions == full_subs
