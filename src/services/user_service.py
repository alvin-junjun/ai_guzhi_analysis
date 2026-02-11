# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 用户服务

提供用户信息管理、自选股管理、使用量统计等功能
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, and_, func, delete

from src.config import get_config
from src.storage import get_db
from src.models.user import User
from src.models.task import UserWatchlist, AnalysisHistory
from src.models.membership import DailyUsage
from src.models.system import SystemConfig

logger = logging.getLogger(__name__)


class UserService:
    """
    用户服务
    
    职责：
    1. 用户信息查询和更新
    2. 自选股管理
    3. 分析历史查询
    4. 使用量统计
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = get_db()
    
    # === 用户信息 ===
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        with self.db.get_session() as session:
            return session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
    
    def get_user_by_uuid(self, uuid: str) -> Optional[User]:
        """根据 UUID 获取用户"""
        with self.db.get_session() as session:
            return session.execute(
                select(User).where(User.uuid == uuid)
            ).scalar_one_or_none()
    
    def update_user_profile(
        self,
        user_id: int,
        nickname: str = None,
        avatar: str = None
    ) -> Tuple[bool, str]:
        """更新用户资料"""
        with self.db.get_session() as session:
            user = session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            
            if not user:
                return False, '用户不存在'
            
            if nickname is not None:
                user.nickname = nickname
            if avatar is not None:
                user.avatar = avatar
            
            session.commit()
            return True, '更新成功'
    
    # === 自选股管理 ===
    
    def get_watchlist(
        self,
        user_id: int,
        group_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户自选股列表
        
        Args:
            user_id: 用户 ID
            group_name: 分组名称（可选）
            
        Returns:
            自选股列表
        """
        with self.db.get_session() as session:
            query = select(UserWatchlist).where(UserWatchlist.user_id == user_id)
            
            if group_name:
                query = query.where(UserWatchlist.group_name == group_name)
            
            query = query.order_by(UserWatchlist.sort_order, UserWatchlist.created_at)
            
            results = session.execute(query).scalars().all()
            return [item.to_dict() for item in results]
    
    def get_watchlist_count(self, user_id: int) -> int:
        """获取用户自选股数量"""
        with self.db.get_session() as session:
            result = session.execute(
                select(func.count(UserWatchlist.id))
                .where(UserWatchlist.user_id == user_id)
            ).scalar()
            return result or 0
    
    def add_to_watchlist(
        self,
        user_id: int,
        stock_code: str,
        stock_name: str = None,
        group_name: str = '默认分组',
        remark: str = None
    ) -> Tuple[bool, str]:
        """
        添加自选股
        
        Args:
            user_id: 用户 ID
            stock_code: 股票代码
            stock_name: 股票名称
            group_name: 分组名称
            remark: 备注
            
        Returns:
            (是否成功, 消息)
        """
        with self.db.get_session() as session:
            # 检查是否已存在
            existing = session.execute(
                select(UserWatchlist)
                .where(
                    and_(
                        UserWatchlist.user_id == user_id,
                        UserWatchlist.stock_code == stock_code
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                return False, '该股票已在自选列表中'
            
            # 检查数量限制
            count = self.get_watchlist_count(user_id)
            user = self.get_user_by_id(user_id)
            limit = self._get_watchlist_limit(user)
            
            if count >= limit:
                return False, f'自选股数量已达上限（{limit}只）'
            
            # 添加自选股
            watchlist = UserWatchlist(
                user_id=user_id,
                stock_code=stock_code,
                stock_name=stock_name,
                group_name=group_name,
                remark=remark,
                sort_order=count,  # 新添加的排在最后
            )
            session.add(watchlist)
            session.commit()
            
            logger.info(f"添加自选股: user_id={user_id}, stock_code={stock_code}")
            return True, '添加成功'
    
    def remove_from_watchlist(
        self,
        user_id: int,
        stock_code: str
    ) -> Tuple[bool, str]:
        """
        删除自选股
        
        Args:
            user_id: 用户 ID
            stock_code: 股票代码
            
        Returns:
            (是否成功, 消息)
        """
        with self.db.get_session() as session:
            result = session.execute(
                delete(UserWatchlist)
                .where(
                    and_(
                        UserWatchlist.user_id == user_id,
                        UserWatchlist.stock_code == stock_code
                    )
                )
            )
            session.commit()
            
            if result.rowcount > 0:
                logger.info(f"删除自选股: user_id={user_id}, stock_code={stock_code}")
                return True, '删除成功'
            else:
                return False, '该股票不在自选列表中'
    
    def update_watchlist_order(
        self,
        user_id: int,
        stock_codes: List[str]
    ) -> bool:
        """
        更新自选股排序
        
        Args:
            user_id: 用户 ID
            stock_codes: 按新顺序排列的股票代码列表
            
        Returns:
            是否成功
        """
        with self.db.get_session() as session:
            for index, code in enumerate(stock_codes):
                session.execute(
                    select(UserWatchlist)
                    .where(
                        and_(
                            UserWatchlist.user_id == user_id,
                            UserWatchlist.stock_code == code
                        )
                    )
                ).scalar_one_or_none()
                
                # 直接更新 sort_order
                watchlist = session.execute(
                    select(UserWatchlist)
                    .where(
                        and_(
                            UserWatchlist.user_id == user_id,
                            UserWatchlist.stock_code == code
                        )
                    )
                ).scalar_one_or_none()
                
                if watchlist:
                    watchlist.sort_order = index
            
            session.commit()
            return True
    
    def get_watchlist_groups(self, user_id: int) -> List[str]:
        """获取用户的自选股分组"""
        with self.db.get_session() as session:
            results = session.execute(
                select(UserWatchlist.group_name)
                .where(UserWatchlist.user_id == user_id)
                .distinct()
            ).scalars().all()
            return list(results)
    
    # === 分析历史 ===
    
    def get_analysis_history(
        self,
        user_id: int,
        stock_code: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取分析历史
        
        Args:
            user_id: 用户 ID
            stock_code: 股票代码（可选）
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            分析历史列表
        """
        with self.db.get_session() as session:
            query = select(AnalysisHistory).where(AnalysisHistory.user_id == user_id)
            
            if stock_code:
                query = query.where(AnalysisHistory.stock_code == stock_code)
            
            query = query.order_by(AnalysisHistory.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            results = session.execute(query).scalars().all()
            return [item.to_dict() for item in results]
    
    def save_analysis_history(
        self,
        user_id: int,
        stock_code: str,
        stock_name: str,
        analysis_date: date,
        market_data: Dict[str, Any] = None,
        analysis_result: Dict[str, Any] = None,
        ai_summary: str = None,
        score: int = None,
        sentiment: str = None,
        task_id: str = None
    ) -> int:
        """
        保存分析历史
        
        Args:
            user_id: 用户 ID
            stock_code: 股票代码
            stock_name: 股票名称
            analysis_date: 分析日期
            market_data: 行情数据
            analysis_result: 分析结果
            ai_summary: AI 摘要
            score: 评分
            sentiment: 情绪判断
            task_id: 关联任务 ID
            
        Returns:
            历史记录 ID
        """
        with self.db.get_session() as session:
            history = AnalysisHistory(
                user_id=user_id,
                task_id=task_id,
                stock_code=stock_code,
                stock_name=stock_name,
                analysis_date=analysis_date,
                ai_summary=ai_summary,
                score=score,
                sentiment=sentiment,
            )
            
            if market_data:
                history.set_market_data(market_data)
            if analysis_result:
                history.set_analysis_result(analysis_result)
            
            session.add(history)
            session.commit()
            
            return history.id
    
    # === 使用量统计 ===
    
    def get_today_usage(self, user_id: int) -> DailyUsage:
        """获取用户今日使用量"""
        today = date.today()
        
        with self.db.get_session() as session:
            usage = session.execute(
                select(DailyUsage)
                .where(
                    and_(
                        DailyUsage.user_id == user_id,
                        DailyUsage.usage_date == today
                    )
                )
            ).scalar_one_or_none()
            
            if not usage:
                # 创建今日记录
                usage = DailyUsage(
                    user_id=user_id,
                    usage_date=today,
                    analysis_count=0,
                )
                session.add(usage)
                session.commit()
                session.refresh(usage)
            
            return usage
    
    def check_analysis_limit(self, user_id: int) -> Tuple[bool, int, int]:
        """
        检查用户今日分析次数限制
        
        使用 daily_usage 表的 analysis_count 字段进行判断
        
        Args:
            user_id: 用户 ID
            
        Returns:
            (是否可继续, 已使用次数, 限制次数)
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False, 0, 0
        
        limit = self._get_daily_analysis_limit(user)
        
        # 从 daily_usage 表获取今日使用量
        usage = self.get_today_usage(user_id)
        today_count = usage.analysis_count
        
        # 会员不限次数
        if limit == -1:
            return True, today_count, limit
        
        can_continue = today_count < limit
        return can_continue, today_count, limit
    
    def increment_analysis_count(self, user_id: int) -> int:
        """
        增加用户今日分析次数
        
        Args:
            user_id: 用户 ID
            
        Returns:
            当前分析次数
        """
        analysis_count = 0
        
        # 第一步：更新 daily_usage 表（核心操作，必须成功）
        try:
            with self.db.get_session() as session:
                today = date.today()
                
                usage = session.execute(
                    select(DailyUsage)
                    .where(
                        and_(
                            DailyUsage.user_id == user_id,
                            DailyUsage.usage_date == today
                        )
                    )
                ).scalar_one_or_none()
                
                if not usage:
                    usage = DailyUsage(
                        user_id=user_id,
                        usage_date=today,
                        analysis_count=1,
                    )
                    session.add(usage)
                else:
                    usage.increment_analysis()
                
                session.commit()
                analysis_count = usage.analysis_count
                logger.info(f"更新用户 {user_id} 今日分析次数: {analysis_count}")
        except Exception as e:
            logger.error(f"更新 daily_usage 失败 user_id={user_id}: {e}")
            raise
        
        # 第二步：更新用户累计分析次数（可选操作，失败不影响主流程）
        try:
            with self.db.get_session() as session:
                user = session.execute(
                    select(User).where(User.id == user_id)
                ).scalar_one_or_none()
                if user:
                    user.total_analysis_count = (user.total_analysis_count or 0) + 1
                    session.commit()
        except Exception as e:
            # 用户表更新失败不影响主流程，只记录日志
            logger.warning(f"更新用户累计分析次数失败 user_id={user_id}: {e}")
        
        return analysis_count
    
    # === 辅助方法 ===
    
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
    
    def _get_daily_analysis_limit(self, user: User) -> int:
        """获取用户每日分析次数限制"""
        if user.is_membership_valid():
            # TODO: 从会员套餐获取限制
            return -1  # 会员不限次数
        # 优先从数据库获取，没有则从 env 配置获取
        return self._get_system_config('free_daily_limit', self.config.free_daily_limit)
    
    def _get_watchlist_limit(self, user: User) -> int:
        """获取用户自选股数量限制"""
        if user.is_membership_valid():
            # TODO: 从会员套餐获取限制
            return 200  # 会员上限
        # 优先从数据库获取，没有则从 env 配置获取
        return self._get_system_config('free_watchlist_limit', self.config.free_watchlist_limit)
    
    def get_free_daily_limit(self) -> int:
        """获取免费用户每日分析次数限制（公开方法）"""
        return self._get_system_config('free_daily_limit', self.config.free_daily_limit)
    
    def get_free_watchlist_limit(self) -> int:
        """获取免费用户自选股数量限制（公开方法）"""
        return self._get_system_config('free_watchlist_limit', self.config.free_watchlist_limit)


# 便捷函数
def get_user_service() -> UserService:
    """获取用户服务实例"""
    return UserService()
