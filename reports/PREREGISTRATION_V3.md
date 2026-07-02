# Preregistration — Study V3 "Origin": narrative-engine bias

- Date: 2026-07-02
- Status: **development phase.** This study originates its own
  mechanization of HTF narrative formation rather than testing ICT's
  canonical composition (V1: failed, concluded; V2.1: frozen, holdouts
  pending and reserved).

## Hypothesis

A mechanized narrative — a weighted vote of 4h, daily, and weekly
structure, draw-on-liquidity imbalance (untaken daily pools + unfilled
daily FVGs above vs. below price), and IPDA 20/40/60-day range events
(close-breaks = continuation; sweep-and-recover = reversal; the windows
vote so cross-horizon agreement scales conviction) — identifies
directional regimes with enough reliability that the ICT trigger stack
(sweep → MSS → IFVG/FVG/OB retest confirmation) extracts a positive
after-cost edge. A conviction threshold enforces "no narrative, no
trade."

Research basis for the factor set: ICT's own stated bias inputs — IPDA
20/40/60-day data ranges as institutional reference points, the next
draw on liquidity as the target, and premium/discount confirmation
(tradingfinder.com, innercircletrader.net IPDA and daily-bias tutorials,
tradingstrategyguides.com trade-plan notes).

## Data-usage protocol

- **Development set (tuning allowed):** BTCUSDT and ETHUSDT 15m+1m,
  2023-01-01 → 2026-07-01. Both are already burned by V1 and carry no
  confirmatory value; using them in-sample is therefore legitimate and
  declared. Any change to weights, conviction threshold, IPDA windows,
  or factor definitions happens here and only here.
- **Holdouts (one shot each, untouched by every prior study):**
  1. BNBUSDT 15m+1m, [2023-01-01, 2026-07-01)
  2. ETHUSDT 15m+1m, [2019-01-01, 2023-01-01)
  (SOLUSDT 2023-2026 and BTCUSDT 2019-2022 remain reserved for V2.1.)
- Pre-2023 FOMC dates must be added via `news_csv` from the Fed's
  published calendar before any holdout price data is inspected.

## Amendment: index-futures track (2026-07-02, before any index data contact)

Per user directive to investigate ICT's home market:

- **ES (S&P 500 futures) 2023-01-01 → 2026-07-01, 15m+1m = development
  data** for the index track — deliberately burned once sourced.
- **NQ (Nasdaq-100 futures) 2023-2026 = reserved index holdout** —
  never fetched, inspected, or summarized until an index-track freeze.
- Prerequisites for any ES run: continuous back-adjusted contract with
  roll method recorded; session-correct `--bars-per-year`; recalibrated
  costs; full high-impact calendar (incl. CPI) per
  `docs/CALENDAR_SOURCES.md`, committed before price contact.
- The crypto holdouts and decision rule below are unaffected.

## Development-phase changes log

- Iteration 01 → 02: `dol_lookback_days = 60` (defect fix: stale
  liquidity no longer counts as draw); setup-funnel instrumentation;
  null test skipped and labeled when n < 5. Declared before any holdout
  contact; crypto dev sets only.

## Decision rule (unchanged machinery)

Frozen config: [`configs/v3_origin.toml`](../configs/v3_origin.toml) as
of the freeze commit (to be declared when development ends; until then
this preregistration binds the *protocol*, not the parameter values).
PASS requires: both holdouts' total return ≥ 0, both mean trade R > 0,
and at least one mean-R null p < 0.025 (500 trade-template sims,
conservative 1m-resolved execution, default costs). Anything else is
FAIL — and V3, like its predecessors, stops there.

## Declared limitations

- The narrative engine codifies four of ICT's stated bias inputs.
  Weekly profiles, seasonality, SMT divergence (needs a correlated
  second instrument), NWOG/NDOG, and bond/dollar correlation are not
  implemented; a future factor must be added *before* holdout contact.
- Equal factor weights are the default to minimize degrees of freedom;
  any tuning on the development set must be reported alongside the
  holdout result.
