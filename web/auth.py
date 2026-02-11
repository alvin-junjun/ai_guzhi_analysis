# -*- coding: utf-8 -*-
"""
===================================
Web 鉴权中间件
===================================

职责：
1. Session 验证
2. 用户状态管理
3. 权限检查
"""

from __future__ import annotations

import logging
from functools import wraps
from http import HTTPStatus
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from http.cookies import SimpleCookie

from src.config import get_config
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service
from src.services.membership_service import MembershipService, get_membership_service
from src.models.user import User

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class AuthContext:
    """
    鉴权上下文
    
    存储当前请求的用户信息和权益
    """
    
    def __init__(self):
        self.user: Optional[User] = None
        self.session_token: Optional[str] = None
        self.is_authenticated: bool = False
        self.benefits: Dict[str, Any] = {}
    
    @property
    def user_id(self) -> Optional[int]:
        return self.user.id if self.user else None
    
    @property
    def is_vip(self) -> bool:
        return self.benefits.get('level') == 'vip'
    
    @property
    def daily_analysis_limit(self) -> int:
        return self.benefits.get('daily_analysis_limit', 5)
    
    @property
    def watchlist_limit(self) -> int:
        return self.benefits.get('watchlist_limit', 10)


class AuthMiddleware:
    """
    鉴权中间件
    
    用于在请求处理前进行用户验证
    """
    
    # Cookie 名称
    SESSION_COOKIE_NAME = 'session_token'
    
    def __init__(self):
        self.config = get_config()
        self.auth_service = get_auth_service()
        self.user_service = get_user_service()
        self.membership_service = get_membership_service()
    
    def extract_session_token(
        self,
        headers: Dict[str, str]
    ) -> Optional[str]:
        """
        从请求头中提取 Session Token
        
        支持两种方式（优先 Authorization，避免过期 Cookie 覆盖登录态）：
        1. Header: Authorization: Bearer xxx（前端 sessionStorage，与登录响应一致）
        2. Cookie: session_token=xxx
        
        Args:
            headers: HTTP 请求头
            
        Returns:
            Session Token 或 None
        """
        # 优先从 Authorization 获取（与前端 getAuthHeaders 一致，避免 Cookie 未写入或被代理剥离）
        auth_header = headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # 再从 Cookie 获取
        cookie_header = headers.get('Cookie', '')
        if cookie_header:
            cookie = SimpleCookie()
            try:
                cookie.load(cookie_header)
                if self.SESSION_COOKIE_NAME in cookie:
                    return cookie[self.SESSION_COOKIE_NAME].value
            except Exception:
                pass
        
        return None
    
    def authenticate(
        self,
        headers: Dict[str, str]
    ) -> AuthContext:
        """
        验证请求并返回鉴权上下文
        
        Args:
            headers: HTTP 请求头
            
        Returns:
            AuthContext 鉴权上下文
        """
        context = AuthContext()
        
        # 如果鉴权未启用，返回匿名上下文
        if not self.config.auth_enabled:
            context.is_authenticated = True  # 模拟已登录
            context.benefits = {
                'level': 'free',
                'daily_analysis_limit': -1,  # 不限
                'watchlist_limit': 100,
            }
            return context
        
        # 提取 Session Token
        session_token = self.extract_session_token(headers)
        if not session_token:
            return context
        
        # 验证 Session
        valid, user = self.auth_service.validate_session(session_token)
        if not valid or not user:
            return context
        
        # 填充上下文
        context.user = user
        context.session_token = session_token
        context.is_authenticated = True
        context.benefits = self.membership_service.get_user_benefits(user.id)
        
        return context
    
    def check_analysis_limit(
        self,
        context: AuthContext
    ) -> tuple[bool, str]:
        """
        检查用户分析次数限制
        
        Args:
            context: 鉴权上下文
            
        Returns:
            (是否可继续, 消息)
        """
        if not context.is_authenticated:
            return False, '请先登录'
        
        if context.daily_analysis_limit == -1:
            return True, ''
        
        can_continue, used, limit = self.user_service.check_analysis_limit(
            context.user_id
        )
        
        if not can_continue:
            return False, f'今日分析次数已用完（{used}/{limit}），请升级会员'
        
        return True, ''
    
    def build_set_cookie_header(
        self,
        session_token: str,
        max_age: int = None
    ) -> str:
        """
        构建 Set-Cookie 响应头
        
        Args:
            session_token: Session Token
            max_age: 过期时间（秒）
            
        Returns:
            Set-Cookie 头值
        """
        if max_age is None:
            max_age = self.config.session_expire_hours * 3600
        
        cookie = SimpleCookie()
        cookie[self.SESSION_COOKIE_NAME] = session_token
        cookie[self.SESSION_COOKIE_NAME]['path'] = '/'
        cookie[self.SESSION_COOKIE_NAME]['httponly'] = True
        cookie[self.SESSION_COOKIE_NAME]['max-age'] = max_age
        cookie[self.SESSION_COOKIE_NAME]['samesite'] = 'Lax'
        if self.config.cookie_domain:
            cookie[self.SESSION_COOKIE_NAME]['domain'] = self.config.cookie_domain
        # HTTPS 部署时设置 COOKIE_SECURE=true，Cookie 仅通过 HTTPS 发送
        if self.config.cookie_secure:
            cookie[self.SESSION_COOKIE_NAME]['secure'] = True
        
        # 提取 Set-Cookie 值
        output = cookie.output(header='')
        return output.strip()
    
    def build_clear_cookie_header(self) -> str:
        """构建清除 Cookie 的响应头"""
        return self.build_set_cookie_header('', max_age=0)


# === 便捷函数 ===

_auth_middleware: Optional[AuthMiddleware] = None


def get_auth_middleware() -> AuthMiddleware:
    """获取鉴权中间件实例"""
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = AuthMiddleware()
    return _auth_middleware


def require_auth(func: Callable) -> Callable:
    """
    装饰器：要求用户登录
    
    用于保护需要登录才能访问的路由
    """
    @wraps(func)
    def wrapper(query: Dict[str, list], **kwargs) -> Any:
        middleware = get_auth_middleware()
        headers = kwargs.get('headers', {})
        context = middleware.authenticate(headers)
        
        if not context.is_authenticated:
            from web.handlers import JsonResponse
            return JsonResponse(
                {'success': False, 'error': '请先登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        kwargs['auth_context'] = context
        return func(query, **kwargs)
    
    return wrapper


def require_vip(func: Callable) -> Callable:
    """
    装饰器：要求 VIP 会员
    
    用于保护会员专属功能
    """
    @wraps(func)
    def wrapper(query: Dict[str, list], **kwargs) -> Any:
        middleware = get_auth_middleware()
        headers = kwargs.get('headers', {})
        context = middleware.authenticate(headers)
        
        if not context.is_authenticated:
            from web.handlers import JsonResponse
            return JsonResponse(
                {'success': False, 'error': '请先登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        if not context.is_vip:
            from web.handlers import JsonResponse
            return JsonResponse(
                {'success': False, 'error': '该功能仅对会员开放', 'code': 'VIP_REQUIRED'},
                status=HTTPStatus.FORBIDDEN
            )
        
        kwargs['auth_context'] = context
        return func(query, **kwargs)
    
    return wrapper
