# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 会员服务

提供会员套餐管理、订单处理、会员状态管理等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, and_

from src.config import get_config
from src.storage import get_db
from src.models.user import User
from src.models.membership import MembershipPlan, Order, UserMembership
from src.models.system import SystemConfig

logger = logging.getLogger(__name__)


class MembershipService:
    """
    会员服务
    
    职责：
    1. 会员套餐管理
    2. 订单创建和处理
    3. 会员状态管理
    4. 权益查询
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = get_db()
    
    # === 套餐管理 ===
    
    def get_active_plans(self) -> List[Dict[str, Any]]:
        """获取所有上架的会员套餐"""
        with self.db.get_session() as session:
            results = session.execute(
                select(MembershipPlan)
                .where(MembershipPlan.is_active == True)
                .order_by(MembershipPlan.sort_order)
            ).scalars().all()
            
            return [plan.to_dict() for plan in results]
    
    def get_plan_by_id(self, plan_id: int) -> Optional[MembershipPlan]:
        """根据 ID 获取套餐"""
        with self.db.get_session() as session:
            return session.execute(
                select(MembershipPlan).where(MembershipPlan.id == plan_id)
            ).scalar_one_or_none()
    
    # === 订单管理 ===
    
    def create_order(
        self,
        user_id: int,
        plan_id: int,
        discount_amount: float = 0
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        创建会员订单
        
        Args:
            user_id: 用户 ID
            plan_id: 套餐 ID
            discount_amount: 优惠金额
            
        Returns:
            (是否成功, 消息, 订单信息)
        """
        with self.db.get_session() as session:
            # 检查套餐
            plan = session.execute(
                select(MembershipPlan).where(MembershipPlan.id == plan_id)
            ).scalar_one_or_none()
            
            if not plan or not plan.is_active:
                return False, '套餐不存在或已下架', None
            
            # 计算金额
            amount = float(plan.price)
            pay_amount = max(0, amount - discount_amount)
            
            # 创建订单
            order = Order(
                order_no=Order.generate_order_no(),
                user_id=user_id,
                plan_id=plan_id,
                plan_name=plan.name,
                amount=amount,
                discount_amount=discount_amount,
                pay_amount=pay_amount,
                payment_status='pending',
                expire_at=datetime.now() + timedelta(hours=2),  # 2小时过期
            )
            session.add(order)
            session.commit()
            session.refresh(order)
            
            logger.info(f"创建订单: order_no={order.order_no}, user_id={user_id}")
            return True, '订单创建成功', order.to_dict()
    
    def get_order_by_no(self, order_no: str) -> Optional[Order]:
        """根据订单号获取订单"""
        with self.db.get_session() as session:
            return session.execute(
                select(Order).where(Order.order_no == order_no)
            ).scalar_one_or_none()
    
    def get_user_orders(
        self,
        user_id: int,
        status: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户订单列表"""
        with self.db.get_session() as session:
            query = select(Order).where(Order.user_id == user_id)
            
            if status:
                query = query.where(Order.payment_status == status)
            
            query = query.order_by(Order.created_at.desc()).limit(limit)
            
            results = session.execute(query).scalars().all()
            return [order.to_dict() for order in results]
    
    def process_payment(
        self,
        order_no: str,
        pay_channel: str,  # 兼容旧参数名
        trade_no: str = None
    ) -> Tuple[bool, str]:
        """
        处理支付回调
        
        Args:
            order_no: 订单号
            pay_channel: 支付方式 (wechat/alipay/manual)
            trade_no: 第三方交易号
            
        Returns:
            (是否成功, 消息)
        """
        with self.db.get_session() as session:
            order = session.execute(
                select(Order).where(Order.order_no == order_no)
            ).scalar_one_or_none()
            
            if not order:
                return False, '订单不存在'
            
            if order.payment_status == 'paid':
                return True, '订单已支付'
            
            if not order.can_pay():
                return False, '订单已过期或无法支付'
            
            # 更新订单状态
            order.mark_paid(pay_channel, trade_no)  # mark_paid 内部会设置 payment_method 和 transaction_id
            
            # 获取套餐信息
            plan = session.execute(
                select(MembershipPlan).where(MembershipPlan.id == order.plan_id)
            ).scalar_one_or_none()
            
            if not plan:
                return False, '套餐信息异常'
            
            # 开通会员
            success, msg = self._activate_membership(
                session, order.user_id, plan, order.id
            )
            
            if success:
                # 邀请充值奖励：在 commit 前读取被邀请人的 referrer_id 与套餐名
                buyer_id = order.user_id
                plan_name = plan.name
                user = session.execute(
                    select(User).where(User.id == buyer_id)
                ).scalar_one_or_none()
                referrer_id = getattr(user, 'referrer_id', None) if user else None
                session.commit()
                logger.info(f"订单支付成功: order_no={order_no}")
                if referrer_id:
                    from src.services.referral_service import get_referral_service
                    get_referral_service().grant_subscription_reward(
                        referrer_id, buyer_id, plan_name
                    )
                return True, '支付成功，会员已开通'
            else:
                session.rollback()
                return False, msg
    
    def manual_activate(
        self,
        user_id: int,
        plan_id: int,
        remark: str = None
    ) -> Tuple[bool, str]:
        """
        手动开通会员（管理员功能）
        
        Args:
            user_id: 用户 ID
            plan_id: 套餐 ID
            remark: 备注
            
        Returns:
            (是否成功, 消息)
        """
        with self.db.get_session() as session:
            plan = session.execute(
                select(MembershipPlan).where(MembershipPlan.id == plan_id)
            ).scalar_one_or_none()
            
            if not plan:
                return False, '套餐不存在'
            
            # 创建内部订单
            order = Order(
                order_no=Order.generate_order_no(),
                user_id=user_id,
                plan_id=plan_id,
                plan_name=plan.name,
                amount=0,
                discount_amount=float(plan.price),
                pay_amount=0,
                payment_status='paid',
                payment_method='manual',
                paid_at=datetime.now(),
                remark=remark or '管理员手动开通',
            )
            session.add(order)
            session.flush()
            
            # 开通会员
            success, msg = self._activate_membership(
                session, user_id, plan, order.id
            )
            
            if success:
                session.commit()
                logger.info(f"手动开通会员: user_id={user_id}, plan={plan.name}")
                return True, '会员开通成功'
            else:
                session.rollback()
                return False, msg
    
    # === 会员状态 ===
    
    def get_user_membership(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户当前有效会员"""
        with self.db.get_session() as session:
            membership = session.execute(
                select(UserMembership)
                .where(
                    and_(
                        UserMembership.user_id == user_id,
                        UserMembership.status == 'active',
                        UserMembership.expire_at > datetime.now()
                    )
                )
                .order_by(UserMembership.expire_at.desc())
            ).scalar_one_or_none()
            
            if not membership:
                return None
            
            # 获取套餐信息
            plan = session.execute(
                select(MembershipPlan).where(MembershipPlan.id == membership.plan_id)
            ).scalar_one_or_none()
            
            return {
                'membership_id': membership.id,
                'plan_id': membership.plan_id,
                'plan_name': plan.name if plan else '未知套餐',
                'start_at': membership.start_at.isoformat(),
                'expire_at': membership.expire_at.isoformat(),
                'days_remaining': membership.days_remaining(),
                'daily_analysis_limit': plan.daily_analysis_limit if plan else 5,
                'watchlist_limit': plan.watchlist_limit if plan else 10,
            }
    
    def get_user_benefits(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户当前权益
        
        优先从 user_memberships 表读取；若无有效记录则回退到 users 表的
        membership_level / membership_expire，保证与数据库一致。
        
        Returns:
            {
                'level': 'free' | 'vip',
                'plan_name': str,
                'daily_analysis_limit': int (-1 表示不限),
                'watchlist_limit': int,
                'expire_at': str | None,
                'days_remaining': int,
            }
        """
        membership = self.get_user_membership(user_id)
        
        if membership:
            return {
                'level': 'vip',
                'plan_name': membership['plan_name'],
                'daily_analysis_limit': membership['daily_analysis_limit'],
                'watchlist_limit': membership['watchlist_limit'],
                'expire_at': membership['expire_at'],
                'days_remaining': membership['days_remaining'],
            }
        
        # 无 user_memberships 记录时，回退到 users 表的会员等级与过期时间
        with self.db.get_session() as session:
            user = session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            if user and user.is_membership_valid():
                expire_at = user.membership_expire
                expire_str = expire_at.isoformat() if expire_at else None
                days_remaining = None if expire_at is None else max(0, (expire_at - datetime.now()).days)
                plan_name = self._membership_level_to_plan_name(user.membership_level)
                return {
                    'level': 'vip',
                    'plan_name': plan_name,
                    'daily_analysis_limit': -1,
                    'watchlist_limit': 200,
                    'expire_at': expire_str,
                    'days_remaining': days_remaining,
                }
        
        # 免费用户
        return {
            'level': 'free',
            'plan_name': '免费版',
            'daily_analysis_limit': self._get_system_config('free_daily_limit', self.config.free_daily_limit),
            'watchlist_limit': self._get_system_config('free_watchlist_limit', self.config.free_watchlist_limit),
            'expire_at': None,
            'days_remaining': 0,
        }
    
    def _membership_level_to_plan_name(self, level: str) -> str:
        """将 users.membership_level 枚举转为页面显示的套餐名称"""
        name_map = {
            'weekly': '周卡',
            'monthly': '月卡',
            'quarterly': '季卡',
            'yearly': '年卡',
        }
        return name_map.get(level, '会员') if level and level != 'free' else '免费版'
    
    def _get_system_config(self, key: str, default: int) -> int:
        """
        从数据库获取系统配置值
        
        优先从 system_configs 表读取，没有则返回默认值
        
        Args:
            key: 配置键名
            default: 默认值（通常从 env 配置获取）
            
        Returns:
            配置值
        """
        try:
            with self.db.get_session() as session:
                config = session.execute(
                    select(SystemConfig).where(SystemConfig.config_key == key)
                ).scalar_one_or_none()
                
                if config and config.config_value:
                    return config.get_int_value(default)
        except Exception as e:
            logger.warning(f"获取系统配置失败 key={key}: {e}")
        
        return default
    
    # === 辅助方法 ===
    
    def _activate_membership(
        self,
        session,
        user_id: int,
        plan: MembershipPlan,
        order_id: int
    ) -> Tuple[bool, str]:
        """
        激活会员
        
        处理逻辑：
        - 如果已有会员，延长有效期
        - 如果没有会员，创建新会员
        """
        try:
            now = datetime.now()
            
            # 检查是否已有有效会员
            existing = session.execute(
                select(UserMembership)
                .where(
                    and_(
                        UserMembership.user_id == user_id,
                        UserMembership.status == 'active',
                        UserMembership.expire_at > now
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                # 延长有效期
                new_expire = existing.expire_at + timedelta(days=plan.duration_days)
                existing.expire_at = new_expire
                start_at = existing.start_at
            else:
                # 创建新会员记录
                start_at = now
                new_expire = now + timedelta(days=plan.duration_days)
                
                membership = UserMembership(
                    user_id=user_id,
                    plan_id=plan.id,
                    order_id=order_id,
                    start_at=start_at,
                    expire_at=new_expire,
                    status='active',
                )
                session.add(membership)
            
            # 更新用户会员等级（冗余字段）
            user = session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            
            if user:
                # 根据套餐名称设置会员等级
                level_map = {
                    '周卡': 'weekly',
                    '月卡': 'monthly',
                    '季卡': 'quarterly',
                    '年卡': 'yearly',
                }
                user.membership_level = level_map.get(plan.name, 'monthly')
                user.membership_expire = new_expire
            
            return True, '会员开通成功'
            
        except Exception as e:
            logger.error(f"激活会员失败: {e}")
            return False, str(e)
    
    def check_expired_memberships(self) -> int:
        """
        检查并处理过期会员
        
        Returns:
            处理的过期会员数量
        """
        with self.db.get_session() as session:
            # 查找过期的会员记录
            expired = session.execute(
                select(UserMembership)
                .where(
                    and_(
                        UserMembership.status == 'active',
                        UserMembership.expire_at < datetime.now()
                    )
                )
            ).scalars().all()
            
            count = 0
            for membership in expired:
                membership.status = 'expired'
                
                # 更新用户冗余字段
                user = session.execute(
                    select(User).where(User.id == membership.user_id)
                ).scalar_one_or_none()
                
                if user:
                    # 检查是否还有其他有效会员
                    other_valid = session.execute(
                        select(UserMembership)
                        .where(
                            and_(
                                UserMembership.user_id == user.id,
                                UserMembership.status == 'active',
                                UserMembership.expire_at > datetime.now(),
                                UserMembership.id != membership.id
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if not other_valid:
                        user.membership_level = 'free'
                        user.membership_expire = None
                
                count += 1
            
            session.commit()
            
            if count > 0:
                logger.info(f"处理过期会员: {count} 条")
            
            return count


# 便捷函数
def get_membership_service() -> MembershipService:
    """获取会员服务实例"""
    return MembershipService()
