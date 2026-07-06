"""Time-of-day filters: ICT killzones.

Windows are expressed in UTC to keep the engine timezone-free.  The
classic EST killzones map to UTC as follows (ignoring DST, which shifts
them by an hour for part of the year — configure to taste):

* Asian          20:00-22:00 EST  -> 01:00-03:00 UTC
* London open    02:00-05:00 EST  -> 07:00-10:00 UTC
* New York open  07:00-09:00 EST  -> 12:00-14:00 UTC
* London close   10:00-12:00 EST  -> 15:00-17:00 UTC
* Silver bullet  10:00-11:00 EST  -> 15:00-16:00 UTC
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Killzone:
    name: str
    start_hour: float  # UTC, inclusive
    end_hour: float    # UTC, exclusive; may be < start_hour to wrap midnight

    def contains(self, hour_utc: np.ndarray | float) -> np.ndarray | bool:
        if self.end_hour >= self.start_hour:
            return (hour_utc >= self.start_hour) & (hour_utc < self.end_hour)
        return (hour_utc >= self.start_hour) | (hour_utc < self.end_hour)


LONDON = Killzone("london", 7.0, 10.0)
NEW_YORK = Killzone("new_york", 12.0, 14.0)
LONDON_CLOSE = Killzone("london_close", 15.0, 17.0)
ASIAN = Killzone("asian", 1.0, 3.0)
SILVER_BULLET = Killzone("silver_bullet", 15.0, 16.0)

DEFAULT_KILLZONES = [LONDON, NEW_YORK]

BY_NAME = {kz.name: kz for kz in (LONDON, NEW_YORK, LONDON_CLOSE, ASIAN, SILVER_BULLET)}

# ICT's canonical definitions are New York local time; evaluating them in a
# real timezone (killzone_tz = "America/New_York") makes them DST-correct,
# unlike the fixed-UTC approximations above.
ET_BY_NAME = {
    "asian": Killzone("asian", 20.0, 22.0),
    "london": Killzone("london", 2.0, 5.0),
    "new_york": Killzone("new_york", 7.0, 9.0),
    "london_close": Killzone("london_close", 10.0, 12.0),
    "silver_bullet": Killzone("silver_bullet", 10.0, 11.0),
}


# ---------------------------------------------------------------------------
# US index RTH session anchors (Program S). 15m bar timestamps = bar OPEN;
# a bar opening at 09:30 ET is minute 570 and closes 09:45.
# ---------------------------------------------------------------------------

RTH_OPEN = 570      # 09:30 bar — session open
RTH_FH_END = 585    # 09:45 bar — closes 10:00, end of the first half hour
RTH_1400 = 825      # 13:45 bar — closes 14:00 (FOMC announcement anchor)
RTH_ROD_END = 915   # 15:15 bar — closes 15:30, end of "rest of day"
RTH_LAST = 930      # 15:30 bar — the last-half-hour window opens here
RTH_CLOSE = 945     # 15:45 bar — closes 16:00, the RTH close


def et_minutes_days(ts: np.ndarray, tz: str = "America/New_York") -> tuple[np.ndarray, np.ndarray]:
    """Per-bar ET minute-of-day and ET calendar-day key (YYYYMMDD int).

    Uses only the bar-open timestamp, which is known before the bar
    exists — safe for both studies and live strategies.  DST-correct.
    """
    import pandas as pd

    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz)
    minute = (idx.hour * 60 + idx.minute).to_numpy(dtype=np.int64)
    day = (idx.year * 10_000 + idx.month * 100 + idx.day).to_numpy(dtype=np.int64)
    return minute, day


def in_killzone(ts: np.ndarray, killzones: list[Killzone], tz: str = "UTC") -> np.ndarray:
    """Boolean mask over bars whose open timestamp falls in any killzone.

    ``tz`` names the timezone the killzone hours are expressed in.  "UTC"
    uses fast modular arithmetic; anything else (e.g. "America/New_York")
    converts properly, including DST transitions.
    """
    if tz == "UTC":
        hour = (ts % 86400) / 3600.0
    else:
        import pandas as pd

        idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz)
        hour = idx.hour.to_numpy() + idx.minute.to_numpy() / 60.0 + idx.second.to_numpy() / 3600.0
    mask = np.zeros(len(ts), dtype=bool)
    for kz in killzones:
        mask |= kz.contains(hour)
    return mask
