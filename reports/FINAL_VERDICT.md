# FINAL VERDICT: FAILED CONFIRMATION — research concluded, do not deploy

- Date: 2026-07-01
- Frozen specification: commit `543ec122cacbd04ff6804b3998a649e3d9c50a12`
- Preregistration: `HOLDOUT_PREREGISTRATION_543ec12.md` (auditor-held)
- Status: **the preregistered stopping rule has fired. This composition is
  closed. No further tuning, re-testing, or deployment.**

## The holdout that ended it

First untouched holdout, run once under the fully frozen strategy with
repaired 1m execution resolution:

- Binance spot ETHUSDT, [2023-01-01, 2026-07-01) UTC
- 15m signal timeframe, 1m execution resolution (conservative fallback on
  the single incomplete bucket), repository-default config and costs
- 500 trade-template-null simulations; mean-R p-value preregistered as the
  primary statistic with a Bonferroni-adjusted 0.025 threshold

| Metric | Result |
|---|---|
| Trades | 129 |
| Total return | **−12.92%** |
| Profit factor | 0.87 |
| Mean trade R | −0.18, 95% block-bootstrap CI [−0.53, 0.18] |
| Mean-R null p | 0.527 |
| Total-return null p | 0.371 |
| Max drawdown | −25.76% |
| CAGR | −3.88% |
| Win rate | 27.1% |

Every required economic direction check failed: negative return, negative
mean R, profit factor below 1, p-value nowhere near threshold. Under the
preregistered two-market rule (each holdout non-negative), a joint pass
became mathematically impossible the moment ETH came in negative.

Data integrity for the run: 122,587 15m candles and 1,838,800 1m candles,
zero duplicates, zero OHLC violations, independently aggregated 1m matched
15m exactly on all 122,586 complete buckets; one exchange gap (5×15m /
80×1m bars) plus one incomplete bucket handled by the preregistered
conservative fallback.

## The complete evidence record

The frozen canonical ICT/SMC composition (HTF bias → liquidity sweep → MSS
→ OTE-band FVG/OB retrace → opposing-liquidity target) failed:

1. **BTCUSDT 15m, 2023–2026** (original audit at `127e2c7`): −34.5%
   conservative, −5.6% at zero costs, negative in every calendar slice,
   p = 1.0 vs the drift control.
2. **BTC regression at `cf8706a`** (burned sample, diagnostic only):
   −18.1% conservative, zero-cost +5.8% statistically inconclusive.
3. **ETHUSDT 15m+1m, 2023–2026** (untouched, preregistered, frozen spec):
   the table above.

Each failure survived progressively stricter execution modeling — including
a phantom-profit engine bug whose *fix removed an advantage* the strategy
had been enjoying, and 1m-resolution fills that eliminated the
conservative/optimistic ambiguity excuse.

## Scope of the conclusion

This does not prove every ICT concept is worthless in every market,
timeframe, or discretionary hand. It establishes, with preregistration and
honest execution modeling, that **this canonical mechanical composition has
no detectable edge and should not be traded or further tuned.** Any future
ICT-related work is a *new study*: new hypothesis, new frozen
specification, new untouched data — not a continuation of this one.

An ES/index-futures run remains educational (ICT's home market) but cannot
alter this verdict and must be labeled exploratory, with its own frozen
provider/roll/session/DST/cost protocol.

## What the project produced

The deliverable was never the strategy — it was the answer. The harness
(confirm-index discipline, prefix-consistency tests, pessimistic and
1m-resolved execution, matched nulls with diagnostics, block bootstrap,
preregistered stopping rules) survived three adversarial audits and is
reusable for the next hypothesis. The strategy did not survive. That is a
completed piece of research: **the popular mechanical reading of Smart
Money Concepts, tested fairly, failed.**
