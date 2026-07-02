"""ict-backtest: Smart Money Concepts strategy + lookahead-safe backtesting harness."""

from .core import BEAR, BULL, Candles, FVG, LiquidityPool, OrderBlock, StructureEvent, Swing, atr, resample
from .engine import Backtester, BacktestResult, CostModel, Order, Trade
from .strategy import RandomStrategy, SMCConfig, SMCStrategy

__version__ = "0.1.0"

__all__ = [
    "BEAR", "BULL", "Candles", "FVG", "LiquidityPool", "OrderBlock",
    "StructureEvent", "Swing", "atr", "resample",
    "Backtester", "BacktestResult", "CostModel", "Order", "Trade",
    "RandomStrategy", "SMCConfig", "SMCStrategy",
]
