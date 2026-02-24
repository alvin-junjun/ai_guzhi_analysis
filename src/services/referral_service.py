# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 邀请分享服务

提供分享码、邀请关系、注册/充值奖励发放
"""

import logging
import secrets
from typing import Optional, Tuple, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.storage import get_db
from src.models.user import User, ReferralRecord
from src.models.system import SystemConfig

logger = logging.getLogger(__name__)

# 套餐名称 -> 配置键
PLAN_CONFIG_KEYS = {
    '周卡': 'referral_reward_weekly',
    '月卡': 'referral_reward_monthly',
    '季卡': 'referral_reward_quarterly',
    'yearly': 'referral_reward_quarterly',  # 年卡按季卡档位，可后续单独配置
}


class ReferralService:
    def __init__(self):
        self.db = get_db()

    def _get_config_int(self, key: str, default: int = 0) -> int:
        """从 system_configs 读取整型配置"""
        with self.db.get_session() as session:
            row = session.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            ).scalar_one_or_none()
            if row and row.config_value:
                try:
                    return int(row.config_value)
                except (ValueError, TypeError):
                    pass
        return default

    def get_referral_config(self) -> Dict[str, int]:
        """获取邀请相关配置（注册奖励、周/月/季卡充值奖励次数）"""
        return {
            'referral_registration_reward': self._get_config_int('referral_registration_reward', 10),
            'referral_reward_weekly': self._get_config_int('referral_reward_weekly', 30),
            'referral_reward_monthly': self._get_config_int('referral_reward_monthly', 100),
            'referral_reward_quarterly': self._get_config_int('referral_reward_quarterly', 300),
        }

    def get_or_create_share_code(self, user_id: int) -> Tuple[bool, str]:
        """
        获取或创建用户的分享码。
        Returns:
            (是否新创建, share_code)
        """
        with self.db.get_session() as session:
            user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if not user:
                return False, ''
            if user.share_code:
                return False, user.share_code
            # 生成唯一 share_code：R + 12 位字母数字
            for _ in range(10):
                code = 'R' + secrets.token_urlsafe(9).replace('-', '').replace('_', '')[:12]
                existing = session.execute(select(User).where(User.share_code == code)).scalar_one_or_none()
                if not existing:
                    user.share_code = code
                    session.commit()
                    logger.info(f"为用户 {user_id} 生成分享码: {code}")
                    return True, code
            return False, ''

    def get_referrer_id_by_share_code(self, share_code: str) -> Optional[int]:
        """根据分享码解析邀请人 user_id，无效返回 None"""
        if not share_code or not share_code.strip():
            return None
        share_code = share_code.strip()
        with self.db.get_session() as session:
            user_id = session.execute(
                select(User.id).where(User.share_code == share_code, User.status == 'active')
            ).scalar_one_or_none()
            return user_id

    def create_referral_record(
        self,
        session: Session,
        referrer_id: int,
        referred_user_id: int
    ) -> ReferralRecord:
        """创建邀请记录（在已有 session 内，由注册流程调用）"""
        record = ReferralRecord(
            referrer_id=referrer_id,
            referred_user_id=referred_user_id,
            registration_reward_given=False,
            subscription_reward_given=False,
        )
        session.add(record)
        return record

    def grant_registration_reward(self, referrer_id: int, referred_user_id: int) -> Tuple[bool, str]:
        """
        发放「被邀请人注册成功」奖励：给邀请人增加免费使用次数。
        仅当 referral_record 存在且 registration_reward_given=False 时发放。
        """
        config = self.get_referral_config()
        reward = config.get('referral_registration_reward', 10)
        if reward <= 0:
            return True, '未配置注册奖励'

        with self.db.get_session() as session:
            record = session.execute(
                select(ReferralRecord).where(
                    ReferralRecord.referrer_id == referrer_id,
                    ReferralRecord.referred_user_id == referred_user_id,
                )
            ).scalar_one_or_none()
            if not record:
                return False, '邀请记录不存在'
            if record.registration_reward_given:
                return True, '已发放过注册奖励'

            referrer = session.execute(select(User).where(User.id == referrer_id)).scalar_one_or_none()
            if not referrer:
                return False, '邀请人不存在'
            referrer.referral_bonus_balance = (referrer.referral_bonus_balance or 0) + reward
            record.registration_reward_given = True
            session.commit()
            logger.info(f"邀请注册奖励: referrer_id={referrer_id}, referred_id={referred_user_id}, +{reward}")
            return True, f'已发放{reward}次免费使用'

    def grant_subscription_reward(
        self,
        referrer_id: int,
        referred_user_id: int,
        plan_name: str
    ) -> Tuple[bool, str]:
        """
        发放「被邀请人充值成功」奖励：按周卡/月卡/季卡给邀请人不同次数。
        仅当 referral_record 存在且 subscription_reward_given=False 时发放。
        """
        config = self.get_referral_config()
        key = PLAN_CONFIG_KEYS.get(plan_name)
        if not key:
            return True, '未配置该套餐奖励'
        reward = config.get(key, 0)
        if reward <= 0:
            return True, '未配置充值奖励'

        with self.db.get_session() as session:
            record = session.execute(
                select(ReferralRecord).where(
                    ReferralRecord.referrer_id == referrer_id,
                    ReferralRecord.referred_user_id == referred_user_id,
                )
            ).scalar_one_or_none()
            if not record:
                return False, '邀请记录不存在'
            if record.subscription_reward_given:
                return True, '已发放过充值奖励'

            referrer = session.execute(select(User).where(User.id == referrer_id)).scalar_one_or_none()
            if not referrer:
                return False, '邀请人不存在'

            plan_type = 'weekly' if '周' in plan_name else 'monthly' if '月' in plan_name else 'quarterly'
            referrer.referral_bonus_balance = (referrer.referral_bonus_balance or 0) + reward
            record.subscription_reward_given = True
            record.subscription_plan_type = plan_type
            session.commit()
            logger.info(f"邀请充值奖励: referrer_id={referrer_id}, referred_id={referred_user_id}, plan={plan_name}, +{reward}")
            return True, f'已发放{reward}次免费使用'


def get_referral_service() -> ReferralService:
    return ReferralService()
