"""Strategy configuration, loadable from TOML."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass(slots=True)
class SMCConfig:
    # -- detector parameters --------------------------------------------------
    swing_k: int = 3               # fractal half-width; confirmation lag in bars
    htf_multiplier: int = 16       # higher timeframe = base tf * this (16 x 15m = 4h)
    eq_tol_atr: float = 0.25       # equal-high/low merge tolerance, in ATRs
    min_gap_atr: float = 0.25      # FVG displacement filter, in ATRs
    atr_period: int = 14
    max_leg_bars: int = 100        # how far back to search for an impulse origin

    # -- setup sequencing ------------------------------------------------------
    use_htf_bias: bool = True      # only trade in the HTF structure direction
    sweep_to_mss_bars: int = 30    # structure break must follow the sweep within N bars
    order_expiry_bars: int = 30    # limit order lifetime after placement
    require_ote: bool = True       # entry must sit in the 62-79% retracement band
    require_discount: bool = True  # longs below the leg midpoint, shorts above
    poi_priority: tuple[str, ...] = ("fvg", "ob")

    # -- risk / exits ----------------------------------------------------------
    stop_buffer_atr: float = 0.25  # stop distance beyond the sweep wick
    min_rr: float = 1.5            # liquidity target must offer at least this R
    default_rr: float = 2.0        # fallback fixed-R target
    risk_pct: float = 1.0          # equity % risked per trade
    max_leverage: float = 5.0

    # -- time filter -----------------------------------------------------------
    use_killzones: bool = True
    killzones: tuple[str, ...] = ("london", "new_york")

    @classmethod
    def from_toml(cls, path: str | Path) -> "SMCConfig":
        raw = tomllib.loads(Path(path).read_text())
        section = raw.get("strategy", raw)
        known = {f.name for f in fields(cls)}
        unknown = set(section) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        kwargs = dict(section)
        for key in ("poi_priority", "killzones"):
            if key in kwargs:
                kwargs[key] = tuple(kwargs[key])
        return cls(**kwargs)
