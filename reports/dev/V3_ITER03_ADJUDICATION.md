# Architect adjudication — V3 Iteration 03

Input: `reports/dev/V3_ITER03.md` (commit `446fccd`; ITER01 backfilled at
`d1d20ac`). Executor conduct: correct — both stop-condition readings
reported without self-adjudication, no levers touched, holdouts intact.

## Ruling: the stop condition is MET. Crypto development halts.

The literal text of my condition ("bull mean ≤ bear mean OR |t| < 1
everywhere, both symbols") was drafted too weakly, and the drafting error
is mine. Two principles resolve it:

1. **Ambiguity in a predeclared rule resolves against the strategy** —
   the same conservatism the execution engine applies to ambiguous bars.
2. **The lone passing cell is a multiple-comparisons expectation, not a
   signal.** BTC h=96 (bull t = +2.36) sits in a family of ~30+ examined
   cells (2 symbols × 2 horizons × {bias, structure, 5 factor signs, 5
   quintiles}); 1–2 cells at |t| ≥ 2 are expected under the null. It
   fails both replication axes — inverts at h=384 on the same symbol,
   inverts at both horizons on the other symbol — and its bear state is
   *also* positive (+0.0019): in a bull-market sample, much of that
   "significant" bull mean is drift.

Worse than mere non-separation: **ETH is anti-predictive** — the bull
state carries negative forward returns at both horizons and the score
quintiles decrease monotonically. A narrative layer that inverts on half
the development data has no stable sign to weight.

## Consequent rulings

- **No weights lever.** Reweighting to flip ETH's inverted factors would
  be fitting the composite to the burned sample — the exact failure mode
  this protocol exists to prevent. Question 2 of the report is thereby
  answered: neither lever opens.
- **V3-crypto closes at the development stage** with a negative finding:
  the mechanized narrative (5 factors, defect-fixed, measured directly
  and before any trigger/execution noise) carries no consistent
  directional information on crypto dev data.
- **The V3 crypto holdouts (BNBUSDT 2023–2026, ETHUSDT 2019–2022) are
  NOT run and remain unburned.** Executing a one-shot holdout for a
  strategy with no in-sample signal converts irreplaceable data into a
  foregone underpowered result. Closing at development is the *efficient*
  negative: zero holdouts spent.
- **Recommendation on V2.1** (user ratification required, since V2.1 was
  separately preregistered): retire its holdout execution. Iteration 02's
  structure-mode rows are development-equivalent evidence that the V2.1
  gate stack yields ~4 trades / 3.5 years — its one-shot would return
  n < 5, underpowered and uninterpretable, burning SOLUSDT 2023–2026 and
  BTCUSDT 2019–2022 for nothing. Default pending ratification: holdouts
  stay untouched (not running is the reversible choice).
- **`structure_bias ≡ factor_sign::struct_mtf` is expected**, by
  construction (structure mode *is* the 4h structure direction). Not a
  defect.

## Program state after this ruling

| Study | Status |
|---|---|
| V1 canonical ICT | Failed confirmatory (BTC, then untouched ETH holdout). Closed. |
| V2.1 maximum-faithfulness | Frozen; holdout execution recommended retired (starved spec). Holdouts preserved. |
| V3 narrative — crypto | **Failed at development** (no consistent forward-return separation; ETH anti-predictive). Closed. Holdouts preserved. |
| V3 narrative — index (ES) | **Sole open line.** Gated on a user-supplied ES export (back-adjusted OI-roll continuous, 23h Globex, 15m+1m; NQ remains reserved). |

If the ES track is not pursued, the program terminates here with three
independent, increasingly faithful mechanizations all failing honest
tests — two at confirmation, one at development — and four reserved
holdouts never wasted.
