# ICT repo reuse notes

Pointers into this repo's existing, tested infrastructure, for reuse in the new ES pipeline. Nothing here was modified.

## (a) Fill/order engine + pessimistic intrabar rules
`src/ict_backtest/engine/backtester.py` (exported via `ict_backtest.engine`)
- `class CostModel(spread_bps=1.0, commission_bps=2.0, slippage_bps=1.0)` — `.fill_price(price, side, aggressive)`, `.commission(notional)`
- `class Order(side, qty, type="market"|"limit"|"stop", price=0.0, sl=0.0, tp=0.0, expiry_index=-1, tag="")`
- `class Broker(candles, cost, initial_equity)` — strategy-facing: `.submit(order)`, `.cancel(id)`, `.cancel_all()`, `.close_position()`, `.equity`, `.position`
- `class Backtester(cost=None, initial_equity=100_000.0, intrabar_policy="conservative"|"optimistic", intrabar: Candles|None=None)` — `.run(candles, strategy) -> BacktestResult`
- `class Trade` / `class BacktestResult(trades, equity_curve, candles, initial_equity)`

Pessimistic rules baked in: orders on bar `i` fill no earlier than `i+1`; a
bar touching both stop and target resolves to the stop under
`"conservative"` (default); gapped exits fill at the open, not the level;
entry-bar take-profit is never granted under `"conservative"` unless finer
`intrabar=` candles resolve the actual touch order (pass 1m `Candles` as
`intrabar=` to a 1h/4h `Backtester`).

**Data format**: `Candles` (`core.py`) is a column-oriented numpy dataclass:
`ts` (int64 **UTC epoch seconds**, not ns/ms), `open/high/low/close/volume`
(float64 arrays), `timeframe_s` (int). A `Strategy` is any object exposing `on_bar(i, broker)`.

## (b) Block-bootstrap / matched-null analytics
`src/ict_backtest/analytics/significance.py` (exported via `ict_backtest.analytics`)
- `bootstrap_ci(values, n_boot=10_000, alpha=0.05, seed=7) -> (mean, lo, hi)` — IID bootstrap
- `block_bootstrap_ci(values, n_boot=10_000, alpha=0.05, block_len=None, seed=7) -> (mean, lo, hi, block_len)` — circular moving-block bootstrap (preferred; preserves serial dependence between trades); `block_len` defaults to `n**(1/3)`
- `matched_baseline_test(candles, result: BacktestResult, backtester: Backtester, eligible_mask=None, n_sims=200, seed=42, risk_pct=1.0, max_leverage=5.0) -> BaselineTest` — replays the strategy's own trade templates (side/stop/target/sizing) at randomized times; p-values for total return and mean per-trade R
- `random_baseline_test(...) -> BaselineTest` — simpler drift-only null, not exposure-matched

**Data format**: takes the `Candles`/`BacktestResult`/`Backtester` from (a);
`values` for the bootstrap functions is any 1-D array of per-trade stats (e.g. R-multiples).

## (c) No-lookahead prefix-consistency test pattern
`tests/test_no_lookahead.py`
- `test_prefix_consistency(cutoff)` and `test_trades_match_on_prefix()`
- Pattern: run the strategy on the full `Candles` series and again on
  `candles.slice(0, cutoff)`; every order submitted (or trade closed) at
  bar `< cutoff` must be byte-identical between runs. A `RecordingStrategy`
  wrapper snapshots `broker.pending` after each `on_bar` to capture
  submissions. Divergence means a detector used data from bars `>= cutoff`.
  Reusable as-is against any `Strategy` — swap `synthetic_candles(...)` for
  real `Candles` loaded from the new parquet files.

## (d) Resampling helper
`src/ict_backtest/core.py`
- `resample(candles: Candles, multiplier: int) -> (htf_candles: Candles, last_base_index: np.ndarray)`
- Buckets align to wall-clock **UTC** boundaries of the target timeframe
  (`ts - ts % (timeframe_s * multiplier)`), e.g. a 4h bar starts at 00/04/08
  UTC — NOT ET-session-anchored like the new `es_4h.parquet`.
  `last_base_index[k]` is the base-bar index of HTF bar k's close, for
  mapping an HTF artifact back to base-timeframe indices with no lookahead.

## Loading the new data into this repo's format
`src/ict_backtest/data/loader.py`: `load_candles(path, timeframe_s=None, start=None, end=None) -> Candles`, `candles_from_dataframe(df, timeframe_s=None)`.
Column matching is **exact-name**, not substring: it wants a column named
one of `ts/timestamp/time/date/datetime/open_time` (case-insensitive). The
new `es_*.parquet` files use `ts_utc`/`ts_et`, which won't match — rename
one to `ts` before calling `candles_from_dataframe`. Timestamps may be epoch
(s or ms, auto-detected) or datetime; volume optional (zero-filled if absent).
