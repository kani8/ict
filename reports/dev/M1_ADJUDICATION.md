# Architect adjudication — Study M1 (liquidity magnetism)

Input: executor M-01 summary (commit `784cb75`, local to the executor
pending push-access resolution; this adjudication reconciles against
`reports/dev/M1_RESULTS.md` when it lands). Executor conduct: correct —
library defaults untouched, downward anomaly surfaced not interpreted,
push failure reported without improvising a remote.

## Verdict on the preregistered question

**Liquidity magnetism: NOT SUPPORTED.** Zero of 18 cells exclude 1.0
upward on any dataset; the reading rule (≥2/3 datasets) returns no
support. On ~72k ES events plus both crypto sets, resting liquidity at
0.5–4 ATR does not attract price beyond what equal-sized unconditional
moves already deliver. "Price seeks liquidity," as a mechanical claim at
these distances and horizons, is not detectable in the data.

## The replicated inverse observation (post-hoc, flagged as such)

The 2.0–4.0 ATR / h=96 cell excludes 1.0 **downward** on all three
datasets (ratios ~0.97–0.98): *mild anti-magnetism* — price under-reaches
toward distant swing extremes relative to baseline. This is consistent
with short-horizon mean reversion near range extremes rather than
liquidity-seeking, and it rhymes with the trading program's conviction
inversion. **Status: post-hoc.** The symmetric rule below was declared
after seeing this result, so the observation is recorded as a
replicated-3/3 hypothesis, to be *confirmed* only by the M-02 temporal
robustness split (declared before that split is run).

## Rulings on the three blocking questions

1. **No library change for Bonferroni.** Raw per-cell CIs stay as
   shipped; multiplicity is handled at the reading-rule layer, where
   cross-dataset replication (≥2/3) is the stronger guard. For the
   record: even one raw upward cell would not have constituted support.
2. **Symmetric rule adopted going forward** (recorded in
   PREREGISTRATION_M): a *downward* exclusion replicated on ≥2/3 datasets
   supports the anti-claim, with the same Bonferroni-at-rule-layer
   treatment. Applied prospectively; today's inverse observation remains
   labeled post-hoc until M-02 Part A rules on it.
3. **Write boundary: `reports/replays/` is confirmed intended** and the
   executor brief is amended to include it.

## M-02 tasking (design declared before execution)

**Part A — temporal robustness of the anti-magnetism cell** (no new
code): rerun `run_magnetism` (defaults, seed 42) on predeclared halves —
ES 2010-06-06→2018-06-30 and 2018-07-01→2026-07-01; BTC and ETH
2023-01-01→2024-09-30 and 2024-10-01→2026-07-01. The 2.0–4.0/96 cell is
**confirmed** iff it excludes 1.0 downward in both halves of ≥2 datasets.
Any other outcome: recorded as unstable, no claim.

**Part B — M2 post-sweep study, frozen design**: events = pool takes at
their `taken_index`, classified sweep vs run. Measures: (i) signed
forward log return at 96/384 (signed so that the ICT-predicted
post-sweep reversal direction is positive); (ii) realized-vol expansion
(std of 1-bar returns over the next 96 bars ÷ prior 96). Controls: K=20
bars matched on ATR ±25% and killzone flag. Support rules: direction —
signed-return CI excludes 0 upward on ≥2/3 datasets; volatility —
event-vs-control expansion CI excludes 1 upward on ≥2/3. Implementation
ships as tested library code (`analytics/sweep_study.py`) from the
architect before Part B runs; the executor does not hand-roll it.
