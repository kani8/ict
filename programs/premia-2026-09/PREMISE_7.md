# PREMISE 7 — "Dash for Cash": Turn-of-the-Month Liquidity Flows in ES

**Status:** FROZEN 2026-09-08 after verification against the primary text (Etula, Rinne, Suominen & Vaittinen, *Dash for Cash*, working-paper PDF read directly; published *RFS* 33(1) 2020) and **before any calendar-conditioned return on our ES data has been computed**. `data_calendar/` is being built as a hygiene-only job. Zero free parameters. Premise cap raised 6 → 8 by the user on 2026-09-08; P8 (FOMC cycle) was rejected at the literature stage (see `RESULTS.md`), so P7 is the last registered premise.

## Economic / behavioural mechanism
Institutions with predictable month-end cash obligations (pension payments, mutual-fund redemptions, salaries) must sell equities by the close of **T−3** (T = last trading day) to have settled cash at month end under T+3 settlement. That selling depresses prices over T−8…T−4 and, because it is liquidity- not information-driven, reverses over T−3…T−1; the cash is then partly reinvested (401k contributions, payroll) over T…T+3, the classic turn-of-the-month effect (Ogden 1990; McConnell & Xu 2008). The authors document the mechanism with institutional trade data (net selling to the morning of T−3, net buying after), month-end funding-rate spikes, and the migration of the pattern when US settlement shortened in June 1995. Settlement is now T+1 (May 2024), which is a pre-stated reason the *timing* within the window may have shifted; the flows themselves remain.

## Falsifiable statement
On ES futures, **the mean daily return over the seven trading days T−3…T+3 exceeds the mean daily return on all other days**, and a position that is long ES only on those days, vol-targeted, earns a **higher net Sharpe than an always-long vol-targeted ES position on the same calendar**. If being long only one-third of the time does not beat being long all the time in Sharpe terms, the calendar carries no information beyond the equity premium and the premise is unsupported.

Predicted: difference-in-means t > 2 (HAC); window-only Sharpe > always-long Sharpe with roughly half the volatility.

## Where it should fail (pre-stated)
- **Post-publication decay / crowding** (paper circulated 2014–15, published 2020). No rigorous 2015–2025 replication exists; informal evidence suggests long-only TOM strategies recently earned less than buy-and-hold with smaller drawdowns.
- **Settlement change to T+1 (2024-05-28)**: the selling deadline moves to T−1, which could shift the reversal window later; this affects the last month of in-sample and all of OOS. Not to be patched by re-defining the window.
- **A 14-year bull market**: always-long is a hard benchmark (SPY Sharpe 0.85 on our stitched calendar). A window that earns "the entire market excess return" must earn *all* of a very large premium in 1/3 of the days.
- **Event clustering**: FOMC days and month-ends coincide often; the window's return may partly be macro-announcement premium (Savor & Wilson 2013) — reported, not filtered.

## Instrument and data (fixed)
ES front-month futures per `data/rolls.csv` (volume-crossover rolls at Sunday session start); daily settle = close of the last 1-minute bar before 16:00 ET; same-contract settle-to-settle returns (on the first date after a roll, the return is computed on the outgoing contract, then the position is rolled). Trading-day index within the month from the ES trading calendar (`data_calendar/trading_days.csv`). Futures return is an excess return.

## Exact rule (frozen, zero parameters)
- **Window**: trading days T−3, T−2, T−1, T, T+1, T+2, T+3 (T = last trading day of the calendar month). Enter long at the settle of **T−4**, exit at the settle of **T+3**; flat all other days. The position earns exactly the seven daily returns T−3…T+3.
- **Sizing**: `w = 0.10 / σ_t` where σ_t = annualised EWMA std (COM 60) of ES daily front-contract returns to the entry date T−4; held constant through the window; gross cap 3× (will not bind). Book $100k. MES contract for live ($5 × index).
- **Costs**: per side 0.25 index points + $0.50 commission per MES, i.e. `(0.25 + 0.10)/P` of notional (0.6–1.7 bp per side over the sample); charged on entry, exit, and on both legs of any roll that falls inside a window. Stress: 2 ticks per side.
- Daily P&L series with zeros on flat days → Sharpe = mean/std · √252.

## Benchmarks (same data, sizing, costs, calendar)
- **Always-long** vol-targeted ES (`w = 0.10/σ_t`, re-set monthly at T−4 for comparability): the falsification benchmark.
- Reported for context (no gate): long only T…T+3 (McConnell–Xu window); long T−3…T−1 only; the rule plus **short T−8…T−4**; SPY buy-and-hold.

## Tests (stitched calendar 2010-07-01 → 2024-06-30, same as P3–P6)
1. **Premise test**: `r_t = a + b·1[t ∈ T−3…T+3] + ε`, Newey–West 5 lags: **t(b) > 2**. Also report mean returns by day-of-month bucket (T−8…T−4, T−3…T−1, T…T+3, T+4…T+8, other) with HAC t-stats.
2. **Fixed rule**: Sharpe (1 tick / 2 ticks), ann. return & vol, max DD, time in market (≈ 33 %), average |w|, P&L and Sharpe per test year (14 Jul→Jun rows), P&L split T−3…T−1 vs T…T+3.
3. **Permutation test (exogenous signal)**: 500 shuffles of the daily return series on the stitched calendar, window indicator fixed to its dates; σ, weights, costs recomputed; p = share ≥ real. Gate (d).
4. **Sensitivity table (report only; changes nothing)**: the four context variants above, Sharpe each.
5. **No-lookahead**: prefix test on σ and weights at 5 cutoffs (the calendar is known in advance; the only estimated input is σ).
6. **Gate**: (a) stitched Sharpe ≥ 0.5; (b) rule Sharpe > always-long Sharpe; (c) ≥ 8/14 positive test years; (d) p < 0.05.

## Honest expectations
If the 1926–2013 magnitude (≈ 11 bp/day in-window) persisted at half strength on ES 2010–2024: ≈ 6 bp/day × 84 days ≈ 5 %/yr on ≈ 10 % vol → **Sharpe ≈ 0.45–0.5 net**; at full strength ≈ 0.9. Gate (b) is the hard one: always-long ES earned ≈ 0.8 over this period. Prior of clearing the gate: **~35 %**. If it passes, its role in the ensemble is a low-vol, one-third-time-in-market equity-premium harvester with near-zero correlation to P4 outside crisis months.

## What I will NOT do
Shift the window after seeing results (including to accommodate T+1 settlement); add FOMC/VIX filters; add the short T−8…T−4 leg to the rule if it happens to help in-sample; trade intraday; re-open OOS.

## Literature anchors (verified against the primary text 2026-09-08)
- Etula, Rinne, Suominen & Vaittinen, *Dash for Cash* (working paper, AEA 2016; *RFS* 33(1), 2020, pp. 75–111): "since July 1926, one could have held the US value-weighted stock index (CRSP) for only seven days a month and pocketed the entire market excess return with nearly fifty percent lower volatility"; "average annualized S&P 500 return from T−8 to T−4 is −3.4 % versus 28.6 % from T−3 to T+3"; CAPM alpha 5.6 %/yr, FF3 6.2 %, 5-factor 6.3 %, all significant at 1 %; selling-pressure returns "statistically indistinguishable from zero" in all 24 markets; reversal T−3…T−1 share of the 7-day return rose from 30 % (1980–May 1995) to 47 % after the 1995 settlement change; institutional trade data (ANcerno 1999–2013) show net selling to the morning of T−3 and net buying T−1…T+4.
- McConnell & Xu (2008), *FAJ* 64(2): turn-of-the-month = last trading day + first three; magnitudes not re-verified today.
- Post-2019 replication: none peer-reviewed found (UNVERIFIED blog evidence of erosion only).

## Deviations / interpretations stated before testing
- Futures instead of the cash index: excess return is the futures return; dividends are in the basis, not a separate leg. T is the last *ES* trading day of the month (equals the NYSE last day).
- Long-only by construction: the paper's own numbers imply the T−8…T−4 short would reduce the leg's Sharpe; the user's long-and-short preference is met by P4, not by forcing a leg with negative expected contribution.
