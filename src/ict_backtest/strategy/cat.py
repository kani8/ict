"""CAT — "categorical trading": consolidation vs. direction price action.

A faithful mechanization of the categorical-trading (CAT) approach as
described by its author (ImanTrading), built for this harness's
no-lookahead discipline.  The source material is discretionary; every
rule below is traced to an explicit claim in the source, and anything
the author leaves to "personal preference" is a config knob with the
author's own stated preference as the default.

The fundamentals, verbatim from the source:

* "All price action exists on a spectrum of extremes somewhere between
  consolidation and direction."  → per-bar category from a Kaufman-style
  efficiency ratio over a trailing window: high efficiency = direction,
  low = consolidation, in between = uncategorizable ("chaos"), no trade.
* Consolidation: "price is more likely to stay where it has already
  been" → trade *toward* already-traded prices: profit target inside
  the recent range; never long near the top / short near the bottom
  (the stated "extreme high-probability loss").  Entries "follow the
  candles" (trade in the direction the last candle closed) rather than
  timing reversals at the extremes.
* Direction: "price is more likely to go to a new area" → trade with
  the trend, target beyond the traded range ("new area"), stop inside.
  The stated high-probability loss — fading the trend for a pullback —
  is structurally impossible here.
* Brackets scale with candle size, not points: "trades are based on the
  current size of the candles ... all you do is adjust the target and
  stop-loss" — target ≈ half the recent average candle range (his 10-pt
  target on 25-pt candles), read through ATR-of-period-1 (i.e. the raw
  true range of each candle).
* Risk:reward defaults to 1:1 — "starting with a one-to-one risk reward
  ratio ... you only need a small edge to flip that coin in your favor".
* "If price action keeps switching from direction to consolidation ...
  what type of trade should you take?  None."  → the coarse category
  must have been stable for ``stability_bars`` closed bars.
* "I also avoid taking a trade after a high-volatility candle ... a huge
  candle is a break of the recent structure and is therefore the start
  of a new price action category" → no entries for ``outlier_skip_bars``
  bars after any candle whose true range exceeds ``outlier_mult`` × the
  prevailing average candle size.
* Timeframe agnosticism is free: everything is expressed in units of
  the trailing average true range, so the same config trades 30-second
  or 30-minute candles identically (his central claim).

Personal-preference knobs (defaults = the author's stated practice):

* ``session_et`` — he trades 09:33–09:50 ET only; default off because he
  is explicit that the session is personal, not part of the system.
* ``require_stop_outside`` — the idealized drawing puts consolidation
  stops *outside* the range, but his live implementation uses small
  brackets "to just play around in the middle"; default off (= his
  live behavior), on = the textbook drawing.
* ``avoid_extremes_frac`` — how much of the range edge is off-limits for
  with-candle consolidation entries (the "don't long the top" band).

A second source — the author's trading-journey retrospective — adds the
elements below.  Rules that are process/psychology (journaling, reminder
documents, simulator use, prop-firm progression) are deliberately NOT
mechanized: they concern the trader, not the trade stream.  What is
mechanizable, is:

* **Category toggles** (``trade_consolidation`` / ``trade_direction``) —
  he traded consolidation-only for a period after the data showed he
  executed direction poorly; "you don't need to adapt and trade
  everything."
* **Volatility band** (``vol_ref_window`` + ``vol_band_low/high``) — his
  timeframe-switching trick "artificially changes volatility ... until I
  get the exact size of candles that I want"; on a fixed timeframe the
  honest equivalent is refusing bars whose candle size leaves a band
  around its long-run typical value.
* **Day-extreme veto** (``avoid_day_extreme_atr``) — "I don't take
  trades when price action is at the low or high of day", and the
  journey's repeated warning against high/low-of-day break-chasing (the
  "scratch-ticket" drift that hit max loss 5 of 7 days).
* **Session discipline** (``max_daily_loss_r``, ``max_trades_per_day``)
  — his max daily loss (−30 points in the drift episode) and the
  strategy-completeness checklist items "how many trades are permitted /
  when trading should stop", enforced externally ("configure the
  platform to lock further trading"), which an engine rule reproduces.
* **Limit-order execution** (``entry_order = "limit"``) — his final
  refinement: "carefully placed limit orders rather than market orders
  ... changes execution but not the core edge."
* **Conditional breakeven** (``breakeven_r``) — tested by him with the
  conclusion it must be condition-tested, never universal; his final
  system moves nothing, so the default is off.
* **Outlier context** (``outlier_block_mode``) — the journey's
  correction that following a large candle "depends on the surrounding
  price action": momentum continuation is legitimate in strong
  direction, so ``"direction_exempt"`` implements the contextual
  reading; the default stays his stated flat rule.

Every per-bar feature is a trailing-window statistic of bars ``<= i``,
so the strategy inherits the harness's prefix-consistency guarantee.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import BEAR, BULL, Candles
from ..engine import Broker, Order

# coarse per-bar categories
CAT_NONE = 0          # uncategorizable — "chaos", no edge, no trade
CAT_DIRECTION = 1
CAT_CONSOLIDATION = 2


@dataclass(slots=True)
class CATConfig:
    # -- categorization --------------------------------------------------------
    regime_window: int = 24        # trailing bars scored for the category
    er_direction: float = 0.40     # efficiency ratio >= this → direction
    er_consolidation: float = 0.15 # efficiency ratio <= this → consolidation
                                   # (between the two = chaos, no trade)
    stability_bars: int = 4        # coarse category unchanged this many bars
                                   # ("switching too fast → take no trade")

    # -- bracket sizing ("based on the current size of the candles") -----------
    candle_size_window: int = 10   # bars averaged for "recent candle size"
    bracket_frac: float = 0.5      # target = this × avg candle range ("just
                                   # under half the size of the recent candles")
    rr: float = 1.0                # target distance / stop distance (1:1 start)

    # -- entry filters ----------------------------------------------------------
    consolidation_mode: str = "follow" # "follow" = his live play (with the
                                       # candle, toward already-traded prices);
                                       # "fade" = the stated equally-valid
                                       # alternative (short the top band, long
                                       # the bottom band of the range)
    avoid_extremes_frac: float = 0.25  # no longs in the top / shorts in the
                                       # bottom `frac` of the range (the stated
                                       # extreme high-probability loss); in
                                       # fade mode, the same band is where
                                       # fades are taken (in reverse)
    require_new_area: bool = True      # direction target must reach beyond the
                                       # trailing range ("go to a new area")
    require_stop_outside: bool = False # consolidation stop beyond the range
                                       # edge (textbook drawing; off = his live
                                       # small-bracket middle play)
    outlier_mult: float = 2.5      # candle range > this × avg = outlier
    outlier_skip_bars: int = 2     # entry blackout after an outlier candle
    outlier_block_mode: str = "always"  # "always" = his stated rule (a huge
                                        # candle is a 50/50 on the next
                                        # category); "direction_exempt" = the
                                        # later contextual refinement (momentum
                                        # continuation is legitimate in strong
                                        # direction); "off"

    # -- category toggles --------------------------------------------------------
    # "you don't need to adapt and trade everything"; the author himself
    # traded consolidation-only for a period after finding he executed
    # direction poorly ("ignore Direction ... I wait for consolidation or
    # do nothing").  Both on = the complete system.
    trade_consolidation: bool = True
    trade_direction: bool = True

    # -- volatility band (the timeframe-switching trick, mechanized) -------------
    # He targets a preferred candle-size band by changing chart timeframe
    # ("artificially changing volatility ... until I get the exact size of
    # candles that I want").  A backtest has a fixed timeframe, so the
    # equivalent is refusing bars whose candle size sits outside a band
    # around its own long-run typical value.  0 window = off (default).
    vol_ref_window: int = 0        # rolling-median window for typical candle size
    vol_band_low: float = 0.0      # skip when avg_tr/typical < this (0 = no floor)
    vol_band_high: float = 0.0     # skip when avg_tr/typical > this (0 = no cap)

    # -- day-extreme veto ---------------------------------------------------------
    # "I don't take trades when price action is at the low or high of day"
    # (his personal, data-derived rule).  Skip entries within this many
    # average-candle units of the running ET-day high/low.  0 = off.
    avoid_day_extreme_atr: float = 0.0

    # -- execution ----------------------------------------------------------------
    # His final refinement: "carefully placed limit orders rather than
    # market orders — changes execution but not the core edge".
    entry_order: str = "market"    # "market" | "limit"
    limit_offset_frac: float = 0.0 # limit improvement vs close, in avg-TR units
    limit_expiry_bars: int = 3     # bars a resting limit stays working

    # -- risk / exits ------------------------------------------------------------
    risk_pct: float = 1.0          # equity % risked per trade
    max_leverage: float = 5.0
    exit_on_flip: bool = False     # flat when the category flips against the
                                   # open trade (off: he lets the bracket
                                   # decide — "no trade will work every time")
    breakeven_r: float = 0.0       # move stop to entry at +N R.  He tested
                                   # auto-breakeven and concluded it must be
                                   # condition-tested, not universal; his final
                                   # system is rigid no-stop-moving → 0 = off
    # session discipline: "determine the best max daily loss" / "how many
    # trades are permitted, when trading should stop" — values are personal
    # and data-derived, so both default off
    max_daily_loss_r: float = 0.0  # stop for the ET day after losing this many R
    max_trades_per_day: int = 0    # entry cap per ET day (0 = unlimited)

    # -- time filter --------------------------------------------------------------
    session_et: str = ""           # "HH:MM-HH:MM" America/New_York window;
                                   # empty = trade all bars (session choice is
                                   # explicitly personal in the source)

    @classmethod
    def from_toml(cls, path: str | Path) -> "CATConfig":
        raw = tomllib.loads(Path(path).read_text())
        section = raw.get("strategy", raw)
        known = {f.name for f in fields(cls)}
        unknown = set(section) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**section)


def efficiency_ratio(close: np.ndarray, window: int) -> np.ndarray:
    """Kaufman efficiency ratio of the trailing ``window`` bars.

    ``er[i] = |close[i] - close[i-window]| / sum(|close diffs|)`` over the
    same span — 1.0 for a straight line (pure direction), → 0 for a path
    that goes nowhere (consolidation).  NaN until enough history exists.
    Value at i uses closes up to and including i only.
    """
    n = len(close)
    er = np.full(n, np.nan)
    if n <= window:
        return er
    diffs = np.abs(np.diff(close))
    csum = np.concatenate(([0.0], np.cumsum(diffs)))
    path = csum[window:] - csum[:-window]          # sum of |diffs| over window
    net = np.abs(close[window:] - close[:-window])
    with np.errstate(invalid="ignore", divide="ignore"):
        er[window:] = np.where(path > 0, net / path, 0.0)
    return er


def true_range(candles: Candles) -> np.ndarray:
    h, l, c = candles.high, candles.low, candles.close
    tr = np.empty(len(candles))
    tr[0] = h[0] - l[0]
    prev = c[:-1]
    tr[1:] = np.maximum(h[1:] - l[1:],
                        np.maximum(np.abs(h[1:] - prev), np.abs(l[1:] - prev)))
    return tr


def _session_mask(ts: np.ndarray, session_et: str) -> np.ndarray:
    """True where the bar's open time falls inside an ET wall-clock window."""
    start_s, end_s = session_et.split("-")
    t = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    minutes = t.hour * 60 + t.minute
    sh, sm = (int(x) for x in start_s.split(":"))
    eh, em = (int(x) for x in end_s.split(":"))
    lo, hi = sh * 60 + sm, eh * 60 + em
    m = (minutes >= lo) & (minutes < hi) if lo <= hi else (minutes >= lo) | (minutes < hi)
    return np.asarray(m)


class CATStrategy:
    """Consolidation/direction categorical strategy over the Broker facade."""

    def __init__(self, candles: Candles, config: CATConfig | None = None) -> None:
        self.cfg = cfg = config or CATConfig()
        if cfg.consolidation_mode not in ("follow", "fade"):
            raise ValueError("consolidation_mode must be 'follow' or 'fade'")
        if cfg.entry_order not in ("market", "limit"):
            raise ValueError("entry_order must be 'market' or 'limit'")
        if cfg.outlier_block_mode not in ("always", "direction_exempt", "off"):
            raise ValueError("outlier_block_mode must be 'always', "
                             "'direction_exempt', or 'off'")
        self.candles = candles
        n = len(candles)
        w = cfg.regime_window

        close = candles.close
        self.er = efficiency_ratio(close, w)

        # trailing range of the last `regime_window` bars, inclusive of i —
        # "where price has already been"
        hs = pd.Series(candles.high).rolling(w, min_periods=w)
        ls = pd.Series(candles.low).rolling(w, min_periods=w)
        self.range_high = hs.max().to_numpy()
        self.range_low = ls.min().to_numpy()

        # "the current size of the candles" — ATR(1) averaged over a short
        # window, exactly the glance he takes at the period-1 ATR pane
        tr = true_range(candles)
        self.avg_tr = (pd.Series(tr).rolling(cfg.candle_size_window,
                                             min_periods=cfg.candle_size_window)
                       .mean().to_numpy())

        # per-bar coarse category + trend sign where directional
        self.category = np.full(n, CAT_NONE, dtype=np.int8)
        self.trend = np.zeros(n, dtype=np.int8)
        valid = ~np.isnan(self.er)
        self.category[valid & (self.er >= cfg.er_direction)] = CAT_DIRECTION
        self.category[valid & (self.er <= cfg.er_consolidation)] = CAT_CONSOLIDATION
        dirmask = self.category == CAT_DIRECTION
        net = np.zeros(n)
        net[w:] = close[w:] - close[:-w]
        self.trend[dirmask] = np.sign(net[dirmask]).astype(np.int8)

        # stability: the category at i held for the last `stability_bars` bars
        self.stable = np.zeros(n, dtype=bool)
        k = max(1, cfg.stability_bars)
        if n >= k:
            cat = self.category
            ok = cat != CAT_NONE
            same = np.ones(n, dtype=bool)
            for lag in range(1, k):
                same[lag:] &= cat[lag:] == cat[:-lag]
                same[:lag] = False
            self.stable = ok & same

        # outlier blackout: any recent candle much larger than the prevailing
        # size voids the category ("start of a new price action category")
        prev_avg = np.concatenate(([np.nan], self.avg_tr[:-1]))
        with np.errstate(invalid="ignore"):
            outlier = tr > cfg.outlier_mult * prev_avg
        self.blocked = np.zeros(n, dtype=bool)
        for lag in range(cfg.outlier_skip_bars + 1):
            self.blocked[lag:] |= outlier[: n - lag] if lag else outlier

        self.eligible_mask = (_session_mask(candles.ts, cfg.session_et)
                              if cfg.session_et else np.ones(n, dtype=bool))

        # ET calendar day per bar + running day high/low ("high/low of day"),
        # both causal: values at i use bars of the same day up to i only
        t = pd.to_datetime(candles.ts, unit="s", utc=True).tz_convert("America/New_York")
        self.day_key = (t.year * 10_000 + t.month * 100 + t.day).to_numpy()
        day_series = pd.Series(self.day_key)
        self.day_high = pd.Series(candles.high).groupby(day_series).cummax().to_numpy()
        self.day_low = pd.Series(candles.low).groupby(day_series).cummin().to_numpy()

        # long-run typical candle size, for the volatility-band filter
        if cfg.vol_ref_window > 0:
            self.vol_ref = (pd.Series(self.avg_tr)
                            .rolling(cfg.vol_ref_window, min_periods=cfg.vol_ref_window)
                            .median().to_numpy())
        else:
            self.vol_ref = None

        # per-ET-day discipline state
        self._day: int | None = None
        self._day_r = 0.0
        self._day_entries = 0
        self._trade_ptr = 0

        self._warmup = max(w, cfg.candle_size_window) + 1
        self.skip_counts = {
            "not_eligible_time": 0, "no_category": 0, "unstable": 0,
            "outlier_blackout": 0, "no_candle_to_follow": 0,
            "extreme_entry_veto": 0, "target_not_inside": 0,
            "target_not_new_area": 0, "stop_not_outside": 0,
            "degenerate_range": 0, "rejected_geometry": 0,
            "category_disabled": 0, "vol_out_of_band": 0,
            "at_day_extreme": 0, "daily_loss_stop": 0, "max_trades_stop": 0,
        }

    # -- trading loop -----------------------------------------------------------

    def on_bar(self, i: int, broker: Broker) -> None:
        cfg = self.cfg
        self._update_day_state(i, broker)
        if broker.position is not None:
            self._manage_breakeven(i, broker)
            if cfg.exit_on_flip and self._flipped_against(i, broker):
                broker.close_position()
            return
        if broker.pending or i < self._warmup:
            return
        if not self.eligible_mask[i]:
            self.skip_counts["not_eligible_time"] += 1
            return
        if cfg.max_daily_loss_r > 0 and self._day_r <= -cfg.max_daily_loss_r:
            self.skip_counts["daily_loss_stop"] += 1
            return
        if cfg.max_trades_per_day > 0 and self._day_entries >= cfg.max_trades_per_day:
            self.skip_counts["max_trades_stop"] += 1
            return
        cat = self.category[i]
        if cat == CAT_NONE:
            self.skip_counts["no_category"] += 1
            return
        if (cat == CAT_CONSOLIDATION and not cfg.trade_consolidation) or \
                (cat == CAT_DIRECTION and not cfg.trade_direction):
            self.skip_counts["category_disabled"] += 1
            return
        if not self.stable[i]:
            self.skip_counts["unstable"] += 1
            return
        if self.blocked[i] and cfg.outlier_block_mode != "off" and not (
                cfg.outlier_block_mode == "direction_exempt" and cat == CAT_DIRECTION):
            self.skip_counts["outlier_blackout"] += 1
            return
        avg = self.avg_tr[i]
        if not np.isfinite(avg) or avg <= 0:
            self.skip_counts["rejected_geometry"] += 1
            return
        if self.vol_ref is not None:
            ref = self.vol_ref[i]
            ratio = avg / ref if np.isfinite(ref) and ref > 0 else np.nan
            if not np.isfinite(ratio) \
                    or (cfg.vol_band_low > 0 and ratio < cfg.vol_band_low) \
                    or (cfg.vol_band_high > 0 and ratio > cfg.vol_band_high):
                self.skip_counts["vol_out_of_band"] += 1
                return

        price = float(self.candles.close[i])
        if cfg.avoid_day_extreme_atr > 0 and (
                self.day_high[i] - price < cfg.avoid_day_extreme_atr * avg
                or price - self.day_low[i] < cfg.avoid_day_extreme_atr * avg):
            self.skip_counts["at_day_extreme"] += 1
            return

        tp_dist = cfg.bracket_frac * avg
        sl_dist = tp_dist / cfg.rr
        hi, lo = float(self.range_high[i]), float(self.range_low[i])

        if cat == CAT_CONSOLIDATION:
            order = self._consolidation_entry(i, price, tp_dist, sl_dist, hi, lo)
        else:
            order = self._direction_entry(i, price, tp_dist, sl_dist, hi, lo)
        if order is None:
            return
        if cfg.entry_order == "limit":
            entry = price - order.side * cfg.limit_offset_frac * avg
            shift = entry - price   # keep bracket distances anchored to the fill
            order.type = "limit"
            order.price = entry
            order.sl += shift
            order.tp += shift
            order.expiry_index = i + max(1, cfg.limit_expiry_bars)
        else:
            order.expiry_index = i + 1   # market entry at the next bar only
        qty = broker.equity * cfg.risk_pct / 100.0 / sl_dist
        qty = min(qty, broker.equity * cfg.max_leverage / price)
        if qty <= 0:
            self.skip_counts["rejected_geometry"] += 1
            return
        order.qty = qty
        broker.submit(order)
        self._day_entries += 1

    def _update_day_state(self, i: int, broker: Broker) -> None:
        """Roll the ET-day counters and fold in newly closed trades' R."""
        day = int(self.day_key[i])
        if day != self._day:
            self._day, self._day_r, self._day_entries = day, 0.0, 0
        while self._trade_ptr < len(broker.trades):
            t = broker.trades[self._trade_ptr]
            self._trade_ptr += 1
            if int(self.day_key[t.exit_index]) == self._day:
                r = t.r_multiple
                if not np.isnan(r):
                    self._day_r += r

    def _manage_breakeven(self, i: int, broker: Broker) -> None:
        """Move the stop to entry once the trade has run ``breakeven_r`` R."""
        cfg = self.cfg
        p = broker.position
        if cfg.breakeven_r <= 0 or p is None or p.initial_sl <= 0:
            return
        risk = abs(p.entry_price - p.initial_sl)
        if risk <= 0:
            return
        unrealized = p.side * (float(self.candles.close[i]) - p.entry_price)
        if unrealized >= cfg.breakeven_r * risk:
            if p.side == BULL and p.sl < p.entry_price:
                p.sl = p.entry_price
            elif p.side == BEAR and (p.sl > p.entry_price or p.sl == 0):
                p.sl = p.entry_price

    def _consolidation_entry(self, i: int, price: float, tp_dist: float,
                             sl_dist: float, hi: float, lo: float) -> Order | None:
        """Mean-stay trade: follow the candle toward already-traded prices."""
        cfg = self.cfg
        rng = hi - lo
        if rng <= 0:
            self.skip_counts["degenerate_range"] += 1
            return None
        pos = (price - lo) / rng
        if cfg.consolidation_mode == "fade":
            # "shorting at the top and going long at the bottom" — the
            # reverse of the stated extreme high-probability loss
            if pos >= 1.0 - cfg.avoid_extremes_frac:
                side = BEAR
            elif pos <= cfg.avoid_extremes_frac:
                side = BULL
            else:
                self.skip_counts["extreme_entry_veto"] += 1
                return None
        else:
            body = self.candles.close[i] - self.candles.open[i]
            if body == 0:
                self.skip_counts["no_candle_to_follow"] += 1
                return None
            side = BULL if body > 0 else BEAR
            # never long near the top / short near the bottom — the stated
            # extreme high-probability loss
            if side == BULL and pos > 1.0 - cfg.avoid_extremes_frac:
                self.skip_counts["extreme_entry_veto"] += 1
                return None
            if side == BEAR and pos < cfg.avoid_extremes_frac:
                self.skip_counts["extreme_entry_veto"] += 1
                return None
        tp = price + side * tp_dist
        if not (lo <= tp <= hi):   # target must be where price has been
            self.skip_counts["target_not_inside"] += 1
            return None
        sl = price - side * sl_dist
        if cfg.require_stop_outside and (sl > lo if side == BULL else sl < hi):
            self.skip_counts["stop_not_outside"] += 1
            return None
        return Order(side=side, qty=0.0, type="market", sl=sl, tp=tp, tag="cat_cons")

    def _direction_entry(self, i: int, price: float, tp_dist: float,
                         sl_dist: float, hi: float, lo: float) -> Order | None:
        """Continuation trade: with the trend, into a new area, stop inside."""
        cfg = self.cfg
        side = int(self.trend[i])
        if side == 0:
            self.skip_counts["no_category"] += 1
            return None
        body = self.candles.close[i] - self.candles.open[i]
        if (body > 0) != (side == BULL) or body == 0:  # follow, don't fade
            self.skip_counts["no_candle_to_follow"] += 1
            return None
        tp = price + side * tp_dist
        if cfg.require_new_area and (tp < hi if side == BULL else tp > lo):
            self.skip_counts["target_not_new_area"] += 1
            return None
        sl = price - side * sl_dist
        return Order(side=side, qty=0.0, type="market", sl=sl, tp=tp, tag="cat_dir")

    def _flipped_against(self, i: int, broker: Broker) -> bool:
        p = broker.position
        assert p is not None
        cat = self.category[i]
        if p.tag == "cat_cons":
            return cat == CAT_DIRECTION and self.stable[i]
        if p.tag == "cat_dir":
            if cat == CAT_CONSOLIDATION and self.stable[i]:
                return True
            return cat == CAT_DIRECTION and self.stable[i] and self.trend[i] == -p.side
        return False
