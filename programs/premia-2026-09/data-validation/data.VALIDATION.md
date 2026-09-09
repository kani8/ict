# VALIDATION.md

## Row counts per file

| file | rows |
|---|---|
| rolls.csv | 65 |
| es_1m.parquet | 5,615,431 |
| es_1m_insample.parquet | 4,907,229 |
| es_1m_oos.parquet | 708,202 |
| es_1h.parquet | 95,759 |
| es_1h_insample.parquet | 83,947 |
| es_1h_oos.parquet | 11,812 |
| es_4h.parquet | 24,656 |
| es_4h_insample.parquet | 21,575 |
| es_4h_oos.parquet | 3,081 |

## Per-year 1h bar counts (combined es_1h)

| year | 1h bars |
|---|---|
| 2010 | 3,524 |
| 2011 | 6,089 |
| 2012 | 6,059 |
| 2013 | 6,012 |
| 2014 | 5,940 |
| 2015 | 6,102 |
| 2016 | 5,911 |
| 2017 | 5,886 |
| 2018 | 5,955 |
| 2019 | 5,899 |
| 2020 | 5,916 |
| 2021 | 5,923 |
| 2022 | 5,903 |
| 2023 | 5,894 |
| 2024 | 5,920 |
| 2025 | 5,880 |
| 2026 | 2,946 |

## Distinct instruments used as front: 66

## Roll table summary

- count: 65
- forced (pre-expiry) rolls: 0
- days-before-expiry: min=3, median=4.0, max=4

## RTH-hour (09:30-16:00 ET weekdays) 1h windows with n_1m < 30

| date | hour ET | n_1m | instrument | condition.json |
|---|---|---|---|---|
| 2010-11-26 | 13:00 | 15 | 3076 | available |
| 2011-05-30 | 11:00 | 29 | 75884 | available |
| 2011-11-25 | 13:00 | 15 | 45580 | available |
| 2012-04-06 | 09:00 | 15 | 27069 | available |
| 2012-07-03 | 13:00 | 16 | 3366 | available |
| 2012-10-29 | 09:00 | 15 | 10113 | available |
| 2012-10-30 | 09:00 | 15 | 10113 | available |
| 2012-11-23 | 13:00 | 15 | 10113 | available |
| 2012-12-24 | 13:00 | 15 | 23970 | available |
| 2013-07-03 | 13:00 | 15 | 17704 | available |
| 2013-11-29 | 13:00 | 15 | 28112 | available |
| 2013-12-24 | 13:00 | 15 | 382206 | available |
| 2014-07-03 | 13:00 | 15 | 111473 | available |
| 2014-11-28 | 13:00 | 15 | 28095 | available |
| 2014-12-24 | 13:00 | 16 | 50393 | available |
| 2015-04-03 | 09:00 | 16 | 85974 | available |
| 2015-07-03 | 13:00 | 1 | 58738 | available |
| 2015-11-27 | 13:00 | 15 | 13950 | available |
| 2015-12-24 | 13:00 | 15 | 49705 | available |
| 2016-11-25 | 13:00 | 15 | 2928 | available |
| 2017-07-03 | 13:00 | 15 | 24842 | available |
| 2017-11-24 | 13:00 | 15 | 23936 | available |
| 2018-07-03 | 13:00 | 16 | 57287 | available |
| 2018-09-03 | 13:00 | 1 | 57287 | available |
| 2018-11-23 | 13:00 | 15 | 16114 | available |
| 2018-12-24 | 13:00 | 15 | 18720 | available |
| 2019-07-03 | 13:00 | 15 | 37699 | available |
| 2019-11-29 | 13:00 | 15 | 16145 | available |
| 2019-12-24 | 13:00 | 15 | 10571 | available |
| 2020-03-16 | 09:00 | 22 | 10571 | available |
| 2020-06-30 | 10:00 | 11 | 12181 | degraded |
| 2020-11-27 | 13:00 | 15 | 19100 | available |
| 2020-12-24 | 13:00 | 15 | 5482 | available |
| 2021-04-02 | 09:00 | 15 | 3853 | available |
| 2021-11-26 | 13:00 | 15 | 8858 | available |
| 2022-11-25 | 13:00 | 15 | 206323 | available |
| 2023-04-07 | 09:00 | 15 | 95414 | available |
| 2023-07-03 | 13:00 | 15 | 3445 | available |
| 2023-11-24 | 13:00 | 15 | 314863 | available |
| 2024-07-03 | 13:00 | 15 | 118 | available |
| 2024-11-29 | 13:00 | 15 | 183748 | available |
| 2024-12-24 | 13:00 | 15 | 5002 | available |
| 2025-07-03 | 13:00 | 15 | 14160 | available |
| 2025-11-28 | 13:00 | 15 | 294973 | degraded |
| 2025-12-24 | 13:00 | 15 | 42140878 | available |
| 2026-04-03 | 09:00 | 15 | 42140864 | available |

## 1-min return check on continuous close (|return| > 5%)

| ts_utc | instrument_id | close | return |
|---|---|---|---|
| 2020-03-16 13:45:00+00:00 | 10571 | 2375.0 | -5.5102% |

## Largest absolute price jump across a roll (from-close vs to-open)

Largest: 73.75 pts at 2024-12-16 23:00:00+00:00 (ESZ4 close 6076.5 -> ESH5 open 6150.25)
Median jump across all 65 rolls: 7.50 pts

## Instrument expiry mapping (5 earliest, 5 latest) -- for eyeballing

| instrument_id | symbol | expiry_date |
|---|---|---|
| 6640 | ESM0 | 2010-06-18 |
| 26714 | ESU0 | 2010-09-17 |
| 3076 | ESZ0 | 2010-12-17 |
| 70248 | ESH1 | 2011-03-18 |
| 75884 | ESM1 | 2011-06-17 |
| 42140878 | ESH6 | 2026-03-20 |
| 42140864 | ESM6 | 2026-06-19 |
| 42140870 | ESU6 | 2026-09-18 |
| 10252 | ESZ6 | 2026-12-18 |
| 42140860 | ESH7 | 2027-03-19 |

## Notes

- Prices are UNADJUSTED across rolls (no back-adjustment), per spec.
- Roll timing is tightly clustered at 3-4 days before expiry (effective sessions fall on {'Monday': 43, 'Tuesday': 22}), i.e. Mon/Tue of expiry week. Spot-checked against raw per-session volume for the first roll (ESM0->ESU0, instrument_id 6640/26714): next-quarter volume genuinely overtakes front on the Friday 7 calendar days before expiry, but the rule only rolls at the START of the FOLLOWING session, which is the Monday after the weekend -- hence the effective roll lands 3-4 days before expiry, not a bug.
- Wall-clock (ET) resampling floors on tz-naive local time; the one ambiguous DST fall-back hour/year is not specially disambiguated, but it falls in CME's weekly Sunday closure so no real bars are affected.
- OOS files (*_oos.parquet) are locked -- do not read until final testing.
