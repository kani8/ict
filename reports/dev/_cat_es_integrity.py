from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DATA_15M = Path("data/es_15m.parquet")
DATA_1M = Path("data/es_1m.parquet")
DATA_1M_RAW = Path("data/es_1m_raw.parquet")
ROLLS = Path("reports/dev/_cat_es_roll_calendar.json")
OUT = Path("reports/dev/_cat_es_integrity.json")


def summarize(df: pd.DataFrame) -> dict:
    ts = df["ts"]
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    return {
        "rows": int(len(df)),
        "first": str(ts.iloc[0]),
        "last": str(ts.iloc[-1]),
        "monotonic": bool(ts.is_monotonic_increasing),
        "duplicates": int(ts.duplicated().sum()),
        "ohlc_violations": int(((h < l) | (h < o) | (h < c) | (l > o) | (l > c)).sum()),
        "min_low": float(l.min()),
        "max_high": float(h.max()),
    }


def reconcile_15m(df_1m: pd.DataFrame, df_15m: pd.DataFrame) -> dict:
    one = df_1m.set_index("ts").sort_index()
    agg = (
        one.resample("15min", label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    merged = df_15m.merge(agg, on="ts", suffixes=("_15m", "_from_1m"), how="outer", indicator=True)
    diffs: dict[str, float] = {}
    mismatches = int((merged["_merge"] != "both").sum())
    both = merged[merged["_merge"] == "both"]
    for col in ["open", "high", "low", "close", "volume"]:
        delta = (both[f"{col}_15m"] - both[f"{col}_from_1m"]).abs()
        max_delta = float(delta.max()) if len(delta) else 0.0
        diffs[col] = max_delta
        mismatches += int((delta > 0).sum())
    return {
        "buckets_15m": int(len(df_15m)),
        "buckets_from_1m": int(len(agg)),
        "max_abs_diff": diffs,
        "mismatches": mismatches,
        "exact": bool(mismatches == 0 and all(v == 0.0 for v in diffs.values())),
    }


def roll_continuity(adjusted: pd.DataFrame, raw: pd.DataFrame) -> dict:
    roll_log = json.loads(ROLLS.read_text())
    merged = adjusted[["ts", "close"]].merge(raw[["ts", "close"]], on="ts", suffixes=("_adj", "_raw"))
    merged["offset"] = merged["close_adj"] - merged["close_raw"]

    residuals: list[dict] = []
    for roll in roll_log["rolls"]:
        eff = pd.Timestamp(roll["effective_day"], tz="UTC")
        before = merged[merged["ts"] < eff + pd.Timedelta(days=1)]
        before = before[before["ts"] < merged.loc[merged["ts"] >= eff, "ts"].iloc[0]]
        after = merged[merged["ts"] >= eff]
        if before.empty or after.empty:
            residuals.append({"roll_index": roll["roll_index"], "matched": False})
            continue
        offset_before = float(before["offset"].iloc[-1])
        offset_after = float(after["offset"].iloc[0])
        offset_step = offset_after - offset_before
        raw_gap = float(roll["raw_gap"])
        residual = offset_step + raw_gap
        residuals.append(
            {
                "roll_index": roll["roll_index"],
                "effective_day": roll["effective_day"],
                "from_symbol": roll["from_symbol"],
                "to_symbol": roll["to_symbol"],
                "raw_gap": raw_gap,
                "offset_before": offset_before,
                "offset_after": offset_after,
                "offset_step": offset_step,
                "residual": residual,
                "matched": abs(residual) < 1e-9,
            }
        )
    matched = [r for r in residuals if r.get("matched")]
    unmatched = [r for r in residuals if not r.get("matched")]
    worst = max((abs(float(r.get("residual", float("inf")))) for r in residuals), default=0.0)
    return {
        "rolls": int(roll_log["n_rolls"]),
        "matched": int(len(matched)),
        "unmatched": int(len(unmatched)),
        "worst_residual": float(worst),
        "all_exact": bool(len(unmatched) == 0 and worst == 0.0),
        "residuals": residuals,
    }


def main() -> None:
    df_15m = pd.read_parquet(DATA_15M)
    df_1m = pd.read_parquet(DATA_1M)
    df_raw = pd.read_parquet(DATA_1M_RAW)
    result = {
        "source": {
            "data_15m": str(DATA_15M),
            "data_1m": str(DATA_1M),
            "data_1m_raw": str(DATA_1M_RAW),
            "roll_calendar": str(ROLLS),
        },
        "es_15m": summarize(df_15m),
        "es_1m": summarize(df_1m),
        "es_1m_raw": summarize(df_raw),
        "aggregation": reconcile_15m(df_1m, df_15m),
        "roll_continuity": roll_continuity(df_1m, df_raw),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
