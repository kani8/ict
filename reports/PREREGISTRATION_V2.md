# Preregistration — Study V2: maximum-faithfulness ICT composition

- Date: 2026-07-02
- Status: **spec frozen at the commit introducing this file; awaiting its
  one-shot holdout runs.** V1 is concluded (`reports/FINAL_VERDICT.md`)
  and is not being rescued; V2 is a distinct hypothesis.

## Amendment V2.1 (2026-07-02, declared before any holdout contact)

No holdout data has been fetched or inspected; this amendment supersedes
the original spec cleanly. Rationale: ICT frames the HTF narrative as the
*majority contributor* to trade probability, with the entry mechanics as
triggers only. The original V2 encoded bias as a single 4h veto, which
under-weights that judgment layer. V2.1 makes bias dominance explicit:

- `bias_htf2_multiplier = 96` — the **daily** structure direction must
  agree with the 4h bias (two-timeframe top-down agreement).
- `require_htf_discount = true` — longs only below the HTF dealing-range
  equilibrium (discount), shorts only above it (premium).
- `require_draw = true` — an untaken HTF liquidity pool must exist beyond
  price in the trade direction: the draw on liquidity the market is
  reaching for.
- `news_day_blackout = true` — the strict "only trade days with no news"
  reading: the entire ET calendar day of any NFP/FOMC event is excluded,
  not just a window around it.

All four gates apply at signal time before any trigger is considered.
Everything else in the original specification, the holdouts, and the
decision rule below is unchanged.

## Hypothesis

Adding the remaining major ICT teachings — inversion fair value gaps as
the primary POI, DST-correct New-York-time killzones including the Silver
Bullet window, standing aside around high-impact news (NFP + FOMC),
retest-plus-confirming-close entries instead of resting limits, and
breakeven at +1R — produces a positive, statistically detectable after-cost
edge where the V1 composition did not.

## Frozen specification

- Strategy: `SMCStrategy` with [`configs/v2_faithful.toml`](../configs/v2_faithful.toml),
  exactly as committed alongside this file. No parameter may change before
  the holdout runs.
- Execution: conservative intrabar policy with 1m sub-bar resolution
  (complete buckets only), default cost model (1 bp spread, 2 bps
  commission/side, 1 bp slippage on aggressive fills), 100k initial equity.
- News calendar: built-in NFP (first Friday 08:30 ET) + FOMC decision days
  (embedded 2023–2026 Fed schedule), 30 min before / 60 min after. For the
  pre-2023 holdout a CSV with that period's FOMC dates must be supplied
  from the Fed's published calendar *before* looking at prices.

## Holdout data (untouched by all prior studies)

1. **SOLUSDT** Binance spot, 15m + 1m, [2023-01-01, 2026-07-01) UTC.
2. **BTCUSDT** Binance spot, 15m + 1m, [2019-01-01, 2023-01-01) UTC
   (period untouched; BTC 2023–2026 is burned).

Each run exactly once, at the frozen commit, with
`--validate 500` (trade-template null; mean-R p-value is the primary
statistic) and the standard report.

## Decision rule (declared before any data is seen)

- **PASS** requires ALL of: both holdouts' total return ≥ 0; both mean
  trade R > 0; and at least one holdout with mean-R null p < 0.025
  (Bonferroni for two markets).
- Anything else is **FAIL — stop.** No re-runs, no parameter changes, no
  additional markets to "check". A failed V2 closes the mechanical-ICT
  research program in this repository.
- An ES/index-futures study, if ever run, is a separate preregistration
  with its own provider/roll/session/cost protocol.

## Known residual limitations (declared up front)

- NFP first-Friday rule has rare exceptions; CPI and other releases are
  not in the built-in calendar. The blackout is therefore a partial
  implementation of "don't trade the news."
- The confirmation entry gates the *signal* by killzone at the structure
  break and the *entry* only by the news filter; a retest can trigger
  outside the killzone window.
- Crypto holdouts test the composition, not ICT's home venue (index
  futures). A negative result binds the composition on crypto.
