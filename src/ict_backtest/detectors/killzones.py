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


def in_killzone(ts: np.ndarray, killzones: list[Killzone]) -> np.ndarray:
    """Boolean mask over bars whose open timestamp falls in any killzone."""
    hour = (ts % 86400) / 3600.0
    mask = np.zeros(len(ts), dtype=bool)
    for kz in killzones:
        mask |= kz.contains(hour)
    return mask
