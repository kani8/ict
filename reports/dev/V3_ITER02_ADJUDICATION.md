# Architect adjudication — V3 Iteration 02

Input: `reports/dev/V3_ITER02.md` (commit `0ff2ef3`). Executor conduct:
correct again — defect isolated, calendar sourced from primary snapshots,
no index data touched, anomalies flagged not tuned.

## Reading of the evidence

- The dol fix worked as specified (58%/52% bearish vs 99%/82%) and its
  downstream effect — *fewer* trades, bull-pointed bias on BTC — is the
  expected behavior of un-sticking a factor, not a new defect.
- The report's §5, however, delivers bias **coverage** and score
  **distributions**, not the **forward-return separation** that Iter-01
  step 5(i) asked for. Whether bull-bias bars out-return bear-bias bars is
  still unmeasured — and it is the single number the whole V3 thesis
  stands on. The gap is closed structurally: the diagnostic now ships as
  a tested library function (`analytics.diagnostics.forward_return_table`,
  non-overlapping windows so t-stats are honest) that Iteration 03 calls
  verbatim.
- Process gap: `V3_ITER01.md` was never pushed (only ITER02 is in the
  repo). Iteration 03 must backfill it.

## Rulings on the four blocking questions

1. **Trade-count lever = the entry path** (`entry_confirmation` → limit
   mode), not a bias/discount gate. Evidence: conviction is not binding
   at 0.25 (counts did not scale), while the await stage loses ~85–90% of
   staged intent (24/4, 28/3). The confirmation-close requirement
   compounding with the 30-bar expiry is the throttle. One lever, paired
   comparison, nothing else moves. The funnel now splits abandonment into
   expired/violated/displaced so the mechanism is visible either way.
2. **Weights hold at (1,1,1,1,1).** No reweight before the forward-return
   tables exist; the executor's own observation stands (weights change
   direction, not frequency).
3. **ES: proceed — request the user export.** Rulings: **back-adjusted**
   continuous contract (raw roll gaps create spurious sweeps/FVGs/breaks;
   every detector consumes price differences, which back-adjustment
   preserves — the bps-cost distortion in deep history is acceptable and
   noted), **OI-based roll with roll dates documented**, **23h Globex
   session** (the London killzone does not exist in RTH data), 15m + 1m
   from the same construction. Provisional ES cost model:
   `spread_bps=0.4, commission_bps=0.1, slippage_bps=0.4` (0.25-tick
   spread at ~6000; executor recalibrates against actual price levels).
   `--bars-per-year` computed from the delivered data (~23h x ~252d).
4. **dol-only ablation: not required.** The defect question is settled by
   the fix + distributions; dol's *predictiveness* will be read from the
   per-factor forward-return table, which supersedes a separate ablation.

## Stop-condition guidance (declared before Iteration 03 runs)

- If the forward-return tables show **no separation** (bull-state mean not
  above bear-state mean on both symbols, |t| < 1 everywhere): the
  narrative layer has no measurable signal on crypto dev data. Crypto
  development halts; the program's remaining question becomes whether ES
  behaves differently, and only the user's ES export can answer it.
- If limit-mode restores evaluable trade counts (n >= 30 combined) with
  the nulls run: normal development continues on whichever bias mode the
  paired comparison favors.
