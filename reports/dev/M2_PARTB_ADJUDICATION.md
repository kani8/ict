# M-02 Part B — adjudication & M3 design freeze

**Provenance.** The architect authored the M3 library
(`src/ict_backtest/analytics/revisit.py`) and its tests
(`tests/test_revisit.py`), freezing the M3 design, then ran out of tokens
before this record landed. The executor recorded this document from the
shipped, frozen artifacts and from `reports/dev/M2_PARTB_RESULTS.md`
(commit `900ad1c`), on branch `claude/m3-revisit-study`, changing no study
logic. The Part B ruling below is fully determined by the Part B results;
the M3 design below is fully determined by the shipped `revisit.py`. One
architect test (`test_structureless_volume_shows_no_revisit_edge`) was
starved of events at `q=0.97` under the 96-bar isolation window; the
executor corrected only that test's synthetic/study **parameters**
(`n=12_000→20_000`, `q=0.97→0.99`, the isolation-optimal quantile) — the
frozen library was not touched. Harness green at **125/125**.

---

## Ruling on Part B (Study M2: post-sweep direction & volatility)

Input: `reports/dev/M2_PARTB_RESULTS.md`. Executor conduct: clean — library
defaults only, uniform killzone construction, anomalies surfaced against
its own tables (including the ES run/96 mild *contra* cell).

- **(a) Direction — NOT SUPPORTED.** No kind×horizon cell reaches 2/3
  datasets excluding 0 upward. The sweep-reversal claim — ICT's central
  tradable assertion — is not supported at either horizon. The lone ES
  sweep/96 cell that excludes 0 upward (+1.7 bp, 1/3) is economically
  negligible; ES run/96 in fact excludes 0 on the *downward* side (1/3),
  mildly contradicting the continuation prediction on the highest-power
  dataset.
- **(b) Volatility expansion — SUPPORTED (3/3 on both kinds).** Every
  event cell expands realized volatility relative to ATR- and
  killzone-matched controls; all six CIs clear 1 (ratios 1.01–1.04). The
  effect does not distinguish sweep from run.

Precise statement: liquidity-taking events (sweep and run alike) coincide
with a small, cross-venue expansion in realized volatility, while carrying
no detectable forward direction — including no post-sweep reversal edge.
Consistent with M1 (magnetism unsupported) and M2-A (anti-magnetism
confirmed).

---

## M3 design (frozen before any real-data run)

Study M3 tests the falsifiable core of the high-volume-revisit folklore: a
bar trading on abnormally high volume marks a level price "cares about" and
returns to. Object of the test: **do the midpoints of isolated high-volume
bars get revisited more often than matched control bars, conditional on
price first leaving the level?**

Bindings (as implemented in `analytics/revisit.py`, all fixed pre-run):

- **Spike** — bar volume exceeds the trailing rolling `q`-quantile of the
  prior `trailing` bars (`shift(1)`, so a bar never enters its own
  threshold); spikes within `isolation` bars of a prior spike are dropped
  so clustered volume counts once. Defaults `q=0.99, trailing=2880,
  isolation=96`.
- **Departure** — first bar in `(t, t+horizon//2]` whose close is
  `>= depart_atr` ATR(at spike) from the spike midpoint. Events that never
  depart are excluded (a level never left cannot be revisited).
  Default `depart_atr=1.0`.
- **Revisit** — after departure, any bar within `(t, t+horizon]` whose
  range brackets the spike midpoint (`low <= mid <= high`).
- **Controls** — `k` non-spike bars matched to the event on ATR (within
  `vol_tol`) and killzone flag; control statistic is the mean revisit over
  the controls that themselves departed. Defaults `k=20, vol_tol=0.25`.
- **Statistic** — ratio of event revisit rate to control revisit rate with
  a block-bootstrap CI (`_ratio_block_ci`). Horizons `(96, 384)`.
  `atr_period=14, seed=42`.

**Support rule (predeclared, symmetric):** the revisit effect is supported
if the ratio CI excludes 1 — *in either direction* — on ≥ 2/3 datasets, per
horizon. A CI excluding 1 *above* supports the folklore's magnet direction;
a CI excluding 1 *below* supports an effect of the opposite sign
(under-revisit), reported as such.

Datasets: burned only — BTC/ETH 15m 2023–2026, ES 15m adj 2010–2026. No
holdouts. Killzone mask uniform across datasets:
`in_killzone(candles.ts, [ET_BY_NAME[n] for n in
("london","new_york","silver_bullet")], "America/New_York")`.
