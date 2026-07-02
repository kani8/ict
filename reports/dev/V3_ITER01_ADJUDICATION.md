# Architect adjudication — V3 Iteration 01

Input: `reports/dev/V3_ITER01.md` (executor, commit `93d686a` runs).
Executor conduct: correct — anomalies reported not patched, holdouts
untouched, no unrequested experiments.

## Rulings on the three blocking questions

1. **Over-gating: not a stop condition — it is contaminated by a defect.**
   The `dol` factor was structurally biased (98.8% bearish through a bull
   market): untaken liquidity accumulates on the side price trends away
   from, so unbounded inventory reads as permanent draw. Ruling: fix the
   defect (recency window, below), re-measure the funnel, and only then
   judge gating. The single sanctioned loosening lever remains
   `narrative_min_conviction` (already in the sweep matrix). If the new
   funnel shows a different dominant killer, one additional lever may be
   declared in Iteration 03 — one lever per iteration, never two.
2. **dol investigated and fixed** (architect spec change, development
   phase): `dol_lookback_days = 60` — only liquidity formed within the
   last 60 daily bars counts as a live draw, matching ICT's own 20/40/60
   IPDA recency framing. Unit-tested against the stale-pool scenario.
3. **Minimum-trade gate: implemented.** `matched_baseline_test` now skips
   the simulation with an explicit note when n < 5, and reports label
   sub-5-trade results "underpowered, not evidence" instead of silently
   omitting CIs.

Also added: **setup-funnel instrumentation** (`SMCStrategy.funnel`) —
counts signals and every rejection reason (bias, bias2, discount, draw,
time, no-POI, OTE, geometry) plus order placements and await outcomes,
so over-gating is now measurable instead of inferred.

## Index-futures track (user directive)

ES/NQ are ICT's home market and the killzone/news/session machinery is
native there. Declared in the V3 preregistration amendment:

- **ES 2023–2026 = development data** (deliberately burned when sourced).
- **NQ 2023–2026 = reserved index holdout.** Do not fetch or inspect.
- Requirements before any ES run: continuous back-adjusted contract with
  the roll method recorded; 15m + 1m; `--bars-per-year` set for the
  Globex session; costs recalibrated (≈0.4–0.5 bp spread + commission);
  full high-impact calendar per `docs/CALENDAR_SOURCES.md` (CPI included
  — index futures respond to it more than crypto does).
- Sourcing: no free API covers this; executor scopes what its access
  allows and reports options + cost; the user approves any purchase.
  Broker exports (e.g. from a futures broker or TradingView) are
  acceptable if OHLCV-complete and roll-documented.

## Iteration 02 scope (issued separately)

Re-run the Iteration-01 matrix on the already-fetched crypto dev data at
the new commit (dol fixed), adding per-run funnel tables and the dol
distribution before/after comparison; assemble the 2023–2026 high-impact
calendar from official sources; scope ES/NQ data acquisition. No weight
tuning yet — weights stay (1,1,1,1,1) until the fixed-dol regime tables
are seen.
