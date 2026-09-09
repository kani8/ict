# VALIDATION.md (calendar hygiene, in-sample only: date < 2024-07-01)

## Trading dates per year vs. dates with a front settle

| year | trading dates | with front settle |
|---|---|---|
| 2010 | 149 | 149 |
| 2011 | 258 | 258 |
| 2012 | 258 | 258 |
| 2013 | 252 | 252 |
| 2014 | 250 | 250 |
| 2015 | 259 | 259 |
| 2016 | 258 | 258 |
| 2017 | 257 | 257 |
| 2018 | 258 | 258 |
| 2019 | 258 | 258 |
| 2020 | 259 | 259 |
| 2021 | 259 | 259 |
| 2022 | 258 | 258 |
| 2023 | 258 | 258 |
| 2024 | 128 | 128 |

## Dates with >1 active (day_volume>0) contract: 3619 (expect ~2 per roll)

## Early-close dates in-sample: 115

| year | early closes |
|---|---|
| 2010 | 4 |
| 2011 | 7 |
| 2012 | 11 |
| 2013 | 3 |
| 2014 | 7 |
| 2015 | 9 |
| 2016 | 7 |
| 2017 | 8 |
| 2018 | 10 |
| 2019 | 9 |
| 2020 | 10 |
| 2021 | 8 |
| 2022 | 8 |
| 2023 | 10 |
| 2024 | 4 |

## prev_front_settle_today NaN in-sample: 1 (dates: 2010-06-07)

## Rolls in-sample: 57
- tdom_from_end on first post-roll date: min=8, median=12.0, max=14 (mid-month sanity for quarterly rolls)

## FOMC scheduled meetings per year

| year | scheduled |
|---|---|
| 2009 | 8 |
| 2010 | 8 |
| 2011 | 8 |
| 2012 | 7 |
| 2013 | 8 |
| 2014 | 8 |
| 2015 | 8 |
| 2016 | 8 |
| 2017 | 8 |
| 2018 | 8 |
| 2019 | 8 |
| 2020 | 7 |
| 2021 | 8 |
| 2022 | 8 |
| 2023 | 8 |
| 2024 | 8 |
| 2025 | 8 |
| 2026 | 8 |
- Years 2009-2025 with count != 8: {2012: np.int64(7), 2020: np.int64(7)}

## First/last dates per file

| file | first | last |
|---|---|---|
| es_settles_insample | 2010-06-07 | 2024-06-28 |
| es_daily_front_insample | 2010-06-07 | 2024-06-28 |
| trading_days.csv (full) | 2010-06-07 | 2026-07-02 |
| fomc_dates.csv | 2009-01-16 | 2026-12-09 |

## Unconditional same-contract |daily return| sanity (hygiene check, not a strategy statistic)

Max |return| = 11.7152% on 2020-03-16.

## Interpretation notes

- `day_volume` sums 1m volume strictly in (prev-day 18:00 ET, this-day 16:00 ET]; the small 16:00-18:00 ET post-settle leg is excluded from every day's day_volume (build_data.py's full 24h session_date window instead folds that leg into the same date).
- `next_id` is session-level: the instrument_id data/rolls.csv's chain says becomes front after the CURRENT front's own next roll (successor of front_id(date)); NaN for the latest front (no successor yet).
- Front/roll assignment is read directly from the already-validated data/rolls.csv, not recomputed.
- FOMC: 'Conference Call' entries and 2020's unscheduled Mar 2/Mar 15 calls are scheduled=False; the 2020 Mar 17-18 slot (cancelled, superseded by those calls) is kept with scheduled=False, empty announce_date -- why 2020 shows <8 scheduled meetings. '(notation vote)' rows are excluded entirely.
- announce_date = last day of the meeting, unless the source page states the statement was released later (e.g. 2020-03-02 meeting -> announced 2020-03-03).
- Network budget for FOMC fetches: 3s used of 600s cap.
