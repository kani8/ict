# Program S — literature research: documented session anomalies on US index markets

- Date: 2026-07-06 (architect)
- Purpose: select the hypotheses for the next preregistered trading
  program from *externally documented* candidate edges, ranked by
  evidence quality and by fit to this repository's harness and data
  (ES futures, 15m signal / 1m execution, 2010–2026, session-correct).
- Relationship to prior work: the SMC/ICT program is concluded
  (`reports/PROGRAM_CONCLUSION.md`) — mechanical SMC carries no positive
  directional edge on crypto or ES, inverted where any signal exists.
  Program S starts from the academic literature instead of trading
  folklore. The in-house measurement program M supplies two relevant
  facts: liquidity-taking events mark small volatility expansion but no
  direction (M2), and distant swing extremes behave like mean-reversion
  boundaries, not magnets (M-02 Part A). Both are consistent with the
  hypothesis family below: session-time flow effects rather than
  price-pattern "narratives".

## Candidate edges, ranked

### 1. Market intraday momentum (S1) — PRIMARY

**Claim**: the market's return from the previous close through the
morning (first half hour) and through 15:30 ET (rest of day) positively
predicts the **last half hour** (15:30–16:00 ET).

**Evidence**: the strongest of any candidate.
- Gao, Han, Li & Zhou, *Market intraday momentum*, JFE 2018
  ([SSRN 2440866](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)):
  SPY 1993–2013, first-half-hour return predicts the last half hour
  (scaled slope 6.94, 1% significance, R² 1.6%); stronger on volatile,
  high-volume, recession and macro-news days; significant out of
  sample; present in ten other major ETFs.
- Baltussen, Da, Lammers & Martens, *Hedging demand and market intraday
  momentum*, JFE 2021
  ([SSRN 3760365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)):
  replicated on **60+ futures** (equities, bonds, commodities, FX)
  1974–2020 — the rest-of-day return predicts the last 30 minutes;
  effect strongest in equity index futures; attributed to **gamma
  hedging demand** of option market makers and leveraged-ETF
  rebalancing. A mechanical flow explanation is the best predictor of
  persistence-after-publication we have.

**Caveats**: the options market changed structurally post-2020 (0DTE
volume; Dim, Eraker & Vilkov 2024 on charm/gamma exposure;
Baltussen, Terstegge & Whelan, *The Derivative Payoff Bias*). The
design therefore requires temporal-half robustness and reports the
2021+ subperiod separately.

**Fit**: excellent. One event per session, ~4,000 sessions on burned ES
15m data, well-powered; the 15m grid matches the 30-minute windows
exactly; execution is two market fills at the day's most liquid times.

### 2. Opening-range breakout (S2) — SECONDARY

**Claim**: a directional break of the first 30 minutes' range continues
into the close (trend-day capture).

**Evidence**: practitioner-grade, genuinely contested.
- Zarattini & Aziz 2023, *Can Day Trading Really Be Profitable?*
  ([Semantic Scholar](https://www.semanticscholar.org/paper/4d55f526cc56f08662cb8976796cd3b719ef6d2b)):
  5-minute ORB on QQQ 2016–2023, 33% annualized alpha — but with
  idealized costs (no spread/slippage) and heavy leverage;
  [CXO's review](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy/)
  flags the assumptions. Zarattini, Barbon & Aziz 2024
  ([SSRN 4729284](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284))
  extends to "stocks in play".
- Against: a 2026 systematic falsification study on MNQ futures
  ([arXiv 2605.04004](https://arxiv.org/pdf/2605.04004)) finds ORB
  variants statistically indistinguishable from chance; Crabel's
  narrow-range filters are folklore-adjacent.

**Fit**: good (same session infrastructure as S1). Ranked second: the
one honest futures study is negative, so this is a real question, not a
likely edge. Cheap to answer alongside S1.

### 3. Pre-FOMC announcement drift (S3) — EVENT STUDY ONLY

**Claim**: equities earn outsized returns in the 24h before scheduled
FOMC announcements (Lucca & Moench, JF 2015,
[SSRN 1923197](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1923197):
more than half the equity premium since 1994).
Post-publication evidence is mixed — the drift concentrated into
press-conference meetings and weakened as Fed communication changed
([QuantSeeker 2025 review](https://www.quantseeker.com/p/trading-the-fed-the-pre-fomc-drift)).
**Fit**: only ~130 events in-sample — enough for an event study, far
too few for a standalone strategy verdict. The repo already carries the
audited 2010–2026 FOMC calendar.

### 4. IBS mean reversion (S4) — EVENT STUDY ONLY

**Claim**: a close near the session low predicts a higher next-session
return (internal bar strength; Pagonidis,
[*The IBS Effect*](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf);
practitioner replications at
[QuantifiedStrategies](https://www.quantifiedstrategies.com/sp-500-mean-reversion-using-ibs-and-rsi/)).
Practitioner-grade only, with decay complaints since ~2017. Consistent
in spirit with M-02 Part A's boundary-reversion observation. Tested as
a quintile study; promotion to a strategy would require a Stage-1 pass
and a program amendment.

### 5. Overnight vs intraday decomposition (S5) — DESCRIPTIVE CONTEXT ONLY

The "night effect" (Lou, Polk & Skouras;
[Elm Wealth review](https://elmwealth.com/night-moves-overnight-drift/))
is real historically but
[decayed and cost-eaten](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/)
post-2015. Not a hypothesis here; measured only as context so the
session studies can be read against the venue's overnight/intraday
return split.

## Rejected for this program

- **Volatility-managed exposure** (Moreira & Muir, JF 2017): direct
  out-of-sample replications find no systematic outperformance
  (Cederburg, O'Doherty, Wang & Yan, JFE 2020,
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X)) —
  fails the evidence bar as a core hypothesis.
- **Anything SMC-derived** (including fading high-conviction SMC states):
  the concluded program's inversion observation is post-hoc, formed on
  burned data, and PROGRAM_CONCLUSION bars descendant hypotheses from
  the sealed holdouts.
- **Turn-of-month / seasonality**: evidence exists but the effect is a
  few events per month on daily bars — underpowered against this
  harness's strengths; may join a later stage as an overlay ablation.

## Honesty clause

No preregistration can promise a profitable strategy. This program
selects the best externally documented candidates, tests them with the
hardened harness (pessimistic fills, 1m execution resolution, matched
nulls, block bootstraps), and commits in advance to the rule that
decides deploy / conclude. The deliverable is a defensible answer.
