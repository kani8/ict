# Real-market verdict: FAILED VALIDATION — do not deploy

**Status: this sample is burned.** Any parameter or rule change inspired by
these results must be evaluated on untouched markets/periods with a frozen
specification. Do not sweep parameters against this dataset.

- Date of audit: 2026-07-01 (external validation run)
- Commit tested: `127e2c77cb7206106a47dbc7a59c2522624c7cda`
- Config: repository defaults (`configs/default.toml`), predeclared before
  any real data was observed — a genuine out-of-sample test
- Data: Binance BTCUSDT spot klines, 15m, 2023-01-01 → 2026-07-01 UTC
  (122,588 rows; 0 duplicates; 0 OHLC violations; one 5-bar gap on
  2023-03-24 12:30–14:00 UTC)
- Costs: 1 bp full spread, 2 bps commission/side, 1 bp slippage on
  aggressive fills

## Headline results (conservative intrabar policy)

| Metric | Value |
|---|---|
| Trades | 174 |
| Total return | **−34.48%** |
| Profit factor | 0.72 |
| Mean R | −0.36, 95% bootstrap CI [−0.64, −0.06] |
| Max drawdown | −40.58% |
| CAGR | −11.39% |

## Robustness

| Test | Trades | Return | PF | Mean R | Read |
|---|---|---|---|---|---|
| Full period, conservative | 174 | −34.48% | 0.72 | −0.36 | Fails |
| Full period, optimistic | 174 | +1.87% | 1.01 | +0.75 (CI [−0.19, 2.33]) | Inconclusive; not an edge |
| Full period, **zero costs** | 174 | −5.59% | 0.95 | −0.03 | **No gross edge exists** |
| 2023 slice | 48 | −4.35% | 0.88 | −0.08 | Negative |
| 2024 slice | 50 | −8.75% | 0.76 | −0.44 | Negative |
| 2025 slice | 55 | −22.84% | 0.50 | −0.54 | Clearly negative |
| 2026 H1 slice | 19 | −4.18% | 0.71 | −0.43 | Negative (small n) |

Random-baseline (drift control, 500 sims): strategy −34.48% vs null mean
−11.30% ± 5.03%, p = 1.000.

The conservative/optimistic spread traces to 12 ambiguous bars whose
stop-vs-target ordering flips between policies; the truth requires 1m data.
Both bounds round to "no edge": the floor is decisively negative, the
ceiling is ~zero over 3.5 years with a −20.9% drawdown.

## Interpretation

The predeclared canonical ICT/SMC composition (HTF bias → liquidity sweep →
MSS → OTE-band FVG/OB retrace → opposing-liquidity target) has **no
detectable gross edge and a clearly negative after-cost edge** on this
market/timeframe/period. This does not disprove every ICT concept in every
context; it does mean this exact composition failed its first honest
real-market test and must not be traded or tuned on these results.

## Audit findings on the harness (addressed after this verdict)

The auditor confirmed test suite, lint, cost handling, next-bar fills,
conservative ambiguity handling, and confirm-index gating, and flagged four
validity improvements — all fixed in commits after `127e2c7`; the fixes do
not and cannot change this verdict:

1. Random-entry control was not exposure/risk matched → replaced by a
   matched-trade-template null with matching diagnostics
   (`analytics/significance.py::matched_baseline_test`).
2. IID bootstrap ignores regime clustering → block bootstrap added and used
   in reports (`block_bootstrap_ci`).
3. OB fallback could select an already mitigated/invalidated block →
   lifecycle-filtered in `SMCStrategy._find_poi`; resting orders now cancel
   when their POI dies.
4. Entry-bar ambiguity needs 1m-data resolution → sub-bar resolution added
   to the engine (`Backtester(intrabar=...)` / `--intrabar-data`).

## Addendum (2026-07-01): regression diagnostic at cf8706a

The audit remediations (notably OB lifecycle filtering) changed the entry
set — **current HEAD is a revised strategy**, not the audited one. The
auditor's re-run on the same burned BTC sample, recorded here strictly as a
software-regression diagnostic:

| Metric (cf8706a, conservative) | Value |
|---|---|
| Trades | 123 (was 174) |
| After-cost return | −18.10% |
| Profit factor | 0.81 |
| Mean R | −0.28, 95% block-bootstrap CI [−0.64, 0.10] |
| Matched-null p (500 sims) | 0.251 |
| Zero-cost return | +5.78% |
| Optimistic after-cost return | +21.40% |

Null-matching diagnostics from that run (why the matched-null label needs
care): strategy exposure 0.67% vs null mean 1.43%; mean holding 6.7 vs 14.2
bars; trades 123 vs 123. The null preserves trade count, side, and fractional
risk geometry but executes at market on randomized timing, so realized
exposure/holding differ — hence the mean-R second statistic added after this
re-audit.

**This addendum is not validation.** The burned sample cannot validate the
revision; the zero-cost regression being positive but inconclusive changes
nothing about the deployment rejection. The revised strategy gets exactly one
frozen test on untouched data (see below).

### Second re-audit (2ef571d): two execution defects, both fixed

Found before the holdout was touched (holdout preserved): (1) partial
intrabar coverage was treated as complete, letting a missing sub-bar
suppress a same-bar stop; buckets now require every expected sub-bar
timestamp or the conservative policy applies. (2) A marketable entry
gapping through its own stop booked the exit at the stale stop level —
phantom profit (a long limit at 100 filling at a 90 open with stop 95
recorded +5 on a "stop loss"); such positions now exit immediately at the
fill basis with full costs. Both reproduced, fixed, and regression-tested.
Notably, the phantom-profit defect was *favorable* to the strategy and it
still failed the BTC test — the historical verdict is unaffected.

## Decision rule going forward

Repair-then-freeze: with the null and bootstrap fixed and (eventually)
1m intrabar resolution added, freeze the specification and run **once** on
untouched instruments and periods. If the result is again negative or
indistinguishable from zero: stop.
