# -*- coding: utf-8 -*-
"""
交易信号层：从 AI 分析结果筛选「买入/加仓」类结论，生成标准化交易信号。

供本应用内 dry-run 记录与 /api/trading/signals 暴露给国信 iQuant 策略拉取。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

from src.analyzer import AnalysisResult

logger = logging.getLogger(__name__)


# 决策类型中视为「买入/加仓」的值
BUY_DECISION_TYPES = ("buy",)
BUY_OPERATION_ADVICE = ("买入", "加仓", "强烈买入")


@dataclass
class TradeSignal:
    """标准化交易信号（供下游执行或 iQuant 拉取）"""

    code: str  # 股票代码，如 600519
    name: str  # 股票名称
    action: str  # buy / sell
    operation_advice: str  # 原始建议，如 买入/加仓
    confidence_level: str  # 高/中/低
    sentiment_score: int  # 0-100
    # 可选：建议金额（元）或股数，由下游与风控决定实际下单量
    suggested_amount: Optional[float] = None  # 元
    suggested_shares: Optional[int] = None   # 股（100 的整数倍）
    # 来源
    source_date: Optional[date] = None
    source_task_id: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "action": self.action,
            "operation_advice": self.operation_advice,
            "confidence_level": self.confidence_level,
            "sentiment_score": self.sentiment_score,
            "suggested_amount": self.suggested_amount,
            "suggested_shares": self.suggested_shares,
            "source_date": self.source_date.isoformat() if self.source_date else None,
            "source_task_id": self.source_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def to_qmt_stock_code(code: str) -> str:
    """
    将本系统股票代码转为 QMT/国信 iQuant 格式。
    A 股：6 开头 -> XXX.SH，否则 -> XXX.SZ。
    """
    code = (code or "").strip().upper()
    if not code:
        return ""
    # 去掉已有后缀
    if "." in code:
        code = code.split(".")[0]
    if code.isdigit():
        return f"{code}.SH" if code.startswith("6") else f"{code}.SZ"
    return code


def build_signals_from_results(
    results: List[AnalysisResult],
    *,
    only_buy: bool = True,
    min_confidence: Optional[str] = None,
    min_score: Optional[int] = None,
    source_date: Optional[date] = None,
    source_task_id: Optional[str] = None,
) -> List[TradeSignal]:
    """
    从分析结果中筛选买入/加仓类信号。

    Args:
        results: AI 分析结果列表
        only_buy: 是否只保留买入类（True 时只保留 decision_type in ('buy',)）
        min_confidence: 最低置信度过滤，如 '中' 表示只保留 高/中
        min_score: 最低 sentiment_score，如 65
        source_date: 信号日期
        source_task_id: 来源任务 ID

    Returns:
        标准化 TradeSignal 列表
    """
    if not results:
        return []

    now = datetime.now()
    day = source_date or date.today()
    signals: List[TradeSignal] = []

    confidence_order = ("低", "中", "高")

    for r in results:
        if not getattr(r, "success", True):
            continue
        decision_type = getattr(r, "decision_type", "hold") or "hold"
        operation_advice = getattr(r, "operation_advice", "") or ""
        if only_buy and decision_type not in BUY_DECISION_TYPES:
            continue
        if only_buy and operation_advice not in BUY_OPERATION_ADVICE:
            continue
        if min_confidence:
            conf = getattr(r, "confidence_level", "中") or "中"
            if confidence_order.index(conf) < confidence_order.index(min_confidence):
                continue
        if min_score is not None:
            score = getattr(r, "sentiment_score", 0) or 0
            if score < min_score:
                continue

        signals.append(
            TradeSignal(
                code=r.code,
                name=getattr(r, "name", "") or f"股票{r.code}",
                action="buy" if only_buy else ("sell" if decision_type == "sell" else "hold"),
                operation_advice=operation_advice,
                confidence_level=getattr(r, "confidence_level", "中") or "中",
                sentiment_score=getattr(r, "sentiment_score", 0) or 0,
                suggested_amount=None,
                suggested_shares=None,
                source_date=day,
                source_task_id=source_task_id,
                created_at=now,
            )
        )

    logger.info(f"交易信号: 从 {len(results)} 条分析中生成 {len(signals)} 条买入/加仓信号")
    return signals
