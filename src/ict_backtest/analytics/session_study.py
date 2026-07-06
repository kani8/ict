"""Program S, Stage 1: descriptive session-anomaly battery for index futures.

Design frozen in ``reports/PREREGISTRATION_S.md`` before any run on real
data.  Five studies over regular-trading-hours (RTH) sessions:

* **S1 — market intraday momentum**: does the first-half-hour return
  (Gao/Han/Li/Zhou 2018) and/or the rest-of-day return (Baltussen/Da/
  Lammers/Martens 2021) predict the last-half-hour return?  Statistic:
  signed last-30m return (sign of predictor times realized last-30m
  logret); support = block-bootstrap CI excludes 0 upward.
* **S2 — opening-range breakout**: after a directional break of the first
  30 minutes' range, does price continue into the close?
* **S3 — pre-FOMC drift** (Lucca & Moench 2015): 24h return into the
  14:00 ET announcement on FOMC days vs all other days.
* **S4 — IBS mean reversion**: does a close near the session low predict
  a higher next-session RTH return (and vice versa)?
* **S5 — overnight/intraday decomposition** (descriptive context only).

Everything is computed from a per-session anchor table built once from
close-visible bar data; no artifact uses information from after its own
bar's close.  Descriptive research on burned data; full-sample
computation is legitimate and is declared as such.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..core import Candles, atr as compute_atr
from ..detectors.killzones import (
    RTH_1400,
    RTH_CLOSE,
    RTH_FH_END,
    RTH_LAST,
    RTH_OPEN,
    RTH_ROD_END,
    et_minutes_days,
)
from .significance import block_bootstrap_ci

# anchor bars a session must have to count as complete
_REQUIRED = (RTH_OPEN, RTH_FH_END, RTH_1400, RTH_ROD_END, RTH_LAST, RTH_CLOSE)


def session_table(candles: Candles, tz: str = "America/New_York",
                  atr_period: int = 14) -> pd.DataFrame:
    """One row per complete RTH session (09:30-16:00 ET), close-anchored.

    A session is complete when all anchor bars exist: 09:30, 09:45,
    13:45, 15:15, 15:30, 15:45 (bar-open ET minutes).  Early closes and
    partial sessions are dropped.  Columns (all log returns):

    - ``prev_close``: 16:00 close of the previous complete session
      (NaN on the first row); ``day_gap`` = calendar days since it.
    - ``r_on`` prev close -> 09:30 open; ``r_fh`` prev close -> 10:00
      (Gao et al. predictor); ``r_rod`` prev close -> 15:30 (Baltussen
      et al. predictor); ``r_last`` 15:30 -> 16:00 (the target);
      ``r_intraday`` 09:30 open -> 16:00 close; ``r_cc`` prev close ->
      close.
    - ``ibs``: (close - RTH low) / (RTH high - RTH low).
    - ``or_high/or_low``: extremes of the first 30 minutes;
      ``first_bar_ret``: 09:30 bar close-vs-open logret (ORB direction);
      ``atr_or``: ATR at the 09:45 bar close (range normalizer).
    - ``i_open, i_fh, i_1400, i_rod, i_last, i_close``: bar indices of
      the anchor bars (for intraday walks).
    """
    if candles.timeframe_s != 900:
        raise ValueError("session_table expects 15m candles")
    minute, day = et_minutes_days(candles.ts, tz)
    a = compute_atr(candles, atr_period)
    rth = (minute >= RTH_OPEN) & (minute < 960)

    rows: list[dict] = []
    for d in pd.unique(day[rth]):
        sel = np.flatnonzero((day == d) & rth)
        mins = minute[sel]
        pos = {m: sel[k] for k, m in enumerate(mins)}
        if any(m not in pos for m in _REQUIRED):
            continue  # early close / partial session
        i_open, i_fh, i_1400 = pos[570], pos[585], pos[825]
        i_rod, i_last, i_close = pos[915], pos[930], pos[945]
        hi = float(candles.high[sel].max())
        lo = float(candles.low[sel].min())
        close = float(candles.close[i_close])
        rows.append({
            "day": int(d),
            "i_open": int(i_open), "i_fh": int(i_fh), "i_1400": int(i_1400),
            "i_rod": int(i_rod), "i_last": int(i_last), "i_close": int(i_close),
            "open_0930": float(candles.open[i_open]),
            "p_1000": float(candles.close[i_fh]),
            "p_1400": float(candles.close[i_1400]),
            "p_1530": float(candles.close[i_rod]),
            "close_1600": close,
            "rth_high": hi, "rth_low": lo,
            "ibs": (close - lo) / (hi - lo) if hi > lo else float("nan"),
            "or_high": float(max(candles.high[i_open], candles.high[i_fh])),
            "or_low": float(min(candles.low[i_open], candles.low[i_fh])),
            "first_bar_ret": float(np.log(candles.close[i_open] / candles.open[i_open])),
            "atr_or": float(a[i_fh]),
        })
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t["prev_close"] = t["close_1600"].shift(1)
    prev_day = pd.to_datetime(t["day"].shift(1), format="%Y%m%d")
    t["day_gap"] = (pd.to_datetime(t["day"], format="%Y%m%d") - prev_day).dt.days
    with np.errstate(invalid="ignore"):
        t["r_on"] = np.log(t["open_0930"] / t["prev_close"])
        t["r_fh"] = np.log(t["p_1000"] / t["prev_close"])
        t["r_rod"] = np.log(t["p_1530"] / t["prev_close"])
        t["r_last"] = np.log(t["close_1600"] / t["p_1530"])
        t["r_intraday"] = np.log(t["close_1600"] / t["open_0930"])
        t["r_cc"] = np.log(t["close_1600"] / t["prev_close"])
    # trailing 20-session realized vol of close-to-close returns, shifted so
    # day d only sees days < d (usable by non-descriptive consumers too)
    t["vol20"] = t["r_cc"].rolling(20).std().shift(1)
    return t


def _ci_row(values: np.ndarray, **extra) -> dict:
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) < 5:
        return {"n": int(len(v)), "mean": float("nan"),
                "ci_lo": float("nan"), "ci_hi": float("nan"), **extra}
    mean, lo, hi, _ = block_bootstrap_ci(v)
    return {"n": int(len(v)), "mean": mean, "ci_lo": lo, "ci_hi": hi, **extra}


def intraday_momentum_rows(table: pd.DataFrame) -> list[dict]:
    """S1: signed last-30m return per predictor, all days + vol terciles.

    ``signed = sign(predictor) * r_last`` — positive means the momentum
    prediction was right.  Predictors: ``fh`` (prev close -> 10:00),
    ``rod`` (prev close -> 15:30), ``both`` (signs must agree; the
    subset of days where they do).
    """
    t = table.dropna(subset=["r_fh", "r_rod", "r_last"])
    rows = []
    preds = {
        "fh": np.sign(t["r_fh"].to_numpy()),
        "rod": np.sign(t["r_rod"].to_numpy()),
    }
    agree = (preds["fh"] == preds["rod"]) & (preds["fh"] != 0)
    preds["both"] = np.where(agree, preds["fh"], 0.0)
    r_last = t["r_last"].to_numpy()
    vol = t["vol20"].to_numpy()
    terc = np.full(len(t), -1)
    ok = ~np.isnan(vol)
    if ok.sum() >= 30:
        q1, q2 = np.nanquantile(vol, [1 / 3, 2 / 3])
        terc[ok] = np.digitize(vol[ok], [q1, q2])
    for name, sgn in preds.items():
        live = sgn != 0
        rows.append(_ci_row(sgn[live] * r_last[live], predictor=name, subset="all"))
        for k, label in enumerate(("low_vol", "mid_vol", "high_vol")):
            m = live & (terc == k)
            rows.append(_ci_row(sgn[m] * r_last[m], predictor=name, subset=label))
    return rows


def orb_rows(table: pd.DataFrame, candles: Candles,
             cutoff_minute: int = 900, tz: str = "America/New_York") -> list[dict]:
    """S2: signed breakout-to-close return for direction-filtered 30m ORB.

    Direction = sign of the 09:30 bar's close-vs-open.  The event is the
    first bar after 10:00 whose high (long) / low (short) exceeds the
    opening range, provided it happens before ``cutoff_minute`` ET.
    Entry proxy = that bar's close (knowable); return = direction *
    log(close_1600 / breakout close).  Subsets: all events, and events
    whose opening range <= trailing-20-day median range ("narrow", the
    Crabel-style filter).
    """
    minute, _ = et_minutes_days(candles.ts, tz)
    t = table.dropna(subset=["prev_close"])
    or_range = (t["or_high"] - t["or_low"]).to_numpy()
    med20 = pd.Series(or_range).rolling(20).median().shift(1).to_numpy()
    signed, narrow = [], []
    for k, row in enumerate(t.itertuples(index=False)):
        direction = float(np.sign(row.first_bar_ret))
        if direction == 0:
            continue
        level = row.or_high if direction > 0 else row.or_low
        hit = -1
        for j in range(row.i_fh + 1, row.i_close + 1):
            if minute[j] >= cutoff_minute:
                break
            if (direction > 0 and candles.high[j] > level) or (
                    direction < 0 and candles.low[j] < level):
                hit = j
                break
        if hit < 0:
            continue
        r = direction * float(np.log(row.close_1600 / candles.close[hit]))
        signed.append(r)
        if not np.isnan(med20[k]) and or_range[k] <= med20[k]:
            narrow.append(r)
    return [_ci_row(np.array(signed), subset="all"),
            _ci_row(np.array(narrow), subset="narrow_range")]


def fomc_rows(table: pd.DataFrame, event_ts: np.ndarray | list[int],
              tz: str = "America/New_York") -> list[dict]:
    """S3: 24h return into 14:00 ET (p_1400[d] / p_1400[d-1]) on FOMC
    decision days vs all other days."""
    ev_min, ev_day = et_minutes_days(np.asarray(event_ts, dtype=np.int64), tz)
    ev_days = set(ev_day.tolist())
    t = table.copy()
    t["pre14"] = np.log(t["p_1400"] / t["p_1400"].shift(1))
    t = t.dropna(subset=["pre14"])
    is_ev = t["day"].isin(ev_days).to_numpy()
    return [_ci_row(t["pre14"].to_numpy()[is_ev], subset="fomc_days"),
            _ci_row(t["pre14"].to_numpy()[~is_ev], subset="other_days")]


def ibs_rows(table: pd.DataFrame) -> list[dict]:
    """S4: next-session RTH return by IBS quintile, plus the Q1-Q5 spread.

    Mean reversion predicts Q1 (close near low) out-returns Q5 (close
    near high).  Spread CI is the difference of independent block-
    bootstrap means (different day sets).
    """
    t = table.copy()
    t["r_next"] = t["r_intraday"].shift(-1)
    t = t.dropna(subset=["ibs", "r_next"])
    q = np.quantile(t["ibs"], [0.2, 0.4, 0.6, 0.8])
    labels = np.digitize(t["ibs"].to_numpy(), q)
    r_next = t["r_next"].to_numpy()
    rows = [_ci_row(r_next[labels == k], subset=f"q{k + 1}") for k in range(5)]
    lo_v, hi_v = r_next[labels == 0], r_next[labels == 4]
    if len(lo_v) >= 5 and len(hi_v) >= 5:
        rng = np.random.default_rng(7)
        boots = []
        for v in (lo_v, hi_v):
            n = len(v)
            b = max(1, round(n ** (1 / 3)))
            k = -(-n // b)
            starts = rng.integers(0, n, size=(10_000, k))
            idx = (starts[:, :, None] + np.arange(b)) % n
            boots.append(v[idx.reshape(10_000, k * b)[:, :n]].mean(axis=1))
        diff = boots[0] - boots[1]
        rows.append({"n": int(len(lo_v) + len(hi_v)),
                     "mean": float(lo_v.mean() - hi_v.mean()),
                     "ci_lo": float(np.quantile(diff, 0.025)),
                     "ci_hi": float(np.quantile(diff, 0.975)),
                     "subset": "q1_minus_q5"})
    return rows


def overnight_rows(table: pd.DataFrame) -> list[dict]:
    """S5 (descriptive): overnight vs RTH-intraday return decomposition."""
    t = table.dropna(subset=["r_on", "r_intraday"])
    return [_ci_row(t["r_on"].to_numpy(), subset="overnight"),
            _ci_row(t["r_intraday"].to_numpy(), subset="intraday")]


def run_session_battery(candles: Candles, fomc_ts: np.ndarray | list[int] | None = None,
                        tz: str = "America/New_York") -> dict:
    """The full Stage-1 battery on one dataset. Returns rows per study."""
    table = session_table(candles, tz)
    out = {
        "n_sessions": int(len(table)),
        "s1_intraday_momentum": intraday_momentum_rows(table),
        "s2_orb": orb_rows(table, candles, tz=tz),
        "s4_ibs": ibs_rows(table),
        "s5_overnight": overnight_rows(table),
    }
    if fomc_ts is not None and len(fomc_ts):
        out["s3_fomc"] = fomc_rows(table, fomc_ts, tz)
    return out


def render_session_battery(result: dict, title: str) -> str:
    """Markdown tables for a battery result, one section per study."""
    def block(name: str, rows: list[dict], key_cols: tuple[str, ...]) -> list[str]:
        head = " | ".join(key_cols)
        lines = [f"*{name}*", "", f"| {head} | n | mean logret | 95% CI |",
                 "|" + "---|" * (len(key_cols) + 3)]
        for r in rows:
            keys = " | ".join(str(r.get(c, "")) for c in key_cols)
            lines.append(f"| {keys} | {r['n']} | {r['mean']:+.5f} | "
                         f"[{r['ci_lo']:+.5f}, {r['ci_hi']:+.5f}] |")
        return lines + [""]

    lines = [f"**{title}** — session battery ({result['n_sessions']} complete sessions)", ""]
    lines += block("S1 intraday momentum (signed last-30m; support = CI > 0)",
                   result["s1_intraday_momentum"], ("predictor", "subset"))
    lines += block("S2 opening-range breakout (signed break-to-close; support = CI > 0)",
                   result["s2_orb"], ("subset",))
    if "s3_fomc" in result:
        lines += block("S3 pre-FOMC 24h drift into 14:00 ET",
                       result["s3_fomc"], ("subset",))
    lines += block("S4 IBS quintiles vs next-session RTH return (support = q1_minus_q5 CI > 0)",
                   result["s4_ibs"], ("subset",))
    lines += block("S5 overnight vs intraday decomposition (descriptive)",
                   result["s5_overnight"], ("subset",))
    return "\n".join(lines)
