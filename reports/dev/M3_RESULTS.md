# M-03 — Study M3: high-volume revisit

Executor run on branch `claude/m3-revisit-study`, harness **125/125**
passing (121 baseline + 4 revisit). Thin driver `reports/dev/_m3_runner.py`
calls the frozen library (`analytics/revisit.py`) at defaults (`q=0.99,
trailing=2880, isolation=96, depart_atr=1.0, horizons=(96,384), k=20,
vol_tol=0.25, atr_period=14, seed=42`). No re-implementation, no parameter
changes. `kz_mask` built uniformly for all three datasets as the frozen
design specifies:

```
in_killzone(candles.ts,
            [ET_BY_NAME[n] for n in ("london","new_york","silver_bullet")],
            "America/New_York")
```

Burned data only (BTC/ETH 15m 2023–2026, ES 15m adj 2010–2026). No holdouts
touched. Design frozen in `reports/dev/M2_PARTB_ADJUDICATION.md`. Raw JSON:
`reports/dev/_m3_results.json`.

Bar / killzone counts: BTC 122,588 bars (30,631 kz); ETH 122,588 (30,631);
ES 376,768 (99,144).

---

## The three rendered tables

Revisit of high-volume bar midpoints, conditional on a ≥ 1 ATR departure.
Ratio = event revisit rate ÷ ATR- and killzone-matched control revisit
rate. Support (either direction) = 95% CI excludes 1.

**BTCUSDT 15m (2023-2026)**

| horizon | n | event revisit | control revisit | ratio | 95% CI |
|---|---|---|---|---|---|
| 96 | 291 | 0.704 | 0.821 | 0.859 | [0.791, 0.922] |
| 384 | 290 | 0.848 | 0.907 | 0.935 | [0.889, 0.980] |

**ETHUSDT 15m (2023-2026)**

| horizon | n | event revisit | control revisit | ratio | 95% CI |
|---|---|---|---|---|---|
| 96 | 322 | 0.724 | 0.819 | 0.883 | [0.826, 0.942] |
| 384 | 323 | 0.851 | 0.905 | 0.940 | [0.902, 0.979] |

**ES 15m adj (2010-2026)**

| horizon | n | event revisit | control revisit | ratio | 95% CI |
|---|---|---|---|---|---|
| 96 | 874 | 0.745 | 0.817 | 0.912 | [0.877, 0.948] |
| 384 | 898 | 0.865 | 0.910 | 0.951 | [0.927, 0.974] |

---

## Verdict — effect SUPPORTED (3/3 both horizons), sign is ANTI-FOLKLORE

Support rule (predeclared, symmetric): ratio CI excludes 1 — in *either*
direction — on ≥ 2/3 datasets, per horizon.

| horizon | BTC | ETH | ES | count | CI excludes 1? | side |
|---|---|---|---|---|---|---|
| 96 | 0.859 [0.791,0.922] | 0.883 [0.826,0.942] | 0.912 [0.877,0.948] | 3/3 | yes | **below** |
| 384 | 0.935 [0.889,0.980] | 0.940 [0.902,0.979] | 0.951 [0.927,0.974] | 3/3 | yes | **below** |

All six cells exclude 1, and **every one excludes it on the low side.**
Under the symmetric support rule the revisit effect is **supported 3/3 on
both horizons — but in the direction opposite the folklore.** High-volume
bar midpoints are revisited *less* often than ATR- and killzone-matched
control bars, conditional on a ≥ 1 ATR departure.

Precise statement: an isolated high-volume bar is, if anything, a level
price returns to slightly *less* readily than an ordinary bar of matched
volatility and session — a small, cross-venue **under-revisit**, the
opposite sign of the "volume marks a level price cares about" claim. The
effect is strongest at h=96 (ratios 0.86–0.91, i.e. ~9–14% under-revisit)
and attenuates toward 1 at h=384 (0.94–0.95, ~5–6%) as revisit rates
saturate (event revisit rises 0.70→0.85, control 0.82→0.91).

This is the program's **second anti-folklore finding**, directionally
consistent with M2-A (confirmed anti-magnetism) and with M1 (magnetism
unsupported) / M2-B direction (post-sweep reversal unsupported).

## Anomalies

1. **The sign is unanimous, not merely 2/3.** All six cells land below 1
   with no straddle and no dataset dissenting. Given the "either direction"
   rule this is a stronger result than the rule's floor — worth the
   architect's attention as a genuine effect rather than a boundary pass.
2. **Attenuation with horizon is monotone on all three venues** (h=96
   ratio < h=384 ratio everywhere). Longer windows let more levels get
   touched regardless of the volume label, so the event-specific deficit
   shrinks; it does not reverse.
3. **Event counts are two orders of magnitude below the M2 studies**
   (n = 290–898 vs 11k–36k). By construction: the `q=0.99` × 96-bar
   isolation filter keeps only sparse, well-separated spikes, then the
   ≥1-ATR-departure condition prunes further. All cells clear the library's
   5-event floor comfortably, and ES (16y, n≈880) carries the tightest CIs.
4. ES's departure-conditioning: revisit rates here are high in absolute
   terms (event 0.75–0.87), so the *ratio* — not the level — is what
   isolates the event-specific deficit; it survives on all three venues.

## Observations (not proposals)

- The high-volume-revisit folklore fails in the same shape the magnetism
  folklore did: the claimed magnet is, at these horizons, a mild
  *repeller*. Whatever an isolated volume spike marks, matched ordinary
  bars get revisited slightly more often than it does.
- The volatility result from M2-B and the under-revisit result here are not
  in tension: high-volume / liquidity-taking bars expand near-term
  volatility (M2-B) yet their specific price *level* is not a
  preferentially revisited target (M3). Volatility ≠ magnetism.
- Consistency across a 16-year futures series and two 3-year crypto series,
  same sign, same attenuation pattern, argues the deficit is structural
  rather than venue- or regime-specific.

## Proposals

- None. Reporting only, per contract.

## Blocking questions

- None. The frozen design fully specified datasets, params, killzone
  construction, and the (symmetric) support rule; all three datasets ran
  without degenerate cells (min n = 290, all ≥ the library's 5-event
  floor).

Pushing and stopping. No strategy inferences, no holdouts touched. The
anti-folklore *sign* of a rule-supported effect is flagged for architect
adjudication (M2-A set the precedent for ruling on a symmetric,
opposite-sign result).
