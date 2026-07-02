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
    bias_mode: str = "structure"   # "structure" (V1/V2) or "narrative" (V3):
                                   # weighted vote of 4h+daily structure, draw
                                   # on liquidity, and IPDA range events
    narrative_weights: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    narrative_min_conviction: float = 0.5  # |score| below this = no bias, no trade
    ipda_days: int = 20            # IPDA data-range lookback (daily bars)
    ipda_hold_days: int = 10       # how long a range event colors the narrative
    # bias-dominance gates: HTF judgment as the majority contributor, with the
    # sweep/MSS/POI mechanics acting only as triggers (all default-off)
    bias_htf2_multiplier: int = 0  # second, higher bias TF that must also agree
                                   # (96 x 15m = daily); 0 = off
    require_htf_discount: bool = False  # longs only below the HTF dealing-range
                                        # equilibrium, shorts only above it
    require_draw: bool = False     # an untaken HTF liquidity pool must exist
                                   # beyond price in the trade direction (the
                                   # "draw on liquidity" the market reaches for)
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
    killzone_tz: str = "UTC"       # "America/New_York" = DST-correct ET windows

    # -- V2 faithfulness features (all default-off; V1 behavior unchanged) ------
    entry_confirmation: bool = False   # wait for zone touch + confirming close,
                                       # then enter at market (no resting limit)
    breakeven_r: float = 0.0           # move stop to entry at +N R (0 = off)
    avoid_news: bool = False           # blackout around high-impact releases
    news_csv: str = ""                 # calendar CSV; empty = built-in NFP+FOMC
    news_before_min: int = 30
    news_after_min: int = 60
    news_day_blackout: bool = False    # exclude the entire ET day of any event
                                       # ("only trade days with no news")

    @classmethod
    def from_toml(cls, path: str | Path) -> "SMCConfig":
        raw = tomllib.loads(Path(path).read_text())
        section = raw.get("strategy", raw)
        known = {f.name for f in fields(cls)}
        unknown = set(section) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        kwargs = dict(section)
        for key in ("poi_priority", "killzones", "narrative_weights"):
            if key in kwargs:
                kwargs[key] = tuple(kwargs[key])
        return cls(**kwargs)
