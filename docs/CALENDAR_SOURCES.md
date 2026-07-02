# High-impact event calendars: sourcing and assembly

The news blackout (`avoid_news`, `news_day_blackout`) consumes event
timestamps from two places: built-in generators (NFP by rule, FOMC from
the Fed's published 2023–2026 schedule — see `data/news.py`) and a CSV
supplied via `news_csv`. This document is the recipe for assembling
richer calendars.

## Why not ForexFactory

No official API, no bulk historical export; the unofficial
`nfs.faireconomy.media/ff_calendar_thisweek.json` feed covers only the
current week (fine for *live* use someday, useless for backtests), and
scraping the calendar pages is brittle and ToS-gray. Go upstream to the
official schedules FF aggregates.

## Official sources (executor: fetch these, they publish per-year schedules)

| Event | Source | Typical time (ET) |
|---|---|---|
| FOMC rate decision | federalreserve.gov/monetarypolicy/fomccalendars.htm (+ historical pages for pre-2023) | 14:00 |
| CPI | bls.gov/schedule/news_release/cpi.htm (per-year pages) | 08:30 |
| Employment Situation / NFP | bls.gov/schedule/news_release/empsit.htm | 08:30 |
| GDP (adv/2nd/3rd) | bea.gov/news/schedule | 08:30 |
| ECB rate decision | ecb.europa.eu (governing council calendar) | 08:15/08:45 |

## CSV format

One row per event; `load_news_csv` accepts a `ts`/`timestamp`/`datetime`
column (epoch seconds/ms or ISO-8601; naive strings are treated as UTC).
An optional `impact` column can be filtered at load time. Example:

```csv
datetime,impact,event
2022-01-12T13:30:00Z,high,CPI
2022-01-26T19:00:00Z,high,FOMC
```

Mind DST when converting ET release times to UTC (08:30 ET = 13:30 UTC
in winter, 12:30 UTC in summer). Prefer writing ISO timestamps with the
zone resolved, as above.

## Assembly and freeze protocol

1. Executor fetches the official schedule pages for the required period
   and hand-assembles (or scripts) the CSV — **verifying dates against
   the official source, never a re-aggregator**.
2. The CSV is committed under `data/calendars/` (exempt from the
   data-directory gitignore) *before* any holdout price data is touched,
   and referenced by the frozen config's `news_csv`.
3. The architect reviews the calendar as part of the freeze. A calendar
   change after freeze invalidates the freeze.

Calendars are known in advance in reality, so calendar-based blackouts
are causally clean (prefix-consistent by construction). A realized-
volatility filter would be *reactive* — a different mechanism requiring
its own careful design; do not substitute one for the other.

## Current coverage vs. gaps

- Covered by built-ins: NFP (rule-based), FOMC 2023–2026.
- Known gaps: CPI (all periods), pre-2023 FOMC (required for the V2.1
  and V3 early holdouts — already a preregistration requirement), GDP,
  ECB. These enter via CSV only; do not hardcode them.
