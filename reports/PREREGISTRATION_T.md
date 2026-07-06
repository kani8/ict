# Preregistration — Program T: diversified time-series momentum with volatility targeting

- Date: 2026-07-06 (architect). Status: **open — Stage 1 tasked**
  (`reports/dev/T_ITER01_TASK.md`).
- Hypothesis source: external literature (`docs/RESEARCH_T.md`); the
  claim is Moskowitz/Ooi/Pedersen TSMOM *as a vol-targeted, diversified
  portfolio* — the scaling and the breadth are part of the hypothesis,
  per the Kim/Tse/Wald attribution critique.
- Code under test, shipped tested before any run on real data:
  `analytics/trend_study.py` (Stage 1), `strategy/tsmom.py` +
  `configs/t1_trend.toml` and `analytics/portfolio.py` (Stage 2).
- Relationship to prior programs: none of S's or the SMC program's
  constructs is used. NQ remains sealed and is **not** part of this
  program in any role.

## Data protocol

- **Resolution**: daily OHLCV bars (volume-roll back-adjusted
  continuous contracts, same Panama recipe as the ES stitch but at 1d).
  Daily resolution is faithful to the hypothesis (positions held weeks+,
  decisions at the close) and makes intrabar ambiguity immaterial.
- **Development set (burned on first contact, declared now)**:
  2010-06-06 → 2026-07-01, GLBX daily bars for
  **ES** (already burned), **CL** (WTI crude), **GC** (gold),
  **ZN** (10y note), **6E** (euro FX) — five markets, four asset
  classes.
- **Holdout (instrument axis, sealed until Stage 3)**: **HG** (copper),
  **ZF** (5y note), **6J** (yen), **ZC** (corn), same window, fetched
  only at the frozen commit, run once. These are *different markets*,
  not different periods — the strongest available out-of-sample axis
  for a cross-asset claim.
- **Holdout (time axis, optional)**: all nine markets strictly after
  2026-07-01, single confirmation permitted after ≥ 250 new sessions.
- **Temporal halves** for robustness rules: A = ≤ 2018-06-30,
  B = > 2018-06-30.
- NQ and all crypto holdouts: untouched, out of scope.

## Stage 1 — signal battery (development markets only)

`analytics.trend_study` at library defaults: lookbacks (21, 63, 252),
vote = majority of sign(trailing return); vol targeting 10% ann.,
63-day realized, cap 4×; per-day gross return x[t] = signal·scale·r[t+1];
block-bootstrap CIs; circular signal-shift null (500 shifts, ≥ 260-day
offset, seed 42).

**Primary object**: the equal-weight 5-market portfolio of x under
(vote, vol-scaled).

**Support rule**: portfolio mean daily x CI > 0 on the full window AND
in both temporal halves, AND portfolio shift-null p < 0.05 on the full
window. Per-instrument and per-variant cells are exploratory: reported
in full, never promoted, usable only to inform the Stage-2 ablation
already declared below.

## Stage 2 — engine backtests with costs (only if Stage 1 supports)

Per-instrument `TimeSeriesMomentumStrategy` runs at
`configs/t1_trend.toml` as committed; costs 0.4/0.1/0.4 bps per side
(futures-grade); initial equity 100k each;
`analytics.portfolio.combine_portfolio` aggregates equal-weight.

**Go criteria (all)**: portfolio net mean daily return block-CI > 0;
net Sharpe ≥ 0.30; net return positive in both halves; per-instrument
turnover consistent with the design (median holding ≥ 10 sessions —
a turnover blow-up means the rebalance band is misbehaving and is a
bug, not a result).

**Predeclared ablation budget** (only on a narrow miss, all runs
reported, Bonferroni ×4 on the CI level): `lookbacks ∈ {(252,),
(63, 252)}` × `rebalance_band ∈ {0.25, 0.50}`. Nothing else moves.

## Stage 3 — freeze and holdout

Architect declares the freeze commit + config. The four holdout
instruments are then fetched, integrity-checked, run once each, and
aggregated with the same portfolio code. **Pass**: holdout-portfolio
net mean daily CI > 0 and net Sharpe > 0. **Fail**: program concludes;
no retuning, no second draw of instruments. The optional time-axis
confirmation, if ever run, cannot override an instrument-axis fail.

## Stopping rules

- Stage-1 support rule unmet → program concludes at Stage 1; holdout
  instruments never fetched.
- Stage-2 go criteria unmet after the declared budget → concludes at
  Stage 2.
- Any in-sample result implying a portfolio Sharpe > 1.5 net is treated
  as a defect until an audit clears it (house rule: too good = bug).
- Refinements only before each stage's first real-data run, logged here.

## Expectation statement (binding context for reading the verdict)

The literature-consistent outcome, if everything passes, is a net
portfolio Sharpe of roughly 0.2–0.7 at 10% per-instrument vol target
over five to nine markets — a modest, real, diversifying return stream,
scalable only by leverage with proportional drawdowns. This program
cannot and does not promise more; it promises a defensible answer.
