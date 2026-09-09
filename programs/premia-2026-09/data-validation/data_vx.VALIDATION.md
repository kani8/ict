# VALIDATION.md

Sources: CBOE VIX_History.csv (spot); CFE_<code><yy>_VX.csv archive 2004-05..2013-12; VX_<expiry>.csv new-format 2013-01..2026-08 (Wed 30d-before-3rd-Friday-next-month rule, then -1/-2 days if 403).
Archive months attempted 116, found 106. New-format months attempted 164, found 164.
Expiries unresolved in EITHER format: ['2004-12', '2005-04', '2005-07', '2005-09']. These 4 (2004-05..2005-09 vintage) predate every walk-forward window and the EWMA warm-up (P4's first train window starts 2007-07-01), so they are irrelevant to P4.
New-format offsets used: 0d=158, -1d=6, -2d=0.
Holiday-shifted (resolved date != nominal Wed): [('2014-03', '2014-03-19', '-1d'), ('2019-03', '2019-03-20', '-1d'), ('2022-03', '2022-03-16', '-1d'), ('2024-06', '2024-06-19', '-1d'), ('2025-03', '2025-03-19', '-1d'), ('2026-05', '2026-05-20', '-1d')].

## Rescale check: median(front settle / VIX close) by quarter

| quarter | n days | median ratio |
|---|---|---|
| 2006Q1 | 62 | 0.999 |
| 2006Q2 | 63 | 1.000 |
| 2006Q3 | 63 | 1.000 |
| 2006Q4 | 63 | 1.000 |
| 2007Q1 | 61 | 1.000 |
| 2007Q2 | 63 | 1.001 |
| 2007Q3 | 63 | 0.999 |
| 2007Q4 | 64 | 1.001 |

## 2013 archive-vs-new discrepancies (|diff| settle > 0.02, both sources valid)

None found (>0.02 threshold).

## 2013 new-format degenerate settle -> archive used as row-level fallback

| contract | days archive used | raw-overlap days | first | last |
|---|---|---|---|---|
| F13 | 185 | 11 | 2012-04-23 | 2013-01-16 |
| G13 | 184 | 30 | 2012-05-21 | 2013-02-13 |
| H13 | 184 | 54 | 2012-06-25 | 2013-03-20 |
| J13 | 184 | 73 | 2012-07-23 | 2013-04-17 |
| K13 | 181 | 98 | 2012-08-27 | 2013-05-17 |
| M13 | 162 | 117 | 2012-09-24 | 2013-05-17 |
F13/G13/H13/J13 new-format files have Settle==0 for their entire life (not just near expiry); K13/M13 mostly so. Merge rule: new-format wins per (date, expiry) only where its own Settle>0, else the archive row for that date is used (source recorded per row) -- coverage is preserved, see per-year table below.

## Per-year summary

| year | vix days | days w/ f1 | days w/ f2 | f1dte<10 & no f2 | zero-vol rows | med f1 vol | med f2 vol | contango share | settle-close MAD |
|---|---|---|---|---|---|---|---|---|---|
| 2004 | 195 | 194 | 194 | 0 | 50 | 103 | 72 | 79.4% | 1.164 |
| 2005 | 252 | 252 | 252 | 0 | 64 | 147 | 52 | 73.4% | 1.088 |
| 2006 | 251 | 251 | 251 | 0 | 301 | 269 | 130 | 69.3% | 3.001 |
| 2007 | 251 | 251 | 251 | 0 | 269 | 1264 | 553 | 60.6% | 2.104 |
| 2008 | 253 | 253 | 253 | 0 | 458 | 1794 | 822 | 53.8% | 5.390 |
| 2009 | 252 | 252 | 252 | 0 | 94 | 1515 | 1094 | 75.8% | 1.665 |
| 2010 | 252 | 252 | 252 | 0 | 22 | 6949 | 4590 | 79.4% | 0.295 |
| 2011 | 252 | 252 | 252 | 0 | 54 | 17890 | 11918 | 71.4% | 0.810 |
| 2012 | 250 | 250 | 250 | 0 | 41 | 36882 | 27456 | 90.0% | 0.513 |
| 2013 | 252 | 252 | 252 | 0 | 24 | 58322 | 45384 | 86.9% | 0.220 |
| 2014 | 252 | 252 | 252 | 0 | 24 | 70309 | 49720 | 83.3% | 0.202 |
| 2015 | 252 | 252 | 252 | 0 | 74 | 87502 | 57020 | 80.6% | 0.699 |
| 2016 | 252 | 252 | 252 | 0 | 47 | 100137 | 73574 | 86.9% | 0.476 |
| 2017 | 251 | 251 | 251 | 0 | 11 | 121955 | 89052 | 96.4% | 0.107 |
| 2018 | 251 | 251 | 251 | 0 | 20 | 110963 | 90800 | 61.8% | 0.223 |
| 2019 | 252 | 252 | 252 | 0 | 49 | 98952 | 82018 | 82.1% | 0.438 |
| 2020 | 253 | 253 | 253 | 0 | 137 | 68230 | 54997 | 67.6% | 1.762 |
| 2021 | 252 | 252 | 252 | 0 | 44 | 87442 | 70316 | 82.9% | 0.613 |
| 2022 | 256 | 251 | 251 | 0 | 19 | 81763 | 65046 | 67.7% | 0.327 |
| 2023 | 257 | 250 | 250 | 0 | 25 | 86720 | 65412 | 87.6% | 0.292 |
| 2024 | 128 | 124 | 124 | 0 | 16 | 96994 | 67646 | 87.9% | 0.313 |

## f1_dte distribution at roll (nominally ~20-21, up to 25 in 5-Wednesday months)

n rolls=255, min=1, p25=19, median=20, p75=24, max=44. ==25 (normal, 5-Wednesday month): 35. >25 (anomalous): 4 -- all of these (42-44 days) coincide exactly with unresolved archive expiries above (front skips the missing contract-month).

## Interpretations

- dte_biz counted on VIX trading calendar per spec; f1/f2 require strictly expiry>date (expiry-day settle itself doesn't count as f1).
- Zero-volume rows kept (illiquid early contracts / far months); settle-close MAD is inflated on those days since close=0 when no trade occurs.
- Archive header identical across 2004-2013 samples checked; no column renaming needed beyond lowercasing/whitespace strip.

## Timing

- Total wall time: 1.7s
