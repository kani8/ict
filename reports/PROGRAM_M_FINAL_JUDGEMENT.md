# Program M — final judgement on the ICT strategy

- Date: 2026-07-03
- Verdict: **the ICT/SMC thesis is refuted as a source of tradable
  directional edge, and its descriptive premises are unsupported or
  inverted. Nothing in this repository should be traded. Research is
  concluded.**

## Provenance of this document

The architect (who normally adjudicates) ran out of tokens and the user
delegated the program-level judgement to the executor. This document makes
no new measurement and changes no study logic; it is a synthesis fully
determined by the committed record — the concluded V-program
(`reports/FINAL_VERDICT.md`, `reports/PROGRAM_CONCLUSION.md`) and the six
Program M adjudications/results (M1, M2-A, M2-B, M3). Every number below is
quoted from those documents. Burned data only; the five sealed holdouts
(BNBUSDT 2023–26, ETHUSDT 2019–22, SOLUSDT 2023–26, BTCUSDT 2019–22, NQ
2010–26) were not touched to reach this verdict and remain sealed.

## Two questions, one answer

The repository asked ICT two separable questions:

1. **Does the mechanical strategy make money?** (V-program — trading tests.)
2. **Are the descriptive claims the strategy rests on even true?**
   (Program M — event studies against matched controls.)

Both answers are no. The second is the more damaging: the folklore fails
not just at the cash register but at the level of the market facts it
asserts. Where the claims carry any signal at all, the sign is the
*opposite* of what ICT teaches.

## The trading record (V-program, concluded 2026-07-03)

| Test | Result |
|---|---|
| V1 canonical ICT, BTC 15m 2023–26 | −34.5% after cost; −5.6% at **zero cost** (no gross edge); p = 1.00 vs drift |
| V1 canonical ICT, ETH 15m+1m 2023–26 (frozen holdout) | −12.9%; mean R −0.18; null p = 0.53 → **stopping rule fired** |
| V3 narrative engine, crypto | No consistent forward-return separation; ETH monotonically **anti-predictive** |
| V3 narrative engine, ES 2010–26 (16y, session-correct) | Inverted at both horizons; 9/10 factor cells inverted; conviction quintiles **monotonically anti-predictive** |

Each failure survived progressively stricter execution modeling, three
adversarial audits, and two defect fixes that *removed* advantages the
strategy had been enjoying (a phantom-profit engine bug among them). The
V-program's own conclusion: mechanical ICT/SMC constructions carry no
positive directional information on crypto or index futures intraday, and
where they carry any, the sign is inverted.

## The descriptive record (Program M)

Program M tested the premises directly, as ratio-of-touch / ratio-of-revisit
event studies with ATR- and killzone-matched controls and block-bootstrap
CIs, on BTC/ETH 15m (2023–26) and ES 15m adjusted (2010–26).

| Study | ICT claim | Predeclared rule | Result |
|---|---|---|---|
| **M1** liquidity magnetism | "price seeks liquidity" | ratio CI excl. 1 **upward**, ≥2/3 | **NOT SUPPORTED** — 0/18 cells upward |
| **M2-A** anti-magnetism | (symmetric anti-claim) | ratio CI excl. 1 **downward**, ≥2/3 | **CONFIRMED** — ES + ETH both temporal halves at 2.0–4.0 ATR / h=96 (~2–3% under-touch); BTC fails; 2/3 |
| **M2-B** post-sweep reversal | sweep = purge-and-reverse (ICT's central tradable claim) | signed-return CI excl. 0 upward, ≥2/3 | **NOT SUPPORTED** — 0/6 kind×horizon cells; ES run/96 mildly *contra* |
| **M2-B** volatility expansion | (non-folklore control measure) | ratio CI excl. 1, ≥2/3 | **SUPPORTED 3/3** both kinds (ratios 1.01–1.04); does not distinguish sweep from run |
| **M3** high-volume revisit | "volume marks a level price returns to" | ratio CI excl. 1 either direction, ≥2/3 | **SUPPORTED 3/3 both horizons — but ANTI-FOLKLORE sign** (under-revisit) |

M3 in detail: all six ratio CIs exclude 1, and **every one on the low
side** — high-volume bar midpoints are revisited *less* often than matched
controls (h=96 ratios 0.86 / 0.88 / 0.91; h=384 0.94 / 0.94 / 0.95),
strongest near-term, attenuating toward 1 as horizons saturate. The claimed
magnet is, at these horizons, a mild repeller — the same shape M1/M2-A
found for magnetism.

## Synthesis — what actually survives

Sorting the findings by what they mean for a trader:

- **Every directional / tradable claim fails.** Magnetism unsupported
  (M1). Post-sweep reversal — the mechanism the whole entry model is built
  on — unsupported (M2-B). High-volume-revisit-as-target refuted with the
  opposite sign (M3). The strategy that monetizes these claims loses money
  after cost and shows no gross edge (V-program).
- **The two effects that *are* real are useless to the folklore.**
  (a) A small **anti-magnetism** (M2-A) and a small **under-revisit** (M3)
  — both genuine, cross-venue, but *opposite* in sign to the teaching, so
  they cannot be traded the ICT way. (b) A **volatility expansion** around
  liquidity-taking bars (M2-B) that is real but **directionless** — it
  tells you the market will move, not which way. Volatility ≠ magnetism ≠
  edge.
- **The signs are consistent across programs.** V3's conviction→return
  inversion on ES and ETH, and M's anti-magnetism / under-revisit, point
  the same way: the more a level looks like a textbook ICT magnet, the
  slightly *less* price is drawn to it. This coherence is why the verdict
  is "refuted," not merely "not shown."

## The verdict

**On the strategy:** the canonical mechanical ICT/SMC composition — HTF
bias → liquidity sweep → MSS → OTE-band FVG/OB retrace → opposing-liquidity
target, and its aggregated narrative form — has **no detectable edge and a
clearly negative after-cost edge**, tested fairly with preregistration,
honest 1m-resolved execution, matched nulls, and block bootstraps. Do not
deploy, do not tune.

**On the folklore:** its descriptive premises do not hold. "Price seeks
liquidity" and "volume marks a level price returns to" are, at intraday
horizons across a 16-year futures series and two crypto series, either
absent or **true with the sign reversed**. The one robust liquidity-event
effect (volatility expansion) carries no direction.

## Scope and honesty of the claim

This is not a proof that no ICT concept helps any discretionary trader in
any market. It is a preregistered, execution-honest demonstration on
burned data that (1) the popular mechanical reading has no edge and (2) its
stated market premises are unsupported or inverted. The inversion is an
**in-sample observation, not a validated fade strategy** — testing "fade the
textbook setup" would be a *new* program with its own preregistration and
its own untouched data, noting up front that individual inverted cells are
weak and monotone shapes may be bull-sample drift artifacts.

## What the project produced

The deliverable was always the answer, not the strategy. What survives is
the instrument: a lookahead-safe detector stack with prefix-consistency
proofs, a pessimistic 1m-resolved execution engine hardened by three
audits, matched nulls with diagnostics, block bootstraps, forward-return
regime diagnostics, a preregistration/stopping-rule workflow that spent
**zero holdouts on dead hypotheses**, and the Program M event-study
libraries (`analytics/magnetism.py`, `sweep_study.py`, `revisit.py`).
Harness green at 125/125. Total external data spend ≈ $31.

**Research is concluded.** Any future work is a new program: new
hypothesis, new preregistration, new data protocol. The sealed holdouts
stay sealed.
