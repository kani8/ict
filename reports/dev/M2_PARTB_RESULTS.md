# M-02 Part B — Study M2: post-sweep direction & volatility

Executor run at commit `900ad1c`, harness **121/121** passing. Thin driver
`reports/dev/_m2_partb_runner.py` calls the frozen library
(`analytics/sweep_study.py`) at defaults (`swing_k=3, eq_tol_atr=0.25,
atr_period=14, horizons=(96,384), window=96, k=20, vol_tol=0.25, seed=42`).
No re-implementation, no parameter changes. `kz_mask` built uniformly for
all three datasets as the frozen design specifies:

```
in_killzone(candles.ts,
            [ET_BY_NAME[n] for n in ("london","new_york","silver_bullet")],
            "America/New_York")
```

Burned data only (BTC/ETH 15m 2023–2026, ES 15m adj 2010–2026). No
holdouts touched. Raw JSON: `reports/dev/_m2_partb_results.json`.

---

## The three rendered table pairs

**BTCUSDT 15m (2023-2026)** — post-liquidity-take behavior (23782 events)

*Direction (signed toward ICT prediction; support = CI > 0)*

| kind | horizon | n | mean signed logret | 95% CI |
|---|---|---|---|---|
| sweep | 96 | 11507 | +0.00016 | [-0.00055, +0.00084] |
| sweep | 384 | 11479 | -0.00003 | [-0.00134, +0.00121] |
| run | 96 | 12262 | -0.00050 | [-0.00125, +0.00026] |
| run | 384 | 12234 | +0.00124 | [-0.00029, +0.00278] |

*Volatility expansion (next 96 / prior 96, vs matched controls; support = CI > 1)*

| kind | n | event | control | ratio | 95% CI |
|---|---|---|---|---|---|
| sweep | 11497 | 1.173 | 1.123 | 1.044 | [1.020, 1.071] |
| run | 12257 | 1.165 | 1.118 | 1.042 | [1.016, 1.071] |

**ETHUSDT 15m (2023-2026)** — post-liquidity-take behavior (24291 events)

*Direction (signed toward ICT prediction; support = CI > 0)*

| kind | horizon | n | mean signed logret | 95% CI |
|---|---|---|---|---|
| sweep | 96 | 12173 | +0.00068 | [-0.00039, +0.00172] |
| sweep | 384 | 12136 | -0.00085 | [-0.00281, +0.00102] |
| run | 96 | 12104 | -0.00105 | [-0.00215, +0.00010] |
| run | 384 | 12077 | +0.00062 | [-0.00155, +0.00289] |

*Volatility expansion (next 96 / prior 96, vs matched controls; support = CI > 1)*

| kind | n | event | control | ratio | 95% CI |
|---|---|---|---|---|---|
| sweep | 12166 | 1.145 | 1.101 | 1.040 | [1.015, 1.065] |
| run | 12097 | 1.132 | 1.100 | 1.029 | [1.007, 1.052] |

**ES 15m adj (2010-2026)** — post-liquidity-take behavior (71832 events)

*Direction (signed toward ICT prediction; support = CI > 0)*

| kind | horizon | n | mean signed logret | 95% CI |
|---|---|---|---|---|
| sweep | 96 | 35730 | +0.00017 | [+0.00003, +0.00031] |
| sweep | 384 | 35698 | +0.00021 | [-0.00006, +0.00047] |
| run | 96 | 36089 | -0.00019 | [-0.00040, -0.00000] |
| run | 384 | 36060 | -0.00037 | [-0.00076, +0.00000] |

*Volatility expansion (next 96 / prior 96, vs matched controls; support = CI > 1)*

| kind | n | event | control | ratio | 95% CI |
|---|---|---|---|---|---|
| sweep | 35726 | 1.092 | 1.061 | 1.030 | [1.019, 1.041] |
| run | 36080 | 1.070 | 1.056 | 1.013 | [1.003, 1.024] |

---

## (a) Direction — **NOT SUPPORTED**

Support rule: signed-return CI excludes 0 upward on ≥2/3 datasets, per
kind×horizon cell. Tally of datasets whose CI excludes 0 **upward**:

| cell | BTC | ETH | ES | count | verdict |
|---|---|---|---|---|---|
| sweep / 96 | no | no | **yes** | 1/3 | not supported |
| sweep / 384 | no | no | no | 0/3 | not supported |
| run / 96 | no | no | no | 0/3 | not supported |
| run / 384 | no | no | no | 0/3 | not supported |

No kind×horizon cell reaches 2/3. **Neither sweep-reversal nor
run-continuation direction is supported.** The single cell excluding 0
upward (ES sweep/96, +0.00017 logret ≈ 1.7 bp) is one dataset out of
three and economically negligible.

## (b) Volatility expansion — **SUPPORTED (3/3 on both kinds)**

Support rule: ratio-of-ratios CI excludes 1 upward on ≥2/3, per kind.

| kind | BTC | ETH | ES | count | verdict |
|---|---|---|---|---|---|
| sweep | **yes** [1.020,1.071] | **yes** [1.015,1.065] | **yes** [1.019,1.041] | 3/3 | supported |
| run | **yes** [1.016,1.071] | **yes** [1.007,1.052] | **yes** [1.003,1.024] | 3/3 | supported |

All six event cells expand realized volatility relative to ATR- and
killzone-matched controls; every CI clears 1. **Both sweep and run events
mark volatility-expansion moments.** Effect is small — ratios 1.01–1.04,
i.e. events expand ~1–4% more than matched controls — but consistent in
sign and clean of 1 across all three venues.

---

## Anomalies

1. **ES run/96 excludes 0 on the *downward* side** ([-0.00040, -0.00000],
   CI_hi = -0.00000). On the highest-power dataset the run-continuation
   prediction is, if anything, *mildly contradicted* (signed return
   negative). 1/3 only, so no anti-claim under the symmetric rule — but it
   is the reverse of ICT's expectation, not merely a null.
2. **ES run/384 CI_hi = +0.00000** (boundary), and **ES sweep/384 CI_lo =
   -0.00006** (near-boundary null). ES's large n makes its CIs tight enough
   that these sit right on 0; BTC/ETH CIs are ~5–20× wider and firmly
   straddle 0.
3. Event and control expansions are *both* > 1 everywhere (e.g. BTC sweep
   event 1.173 vs control 1.123). The next-96 window simply runs more
   volatile than the prior-96 window for matched bars too; the *ratio* is
   what isolates the event-specific excess, and it survives.

## Observations (not proposals)

- The two questions split exactly along the seam the frozen design drew:
  **direction nulls, volatility confirms.** Liquidity-taking events (sweep
  and run alike) coincide with a small, cross-venue expansion in realized
  volatility, while carrying no detectable forward direction — including no
  support for the sweep-reversal claim that is ICT's central tradable
  assertion.
- The volatility effect does **not** distinguish sweep from run: both kinds
  expand, ratios overlap heavily. Whatever these events mark, they mark it
  regardless of the purge-and-close-back vs continuation label.
- Direction results are consistent with M1/Part-A: at these horizons the
  data shows no liquidity-seeking and no post-sweep reversal edge.

## Proposals

- None. Reporting only, per contract.

## Blocking questions

- None. The frozen design fully specified datasets, params, killzone
  construction, and both support rules; all three datasets ran without
  degenerate cells (min n = 11,479, all ≥ the library's 5-event floor).

Pushing and stopping. No M3, no strategy inferences, no holdouts.
