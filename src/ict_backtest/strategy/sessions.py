"""Program S, Stage 2: executable session-anomaly strategies.

Two mechanizations of the literature hypotheses tested by
``analytics/session_study.py`` (see ``reports/PREREGISTRATION_S.md``):

* ``IntradayMomentumStrategy`` — trade the last half hour (15:30-16:00
  ET) in the direction of the day-so-far return (Gao/Han/Li/Zhou 2018;
  Baltussen/Da/Lammers/Martens 2021).  Signal is computed at the close
  of the 15:15 bar; entry is a market order filling at the 15:30 bar's
  open; exit is a market close filling at the 16:00 bar's open.  A wide
  protective ATR stop bounds the loss and provides the R basis (the
  papers trade stopless; the stop is declared in the preregistration).
* ``OpeningRangeBreakoutStrategy`` — Crabel/Zarattini-style 30-minute
  opening-range breakout, direction-filtered by the first bar, entered
  on a stop order at the range extreme, stopped at the opposite extreme
  (or an ATR distance), flat by the close.

Both act only on closed bars, use only bar-open timestamps for session
arithmetic, trade at most once per ET session, and force-flat on any
day change (the safety net for early closes, which lack 15:30+ bars).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np

from ..detectors.killzones import (
    RTH_CLOSE,
    RTH_FH_END,
    RTH_OPEN,
    RTH_ROD_END,
    et_minutes_days,
)
from ..core import BEAR, BULL, Candles, atr as compute_atr
from ..engine import Broker, Order


@dataclass(slots=True)
class SessionConfig:
    tz: str = "America/New_York"
    atr_period: int = 14
    risk_pct: float = 1.0          # equity % risked per trade
    max_leverage: float = 5.0

    # -- intraday momentum -----------------------------------------------------
    im_predictor: str = "both"     # "fh" | "rod" | "both" (signs must agree)
    im_min_abs_signal: float = 0.0  # min |rest-of-day logret| to act (0 = any)
    im_stop_atr: float = 3.0       # protective stop distance, ATRs

    # -- opening-range breakout --------------------------------------------------
    orb_stop_mode: str = "range"   # "range" (opposite extreme) | "atr"
    orb_stop_atr: float = 2.0      # stop distance when orb_stop_mode = "atr"
    orb_take_profit_r: float = 0.0  # target in R (0 = none, exit at close)
    orb_entry_cutoff_minute: int = 900  # cancel unfilled entries at 15:00 ET
    orb_min_range_atr: float = 0.0  # skip days with range below this (0 = off)
    orb_max_range_atr: float = 0.0  # skip days with range above this (0 = off)

    @classmethod
    def from_toml(cls, path: str | Path) -> "SessionConfig":
        raw = tomllib.loads(Path(path).read_text())
        section = raw.get("session", raw)
        known = {f.name for f in fields(cls)}
        unknown = set(section) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**section)


class _SessionStrategyBase:
    """Shared per-bar ET clock, ATR, sizing, and force-flat safety."""

    def __init__(self, candles: Candles, cfg: SessionConfig) -> None:
        self.candles = candles
        self.cfg = cfg
        self.minute, self.day = et_minutes_days(candles.ts, cfg.tz)
        self.atr = compute_atr(candles, cfg.atr_period)

    def _sized_qty(self, broker: Broker, price: float, stop_dist: float) -> float:
        if stop_dist <= 0 or price <= 0:
            return 0.0
        qty = broker.equity * self.cfg.risk_pct / 100.0 / stop_dist
        return min(qty, broker.equity * self.cfg.max_leverage / price)

    def _flat_if_session_over(self, i: int, broker: Broker) -> bool:
        """Force-flat at/after the RTH close bar or on any ET-day change.

        Returns True when a position exists (caller should not act)."""
        if broker.position is None:
            return False
        entry_day = self.day[broker.position.entry_index]
        if self.day[i] != entry_day or self.minute[i] >= RTH_CLOSE:
            broker.close_position()
        return True


class IntradayMomentumStrategy(_SessionStrategyBase):
    def __init__(self, candles: Candles, cfg: SessionConfig | None = None) -> None:
        super().__init__(candles, cfg or SessionConfig())
        self._cur_day: int = -1
        self._prev_close: float = float("nan")   # prior session's 16:00 close
        self._p1000: float = float("nan")        # today's 10:00 price
        self._open_seen: bool = False

    def on_bar(self, i: int, broker: Broker) -> None:
        m, d = int(self.minute[i]), int(self.day[i])
        if d != self._cur_day:
            self._cur_day = d
            self._p1000 = float("nan")
            self._open_seen = False
            broker.cancel_all()
        close = float(self.candles.close[i])
        if m == RTH_CLOSE:
            # today's 16:00 close becomes tomorrow's predictor base; recorded
            # before the flat-check early-return so traded days count too
            self._prev_close = close
        if self._flat_if_session_over(i, broker):
            return
        if m == RTH_OPEN:
            self._open_seen = True
        elif m == RTH_FH_END:
            self._p1000 = close
        elif m == RTH_ROD_END:
            self._try_entry(i, broker, close)

    def _try_entry(self, i: int, broker: Broker, close: float) -> None:
        if broker.pending or not self._open_seen or not np.isfinite(self._prev_close):
            return
        r_rod = float(np.log(close / self._prev_close))
        direction = 0.0
        if self.cfg.im_predictor in ("fh", "both"):
            if not np.isfinite(self._p1000):
                return
            r_fh = float(np.log(self._p1000 / self._prev_close))
            direction = np.sign(r_fh)
        if self.cfg.im_predictor in ("rod", "both"):
            rod_sign = np.sign(r_rod)
            if self.cfg.im_predictor == "rod":
                direction = rod_sign
            elif rod_sign != direction:
                return  # "both": signs must agree
        if direction == 0 or abs(r_rod) < self.cfg.im_min_abs_signal:
            return
        side = BULL if direction > 0 else BEAR
        stop_dist = self.cfg.im_stop_atr * float(self.atr[i])
        qty = self._sized_qty(broker, close, stop_dist)
        if qty <= 0:
            return
        broker.submit(Order(side=side, qty=qty, type="market",
                            sl=close - side * stop_dist,
                            expiry_index=i + 1, tag="im_last30"))


class OpeningRangeBreakoutStrategy(_SessionStrategyBase):
    def __init__(self, candles: Candles, cfg: SessionConfig | None = None) -> None:
        super().__init__(candles, cfg or SessionConfig())
        self._cur_day: int = -1
        self._or_high: float = float("nan")
        self._or_low: float = float("nan")
        self._direction: int = 0
        self._submitted: bool = False

    def on_bar(self, i: int, broker: Broker) -> None:
        m, d = int(self.minute[i]), int(self.day[i])
        if d != self._cur_day:
            self._cur_day = d
            self._or_high = self._or_low = float("nan")
            self._direction = 0
            self._submitted = False
            broker.cancel_all()
        if self._flat_if_session_over(i, broker):
            return
        if broker.pending and m >= self.cfg.orb_entry_cutoff_minute:
            broker.cancel_all()
            return
        if m == RTH_OPEN:
            self._or_high = float(self.candles.high[i])
            self._or_low = float(self.candles.low[i])
            self._direction = int(np.sign(self.candles.close[i] - self.candles.open[i]))
        elif m == RTH_FH_END and not np.isnan(self._or_high):
            self._or_high = max(self._or_high, float(self.candles.high[i]))
            self._or_low = min(self._or_low, float(self.candles.low[i]))
            self._try_entry(i, broker)

    def _try_entry(self, i: int, broker: Broker) -> None:
        if self._submitted or self._direction == 0 or broker.pending:
            return
        rng = self._or_high - self._or_low
        if rng <= 0:
            return
        atr_i = float(self.atr[i])
        if self.cfg.orb_min_range_atr > 0 and rng < self.cfg.orb_min_range_atr * atr_i:
            return
        if self.cfg.orb_max_range_atr > 0 and rng > self.cfg.orb_max_range_atr * atr_i:
            return
        side = BULL if self._direction > 0 else BEAR
        trigger = self._or_high if side == BULL else self._or_low
        if self.cfg.orb_stop_mode == "atr":
            stop_dist = self.cfg.orb_stop_atr * atr_i
        else:
            stop_dist = rng
        sl = trigger - side * stop_dist
        tp = trigger + side * self.cfg.orb_take_profit_r * stop_dist \
            if self.cfg.orb_take_profit_r > 0 else 0.0
        qty = self._sized_qty(broker, trigger, stop_dist)
        if qty <= 0:
            return
        self._submitted = True
        broker.submit(Order(side=side, qty=qty, type="stop", price=trigger,
                            sl=sl, tp=tp, tag="orb30"))
