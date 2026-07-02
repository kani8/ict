"""High-impact news calendar and blackout masks.

ICT teaches standing aside around medium/high-impact releases (FOMC, NFP,
CPI, ...): no entries shortly before or after.  This module provides

* built-in generators for the two releases with deterministic-enough
  schedules — NFP (first Friday of the month, 08:30 ET) and FOMC decision
  afternoons (14:00 ET, dates embedded for 2023-2026 from the Fed's
  published calendar); and
* a CSV loader for a full calendar (one timestamp column, UTC or ISO),
  which should be preferred for serious runs — CPI and other releases move
  around too much to hardcode.

All times are computed through America/New_York so DST is handled.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")

# FOMC rate-decision days (second day of each scheduled meeting), 14:00 ET.
# Source: Federal Reserve published meeting calendars, 2023-2026.
FOMC_DECISION_DAYS = [
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]


def _epoch(day: dt.date, hour: int, minute: int) -> int:
    return int(dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=ET).timestamp())


def nfp_events(start_ts: int, end_ts: int) -> list[int]:
    """First Friday of each month, 08:30 ET.  (The BLS occasionally shifts
    a release; supply a CSV calendar when exactness matters.)"""
    start = dt.datetime.fromtimestamp(start_ts, tz=ET).date().replace(day=1)
    end = dt.datetime.fromtimestamp(end_ts, tz=ET).date()
    events = []
    cur = start
    while cur <= end:
        first_friday = cur + dt.timedelta(days=(4 - cur.weekday()) % 7)
        ts = _epoch(first_friday, 8, 30)
        if start_ts <= ts < end_ts:
            events.append(ts)
        cur = (cur + dt.timedelta(days=32)).replace(day=1)
    return events


def fomc_events(start_ts: int, end_ts: int) -> list[int]:
    """FOMC decision timestamps (14:00 ET) inside the range."""
    events = []
    for day in FOMC_DECISION_DAYS:
        ts = _epoch(dt.date.fromisoformat(day), 14, 0)
        if start_ts <= ts < end_ts:
            events.append(ts)
    return events


def load_news_csv(path: str | Path,
                  impact_filter: tuple[str, ...] | None = None) -> list[int]:
    """Load event timestamps from a CSV with a 'ts'/'timestamp'/'datetime' column.

    If the file has an ``impact`` column and ``impact_filter`` is given,
    only rows whose impact matches (case-insensitive) are kept — handy for
    calendars that mix high/medium/low rows.
    """
    import pandas as pd

    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    if impact_filter is not None and "impact" in cols:
        wanted = {s.lower() for s in impact_filter}
        df = df[df[cols["impact"]].astype(str).str.lower().isin(wanted)]
    for key in ("ts", "timestamp", "time", "datetime", "date"):
        if key in cols:
            col = df[cols[key]]
            break
    else:
        raise ValueError(f"no timestamp column found among {list(df.columns)}")
    if pd.api.types.is_numeric_dtype(col.dtype):
        vals = col.astype(np.int64).to_numpy()
        if vals.max() > 10_000_000_000:
            vals = vals // 1000
        return sorted(int(v) for v in vals)
    parsed = pd.to_datetime(col, utc=True).astype("datetime64[ns, UTC]")
    return sorted(int(v) for v in parsed.astype(np.int64) // 10**9)


def default_events(start_ts: int, end_ts: int) -> list[int]:
    """Built-in high-impact schedule: NFP + FOMC."""
    return sorted(nfp_events(start_ts, end_ts) + fomc_events(start_ts, end_ts))


def blackout_mask(ts: np.ndarray, events: list[int],
                  before_min: int = 30, after_min: int = 60) -> np.ndarray:
    """True where a bar's open falls inside any event blackout window."""
    mask = np.zeros(len(ts), dtype=bool)
    for e in events:
        mask |= (ts >= e - before_min * 60) & (ts < e + after_min * 60)
    return mask


def news_day_mask(ts: np.ndarray, events: list[int]) -> np.ndarray:
    """True for every bar on the ET calendar day of any event.

    Implements the strict reading of "only trade days with no news".
    """
    import pandas as pd

    if not events:
        return np.zeros(len(ts), dtype=bool)
    event_days = {
        dt.datetime.fromtimestamp(e, tz=ET).date() for e in events
    }
    bar_days = pd.to_datetime(ts, unit="s", utc=True).tz_convert(ET).date
    return np.array([d in event_days for d in bar_days], dtype=bool)
