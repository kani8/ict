# Preregistration — Study V3 "Origin": narrative-engine bias

- Date: 2026-07-02
- Status: **CONCLUDED (2026-07-03). Crypto track closed at development;
  ES track closed at development (Iteration 04: separation absent or
  inverted on 16y of ES). See `reports/PROGRAM_CONCLUSION.md`. All
  holdouts sealed, never touched.** See the change log below and
  `reports/dev/V3_ITER03_ADJUDICATION.md`. This study originates its own
  mechanization of HTF narrative formation rather than testing ICT's
  canonical composition (V1: failed, concluded; V2.1: frozen, holdout
  execution recommended retired).

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

- **ES (S&P 500 futures) = development data** for the index track —
  deliberately burned once sourced. Window widened (2026-07-02, declared
  before any index data contact) from 2023-2026 to the **full available
  history 2010-06-06 → 2026-07-01** for statistical power: ~1,000+
  non-overlapping 4-day diagnostic windows across four volatility
  regimes vs ~230 in one regime. Source: Databento GLBX.MDP3, schema
  OHLCV-1m (15m derived locally by exact resample), purchased as the
  full ES product (all instruments, 1m bars). Roll method (declared
  before data contact): the executor stitches the lead contract by
  **volume rank** computed from the bars themselves (OHLCV carries
  volume, not open interest), rolling when the next contract's daily
  volume overtakes the front's, then **back-adjusts** at each roll and
  logs every roll date in the iteration report. Spread instruments
  (e.g. ESU6-ESZ6) are excluded before stitching.
- **NQ (Nasdaq-100 futures) = reserved index holdout**, widened to the
  same 2010-2026 span (declared before contact) — never fetched,
  inspected, or summarized until an index-track freeze.
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
- Iteration 02 → 03: forward-return diagnostic added as a tested library
  function (non-overlapping windows); await-abandonment split into
  expired/violated/displaced; single declared lever for Iteration 03 =
  entry path (`entry_confirmation` paired comparison), weights held;
  ES export protocol ruled (back-adjusted, OI roll, 23h Globex).
  Stop-condition for crypto development declared in
  `reports/dev/V3_ITER02_ADJUDICATION.md`.
- Iteration 03 → close: **stop condition ruled MET**
  (`reports/dev/V3_ITER03_ADJUDICATION.md`). The crypto development
  track is closed with a negative finding (no consistent forward-return
  separation; ETH anti-predictive). The crypto holdouts (BNBUSDT
  2023–2026, ETHUSDT 2019–2022) were never touched and remain reserved.
  The index track (ES development / NQ holdout) is the sole open line,
  gated on a user-supplied ES export.

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
