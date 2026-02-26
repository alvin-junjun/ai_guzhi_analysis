# -*- coding: utf-8 -*-
"""
交易执行层：风控校验、信号持久化、dry-run 记录。

本应用不直接连接券商下单；实盘由国信 iQuant 内策略通过 passorder 完成。
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from src.config import get_config
from src.trading.signals import TradeSignal, build_signals_from_results
from src.analyzer import AnalysisResult

logger = logging.getLogger(__name__)

# 默认信号持久化路径（项目 data 目录下）
DEFAULT_SIGNALS_PATH = "data/trading_signals_latest.json"


class TradingExecutionEngine:
    """
    交易执行引擎：生成信号、风控过滤、持久化供 iQuant 拉取、dry-run 时仅记录。
    """

    def __init__(
        self,
        signals_path: Optional[str] = None,
        dry_run: Optional[bool] = None,
        max_order_amount: Optional[float] = None,
        daily_max_buy_amount: Optional[float] = None,
    ):
        cfg = get_config()
        self.signals_path = Path(signals_path or getattr(cfg, "trading_signals_path", None) or DEFAULT_SIGNALS_PATH)
        self.dry_run = dry_run if dry_run is not None else getattr(cfg, "auto_trade_dry_run", True)
        self.max_order_amount = max_order_amount if max_order_amount is not None else getattr(cfg, "trading_max_order_amount", 0.0) or 0.0
        self.daily_max_buy_amount = daily_max_buy_amount if daily_max_buy_amount is not None else getattr(cfg, "trading_daily_max_buy_amount", 0.0) or 0.0

    def run(
        self,
        results: List[AnalysisResult],
        *,
        source_date: Optional[date] = None,
        source_task_id: Optional[str] = None,
    ) -> List[TradeSignal]:
        """
        根据分析结果生成买入信号，风控过滤后持久化并（dry_run 时）记录日志。

        Returns:
            本次实际保留的信号列表（风控后）
        """
        signals = build_signals_from_results(
            results,
            only_buy=True,
            source_date=source_date,
            source_task_id=source_task_id,
        )
        if not signals:
            self._persist_signals([])
            return []

        # 简单风控：单笔金额、日累计金额（此处无实际下单金额，仅做条数/占位校验，实际金额由 iQuant 侧控制）
        filtered: List[TradeSignal] = []
        for s in signals:
            if self.max_order_amount and (s.suggested_amount or 0) > self.max_order_amount:
                logger.warning(f"[交易风控] 跳过 {s.code}：单笔建议金额 {s.suggested_amount} 超过上限 {self.max_order_amount}")
                continue
            filtered.append(s)

        if self.daily_max_buy_amount and filtered:
            # 无实际累计时仅记录提示；真实日累计应在 iQuant 或柜台侧做
            logger.info(f"[交易风控] 当日买入信号数: {len(filtered)}，日累计上限配置: {self.daily_max_buy_amount}")

        if self.dry_run:
            for s in filtered:
                logger.info(f"[DryRun] 信号: {s.action} {s.code} {s.name} | {s.operation_advice} 置信度={s.confidence_level} 评分={s.sentiment_score}")

        self._persist_signals(filtered)
        return filtered

    def _persist_signals(self, signals: List[TradeSignal]) -> None:
        """将信号列表写入 JSON 文件，供 /api/trading/signals 或 iQuant 拉取。"""
        path = Path(self.signals_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now().isoformat(),
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"交易信号已写入: {path}，共 {len(signals)} 条")
        except Exception as e:
            logger.error(f"写入交易信号失败: {path} - {e}")

    def load_latest_signals(self) -> dict:
        """读取当前持久化的信号（供 API 返回）。"""
        path = Path(self.signals_path)
        if not path.exists():
            return {"updated_at": None, "count": 0, "signals": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取交易信号失败: {path} - {e}")
            return {"updated_at": None, "count": 0, "signals": []}


_trading_engine: Optional[TradingExecutionEngine] = None


def get_trading_engine() -> TradingExecutionEngine:
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = TradingExecutionEngine()
    return _trading_engine
