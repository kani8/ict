# Validation protocol (Trail A) — as of 2026-09-08

Order of operations for every premise. A premise advances only by passing each stage; failing stages are recorded in `RESULTS.md`.

| Stage | Test | Purpose | Threshold |
|---|---|---|---|
| 0 | Literature verification + written pre-registration (`PREMISE_n.md`) before any data look | Kill pattern-hunting at the source; fix the rule, ≤ 4 params, grids, costs, and pass/fail before results exist | — |
| 1 | **Premise test**: rule-independent regression of the target return on the predictor (HAC / clustered SE) | Does the *mechanism* show up at all, independent of any trading rule? (Masters: test entries separately from exits) | t > 2 |
| 2 | **(i) In-sample excellence**: best grid point over the full in-sample span | Is there anything to find even with hindsight? | report |
| 3 | **(ii) In-sample permutation test**: re-optimise on 300 day-shuffled datasets | Is the in-sample best distinguishable from optimising on noise? (selection bias) | report; p < 0.05 expected |
| 4 | **(iii) Walk-forward**: 3y train / 1y test, step 1y, per-window selection, stitched test P&L; **grid-sensitivity table** for every window | Out-of-sample-in-spirit performance; plateau vs spike | gate: stitched Sharpe ≥ threshold pre-stated per premise (1.0 for P1–P2; 0.5 for P3 with justification) and trade-count / positive-year minimums |
| 5 | **(iv) Walk-forward permutation test**: full walk-forward re-run on 200 day-shuffled datasets | Could the walk-forward procedure itself produce this by chance? | **gate: p < 0.05** |
| 6 | Falsification benchmarks pre-stated per premise (e.g. TSH for trend; "always trade" and buy-and-hold for intraday) | Attribute returns to the mechanism vs. drift / risk premia | premise-specific |
| 7 | **OOS, opened once**: 2024-07-01 → 2026-07-01 | The only true out-of-sample number | target net Sharpe ≥ 1.5 |
| 8 | **Deflated Sharpe Ratio** at OOS, using the number of trials across all premises and grids (≈ 3 premises × 4–15 grid points, treated as the trial count), OOS return skew/kurtosis, and 2 years of daily data | Selection bias across the whole programme (Masters' central concern; Bailey–López de Prado's closed form) | report; the Sharpe needed for DSR ≥ 0.95 is stated next to the raw 1.5 |
| 9 | Robustness: 20-day block bootstrap (5,000 reps → 5th-pct Sharpe, 95th-pct drawdown); costs × 0.5 / × 1.5 | Sequence risk and cost sensitivity | report |
| 10 | Sizing review: constant-vol targeting with equity-based throttle added before paper trading | Risk control, not a parameter | — |
| 11 | **Paper trading ≥ 4 weeks** with a pre-stated consistency test: CUSUM on cumulative (paper − backtest-expected) daily P&L with a stopping boundary at 2σ of the backtest daily P&L × √n; realised costs ≤ modelled | Live-vs-backtest drift detection (Masters' monitoring logic) | boundary crossed → stop and diagnose |

Permutation scheme (stages 3, 5): shuffle the order of trading days, each day's cross-sectional return vector moving as a unit (preserves marginals and cross-asset correlation; destroys serial dependence and trends). Restricted to the span where all instruments are listed. For single-instrument intraday premises the analogue is shuffling the order of sessions.
- *Endogenous signal* (trend, P3): the signal is a function of past returns, so shuffling returns scrambles it automatically.
- *Exogenous signal* (VIX basis P4, carry / term spread P5): the return rows are shuffled and re-cumulated onto the original dates while the signal series stays on its original dates. The null is exactly "this signal has no predictive relation to these returns". Drift is preserved under the null in both cases, so (iv) measures the signal's contribution over and above the unconditional premium — the same question each premise's no-signal benchmark (TSH; always-short; equal-weight / always-long) asks directly. Caveat: with autocorrelated signals and returns the permutation p is mildly anti-conservative; it is one gate among several.
- Parameter counts do not grow to accommodate the tests: P3 has one parameter (L), P4 one (θ), P5 one (FX variant), and the ensemble combination rule has none. Fewer grid points make (ii) and (iv) *harder* to pass, not easier.

Not done, deliberately: nested walk-forward (nothing to nest with ≤ 2 params), window-length sensitivity (the brief forbids tuning the scheme), cross-validation (leaks regimes in non-stationary data).

Premises 1 and 2 predate stages 2–3, 5 and 8; they failed at stage 4 with negative stitched Sharpes, and permutation tests can only make a failed result look worse, so they were not back-filled.
