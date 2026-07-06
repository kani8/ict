# Architect adjudication — Program S, Iteration 01

Input: `reports/dev/S_ITER01.md` (run at commit `535a8d7`). Executor
conduct: exemplary — the tasked-snippet defect was diagnosed to root
cause and corrected in the runner without touching frozen code, both
code paths were preserved in the JSON, the dropped-session tripwire was
investigated to a per-day classification instead of hand-waved, and no
unrequested experiment was run.

## Ancillary rulings first

1. **FOMC timestamp deviation — ACCEPTED.** The `//10**9` in my tasked
   snippet was a bug (it assumed nanosecond `datetime64` resolution;
   this pandas build parses the calendar to microseconds). The
   executor's `int(Timestamp.timestamp())` conversion implements the
   *intended* semantics — epoch seconds, the unit of `candles.ts` and
   `et_minutes_days` — and is unit-safe. The S3 tables in §2/§3 of the
   report are the S3 result of record; the as-tasked n=0 outcome is a
   snippet artifact, not a finding. Defect was the architect's.
2. **Dropped-session tripwire recalibrated.** The "~12" heuristic in the
   tasking was wrong (it echoed the 1m *gap* attribution, not the
   session count); the executor's ≈8/yr early-close cadence (128 over
   16.07y, per-year stable, all in the early-close bucket) is the
   correct expectation and `session_table` behaved exactly as designed.
   No action beyond this correction of the record.

## Ruling on the preregistered support rules: NONE SUPPORTED

The arithmetic is not close in any study:

| study | rule | outcome |
|---|---|---|
| S1 intraday momentum (rod/all) | CI > 0 on full + both halves | 0/3 windows (full ci_lo −0.00001) |
| S2 ORB (all) | CI > 0 on full + both halves | 0/3 windows |
| S3 pre-FOMC | CI > 0 and mean ≥ 2× baseline | both conditions fail (CI straddles 0; ratio 1.9×) |
| S4 IBS (q1−q5) | CI > 0 on full + both halves | 0/3 windows |

Under the preregistered stopping rule — "No Stage-1 study supported →
program concludes at Stage 1 with a descriptive verdict; the NQ
re-consecration lapses unused" — **Program S concludes at Stage 1.**

- Stage 2 does not open. The strategy implementations
  (`strategy/sessions.py`) are never run on real data under this
  program; they remain tested library code for any future, separately
  preregistered program.
- The ablation budget does not apply: it existed only inside Stage 2
  for supported studies. There is no predeclared path from an
  exploratory cell to a trade, and none is created now.
- **NQ 2010–2026 is not fetched. Its Program-S re-consecration lapses
  and it returns to the sealed pool, still never price-touched.** All
  other holdouts remain sealed as before.

## The descriptive verdict (what 16 years of ES said)

Stated for the record, at the level of precision the data supports:

1. **The published session anomalies exist on ES 2010–2026 only as
   sub-costs residues.** Every primary effect carries the
   literature-predicted sign (intraday momentum +0.7 bp/day on the
   rest-of-day predictor, stable across both halves; ORB +0.6 bp;
   pre-FOMC +7.0 bp/event vs +3.7 bp baseline; IBS q1−q5 +4.9 bp), and
   every one of them straddles zero at 95% even with ~4,000 sessions of
   power. For scale: the engine's ES round-trip cost at the declared
   cost model is ≈1.4 bp — double the mean intraday-momentum effect
   before any statistical uncertainty is spent.
2. **The volatility conditioning replicates directionally; the
   tradable core does not.** The one full-sample cell with CI > 0
   (rod/high-vol, +2.0 bp [+0.2, +3.9]) matches Gao et al./Baltussen et
   al.'s "stronger on volatile days" — but it is exploratory (one of
   ~50 reported cells), fails both temporal halves individually, fades
   to +0.5 bp in 2021+ (consistent with the documented post-2020/0DTE
   structure change), and its CI floor sits below one round trip.
3. **The overnight drift is the only significantly positive
   decomposition** (+2.4 bp/night [+0.6, +4.0]) — exactly the
   literature's picture, and exactly the effect the literature already
   shows is consumed by holding-period costs and tail risk.
4. Read jointly with the concluded SMC program and measurement program
   M: on this venue, at intraday horizons, through an execution-honest
   harness, neither folklore patterns nor the best peer-reviewed
   session anomalies of the 2010s survive 2010–2026 ES at retail-scale
   costs. That is a finished, publishable-quality negative result, and
   it is the program's deliverable.

## Program state after this adjudication

- `reports/PREREGISTRATION_S.md` → status CONCLUDED (Stage-1 fail),
  annotated in place.
- Sealed and untouched: NQ 2010–2026, BNBUSDT 2023–2026, ETHUSDT
  2019–2022, SOLUSDT 2023–2026, BTCUSDT 2019–2022, ES post-2026-07.
- Open: measurement program M (M3 not yet tasked). Any future trading
  program starts from a new hypothesis and a new preregistration.
- No trading deployment of any kind is authorized by this repository's
  research to date.
