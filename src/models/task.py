# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 任务模型

定义分析任务、自选股、分析历史相关的数据模型
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, Date,
    Enum as SQLEnum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from src.storage import Base


class AnalysisTask(Base):
    """
    分析任务表
    
    持久化存储分析任务状态，支持任务恢复和历史查询
    """
    __tablename__ = 'analysis_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 任务标识
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment='任务ID')
    
    # 关联用户（可选，支持匿名任务）
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True, comment='用户ID')
    
    # 任务类型
    task_type = Column(
        SQLEnum('single', 'batch', 'scheduled', 'market_review', name='task_type'),
        default='single',
        nullable=False,
        comment='任务类型'
    )
    
    # 任务状态
    status = Column(
        SQLEnum('pending', 'running', 'completed', 'failed', 'cancelled', name='task_status'),
        default='pending',
        nullable=False,
        index=True,
        comment='任务状态'
    )
    
    # 任务参数
    stock_codes = Column(Text, nullable=True, comment='股票代码列表（JSON）')
    params = Column(Text, nullable=True, comment='其他参数（JSON）')
    
    # 进度
    total_count = Column(Integer, default=0, comment='总任务数')
    completed_count = Column(Integer, default=0, comment='已完成数')
    failed_count = Column(Integer, default=0, comment='失败数')
    progress = Column(Integer, default=0, comment='进度百分比')
    
    # 结果
    result = Column(Text, nullable=True, comment='任务结果（JSON）')
    error_message = Column(Text, nullable=True, comment='错误信息')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    started_at = Column(DateTime, nullable=True, comment='开始执行时间')
    completed_at = Column(DateTime, nullable=True, comment='完成时间')
    
    # 来源信息
    source_ip = Column(String(50), nullable=True, comment='来源IP')
    user_agent = Column(String(255), nullable=True, comment='用户代理')
    
    # 关联关系
    user = relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AnalysisTask(task_id={self.task_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'task_type': self.task_type,
            'status': self.status,
            'stock_codes': self.get_stock_codes(),
            'total_count': self.total_count,
            'completed_count': self.completed_count,
            'failed_count': self.failed_count,
            'progress': self.progress,
            'result': self.get_result(),
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def get_stock_codes(self) -> List[str]:
        """获取股票代码列表"""
        if self.stock_codes:
            try:
                return json.loads(self.stock_codes)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_stock_codes(self, codes: List[str]):
        """设置股票代码列表"""
        self.stock_codes = json.dumps(codes, ensure_ascii=False)
    
    def get_params(self) -> Dict[str, Any]:
        """获取任务参数"""
        if self.params:
            try:
                return json.loads(self.params)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_params(self, params: Dict[str, Any]):
        """设置任务参数"""
        self.params = json.dumps(params, ensure_ascii=False)
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        if self.result:
            try:
                return json.loads(self.result)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_result(self, result: Dict[str, Any]):
        """设置任务结果"""
        self.result = json.dumps(result, ensure_ascii=False)
    
    def start(self):
        """开始任务"""
        self.status = 'running'
        self.started_at = datetime.now()
    
    def complete(self, result: Dict[str, Any] = None):
        """完成任务"""
        self.status = 'completed'
        self.completed_at = datetime.now()
        self.progress = 100
        if result:
            self.set_result(result)
    
    def fail(self, error_message: str):
        """任务失败"""
        self.status = 'failed'
        self.completed_at = datetime.now()
        self.error_message = error_message
    
    def update_progress(self, completed: int, failed: int = 0):
        """更新进度"""
        self.completed_count = completed
        self.failed_count = failed
        if self.total_count > 0:
            self.progress = int((completed + failed) / self.total_count * 100)


class UserWatchlist(Base):
    """
    用户自选股表
    
    记录用户关注的股票
    """
    __tablename__ = 'user_watchlists'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='用户ID')
    
    # 股票信息
    stock_code = Column(String(10), nullable=False, index=True, comment='股票代码')
    stock_name = Column(String(50), nullable=True, comment='股票名称')
    
    # 分组
    group_name = Column(String(50), default='默认分组', comment='分组名称')
    
    # 排序
    sort_order = Column(Integer, default=0, comment='排序顺序')
    
    # 备注
    remark = Column(String(255), nullable=True, comment='备注')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='添加时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 唯一约束：同一用户不能重复添加同一股票
    __table_args__ = (
        UniqueConstraint('user_id', 'stock_code', name='uix_user_stock'),
        Index('ix_user_group', 'user_id', 'group_name'),
    )
    
    # 关联关系
    user = relationship('User', back_populates='watchlists', foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<UserWatchlist(user_id={self.user_id}, stock_code={self.stock_code})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'group_name': self.group_name,
            'sort_order': self.sort_order,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AnalysisHistory(Base):
    """
    分析历史记录表
    
    保存用户的分析历史结果
    """
    __tablename__ = 'analysis_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True, comment='用户ID')
    task_id = Column(String(64), nullable=True, index=True, comment='关联任务ID')
    
    # 股票信息
    stock_code = Column(String(10), nullable=False, index=True, comment='股票代码')
    stock_name = Column(String(50), nullable=True, comment='股票名称')
    
    # 分析日期
    analysis_date = Column(Date, nullable=False, index=True, comment='分析日期')
    
    # 分析结果
    market_data = Column(Text, nullable=True, comment='行情数据（JSON）')
    analysis_result = Column(Text, nullable=True, comment='分析结果（JSON）')
    ai_summary = Column(Text, nullable=True, comment='AI 分析摘要')
    
    # 评分（用于排序和筛选）
    score = Column(Integer, nullable=True, comment='分析评分')
    sentiment = Column(
        SQLEnum('bullish', 'neutral', 'bearish', name='sentiment_type'),
        nullable=True,
        comment='情绪判断'
    )
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 索引
    __table_args__ = (
        Index('ix_user_stock_date', 'user_id', 'stock_code', 'analysis_date'),
    )
    
    # 关联关系
    user = relationship('User', back_populates='analysis_history', foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AnalysisHistory(stock_code={self.stock_code}, date={self.analysis_date})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'market_data': self.get_market_data(),
            'analysis_result': self.get_analysis_result(),
            'ai_summary': self.ai_summary,
            'score': self.score,
            'sentiment': self.sentiment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_market_data(self) -> Optional[Dict[str, Any]]:
        """获取行情数据"""
        if self.market_data:
            try:
                return json.loads(self.market_data)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_market_data(self, data: Dict[str, Any]):
        """设置行情数据"""
        self.market_data = json.dumps(data, ensure_ascii=False)
    
    def get_analysis_result(self) -> Optional[Dict[str, Any]]:
        """获取分析结果"""
        if self.analysis_result:
            try:
                return json.loads(self.analysis_result)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_analysis_result(self, result: Dict[str, Any]):
        """设置分析结果"""
        self.analysis_result = json.dumps(result, ensure_ascii=False)
