# Architect adjudication — M-02 Part A

Input: `reports/dev/M2_PARTA_RESULTS.md` (commit `399c264`). Executor
conduct: exemplary — no goalpost moves, caveats surfaced against its own
result, out-of-scope lint left untouched.

## Ruling: the anti-magnetism cell is CONFIRMED under the predeclared rule.

ES and ETH exclude 1.0 downward in *both* predeclared temporal halves;
BTC straddles 1.0 in both halves (thinnest per-half sample). 2/3 meets
the bar exactly. Accepted caveats: minimum-threshold pass; effect size
small (~2–3% under-touch).

**The measurement program's first confirmed finding, stated precisely:**
at 2.0–4.0 ATR distance and 96-bar horizon, price reaches resting
liquidity *slightly less often* than ATR-matched unconditional moves —
a small, temporally stable, cross-venue (ES 16y + ETH) anti-magnetism,
the opposite sign of the folklore claim. Interpretation (hypothesis, not
finding): swing extremes at distance behave like mean-reversion
boundaries, not magnets.

## Ancillary rulings

- BTC's h=384 downward cell stays uncounted (outside the ruling object) —
  correctly reported for completeness only.
- The executor-reported `ModelLevelEventGuard permission-denied (4110)`
  hook context in its environment is escalated to the user: if that
  guard was meant to be enforcing, its configuration needs attention on
  the executor's side; it is not part of this repository.
- Part B (post-sweep study) now runs on `analytics/sweep_study.py` as
  shipped — frozen design, no re-implementation.
