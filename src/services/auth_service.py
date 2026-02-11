# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 鉴权服务

提供用户注册、登录、验证码、Session 管理等功能
"""

import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from src.config import get_config
from src.storage import get_db
from src.models.user import User, VerificationCode, UserSession

logger = logging.getLogger(__name__)


class AuthService:
    """
    鉴权服务
    
    职责：
    1. 用户注册（手机号/邮箱）
    2. 验证码发送和校验
    3. Session 管理（登录/登出/验证）
    4. 白名单校验
    """
    
    # 手机号正则
    PHONE_PATTERN = re.compile(r'^1[3-9]\d{9}$')
    # QQ 邮箱正则
    EMAIL_PATTERN = re.compile(r'^[1-9]\d{4,10}@qq\.com$', re.IGNORECASE)
    
    def __init__(self):
        self.config = get_config()
        self.db = get_db()
    
    # === 验证码相关 ===
    
    def send_verification_code(
        self,
        target: str,
        purpose: str = 'login',
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        发送验证码
        
        Args:
            target: 手机号或邮箱
            purpose: 用途（register/login/reset_password/bind）
            ip_address: 请求 IP
            user_agent: 用户代理
            
        Returns:
            (是否成功, 消息, 验证码-仅开发环境返回)
        """
        # 1. 验证目标格式
        target_type = self._detect_target_type(target)
        if target_type is None:
            return False, '手机号或邮箱格式不正确', None
        
        # 2. 白名单检查
        if not self._check_whitelist(target, target_type):
            return False, '该手机号/邮箱不在允许注册范围内', None
        
        # 3. 检查发送频率
        with self.db.get_session() as session:
            recent_code = session.execute(
                select(VerificationCode)
                .where(
                    and_(
                        VerificationCode.target == target,
                        VerificationCode.created_at > datetime.now() - timedelta(seconds=60)
                    )
                )
                .order_by(VerificationCode.created_at.desc())
            ).scalar_one_or_none()
            
            if recent_code:
                wait_seconds = 60 - (datetime.now() - recent_code.created_at).seconds
                return False, f'请等待 {wait_seconds} 秒后重试', None
            
            # 4. 生成验证码
            code = VerificationCode.generate_code(self.config.verification_code_length)
            
            # 5. 保存验证码记录
            verification = VerificationCode(
                target=target,
                target_type=target_type,
                code=code,
                purpose=purpose,
                expire_at=datetime.now() + timedelta(minutes=self.config.verification_code_expire_minutes),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(verification)
            session.commit()
            
            # 6. 发送验证码（TODO: 接入实际的短信/邮件服务）
            success = self._do_send_code(target, target_type, code)
            
            if success:
                logger.info(f"验证码已发送: {target}")
                # 开发环境返回验证码便于测试
                dev_code = code if self.config.debug else None
                return True, '验证码已发送', dev_code
            else:
                return False, '验证码发送失败，请稍后重试', None
    
    def verify_code(
        self,
        target: str,
        code: str,
        purpose: str = 'login'
    ) -> Tuple[bool, str]:
        """
        验证验证码
        
        Args:
            target: 手机号或邮箱
            code: 验证码
            purpose: 用途
            
        Returns:
            (是否成功, 消息)
        """
        with self.db.get_session() as session:
            # 查找最近的未使用验证码
            verification = session.execute(
                select(VerificationCode)
                .where(
                    and_(
                        VerificationCode.target == target,
                        VerificationCode.purpose == purpose,
                        VerificationCode.is_used == False
                    )
                )
                .order_by(VerificationCode.created_at.desc())
            ).scalar_one_or_none()
            
            if not verification:
                return False, '验证码不存在或已过期'
            
            if not verification.is_valid():
                return False, '验证码已过期'
            
            if verification.code != code:
                return False, '验证码错误'
            
            # 标记为已使用
            verification.mark_used()
            session.commit()
            
            return True, '验证成功'
    
    # === 用户注册 ===
    
    def register_with_password(
        self,
        target: str,
        password: str,
        nickname: str = None,
        ip_address: str = None,
        email: str = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        密码注册（无需验证码）
        
        Args:
            target: 手机号或邮箱
            password: 密码
            nickname: 昵称（可选）
            ip_address: 注册 IP
            email: 接收报告的QQ邮箱（手机号注册时传入）
            
        Returns:
            (是否成功, 消息, 用户信息)
        """
        # 1. 验证目标格式
        target_type = self._detect_target_type(target)
        if target_type is None:
            return False, '手机号或邮箱格式不正确', None
        
        # 2. 白名单检查
        if not self._check_whitelist(target, target_type):
            return False, '该手机号/邮箱不在允许注册范围内', None
        
        # 3. 验证密码
        if not password or len(password) < 6:
            return False, '密码长度至少6位', None
        
        if len(password) > 32:
            return False, '密码长度不能超过32位', None
        
        # 4. 处理邮箱：手机号注册时必须提供邮箱，QQ邮箱注册时email就是target
        final_email = None
        if target_type == 'phone':
            # 手机号注册，必须提供QQ邮箱
            if not email:
                return False, '请填写接收报告的QQ邮箱', None
            if not self.EMAIL_PATTERN.match(email):
                return False, '请输入正确的QQ邮箱格式', None
            final_email = email.lower()  # 统一转小写
        else:
            # QQ邮箱注册，email就是target
            final_email = target.lower()
        
        with self.db.get_session() as session:
            # 5. 检查用户是否已存在
            existing = self._find_user_by_target(session, target, target_type)
            if existing:
                return False, '该手机号/邮箱已注册', None
            
            # 6. 检查邮箱是否已被其他用户使用（手机号注册时）
            if target_type == 'phone' and final_email:
                existing_email = session.execute(
                    select(User).where(User.email == final_email)
                ).scalar_one_or_none()
                if existing_email:
                    return False, '该QQ邮箱已被其他账号使用', None
            
            # 7. 创建用户
            user = User(
                uuid=str(uuid.uuid4()),
                phone=target if target_type == 'phone' else None,
                email=final_email,  # 统一保存邮箱
                password_hash=User.hash_password(password),
                nickname=nickname,
                status='active',
                membership_level='free',
                last_login_at=datetime.now(),
                last_login_ip=ip_address,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"新用户注册: {target}, 报告接收邮箱: {final_email}")
            return True, '注册成功', user.to_dict()
    
    def register(
        self,
        target: str,
        code: str,
        nickname: str = None,
        ip_address: str = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        用户注册（验证码方式，保留兼容）
        
        Args:
            target: 手机号或邮箱
            code: 验证码
            nickname: 昵称（可选）
            ip_address: 注册 IP
            
        Returns:
            (是否成功, 消息, 用户信息)
        """
        # 1. 验证码校验
        valid, msg = self.verify_code(target, code, 'register')
        if not valid:
            return False, msg, None
        
        target_type = self._detect_target_type(target)
        
        with self.db.get_session() as session:
            # 2. 检查用户是否已存在
            existing = self._find_user_by_target(session, target, target_type)
            if existing:
                return False, '该手机号/邮箱已注册', None
            
            # 3. 创建用户
            user = User(
                uuid=str(uuid.uuid4()),
                phone=target if target_type == 'phone' else None,
                email=target if target_type == 'email' else None,
                nickname=nickname,
                status='active',
                membership_level='free',
                last_login_at=datetime.now(),
                last_login_ip=ip_address,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"新用户注册: {target}")
            return True, '注册成功', user.to_dict()
    
    # === 登录相关 ===
    
    def login_with_password(
        self,
        target: str,
        password: str,
        device_type: str = 'web',
        device_info: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        密码登录
        
        Args:
            target: 手机号或邮箱
            password: 密码
            device_type: 设备类型
            device_info: 设备信息
            ip_address: 登录 IP
            user_agent: 用户代理
            
        Returns:
            (是否成功, 消息, {user, session_token})
        """
        # 1. 验证目标格式
        target_type = self._detect_target_type(target)
        if target_type is None:
            return False, '手机号或邮箱格式不正确', None
        
        # 2. 验证密码
        if not password:
            return False, '请输入密码', None
        
        with self.db.get_session() as session:
            # 3. 查找用户
            user = self._find_user_by_target(session, target, target_type)
            
            if not user:
                return False, '账号不存在，请先注册', None
            
            # 4. 验证密码
            if not user.verify_password(password):
                return False, '密码错误', None
            
            # 5. 检查用户状态
            if user.status != 'active':
                return False, '账号已被禁用', None
            
            # 6. 更新登录信息
            user.last_login_at = datetime.now()
            user.last_login_ip = ip_address
            
            # 7. 创建 Session
            session_token = UserSession.generate_token()
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                device_type=device_type,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                expire_at=datetime.now() + timedelta(hours=self.config.session_expire_hours),
            )
            session.add(user_session)
            session.commit()
            session.refresh(user)
            
            logger.info(f"用户登录成功: {target}")
            return True, '登录成功', {
                'user': user.to_dict(),
                'session_token': session_token,
                'expire_at': user_session.expire_at.isoformat(),
            }
    
    def login_with_code(
        self,
        target: str,
        code: str,
        device_type: str = 'web',
        device_info: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        验证码登录
        
        Args:
            target: 手机号或邮箱
            code: 验证码
            device_type: 设备类型
            device_info: 设备信息
            ip_address: 登录 IP
            user_agent: 用户代理
            
        Returns:
            (是否成功, 消息, {user, session_token})
        """
        # 1. 验证码校验
        valid, msg = self.verify_code(target, code, 'login')
        if not valid:
            return False, msg, None
        
        target_type = self._detect_target_type(target)
        
        with self.db.get_session() as session:
            # 2. 查找用户
            user = self._find_user_by_target(session, target, target_type)
            
            if not user:
                # 新用户自动注册
                user = User(
                    uuid=str(uuid.uuid4()),
                    phone=target if target_type == 'phone' else None,
                    email=target if target_type == 'email' else None,
                    status='active',
                    membership_level='free',
                )
                session.add(user)
                session.flush()
                logger.info(f"新用户自动注册: {target}")
            
            # 3. 检查用户状态
            if user.status != 'active':
                return False, '账号已被禁用', None
            
            # 4. 更新登录信息
            user.last_login_at = datetime.now()
            user.last_login_ip = ip_address
            
            # 5. 创建 Session
            session_token = UserSession.generate_token()
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                device_type=device_type,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                expire_at=datetime.now() + timedelta(hours=self.config.session_expire_hours),
            )
            session.add(user_session)
            session.commit()
            session.refresh(user)
            
            logger.info(f"用户登录成功: {target}")
            return True, '登录成功', {
                'user': user.to_dict(),
                'session_token': session_token,
                'expire_at': user_session.expire_at.isoformat(),
            }
    
    def validate_session(self, session_token: str) -> Tuple[bool, Optional[User]]:
        """
        验证 Session
        
        Args:
            session_token: Session Token
            
        Returns:
            (是否有效, 用户对象)
        """
        if not session_token:
            return False, None
        
        with self.db.get_session() as session:
            user_session = session.execute(
                select(UserSession)
                .where(UserSession.session_token == session_token)
            ).scalar_one_or_none()
            
            if not user_session or not user_session.is_valid():
                return False, None
            
            # 获取用户
            user = session.execute(
                select(User).where(User.id == user_session.user_id)
            ).scalar_one_or_none()
            
            if not user or user.status != 'active':
                return False, None
            
            # 刷新 Session
            user_session.refresh(self.config.session_expire_hours)
            session.commit()
            
            # commit 后属性会被标记为过期，需要重新加载
            session.refresh(user)
            # 将用户对象从 session 中分离，保留当前属性值
            # 这样在 session 关闭后仍然可以访问用户属性
            session.expunge(user)
            
            return True, user
    
    def logout(self, session_token: str) -> bool:
        """
        登出
        
        Args:
            session_token: Session Token
            
        Returns:
            是否成功
        """
        if not session_token:
            return False
        
        with self.db.get_session() as session:
            user_session = session.execute(
                select(UserSession)
                .where(UserSession.session_token == session_token)
            ).scalar_one_or_none()
            
            if user_session:
                user_session.invalidate()
                session.commit()
                logger.info(f"用户登出: user_id={user_session.user_id}")
                return True
        
        return False
    
    def logout_all(self, user_id: int) -> int:
        """
        登出用户所有设备
        
        Args:
            user_id: 用户 ID
            
        Returns:
            登出的 Session 数量
        """
        with self.db.get_session() as session:
            result = session.execute(
                select(UserSession)
                .where(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.is_active == True
                    )
                )
            ).scalars().all()
            
            count = 0
            for user_session in result:
                user_session.invalidate()
                count += 1
            
            session.commit()
            logger.info(f"用户所有设备登出: user_id={user_id}, count={count}")
            return count
    
    # === 辅助方法 ===
    
    def _detect_target_type(self, target: str) -> Optional[str]:
        """检测目标类型（手机号/邮箱）"""
        if self.PHONE_PATTERN.match(target):
            return 'phone'
        if self.EMAIL_PATTERN.match(target):
            return 'email'
        return None
    
    def _check_whitelist(self, target: str, target_type: str) -> bool:
        """检查白名单"""
        # 如果没有配置白名单，则允许所有
        if target_type == 'phone':
            if not self.config.phone_whitelist:
                return True
            return target in self.config.phone_whitelist
        elif target_type == 'email':
            if not self.config.email_whitelist:
                return True
            return target in self.config.email_whitelist
        return False
    
    def _find_user_by_target(
        self,
        session: Session,
        target: str,
        target_type: str
    ) -> Optional[User]:
        """根据目标查找用户"""
        if target_type == 'phone':
            return session.execute(
                select(User).where(User.phone == target)
            ).scalar_one_or_none()
        elif target_type == 'email':
            return session.execute(
                select(User).where(User.email == target)
            ).scalar_one_or_none()
        return None
    
    def _do_send_code(self, target: str, target_type: str, code: str) -> bool:
        """
        实际发送验证码
        
        TODO: 接入短信/邮件服务
        """
        if target_type == 'phone':
            # TODO: 接入短信服务（阿里云/腾讯云等）
            logger.info(f"[模拟] 短信验证码发送: {target} -> {code}")
            return True
        elif target_type == 'email':
            # TODO: 接入邮件服务（SMTP/第三方服务等）
            logger.info(f"[模拟] 邮件验证码发送: {target} -> {code}")
            return True
        return False


# 便捷函数
def get_auth_service() -> AuthService:
    """获取鉴权服务实例"""
    return AuthService()
