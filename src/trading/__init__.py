# -*- coding: utf-8 -*-
"""
自动交易模块：从分析结果生成买卖信号，供国信 iQuant 等客户端拉取并执行下单。

- signals: 从 AnalysisResult 生成标准化 TradeSignal
- execution: 风控与执行（本应用侧仅 dry-run 记录；实盘由 iQuant 内策略 passorder 完成）
"""

from src.trading.signals import TradeSignal, build_signals_from_results, to_qmt_stock_code
from src.trading.execution import TradingExecutionEngine, get_trading_engine

__all__ = [
    "TradeSignal",
    "build_signals_from_results",
    "to_qmt_stock_code",
    "TradingExecutionEngine",
    "get_trading_engine",
]
