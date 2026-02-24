# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 用户模型

定义用户、验证码、会话相关的数据模型
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, Enum as SQLEnum, ForeignKey
)
from sqlalchemy.orm import relationship

from src.storage import Base


class User(Base):
    """
    用户表
    
    支持手机号/QQ邮箱两种注册方式
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 用户唯一标识
    uuid = Column(String(36), unique=True, nullable=False, index=True, comment='用户UUID')
    
    # 登录凭证（二选一）
    phone = Column(String(20), unique=True, nullable=True, index=True, comment='手机号')
    email = Column(String(100), unique=True, nullable=True, index=True, comment='QQ邮箱')
    
    # 用户信息
    nickname = Column(String(50), nullable=True, comment='昵称')
    avatar = Column(String(255), nullable=True, comment='头像URL')
    
    # 密码（可选，未来扩展用）
    password_hash = Column(String(128), nullable=True, comment='密码哈希')
    
    # 状态
    status = Column(
        SQLEnum('active', 'disabled', 'deleted', name='user_status'),
        default='active',
        nullable=False,
        comment='用户状态'
    )
    
    # 会员等级（冗余字段，便于快速查询）
    membership_level = Column(
        SQLEnum('free', 'weekly', 'monthly', 'quarterly', 'yearly', name='membership_level'),
        default='free',
        nullable=False,
        comment='会员等级'
    )
    membership_expire = Column(DateTime, nullable=True, comment='会员过期时间')
    
    # 统计字段
    total_analysis_count = Column(Integer, default=0, comment='累计分析次数')
    last_login_at = Column(DateTime, nullable=True, comment='最后登录时间')
    last_login_ip = Column(String(50), nullable=True, comment='最后登录IP')
    
    # 邀请相关
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True, comment='邀请人用户ID')
    referral_bonus_balance = Column(Integer, default=0, nullable=False, comment='邀请奖励的免费使用次数余额')
    share_code = Column(String(32), unique=True, nullable=True, index=True, comment='分享码，用于生成邀请链接')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关联关系
    referrer = relationship('User', remote_side='User.id', foreign_keys=[referrer_id])
    sessions = relationship('UserSession', back_populates='user', lazy='dynamic')
    memberships = relationship('UserMembership', back_populates='user', lazy='dynamic')
    watchlists = relationship('UserWatchlist', back_populates='user', lazy='dynamic')
    analysis_history = relationship('AnalysisHistory', back_populates='user', lazy='dynamic')
    
    def __repr__(self):
        identifier = self.phone or self.email or self.uuid
        return f"<User(id={self.id}, identifier={identifier})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（隐藏敏感信息）"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'phone': self._mask_phone(self.phone) if self.phone else None,
            'email': self._mask_email(self.email) if self.email else None,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'status': self.status,
            'membership_level': self.membership_level,
            'membership_expire': self.membership_expire.isoformat() if self.membership_expire else None,
            'total_analysis_count': self.total_analysis_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def is_membership_valid(self) -> bool:
        """检查会员是否有效。非 free 等级且未过期（或未填过期时间视为长期有效）即有效。"""
        if self.membership_level == 'free':
            return False
        if self.membership_expire is None:
            return True  # 未填过期时间视为长期有效，与等级一致
        return self.membership_expire > datetime.now()
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        if self.nickname:
            return self.nickname
        if self.phone:
            return self._mask_phone(self.phone)
        if self.email:
            return self._mask_email(self.email)
        return f"用户{self.id}"
    
    @staticmethod
    def _mask_phone(phone: str) -> str:
        """手机号脱敏：138****1234"""
        if len(phone) >= 11:
            return f"{phone[:3]}****{phone[-4:]}"
        return phone
    
    @staticmethod
    def _mask_email(email: str) -> str:
        """邮箱脱敏：ab***@qq.com"""
        if '@' in email:
            local, domain = email.split('@', 1)
            if len(local) > 2:
                return f"{local[:2]}***@{domain}"
            return f"{local}***@{domain}"
        return email
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希（简单实现，生产建议使用 bcrypt）"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        if not self.password_hash:
            return False
        return self.password_hash == self.hash_password(password)


class VerificationCode(Base):
    """
    验证码表
    
    支持手机短信验证码和邮箱验证码
    """
    __tablename__ = 'verification_codes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 目标（手机号或邮箱）
    target = Column(String(100), nullable=False, index=True, comment='手机号或邮箱')
    target_type = Column(
        SQLEnum('phone', 'email', name='verification_target_type'),
        nullable=False,
        comment='目标类型'
    )
    
    # 验证码
    code = Column(String(10), nullable=False, comment='验证码')
    
    # 用途
    purpose = Column(
        SQLEnum('register', 'login', 'reset_password', 'bind', name='verification_purpose'),
        default='login',
        nullable=False,
        comment='验证码用途'
    )
    
    # 状态
    is_used = Column(Boolean, default=False, comment='是否已使用')
    used_at = Column(DateTime, nullable=True, comment='使用时间')
    
    # 过期时间
    expire_at = Column(DateTime, nullable=False, comment='过期时间')
    
    # 发送信息
    ip_address = Column(String(50), nullable=True, comment='请求IP')
    user_agent = Column(String(255), nullable=True, comment='用户代理')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    def __repr__(self):
        return f"<VerificationCode(target={self.target}, code={self.code})>"
    
    def is_valid(self) -> bool:
        """检查验证码是否有效"""
        if self.is_used:
            return False
        if datetime.now() > self.expire_at:
            return False
        return True
    
    def mark_used(self):
        """标记为已使用"""
        self.is_used = True
        self.used_at = datetime.now()
    
    @classmethod
    def generate_code(cls, length: int = 6) -> str:
        """生成随机验证码"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


class UserSession(Base):
    """
    用户会话表
    
    管理用户登录状态，支持多端登录
    """
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联用户
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='用户ID')
    
    # Session 凭证
    session_token = Column(String(128), unique=True, nullable=False, index=True, comment='Session Token')
    
    # 设备信息
    device_type = Column(
        SQLEnum('web', 'mobile', 'api', name='device_type'),
        default='web',
        comment='设备类型'
    )
    device_info = Column(String(255), nullable=True, comment='设备信息')
    ip_address = Column(String(50), nullable=True, comment='登录IP')
    user_agent = Column(Text, nullable=True, comment='用户代理')
    
    # 过期时间
    expire_at = Column(DateTime, nullable=False, comment='过期时间')
    
    # 状态
    is_active = Column(Boolean, default=True, comment='是否有效')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    last_active_at = Column(DateTime, default=datetime.now, comment='最后活跃时间')
    
    # 关联关系
    user = relationship('User', back_populates='sessions')
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, token={self.session_token[:8]}...)>"
    
    def is_valid(self) -> bool:
        """检查会话是否有效"""
        if not self.is_active:
            return False
        if datetime.now() > self.expire_at:
            return False
        return True
    
    def refresh(self, hours: int = 24):
        """刷新会话有效期"""
        self.expire_at = datetime.now() + timedelta(hours=hours)
        self.last_active_at = datetime.now()
    
    def invalidate(self):
        """使会话失效"""
        self.is_active = False
    
    @classmethod
    def generate_token(cls) -> str:
        """生成随机 Session Token"""
        return secrets.token_urlsafe(64)


class ReferralRecord(Base):
    """
    邀请记录表
    
    记录谁邀请了谁，以及注册奖励、充值奖励是否已发放
    """
    __tablename__ = 'referral_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='邀请人用户ID')
    referred_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='被邀请人用户ID')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    registration_reward_given = Column(Boolean, default=False, nullable=False, comment='是否已发放注册奖励')
    subscription_reward_given = Column(Boolean, default=False, nullable=False, comment='是否已发放充值奖励')
    subscription_plan_type = Column(String(20), nullable=True, comment='充值套餐类型: weekly/monthly/quarterly')

    referrer = relationship('User', foreign_keys=[referrer_id])
    referred_user = relationship('User', foreign_keys=[referred_user_id])
