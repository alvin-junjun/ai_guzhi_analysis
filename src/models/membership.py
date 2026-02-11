# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 会员模型

定义会员套餐、订单、用户会员关系、使用量统计相关的数据模型
"""

import json
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, Date,
    Numeric, Enum as SQLEnum, ForeignKey
)
from sqlalchemy.orm import relationship

from src.storage import Base


class MembershipPlan(Base):
    """
    会员套餐表
    
    定义不同级别的会员权益
    """
    __tablename__ = 'membership_plans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 套餐信息
    name = Column(String(50), nullable=False, comment='套餐名称')
    description = Column(String(255), nullable=True, comment='套餐描述')
    
    # 价格
    price = Column(Numeric(10, 2), nullable=False, comment='当前价格')
    original_price = Column(Numeric(10, 2), nullable=True, comment='原价')
    
    # 有效期
    duration_days = Column(Integer, nullable=False, comment='有效天数')
    
    # 权益配置
    daily_analysis_limit = Column(Integer, default=-1, comment='每日分析次数限制（-1表示不限）')
    watchlist_limit = Column(Integer, default=10, comment='自选股数量限制')
    features = Column(Text, nullable=True, comment='功能列表（JSON）')
    
    # 显示配置
    sort_order = Column(Integer, default=0, comment='排序顺序')
    is_active = Column(Boolean, default=True, comment='是否上架')
    is_recommended = Column(Boolean, default=False, comment='是否推荐')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def __repr__(self):
        return f"<MembershipPlan(id={self.id}, name={self.name})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price) if self.price else 0,
            'original_price': float(self.original_price) if self.original_price else None,
            'duration_days': self.duration_days,
            'daily_analysis_limit': self.daily_analysis_limit,
            'watchlist_limit': self.watchlist_limit,
            'features': self.get_features(),
            'is_recommended': self.is_recommended,
        }
    
    def get_features(self) -> List[str]:
        """获取功能列表"""
        if self.features:
            try:
                return json.loads(self.features)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_features(self, features: List[str]):
        """设置功能列表"""
        self.features = json.dumps(features, ensure_ascii=False)
    
    def has_unlimited_analysis(self) -> bool:
        """是否不限分析次数"""
        return self.daily_analysis_limit == -1


class Order(Base):
    """
    订单表
    
    记录会员购买订单
    """
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 订单信息
    order_no = Column(String(50), unique=True, nullable=False, index=True, comment='订单号')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='用户ID')
    plan_id = Column(Integer, ForeignKey('membership_plans.id'), nullable=False, comment='套餐ID')
    plan_name = Column(String(50), nullable=False, comment='套餐名称(冗余)')
    
    # 金额
    amount = Column(Numeric(10, 2), nullable=False, comment='订单金额')
    pay_amount = Column(Numeric(10, 2), nullable=False, comment='实付金额')
    discount_amount = Column(Numeric(10, 2), default=0, comment='优惠金额')
    
    # 支付信息
    payment_method = Column(String(20), default='wechat', comment='支付方式: wechat/alipay')
    payment_status = Column(String(20), default='pending', comment='支付状态: pending/paid/failed/refunded/closed')
    transaction_id = Column(String(100), nullable=True, comment='第三方交易号')
    prepay_id = Column(String(100), nullable=True, comment='预支付ID(微信)')
    qrcode_url = Column(String(500), nullable=True, comment='支付二维码URL')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    paid_at = Column(DateTime, nullable=True, comment='支付时间')
    expire_at = Column(DateTime, nullable=True, comment='订单过期时间')
    refund_at = Column(DateTime, nullable=True, comment='退款时间')
    
    # 备注
    remark = Column(String(500), nullable=True, comment='备注')
    refund_reason = Column(String(500), nullable=True, comment='退款原因')
    
    # 关联关系
    user = relationship('User', foreign_keys=[user_id])
    plan = relationship('MembershipPlan', foreign_keys=[plan_id])
    
    def __repr__(self):
        return f"<Order(order_no={self.order_no}, status={self.payment_status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'order_no': self.order_no,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'plan_name': self.plan_name,
            'amount': float(self.amount) if self.amount else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'pay_amount': float(self.pay_amount) if self.pay_amount else 0,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }
    
    def can_pay(self) -> bool:
        """是否可以支付"""
        if self.payment_status != 'pending':
            return False
        if self.expire_at and datetime.now() > self.expire_at:
            return False
        return True
    
    def mark_paid(self, payment_method: str, transaction_id: str = None):
        """标记为已支付"""
        self.payment_status = 'paid'
        self.payment_method = payment_method
        self.transaction_id = transaction_id
        self.paid_at = datetime.now()
    
    @classmethod
    def generate_order_no(cls) -> str:
        """生成订单号"""
        import secrets
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = secrets.token_hex(4).upper()
        return f"M{timestamp}{random_str}"


class UserMembership(Base):
    """
    用户会员关系表
    
    记录用户购买的会员及有效期
    """
    __tablename__ = 'user_memberships'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='用户ID')
    plan_id = Column(Integer, ForeignKey('membership_plans.id'), nullable=False, comment='套餐ID')
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True, comment='关联订单ID')
    
    # 有效期
    start_at = Column(DateTime, nullable=False, comment='开始时间')
    expire_at = Column(DateTime, nullable=False, comment='过期时间')
    
    # 状态
    status = Column(
        SQLEnum('active', 'expired', 'cancelled', name='membership_status'),
        default='active',
        nullable=False,
        comment='会员状态'
    )
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 关联关系
    user = relationship('User', back_populates='memberships', foreign_keys=[user_id])
    plan = relationship('MembershipPlan', foreign_keys=[plan_id])
    order = relationship('Order', foreign_keys=[order_id])
    
    def __repr__(self):
        return f"<UserMembership(user_id={self.user_id}, plan_id={self.plan_id})>"
    
    def is_valid(self) -> bool:
        """检查会员是否有效"""
        if self.status != 'active':
            return False
        if datetime.now() > self.expire_at:
            return False
        return True
    
    def days_remaining(self) -> int:
        """剩余天数"""
        if datetime.now() > self.expire_at:
            return 0
        delta = self.expire_at - datetime.now()
        return max(0, delta.days)


class DailyUsage(Base):
    """
    每日使用量统计表
    
    记录用户每日的分析次数等使用情况
    """
    __tablename__ = 'daily_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='用户ID')
    
    # 日期
    usage_date = Column(Date, nullable=False, index=True, comment='使用日期')
    
    # 使用量
    analysis_count = Column(Integer, default=0, comment='分析次数')
    watchlist_count = Column(Integer, default=0, comment='自选股操作次数')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 唯一约束
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )
    
    def __repr__(self):
        return f"<DailyUsage(user_id={self.user_id}, date={self.usage_date})>"
    
    def can_analyze(self, limit: int) -> bool:
        """检查是否可以继续分析"""
        if limit == -1:  # 不限次数
            return True
        return self.analysis_count < limit
    
    def increment_analysis(self):
        """增加分析次数"""
        self.analysis_count += 1
        self.updated_at = datetime.now()
