# CAT ES Results

## Header

| item | value |
|---|---|
| commit | `d0f56e5` |
| date | 2026-07-12T03:31:48Z |
| branch binding | detached `d0f56e5` for execution; no code/config edits |
| config | `configs/cat_es.toml` |
| data source | restored local files from `/Users/kanis/Downloads/ict/data/` |
| Databento job id | `GLBX-20260702-TBF7DT8KTH` |
| source file | `glbx-mdp3-20100606-20260701.ohlcv-1m.csv.zst` |
| source sha256 | `e9ebda22332f27ed31a360bc9d8c8f6dba18f6bec916702ed3bab624b8691000` |
| cost | no new Databento fetch; restored local data only. Purchase/export cost not present in restored metadata. |
| seeds | matched null seed 42; block bootstrap seed 7 |

Preflight:

```bash
/Users/kanis/.local/bin/uv sync --extra dev
/Users/kanis/.local/bin/uv run pytest -q
/Users/kanis/.local/bin/uv run ruff check src tests
```

Result: `147 passed in 12.75s`; ruff clean.

One-shot invocation:

```bash
/Users/kanis/.local/bin/uv run ict-backtest run --strategy cat \
  --data data/es_15m.parquet --intrabar-data data/es_1m.parquet \
  --config configs/cat_es.toml \
  --spread-bps 0.4 --commission-bps 0.1 --slippage-bps 0.4 \
  --bars-per-year 23447.4 --validate 500 --report reports/dev/CAT_ES_RUN.md
```

Auxiliary, allowed by the task, after the CLI run:

```bash
/Users/kanis/.local/bin/uv run python reports/dev/_cat_es_driver.py
```

The driver re-executed the identical Python API backtest solely for per-leg
decomposition and `strategy.skip_counts`; it asserted the rounded CLI headline
numbers before writing `_cat_es_driver.json`.

## Data Integrity

Artifacts copied/restored:

- `data/es_15m.parquet` — sha256 `a3fc183db2a464410d54b9ce6fab442cacbf1ac390a99515a23efc1b38cdd478`
- `data/es_1m.parquet` — sha256 `20998ac6b8c10a77c2789bce745cf5a5f4443a86bb360a00756dfcb7d53b7bc7`
- `data/es_1m_raw.parquet` — sha256 `00fc93c2524970747079c50c882024d2fccf2f5bd13965bca2f9ca0781c41753`
- `reports/dev/_cat_es_roll_calendar.json` — restored roll log, 65 rolls

Integrity invocation:

```bash
/Users/kanis/.local/bin/uv run python reports/dev/_cat_es_integrity.py
```

| gate | result |
|---|---|
| 15m rows/range | 376,768; 2010-06-06 22:00:00+00:00 → 2026-07-01 23:45:00+00:00 |
| 1m rows/range | 5,615,435; 2010-06-06 22:00:00+00:00 → 2026-07-01 23:59:00+00:00 |
| monotonic timestamps | pass for 15m, 1m, raw 1m |
| duplicates | 0 for 15m, 1m, raw 1m |
| OHLC violations | 0 for 15m, 1m, raw 1m |
| adjusted min low | 1600.25 (> 0) |
| 15m ↔ 1m aggregation | exact: 376,768 / 376,768 buckets, max abs diff 0.0 for OHLCV |
| roll continuity | exact: 65 / 65 matched, worst residual 0.0 |

## Results

| trades | total return | PF | mean R | block-bootstrap CI | p(return) | p(mean R) | max DD | exposure |
|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 47,387 | -100.00% | 0.62 | -0.34 | [-0.35, -0.33] | 0.054 | 0.830 | -100.00% | 6.6% |

Additional headline metrics: win rate 46.5%, final equity rendered as 0
(`1.87e-09` before report formatting), Sharpe -10.89, Sortino -6.78, average
/ median holding 0.5 / 0.0 bars. Exit reasons: 24,717 stop losses, 22,670
take profits.

Null diagnostics: trade-template null with 500 simulations had null mean return
-100.00% ± 0.00%; strategy -100.00%. Null mean trades 47,386.7; strategy trades
47,387. Null exposure 28.57%; strategy exposure 6.56%. Null mean holding 2.3
bars; strategy mean holding 0.5 bars.

## Per-Leg Decomposition

| leg | n | mean R | win rate |
|---|---:|---:|---:|
| `cat_cons` | 41,560 | -0.346 | 46.4% |
| `cat_dir` | 5,827 | -0.292 | 47.1% |

Both registered legs are negative. Direction is less negative than
consolidation, but neither leg is close to positive expectancy.

## Skip-Count Funnel

| key | count |
|---|---:|
| no_category | 165,593 |
| unstable | 93,875 |
| extreme_entry_veto | 17,006 |
| no_candle_to_follow | 16,752 |
| target_not_new_area | 6,345 |
| outlier_blackout | 4,994 |
| rejected_geometry | 62 |
| target_not_inside | 2 |
| not_eligible_time | 0 |
| category_disabled | 0 |
| stop_not_outside | 0 |
| degenerate_range | 0 |
| vol_out_of_band | 0 |
| at_day_extreme | 0 |
| daily_loss_stop | 0 |
| max_trades_stop | 0 |

## Anomalies

- `uv` was not initially installed in the active shell. Installed user-local
  `uv` at `/Users/kanis/.local/bin/uv`, then ran the required `uv` preflight.
- ES data was not in `/Users/kanis/Desktop/ict/data`; it was restored from
  `/Users/kanis/Downloads/ict/data`. No Databento API call was made and
  `DATABENTO_API_KEY` remains unnecessary for this execution.
- No data-integrity anomalies after restore.
- No NQ data was fetched, inspected, or summarized.

## Decision-Rule Branch

`reports/CAT_STUDY.md` §6 declares a positive result only if the conservative
1m-resolved run has mean-trade-R 95% block-bootstrap CI entirely above zero and
both matched-null p-values < 0.05.

This run falls in the negative branch: CI is entirely below zero
([-0.35, -0.33]), p(return)=0.054 is not < 0.05, and p(mean R)=0.830 is not
< 0.05. The adjudication itself remains the architect's.

## Observations

- The restored ES contract passes every documented gate from the V3 protocol.
- The CAT system trades frequently on ES (47,387 trades over 376,768 bars) and
  loses the account under the frozen risk/cost assumptions.
- The loss is not confined to one category: both `cat_cons` and `cat_dir` have
  negative mean R.
- The principal non-entry reason is categorical: 165,593 bars have no category
  and 93,875 fail stability.

## Proposals

- Treat this as a failed CAT-on-ES confirmation under the preregistered §6
  decision rule.
- Do not source or touch NQ from this result alone; if NQ is ever used, it
  should require a new explicit architect ruling.
- If the architect wants to investigate why the frozen complete system trades
  so frequently and compounds to zero, do it as a new development study, not as
  a post-hoc amendment to this one-shot.
