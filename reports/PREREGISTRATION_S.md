# Preregistration — Program S: session anomalies on index futures

- Date: 2026-07-06 (architect). Status: **open — Stage 1 tasked**
  (`reports/dev/S_ITER01_TASK.md`).
- Hypothesis sources: external literature only
  (`docs/RESEARCH_S1.md`). No hypothesis in this program derives from
  the concluded SMC/ICT program or from program M's findings; M's
  results informed only the *ranking* rationale, not any rule.
- Code under test: `analytics/session_study.py` (Stage 1),
  `strategy/sessions.py` + `configs/s1_sessions.toml` (Stage 2), shipped
  tested at the commit that adds this document, **before any run on
  real data**. The executor runs the frozen library; it never
  re-implements or edits it.

## Data protocol

- **Development / in-sample (burned)**: ES 15m adjusted + 1m intrabar,
  2010-06-06 → 2026-07-01, rebuilt from the pinned Databento GLBX file
  (sha256 `e9ebda22…`, recipe and integrity gates of
  `reports/dev/V3_ITER04.md` §1a apply verbatim). Crypto burned sets
  are **not** used: 24/7 venues have no RTH session and are out of
  scope for session hypotheses.
- **Holdout 1 (venue)**: NQ 15m + 1m, 2010–2026, GLBX, same stitch
  recipe. **Re-consecration ruling**: NQ was sealed by
  `PROGRAM_CONCLUSION.md` against the SMC program *and descendants of
  its hypotheses*. Program S's hypotheses are external-literature
  session effects, not SMC descendants, and NQ has never had price
  contact in this repository; it is hereby formally re-consecrated as
  Program S's single venue holdout. It is fetched only at Stage 3,
  run once, at the frozen commit.
- **Holdout 2 (temporal)**: ES data strictly after 2026-07-01 accrues
  untouched; an optional second confirmation may run once ≥ 250 new
  complete sessions exist (~mid-2027). Absence of this run does not
  block a Stage-3 verdict.
- **Temporal halves** (used by every support rule): half A =
  sessions dated ≤ 2018-06-30, half B = sessions dated > 2018-06-30
  (splits the 16.1y sample at its midpoint; also brackets the
  documented post-2020 options-structure change, which additionally
  gets a descriptive 2021+ cut).

## Stage 1 — descriptive battery (burned ES only)

Run `analytics.session_study.run_session_battery` at library defaults
on the full sample, half A, half B, and (descriptive) 2021+. FOMC
events = rows with `event == "FOMC"` from the audited
`data/calendars/high_impact_2010_2026.csv`.

Support rules (declared now; a study not meeting its rule is
unsupported — no re-reading, no new cells):

| study | primary statistic | supported iff |
|---|---|---|
| S1 intraday momentum | signed last-30m logret, predictor **rod**, subset **all** | block-bootstrap 95% CI excludes 0 upward on the full sample AND in both halves |
| S2 opening-range breakout | signed break-to-close logret, subset **all** | same rule as S1 |
| S3 pre-FOMC drift | 24h logret into 14:00 ET on FOMC days | CI excludes 0 upward AND mean ≥ 2× the other-days mean (halves reported descriptively — too few events per half) |
| S4 IBS reversion | q1 − q5 next-session RTH return spread | CI excludes 0 upward on the full sample AND in both halves |
| S5 overnight split | — | descriptive only, no claim |

All other battery cells (fh/both predictors, vol terciles, narrow-range
ORB, individual IBS quintiles) are **exploratory**: reported in full,
never promoted to support, usable only to *narrow* a Stage-2 ablation
that is already predeclared below. Symmetric anti-claims (CI excluding
0 downward on full + both halves) are recorded as findings but do not
open a fade strategy inside this program.

## Stage 2 — strategy backtests (burned ES; only for supported studies)

S1 supported → `IntradayMomentumStrategy`; S2 supported →
`OpeningRangeBreakoutStrategy`. S3/S4 support does not create a
strategy in this program (amendment required first).

Fixed protocol: `configs/s1_sessions.toml` as committed; costs
0.4/0.1/0.4 bps; 1m intrabar, conservative fallback; bars/year
23,447.4; initial equity 100k; `matched_baseline_test` with 500 sims,
seed 42, `eligible_mask` = bars with ET minute in [570, 960).

**Go criteria (all must hold)**: ≥ 300 trades; mean net R > 0 with the
block-bootstrap CI not excluding 0 downward; PF > 1; p(mean R) < 0.05;
total return positive in both temporal halves.

**Predeclared ablation budget**: if the frozen default narrowly fails
(some but not all criteria), at most **six** variants may run, all
reported: `im_predictor ∈ {fh, rod}`, `im_min_abs_signal ∈ {0.0005,
0.001}` for S1; `orb_min_range_atr = 0` vs a narrow-range filter and
`orb_take_profit_r ∈ {0, 2}` for S2. A variant may go to Stage 3 only
if it passes **all** go criteria with p(mean R) < 0.05/6 (Bonferroni
across the budget) and both halves positive. No other lever exists.

## Stage 3 — freeze and holdout

- Architect declares a freeze commit + exact config. NQ 2010–2026 is
  then fetched, integrity-audited (same gates), and the frozen
  strategy runs **once** with 500-sim matched null.
- **Pass**: total return ≥ 0, PF > 1, mean R > 0, p(mean R) < 0.05.
  Pass → the strategy graduates to paper-trading consideration; even
  then, position sizing for any live use is a separate decision outside
  this repository's scope.
- **Fail**: the program concludes — no deployment, no retuning, no
  second shot at NQ. A fail is a finished research result.

## Stopping rules

- No Stage-1 study supported → program concludes at Stage 1 with a
  descriptive verdict; the NQ re-consecration lapses unused.
- Stage-2 go criteria unmet after the declared ablation budget →
  program concludes at Stage 2.
- Design refinements are allowed only *before* each stage's first run
  on real data and must be logged here with a date.

## Roles

Architect: designs, adjudicates, owns `src/`, `configs/`,
preregistrations. Executor: runs exactly what is tasked, reports per
the standing format (`docs/EXECUTOR_BRIEF.md`), writes only under
`reports/dev/` and `data/`.
