"""Program T, Stage 2: time-series momentum with volatility targeting.

The Moskowitz/Ooi/Pedersen construction mechanized for the engine, on
daily bars, one instrument per run (the portfolio is assembled by
``analytics/portfolio.py`` from per-instrument results):

* signal at day t's close = majority vote of the signs of the trailing
  21/63/252-day log returns (configurable);
* target notional = equity × min(vol_target / realized_vol_63d, cap);
* re-trade only on a signal flip or when the target notional drifts
  more than ``rebalance_band`` from the held notional (turnover
  control — costs are per fill);
* always in the market once warmed up; no stops or targets (per the
  literature); the engine closes any open position at the data's end.

Decisions use only closes up to the current bar; entries fill at the
next day's open through the standard pessimistic engine path.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import BEAR, BULL, Candles
from ..engine import Broker, Order


@dataclass(slots=True)
class TrendConfig:
    lookbacks: tuple[int, ...] = (21, 63, 252)
    vol_lookback: int = 63
    vol_target: float = 0.10       # annualized volatility target per instrument
    max_leverage: float = 4.0      # cap on notional / equity
    rebalance_band: float = 0.25   # re-trade when |target-held|/held exceeds this
    periods_per_year: int = 252

    @classmethod
    def from_toml(cls, path: str | Path) -> "TrendConfig":
        raw = tomllib.loads(Path(path).read_text())
        section = raw.get("trend", raw)
        known = {f.name for f in fields(cls)}
        unknown = set(section) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        kwargs = dict(section)
        if "lookbacks" in kwargs:
            kwargs["lookbacks"] = tuple(kwargs["lookbacks"])
        return cls(**kwargs)


class TimeSeriesMomentumStrategy:
    def __init__(self, candles: Candles, cfg: TrendConfig | None = None) -> None:
        self.candles = candles
        self.cfg = cfg or TrendConfig()
        close = candles.close
        logc = np.log(close)
        n = len(close)

        total = np.zeros(n)
        for lb in self.cfg.lookbacks:
            sig = np.zeros(n)
            if n > lb:
                sig[lb:] = np.sign(logc[lb:] - logc[:-lb])
            total += sig
        self.signal = np.sign(total)
        warmup = max(max(self.cfg.lookbacks), self.cfg.vol_lookback)
        self.signal[:warmup] = 0.0

        r = pd.Series(np.diff(logc, prepend=logc[0]))
        realized = (r.rolling(self.cfg.vol_lookback).std().to_numpy()
                    * np.sqrt(self.cfg.periods_per_year))
        with np.errstate(divide="ignore", invalid="ignore"):
            lev = np.where(realized > 0, self.cfg.vol_target / realized, 0.0)
        lev[np.isnan(lev)] = 0.0
        self.leverage = np.minimum(lev, self.cfg.max_leverage)

    def on_bar(self, i: int, broker: Broker) -> None:
        sig = int(self.signal[i])
        lev = float(self.leverage[i])
        price = float(self.candles.close[i])
        if price <= 0:
            return
        target_qty = broker.equity * lev / price if sig != 0 else 0.0

        pos = broker.position
        if pos is None:
            if broker.pending or sig == 0 or target_qty <= 0:
                return
            side = BULL if sig > 0 else BEAR
            broker.submit(Order(side=side, qty=target_qty, type="market", tag="tsmom"))
            return

        held_side = 1 if pos.side == BULL else -1
        if sig == 0 or held_side != sig:
            broker.close_position()
            if sig != 0 and target_qty > 0 and not broker.pending:
                side = BULL if sig > 0 else BEAR
                broker.submit(Order(side=side, qty=target_qty, type="market", tag="tsmom"))
            return

        # same direction: resize only outside the band (turnover control)
        if pos.qty > 0 and abs(target_qty - pos.qty) / pos.qty > self.cfg.rebalance_band:
            broker.close_position()
            if target_qty > 0 and not broker.pending:
                side = BULL if sig > 0 else BEAR
                broker.submit(Order(side=side, qty=target_qty, type="market", tag="tsmom"))
