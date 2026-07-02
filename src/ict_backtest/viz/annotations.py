"""Annotation bundle: everything the chart UI needs, per timeframe.

Each timeframe layer is produced by running the *actual* detector stack on
candles resampled to that timeframe — not by rescaling base-timeframe
artifacts — so what you see at 4h is what the detectors find at 4h.

Every artifact carries the index at which it becomes *visible* (its
confirm/created index) plus the indices of its later lifecycle events
(fill, invalidation, sweep). The UI's playback mode reveals artifacts only
from their visible index and clips zones at the reveal cursor, so the
replay is lookahead-honest by construction — the same discipline as the
backtester.
"""

from __future__ import annotations

import numpy as np

from ..core import Candles, resample
from ..detectors import (
    detect_fvgs,
    detect_liquidity_pools,
    detect_order_blocks,
    detect_structure,
    detect_swings,
)
from ..detectors.killzones import BY_NAME, ET_BY_NAME, in_killzone
from ..strategy import SMCConfig
from .timeline import build_timeline


def _r(x: float) -> float:
    return round(float(x), 6)


def tf_label(seconds: int) -> str:
    if seconds % 86_400 == 0:
        return f"{seconds // 86_400}d"
    if seconds % 3_600 == 0:
        return f"{seconds // 3_600}h"
    return f"{seconds // 60}m"


def build_layer(candles: Candles, cfg: SMCConfig) -> dict:
    """Detector artifacts for one timeframe, in a compact array encoding."""
    swings = detect_swings(candles, cfg.swing_k)
    events = detect_structure(candles, swings)
    obs = detect_order_blocks(candles, events, cfg.max_leg_bars)
    fvgs = detect_fvgs(candles, cfg.min_gap_atr, cfg.atr_period)
    pools = detect_liquidity_pools(candles, swings, cfg.eq_tol_atr, cfg.atr_period)

    if cfg.use_killzones:
        table = ET_BY_NAME if cfg.killzone_tz != "UTC" else BY_NAME
        kz = in_killzone(candles.ts, [table[n] for n in cfg.killzones], cfg.killzone_tz)
    else:
        kz = np.zeros(len(candles), dtype=bool)
    if cfg.avoid_news:
        from ..data.news import blackout_mask, default_events, load_news_csv, news_day_mask

        ev = (load_news_csv(cfg.news_csv) if cfg.news_csv
              else default_events(int(candles.ts[0]), int(candles.ts[-1]) + candles.timeframe_s))
        news = blackout_mask(candles.ts, ev, cfg.news_before_min, cfg.news_after_min)
        if cfg.news_day_blackout:
            news |= news_day_mask(candles.ts, ev)
    else:
        news = np.zeros(len(candles), dtype=bool)

    return {
        "label": tf_label(candles.timeframe_s),
        "tf_s": int(candles.timeframe_s),
        "ts": [int(t) for t in candles.ts],
        "o": [_r(x) for x in candles.open],
        "h": [_r(x) for x in candles.high],
        "l": [_r(x) for x in candles.low],
        "c": [_r(x) for x in candles.close],
        # [i, lo, hi, dir, visible, touch, fill, invert, invert_fail]
        "fvg": [[g.index, _r(g.low), _r(g.high), g.direction, g.confirm_index,
                 g.touch_index, g.fill_index, g.invert_index, g.invert_fail_index]
                for g in fvgs],
        # [i, lo, hi, dir, visible(created), mitigated, invalidated]
        "ob": [[b.index, _r(b.low), _r(b.high), b.direction, b.created_index,
                b.mitigated_index, b.invalidated_index]
               for b in obs],
        # [side, level, first_swing, visible(confirm), taken, kind(0 none/1 sweep/2 run), members]
        "pool": [[p.side, _r(p.level), min(p.swing_indices), p.confirm_index,
                  p.taken_index, {None: 0, "sweep": 1, "run": 2}[p.taken_kind],
                  len(p.swing_indices)]
                 for p in pools],
        # [i, price, kind, visible(confirm)]
        "swing": [[s.index, _r(s.price), s.kind, s.confirm_index] for s in swings],
        # [i, dir, kind(0 BOS/1 MSS), level, swing_i]
        "ev": [[e.index, e.direction, 0 if e.kind == "BOS" else 1,
                _r(e.level), e.swing_index] for e in events],
        "kz": [int(x) for x in kz],
        "news": [int(x) for x in news],
    }


def build_bundle(
    candles: Candles,
    cfg: SMCConfig | None = None,
    multipliers: tuple[int, ...] = (1, 4, 16, 96),
    title: str = "ICT Strategy Replay",
    include_timeline: bool = True,
) -> dict:
    """Full bundle: one detector layer per timeframe + the base-TF timeline."""
    cfg = cfg or SMCConfig()
    layers = []
    for m in sorted(set(multipliers)):
        tf_candles = candles if m == 1 else resample(candles, m)[0]
        if len(tf_candles) < max(cfg.swing_k * 2 + 1, 10):
            continue
        layers.append(build_layer(tf_candles, cfg))

    bundle = {
        "meta": {
            "title": title,
            "base_tf_s": int(candles.timeframe_s),
            "bars": len(candles),
            "config": {
                "bias_mode": cfg.bias_mode,
                "poi_priority": list(cfg.poi_priority),
                "killzones": list(cfg.killzones) if cfg.use_killzones else [],
                "killzone_tz": cfg.killzone_tz,
                "avoid_news": cfg.avoid_news,
                "entry_confirmation": cfg.entry_confirmation,
            },
        },
        "tfs": layers,
        "timeline": build_timeline(candles, cfg) if include_timeline else None,
    }
    return bundle
