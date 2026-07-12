# Study CAT: "categorical trading" — implementation, mechanics calibration, and ES preregistration

**Date:** 2026-07-12 · **Status:** mechanics validated on synthetic worlds;
**ES confirmatory run preregistered and pending data availability** ·
**Code:** `src/ict_backtest/strategy/cat.py` · **Configs:**
`configs/cat_default.toml`, `configs/cat_es.toml` (frozen)

---

## 1. What is being tested

CAT ("categorical trading", ImanTrading) is a discretionary price-action
approach whose single organizing claim is:

> All price action exists on a spectrum between **consolidation** and
> **direction**. In consolidation, price is more likely to stay where it
> has already been; in direction, it is more likely to go to a new area.
> Every condition has clearly defined high-probability wins and losses,
> and brackets scale with the current candle size, so the approach is
> timeframe-agnostic.

This study mechanizes that claim faithfully and asks the harness's usual
question: does following it produce returns distinguishable from
randomly-timed trades with identical geometry?

## 2. Faithful mechanization (claim → code)

Every rule is traced to an explicit statement in the source material;
`strategy/cat.py`'s docstring carries the full mapping. Summary:

| Source claim | Mechanization |
|---|---|
| "spectrum of extremes ... between consolidation and direction" | Kaufman efficiency ratio of the trailing `regime_window` (24) closes: ≥ 0.40 → direction, ≤ 0.15 → consolidation, between → **no category** |
| "if the category keeps changing too fast ... take no trade" | coarse category must be identical for `stability_bars` (4) closed bars |
| "avoid a trade after a high-volatility candle — the start of a new category" | no entries for 2 bars after any candle with true range > 2.5 × trailing average |
| "trades are based on the current size of the candles" (ATR period 1) | bracket = `bracket_frac` (0.5) × mean true range of the last 10 candles — "targeting just under half the size of the recent candles" |
| "starting with a one-to-one risk-reward ratio" | `rr = 1.0`; stop distance = target distance |
| consolidation: "targets inside, stops outside; never long the top / short the bottom" | target must lie inside the trailing 24-bar range; entries vetoed in the outer 25% band against the trade; `require_stop_outside` reproduces the textbook drawing (off by default = his live small-bracket play) |
| consolidation entries "follow the candles ... when it looks like it's turning around" | default `consolidation_mode = "follow"`: trade in the direction of the last closed candle toward already-traded prices |
| "going against the direction at the extremes is an equally valid approach" | `consolidation_mode = "fade"`: short the top band, long the bottom band |
| direction: "flip your entries to target new areas, stop loss inside" | with-trend entries only (never fading a pullback — the stated high-probability loss); target must reach beyond the trailing range; stop sits inside it |
| "expect what's happening to continue" | entry candle's body must agree with the trade direction |
| timeframe agnosticism | no timeframe parameter exists; all distances are multiples of the trailing average candle range |
| personal-preference items (09:33–09:50 ET session, avoiding high/low of day, news days) | `session_et` knob (default off); the author is explicit these are his personal data-driven choices, not the system |

Decisions are made on closed bars only; every per-bar feature is a
trailing-window statistic, so the strategy passes the harness's
prefix-consistency (no-lookahead) test (`tests/test_cat.py`, 16 tests).

## 3. Why the calibration is synthetic (and why ES is not here yet)

This environment contains **no ES data**: `data/es_15m.parquet` /
`data/es_1m.parquet` were built in a previous session from a Databento
GLBX.MDP3 export (provenance and roll protocol in
`reports/dev/V3_ITER04.md`), were never committed, and every
market-data host is blocked by the session's network policy (verified:
stooq, Yahoo, Binance, Databento, polygon, nasdaq — all CONNECT-denied;
only package registries and GitHub are reachable).

That constraint is turned into a feature: **the CAT specification and
`configs/cat_es.toml` are frozen before any ES data contact**, making
the eventual ES run a genuine one-shot preregistered test rather than a
tuned backtest (§6).

What CAN be tested without market data is whether the mechanics are
implemented correctly, using two purpose-built synthetic worlds:

1. **Regime world** (`synthetic_cat_regimes`): alternating
   Ornstein-Uhlenbeck consolidation segments (price pulled toward the
   segment anchor — "stays where it has been") and drifting direction
   segments ("goes to a new area"). This is exactly the universe CAT
   claims as its edge; a correct implementation must extract it.
2. **Null world** (`synthetic_candles`, zero trend): a pure random
   walk; a correct implementation must find nothing, and a "profit"
   here would indicate a lookahead leak.

Passing both is a **calibration of the implementation, not evidence
about any market.**

## 4. Calibration results

One year of 15m bars per seed (35,040), three seeds, ES-calibrated costs
(spread 0.4 / commission 0.1 / slippage 0.4 bps), conservative intrabar
policy, defaults from `configs/cat_default.toml`, matched-baseline null
with 300 sims. Raw output: `reports/dev/_cat_results.json`.

### Regime world — edge exists by construction, and the mechanics find it

| seed | trades | mean R [95% block CI] | PF | win rate | p(return) | p(mean R) |
|---|---|---|---|---|---|---|
| 1 | 6,171 | **+0.126 [0.082, 0.170]** | 1.25 | 49.4% | 0.003 | 0.003 |
| 2 | 6,189 | **+0.170 [0.128, 0.212]** | 1.45 | 51.1% | 0.003 | 0.003 |
| 3 | 6,309 | **+0.181 [0.135, 0.227]** | 1.38 | 51.7% | 0.003 | 0.003 |

All CIs are entirely above zero and both null p-values sit at the
1/(N+1) floor on every seed. The classifier itself: ~68% of scored bars
receive a category, and ~90% of categorized bars agree with the
ground-truth regime label.

The optimistic intrabar policy gives the same qualitative answer
(seed 1: mean R +0.097, CI [0.071, 0.126]), so the result does not
depend on intrabar wishful thinking in either direction.

### Null world — no regimes, no edge, no leak

| seed | trades | mean R [95% block CI] | PF | p(return) | p(mean R) |
|---|---|---|---|---|---|
| 1 | 4,337 | −0.054 [−0.093, −0.016] | 0.91 | 0.43 | 0.60 |
| 2 | 4,302 | −0.080 [−0.117, −0.041] | 0.84 | 0.90 | 0.90 |
| 3 | 4,271 | −0.039 [−0.079, +0.002] | 0.93 | 0.32 | 0.40 |

Mean R ≈ minus the round-trip cost, exactly what an edgeless rule
should produce. The implementation is clean.

### Which category carries the edge (regime world)

| leg | trades/seed | mean R | win rate |
|---|---|---|---|
| direction (`cat_dir`) | ~2,200–2,500 | **+0.50 to +0.54** | ~64% |
| consolidation, `follow` mode (`cat_cons`) | ~3,800–3,900 | **−0.04 to −0.11** | ~41–43% |
| consolidation, `fade` mode (separate run) | see `_cat_results.json` `fade_mode` | | |

An honest and instructive decomposition: in this world the entire edge
comes from the **direction** leg. The author's own preferred
consolidation entry — following the last candle toward the interior —
is slightly negative here, because inside a mean-reverting segment the
next move is anti-correlated with the last candle. (Notably, the author
himself reports being unable to trade one of the two categories
profitably and simply sitting it out; the data reproduces the
experience that the two legs are different skills.) The `fade` variant
he describes as "equally valid" trades the same segments in the
opposite spirit; its numbers are in the results JSON alongside.

### Cost sensitivity — the quiet killer of half-candle brackets

Same seed-1 regime world, `follow` defaults:

| cost model | mean R | outcome |
|---|---|---|
| zero costs | +0.291 | large edge |
| ES futures (0.4/0.1/0.4 bps) | +0.126 | edge halved |
| crypto taker (1/2/1 bps) | **−0.459** | account destroyed (−100%) |

With targets of ~half a candle, round-trip costs consume R at brutal
scale. CAT-style scalping is only conceivable on venues with
futures-grade costs — consistent with the author trading CME futures —
and any ES verdict will hinge on the cost calibration being right.

## 5. What the calibration does and does not establish

**Established:** the implementation is faithful to the described rules,
lookahead-clean (prefix-consistency tests + null-world behavior), and
capable of extracting the exact edge the approach postulates when that
edge is planted in the data. The harness plumbing (matched nulls, block
bootstrap, cost model, intrabar policies) runs end-to-end on it.

**Not established:** that real markets — ES included — contain
detectable consolidation/direction regimes of the kind planted here.
That is precisely the open empirical question the ES run will answer,
and nothing in this report predicts its sign. The synthetic regime
world was *constructed* to reward the strategy; real data has no such
obligation.

## 6. Preregistered ES protocol (one shot)

Frozen before any ES data contact (this date, this commit). When
`data/es_15m.parquet` + `data/es_1m.parquet` are restored per the
documented Databento export and roll protocol (`reports/dev/V3_ITER04.md`
§1b; integrity gates must pass), run **once**:

```bash
uv run ict-backtest run --strategy cat \
  --data data/es_15m.parquet --intrabar-data data/es_1m.parquet \
  --config configs/cat_es.toml \
  --spread-bps 0.4 --commission-bps 0.1 --slippage-bps 0.4 \
  --bars-per-year 23447.4 --validate 500 --report reports/cat_es.md
```

Decision rule, declared now:

- **Positive** only if the block-bootstrap 95% CI of mean trade R is
  entirely above zero AND both matched-null p-values are < 0.05 under
  the conservative intrabar policy (1m resolution active).
- Anything else — including "positive return, CI straddling zero" — is
  **negative or inconclusive**, and the config is not retuned on ES
  afterward. A second run on new parameters would be a new,
  separately preregistered study.
- The per-leg decomposition (`cat_cons` vs `cat_dir`) is reported
  descriptively either way, since §4 predicts the legs can differ.
- ES 2010–2026 is already burned for tuning purposes by studies M/V3
  (its price paths have been analyzed in this repo), so this run is
  labeled **confirmatory-on-burned-data**: a pass would justify
  sourcing the reserved NQ holdout for a true one-shot; a fail closes
  the CAT-on-index track.

## 7. Files

| artifact | path |
|---|---|
| strategy + config dataclass | `src/ict_backtest/strategy/cat.py` |
| default / ES-frozen configs | `configs/cat_default.toml`, `configs/cat_es.toml` |
| regime-world generator | `src/ict_backtest/data/synthetic.py::synthetic_cat_regimes` |
| tests (incl. no-lookahead) | `tests/test_cat.py` |
| calibration driver + raw results | `reports/dev/_cat_runner.py`, `reports/dev/_cat_results.json` |
