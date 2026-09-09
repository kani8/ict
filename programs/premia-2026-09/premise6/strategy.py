"""Premise 6 core: 38-ETF class map, class-balanced weights, loaders (guarded).
Generic machinery (excess returns, EWMA vol/cov, signals/TSH, simulate,
pnl_breakdown, sharpe/max_drawdown/md_table, P3's 1/N target_weights for the
sensitivity table, _cov_tensor, _lagged_positions) is loaded from
premise3/strategy.py by file path under the name "p3_strategy" -- NOT via a
bare `import strategy`, which would self-reference this very module. Only
what differs from P3 lives here: the universe/class map and the
class-balanced raw-weight formula (PREMISE_6.md)."""
from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pandas as pd

ROOT = "/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
OOS_CUTOFF = pd.Timestamp("2024-07-01")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


p3 = _load("p3_strategy", f"{ROOT}/premise3/strategy.py")

CLASS_MAP = {
    "equities": ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ", "EWG", "EWU", "EWA",
                 "EWC", "EWZ", "EWH", "EWY", "FXI"],
    "bonds": ["TLT", "IEF", "LQD", "HYG", "TIP", "MBB", "BWX", "EMB"],
    "commodities": ["GLD", "SLV", "USO", "UNG", "DBC", "DBA", "DBB"],
    "currencies": ["UUP", "FXE", "FXY", "FXA", "FXB", "FXC", "FXF"],
    "real_estate": ["VNQ", "RWX"],
}
UNIVERSE = [t for ts in CLASS_MAP.values() for t in ts]
ASSET_CLASS = {t: c for c, ts in CLASS_MAP.items() for t in ts}
assert len(UNIVERSE) == 38 and len(set(UNIVERSE)) == 38

LOW_COST = {"SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "GLD", "VNQ"}
COST_BP = {t: (0.0005 if t in LOW_COST else 0.0010) for t in UNIVERSE}


def load_insample_prices(root: str = ROOT) -> pd.DataFrame:
    """Wide adj_close panel (date x ticker), 38-ETF universe. Guard: refuse if any date >= OOS cutoff."""
    df = pd.read_parquet(f"{root}/data_breadth/etf_daily_insample.parquet")
    df["date"] = pd.to_datetime(df["date"])
    mx = df["date"].max()
    if mx >= OOS_CUTOFF:
        raise ValueError(f"etf_daily_insample.parquet date.max()={mx} >= {OOS_CUTOFF} -- refusing (OOS leak)")
    px = df.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    return px[UNIVERSE]


def load_insample_rf(calendar: pd.DatetimeIndex, root: str = ROOT) -> pd.Series:
    """Daily rf (rate_pct/100/360) ffilled onto `calendar`; tbill_3m spans the
    full history so filter to < OOS_CUTOFF ourselves and re-assert."""
    tb = pd.read_parquet(f"{root}/data_breadth/tbill_3m.parquet")
    tb["date"] = pd.to_datetime(tb["date"])
    tb = tb[tb["date"] < OOS_CUTOFF].sort_values("date")
    if tb["date"].max() >= OOS_CUTOFF:
        raise ValueError("tbill_3m filter failed -- OOS leak")
    rf = tb.set_index("date")["rate_pct"] / 100.0 / 360.0
    return rf.reindex(calendar).ffill()


def class_balanced_weights(sig: pd.DataFrame, sigma: pd.DataFrame, cov_pairs: pd.DataFrame,
                            elig: pd.DataFrame, me: pd.DatetimeIndex, asset_class: dict = ASSET_CLASS):
    """w~_i,t = s_i,t*(0.40/sigma_i,t)*(1/n_c(i),t)*(1/C_t) (PREMISE_6.md), then
    P3's lambda scaling to 10% vol via EWMA cov + 3x gross cap (same machinery
    as premise3.strategy.target_weights, differing only in the raw formula)."""
    tickers = list(sig.columns)
    classes = sorted(set(asset_class.values()))
    sig_m, sigma_m = sig.reindex(me), sigma.reindex(me)
    elig_m = elig.reindex(me).fillna(False)

    n_c = pd.DataFrame({c: elig_m[[t for t in tickers if asset_class[t] == c]].sum(axis=1)
                         for c in classes}, index=me)
    C_t = (n_c > 0).sum(axis=1).astype(float)
    n_c_of_i = pd.DataFrame({t: n_c[asset_class[t]] for t in tickers}, index=me)

    raw = sig_m.where(elig_m, 0.0) * (p3.PER_INSTR_SCALE / sigma_m)
    raw = raw.div(n_c_of_i.replace(0, np.nan)).div(C_t.replace(0, np.nan), axis=0).fillna(0.0)

    cov_t = p3._cov_tensor(cov_pairs.reindex(me), tickers)
    var_p = np.einsum("ti,tij,tj->t", raw.to_numpy(), cov_t, raw.to_numpy())
    lam = p3.PORT_VOL_TARGET / np.sqrt(var_p)
    w = raw.mul(lam, axis=0)

    gross = w.abs().sum(axis=1)
    cap_binding = gross > p3.GROSS_CAP
    w = w.mul(np.where(cap_binding, p3.GROSS_CAP / gross, 1.0), axis=0)

    diag = pd.DataFrame({"n_eligible": elig_m.sum(axis=1).astype(float), "n_classes": C_t,
                          "gross_pre_cap": gross, "cap_binding": cap_binding,
                          "gross_post_cap": w.abs().sum(axis=1)}, index=me)
    return w, diag


if __name__ == "__main__":
    px = load_insample_prices()
    x = p3.daily_excess_returns(px, load_insample_rf(px.index))
    elig, me = p3.eligibility(px), p3.month_ends(px.index)
    sigma, cov_pairs = p3.ewma_vol_cov(x)
    w, diag = class_balanced_weights(p3.signals(x, 12), sigma, cov_pairs, elig, me)
    pnl = p3.simulate(w, x, cost_bp=COST_BP)
    print(f"prices {px.shape}, avg gross lev {diag['gross_post_cap'].mean():.3f}, "
          f"Sharpe {p3.sharpe(pnl['net']):.3f}")
