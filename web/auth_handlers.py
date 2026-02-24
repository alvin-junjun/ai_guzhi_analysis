# -*- coding: utf-8 -*-
"""
===================================
Web 鉴权处理器
===================================

职责：
1. 处理登录/注册请求
2. 处理验证码发送
3. 用户信息接口
4. 会员信息接口
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Dict, Any, Optional

from web.handlers import Response, JsonResponse, HtmlResponse
from web.auth import get_auth_middleware, AuthContext
from web.auth_templates import (
    render_login_page, render_register_page, render_user_center_page,
    render_membership_page, render_history_page
)
from src.config import get_config
from src.services.auth_service import get_auth_service
from src.services.user_service import get_user_service
from src.services.membership_service import get_membership_service
from src.services.payment_service import get_payment_service
from src.services.referral_service import get_referral_service

logger = logging.getLogger(__name__)


class AuthPageHandler:
    """鉴权页面处理器"""
    
    def __init__(self):
        self.config = get_config()
        self.auth_service = get_auth_service()
        self.auth_middleware = get_auth_middleware()
    
    def handle_login_page(self, query: Dict[str, list]) -> Response:
        """
        登录页面 GET /login
        """
        # 检查是否已登录
        redirect_url = query.get('redirect', ['/'])[0]
        error_msg = query.get('error', [''])[0]
        
        body = render_login_page(redirect_url=redirect_url, error=error_msg)
        return HtmlResponse(body)
    
    def handle_register_page(self, query: Dict[str, list]) -> Response:
        """
        注册页面 GET /register，支持 ?ref=分享码 用于邀请注册
        """
        error_msg = query.get('error', [''])[0]
        ref = query.get('ref', [''])[0]
        body = render_register_page(error=error_msg, ref=ref)
        return HtmlResponse(body)
    
    def handle_user_center_page(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        用户中心页面 GET /user
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            # 重定向到登录页
            return self._redirect_response('/login?redirect=/user')
        
        # 获取用户详细信息
        user_service = get_user_service()
        membership_service = get_membership_service()
        
        user_info = context.user.to_dict() if context.user else {}
        benefits = context.benefits
        
        # 获取今日使用量
        can_analyze, used, limit = user_service.check_analysis_limit(context.user_id)
        usage_info = {
            'used': used,
            'limit': limit if limit != -1 else '不限',
            'can_analyze': can_analyze,
        }
        
        body = render_user_center_page(
            user_info=user_info,
            benefits=benefits,
            usage_info=usage_info
        )
        return HtmlResponse(body)
    
    def handle_history_page(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        历史分析记录页面 GET /user/history
        """
        context = self.auth_middleware.authenticate(headers)
        if not context.is_authenticated:
            return self._redirect_response('/login?redirect=/user/history')
        body = render_history_page()
        return HtmlResponse(body)
    
    def handle_membership_page(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        会员充值页面 GET /membership
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            # 重定向到登录页
            return self._redirect_response('/login?redirect=/membership')
        
        # 获取用户信息
        user_info = context.user.to_dict() if context.user else {}
        benefits = context.benefits
        
        # 获取套餐列表
        membership_service = get_membership_service()
        plans = membership_service.get_active_plans()
        
        # 获取当前待支付订单（如有）
        pending_orders = membership_service.get_user_orders(
            context.user_id, status='pending', limit=1
        )
        current_order = pending_orders[0] if pending_orders else None
        
        body = render_membership_page(
            user_info=user_info,
            benefits=benefits,
            plans=plans,
            current_order=current_order
        )
        return HtmlResponse(body)
    
    def _redirect_response(self, url: str) -> Response:
        """创建重定向响应"""
        body = f'<html><head><meta http-equiv="refresh" content="0;url={url}"></head></html>'
        return HtmlResponse(body.encode('utf-8'), status=HTTPStatus.FOUND)


class AuthApiHandler:
    """鉴权 API 处理器"""
    
    def __init__(self):
        self.config = get_config()
        self.auth_service = get_auth_service()
        self.user_service = get_user_service()
        self.membership_service = get_membership_service()
        self.auth_middleware = get_auth_middleware()
    
    def handle_send_code(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        发送验证码 POST /api/auth/send-code
        
        参数:
            target: 手机号或邮箱
            purpose: 用途（login/register）
        """
        target = form_data.get('target', [''])[0].strip()
        purpose = form_data.get('purpose', ['login'])[0]
        
        if not target:
            return JsonResponse(
                {'success': False, 'error': '请输入手机号或邮箱'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 获取客户端信息
        ip_address = headers.get('X-Forwarded-For', headers.get('X-Real-IP', ''))
        user_agent = headers.get('User-Agent', '')
        
        success, msg, code = self.auth_service.send_verification_code(
            target=target,
            purpose=purpose,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        result = {'success': success, 'message': msg}
        
        # 开发模式下返回验证码
        if code and self.config.debug:
            result['debug_code'] = code
        
        return JsonResponse(result)
    
    def handle_login(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        用户登录 POST /api/auth/login
        
        参数:
            target: 手机号或邮箱
            password: 密码
        """
        target = form_data.get('target', [''])[0].strip()
        password = form_data.get('password', [''])[0]
        
        if not target or not password:
            return JsonResponse(
                {'success': False, 'error': '请输入手机号/邮箱和密码'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 获取客户端信息
        ip_address = headers.get('X-Forwarded-For', headers.get('X-Real-IP', ''))
        user_agent = headers.get('User-Agent', '')
        
        success, msg, data = self.auth_service.login_with_password(
            target=target,
            password=password,
            device_type='web',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not success:
            return JsonResponse({'success': False, 'error': msg})
        
        # 构建响应（包含 Set-Cookie）；同时返回 session_token 供前端存储，兼容 Cookie 不可用场景（如部分 WebView）
        response_data = {
            'success': True,
            'message': msg,
            'user': data['user'],
            'expire_at': data['expire_at'],
            'session_token': data['session_token'],
        }
        
        # 创建带 Cookie 的响应
        response = JsonResponseWithCookie(
            data=response_data,
            cookie_value=data['session_token'],
            cookie_max_age=self.config.session_expire_hours * 3600
        )
        
        return response
    
    def handle_register(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        用户注册 POST /api/auth/register
        
        参数:
            target: 手机号或邮箱
            password: 密码
            nickname: 昵称（可选）
            email: 接收报告的QQ邮箱（手机号注册时必填）
        """
        target = form_data.get('target', [''])[0].strip()
        password = form_data.get('password', [''])[0]
        nickname = form_data.get('nickname', [''])[0].strip() or None
        email = form_data.get('email', [''])[0].strip() or None
        ref = form_data.get('ref', [''])[0].strip() or None
        
        if not target or not password:
            return JsonResponse(
                {'success': False, 'error': '请输入手机号/邮箱和密码'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        ip_address = headers.get('X-Forwarded-For', headers.get('X-Real-IP', ''))
        
        success, msg, user_info = self.auth_service.register_with_password(
            target=target,
            password=password,
            nickname=nickname,
            ip_address=ip_address,
            email=email,
            referrer_share_code=ref
        )
        
        if not success:
            return JsonResponse({'success': False, 'error': msg})
        
        return JsonResponse({
            'success': True,
            'message': msg,
            'user': user_info
        })
    
    def handle_logout(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        用户登出 POST /api/auth/logout
        """
        session_token = self.auth_middleware.extract_session_token(headers)
        
        if session_token:
            self.auth_service.logout(session_token)
        
        # 清除 Cookie
        response = JsonResponseWithCookie(
            data={'success': True, 'message': '已登出'},
            cookie_value='',
            cookie_max_age=0
        )
        return response
    
    def handle_user_info(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        获取当前用户信息 GET /api/auth/user
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '未登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        # 使用量：直接用 context.benefits 的 limit，只查一次今日使用量，避免重复 get_user_by_id
        limit = context.benefits.get('daily_analysis_limit', 5)
        usage = self.user_service.get_today_usage(context.user_id)
        used = usage.analysis_count
        can_analyze = (limit == -1 or used < limit)
        
        return JsonResponse({
            'success': True,
            'user': context.user.to_dict() if context.user else None,
            'benefits': context.benefits,
            'usage': {
                'analysis_used': used,
                'analysis_limit': limit,
                'can_analyze': can_analyze,
            }
        })
    
    def handle_referral_share_link(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        获取邀请分享链接 GET /api/referral/share-link（需登录）
        返回分享码，前端用 origin + /register?ref= 拼完整链接并复制
        """
        context = self.auth_middleware.authenticate(headers)
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '请先登录'},
                status=HTTPStatus.UNAUTHORIZED
            )
        ok, share_code = get_referral_service().get_or_create_share_code(context.user_id)
        if not share_code:
            return JsonResponse({'success': False, 'error': '获取分享码失败'})
        return JsonResponse({
            'success': True,
            'share_code': share_code,
        })
    
    def handle_analysis_history(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        获取当前用户历史分析记录 GET /api/user/analysis-history
        支持 query: limit, offset
        """
        context = self.auth_middleware.authenticate(headers)
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '未登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        limit = 100
        offset = 0
        q = query or {}
        if q.get('limit'):
            try:
                limit = min(int(q['limit'][0]), 200)
            except (ValueError, TypeError):
                pass
        if q.get('offset'):
            try:
                offset = max(0, int(q['offset'][0]))
            except (ValueError, TypeError):
                pass
        user_service = get_user_service()
        items = user_service.get_analysis_history(
            user_id=context.user_id,
            limit=limit,
            offset=offset
        )
        return JsonResponse({'success': True, 'list': items})
    
    def handle_membership_plans(
        self,
        query: Dict[str, list]
    ) -> Response:
        """
        获取会员套餐列表 GET /api/membership/plans
        """
        plans = self.membership_service.get_active_plans()
        return JsonResponse({
            'success': True,
            'plans': plans
        })
    
    def handle_create_order(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        创建会员订单 POST /api/membership/create-order
        
        参数:
            plan_id: 套餐 ID
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '请先登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        plan_id_str = form_data.get('plan_id', [''])[0]
        if not plan_id_str or not plan_id_str.isdigit():
            return JsonResponse(
                {'success': False, 'error': '请选择套餐'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        plan_id = int(plan_id_str)
        
        # 创建订单
        success, msg, order_info = self.membership_service.create_order(
            user_id=context.user_id,
            plan_id=plan_id
        )
        
        if not success:
            return JsonResponse({'success': False, 'error': msg})
        
        # 支付模式：商户号 API > 个人收款码 > 模拟支付
        is_personal = bool(
            not self.config.wechat_pay_enabled
            and self.config.wechat_pay_personal_qr_url
        )
        is_mock = (
            not self.config.wechat_pay_enabled
            and not self.config.wechat_pay_personal_qr_url
        )

        if is_personal:
            # 个人收款码：只展示静态二维码，不调微信 API
            return JsonResponse({
                'success': True,
                'order': order_info,
                'qrcode_url': None,
                'is_mock': False,
                'is_personal': True,
                'personal_qr_url': self.config.wechat_pay_personal_qr_url,
            })
        elif self.config.wechat_pay_enabled:
            # 商户号 Native 支付
            payment_service = get_payment_service()
            pay_amount_fen = int(order_info['pay_amount'] * 100)
            plan = self.membership_service.get_plan_by_id(plan_id)
            description = f"A股分析会员-{plan.name if plan else '会员套餐'}"
            pay_success, pay_msg, qrcode_url = payment_service.create_native_order(
                order_no=order_info['order_no'],
                description=description,
                amount=pay_amount_fen,
                attach=str(context.user_id)
            )
            if pay_success:
                return JsonResponse({
                    'success': True,
                    'order': order_info,
                    'qrcode_url': qrcode_url,
                    'is_mock': False,
                    'is_personal': False,
                })
            return JsonResponse({
                'success': False,
                'error': f'创建支付失败: {pay_msg}',
                'order': order_info,
            })
        else:
            # 模拟支付（开发模式）
            payment_service = get_payment_service()
            pay_amount_fen = int(order_info['pay_amount'] * 100)
            plan = self.membership_service.get_plan_by_id(plan_id)
            description = f"A股分析会员-{plan.name if plan else '会员套餐'}"
            pay_success, pay_msg, qrcode_url = payment_service.create_native_order(
                order_no=order_info['order_no'],
                description=description,
                amount=pay_amount_fen,
                attach=str(context.user_id)
            )
            if pay_success:
                return JsonResponse({
                    'success': True,
                    'order': order_info,
                    'qrcode_url': qrcode_url,
                    'is_mock': True,
                    'is_personal': False,
                })
            return JsonResponse({
                'success': False,
                'error': f'创建支付失败: {pay_msg}',
                'order': order_info,
            })
    
    def handle_order_status(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        查询订单状态 GET /api/membership/order-status
        
        参数:
            order_no: 订单号
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '请先登录'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        order_no = query.get('order_no', [''])[0]
        if not order_no:
            return JsonResponse(
                {'success': False, 'error': '缺少订单号'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        order = self.membership_service.get_order_by_no(order_no)
        if not order:
            return JsonResponse({'success': False, 'error': '订单不存在'})
        
        # 检查订单是否属于当前用户
        if order.user_id != context.user_id:
            return JsonResponse({'success': False, 'error': '无权查看此订单'})
        
        # 如果订单未支付，尝试查询支付状态
        if order.payment_status == 'pending':
            payment_service = get_payment_service()
            pay_success, pay_msg, pay_result = payment_service.query_order(order_no)
            
            if pay_success and pay_result:
                trade_state = pay_result.get('trade_state')
                if trade_state == 'SUCCESS':
                    # 支付成功，处理订单
                    self.membership_service.process_payment(
                        order_no=order_no,
                        pay_channel='wechat',
                        trade_no=pay_result.get('transaction_id')
                    )
                    # 重新获取订单
                    order = self.membership_service.get_order_by_no(order_no)
        
        # 判断是否是模拟支付
        is_mock = not self.config.wechat_pay_enabled
        
        return JsonResponse({
            'success': True,
            'order': order.to_dict() if order else None,
            'is_mock': is_mock,
        })
    
    def handle_cancel_order(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        取消订单 POST /api/membership/cancel-order
        
        参数:
            order_no: 订单号
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '请先登录'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        order_no = form_data.get('order_no', [''])[0]
        if not order_no:
            return JsonResponse(
                {'success': False, 'error': '缺少订单号'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        order = self.membership_service.get_order_by_no(order_no)
        if not order:
            return JsonResponse({'success': False, 'error': '订单不存在'})
        
        if order.user_id != context.user_id:
            return JsonResponse({'success': False, 'error': '无权操作此订单'})
        
        if order.payment_status != 'pending':
            return JsonResponse({'success': False, 'error': '订单状态不允许取消'})
        
        # 取消订单
        from src.storage import get_db
        from sqlalchemy import select
        from src.models.membership import Order
        
        db = get_db()
        with db.get_session() as session:
            order_obj = session.execute(
                select(Order).where(Order.order_no == order_no)
            ).scalar_one_or_none()
            
            if order_obj:
                order_obj.payment_status = 'cancelled'
                session.commit()
        
        return JsonResponse({'success': True, 'message': '订单已取消'})
    
    def handle_mock_pay(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        模拟支付成功 POST /api/payment/mock-pay
        
        仅在开发模式下可用
        """
        # 检查是否是开发模式
        if self.config.wechat_pay_enabled:
            return JsonResponse(
                {'success': False, 'error': '生产环境不支持模拟支付'},
                status=HTTPStatus.FORBIDDEN
            )
        
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '请先登录'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        order_no = form_data.get('order_no', [''])[0]
        if not order_no:
            return JsonResponse(
                {'success': False, 'error': '缺少订单号'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        order = self.membership_service.get_order_by_no(order_no)
        if not order:
            return JsonResponse({'success': False, 'error': '订单不存在'})
        
        if order.user_id != context.user_id:
            return JsonResponse({'success': False, 'error': '无权操作此订单'})
        
        if order.payment_status != 'pending':
            return JsonResponse({'success': False, 'error': '订单已处理'})
        
        # 模拟支付成功
        payment_service = get_payment_service()
        if hasattr(payment_service, 'mock_pay_success'):
            payment_service.mock_pay_success(order_no)
        
        # 处理订单
        success, msg = self.membership_service.process_payment(
            order_no=order_no,
            pay_channel='wechat',
            trade_no=f'MOCK_{order_no}'
        )
        
        if success:
            return JsonResponse({'success': True, 'message': '支付成功'})
        else:
            return JsonResponse({'success': False, 'error': msg})
    
    def handle_payment_notify(
        self,
        body: bytes,
        headers: Dict[str, str]
    ) -> Response:
        """
        微信支付回调通知 POST /api/payment/notify
        """
        if not self.config.wechat_pay_enabled:
            return JsonResponse({'code': 'FAIL', 'message': '支付未启用'})
        
        payment_service = get_payment_service()
        
        # 验证签名
        timestamp = headers.get('Wechatpay-Timestamp', '')
        nonce = headers.get('Wechatpay-Nonce', '')
        signature = headers.get('Wechatpay-Signature', '')
        
        if not payment_service.verify_notify_signature(
            timestamp, nonce, body.decode('utf-8'), signature
        ):
            logger.warning("支付回调签名验证失败")
            return JsonResponse({'code': 'FAIL', 'message': '签名验证失败'})
        
        # 解析通知
        success, msg, result = payment_service.parse_notify(body.decode('utf-8'))
        
        if not success:
            logger.error(f"解析支付通知失败: {msg}")
            return JsonResponse({'code': 'FAIL', 'message': msg})
        
        # 处理支付结果
        order_no = result.get('out_trade_no')
        trade_no = result.get('transaction_id')
        
        if order_no:
            process_success, process_msg = self.membership_service.process_payment(
                order_no=order_no,
                pay_channel='wechat',
                trade_no=trade_no
            )
            
            if process_success:
                logger.info(f"支付回调处理成功: order_no={order_no}")
                return JsonResponse({'code': 'SUCCESS', 'message': '成功'})
            else:
                logger.error(f"支付回调处理失败: {process_msg}")
                return JsonResponse({'code': 'FAIL', 'message': process_msg})
        
        return JsonResponse({'code': 'SUCCESS', 'message': '成功'})
    
    # === 用户自选股相关 API ===
    
    def handle_get_watchlist(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        获取用户自选股列表 GET /api/watchlist
        
        参数:
            limit: 返回数量限制（默认20）
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '未登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        limit = int(query.get('limit', ['20'])[0])
        limit = min(limit, 100)  # 最多返回100条
        
        watchlist = self.user_service.get_watchlist(context.user_id)
        
        # 限制返回数量
        watchlist = watchlist[:limit]
        
        return JsonResponse({
            'success': True,
            'watchlist': watchlist,
            'total': len(watchlist)
        })
    
    def handle_get_watchlist_groups(
        self,
        query: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        获取用户自选股分组列表 GET /api/watchlist/groups
        
        返回用户已有的分组名称（去重）
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '未登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        groups = self.user_service.get_watchlist_groups(context.user_id)
        # 过滤掉空值
        groups = [g for g in groups if g]
        
        return JsonResponse({
            'success': True,
            'groups': groups
        })
    
    def handle_save_watchlist(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        批量保存用户自选股 POST /api/watchlist/save
        
        参数:
            stocks: 股票代码列表（逗号分隔）
            group_name: 分组名称（可选，从下拉框选择或输入新分组）
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '未登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        stocks_str = form_data.get('stocks', [''])[0].strip()
        
        if not stocks_str:
            return JsonResponse(
                {'success': False, 'error': '请输入股票代码'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 获取分组名称：优先使用新输入的分组名，否则使用下拉框选择的
        new_group_name = form_data.get('new_group_name', [''])[0].strip()
        selected_group = form_data.get('group_name', [''])[0].strip()
        
        # 优先使用新输入的分组名
        if new_group_name:
            # 验证分组名称长度（最多10个汉字）
            if len(new_group_name) > 10:
                return JsonResponse(
                    {'success': False, 'error': '分组名称最多10个字符'},
                    status=HTTPStatus.BAD_REQUEST
                )
            group_name = new_group_name
        elif selected_group:
            group_name = selected_group
        else:
            group_name = '默认分组'
        
        # 解析股票代码（支持逗号、空格、换行分隔）
        import re
        stock_codes = re.split(r'[,\s\n]+', stocks_str)
        stock_codes = [code.strip() for code in stock_codes if code.strip()]
        
        if not stock_codes:
            return JsonResponse(
                {'success': False, 'error': '请输入有效的股票代码'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 检查数量限制
        current_count = self.user_service.get_watchlist_count(context.user_id)
        limit = context.benefits.get('watchlist_limit', 10)
        
        added = []
        failed = []
        
        for code in stock_codes:
            # 检查是否超过限制
            if current_count >= limit:
                failed.append({'code': code, 'reason': f'已达上限({limit}只)'})
                continue
            
            success, msg = self.user_service.add_to_watchlist(
                user_id=context.user_id,
                stock_code=code,
                stock_name=None,  # 股票名称可以后续补充
                group_name=group_name
            )
            
            if success:
                added.append(code)
                current_count += 1
            else:
                failed.append({'code': code, 'reason': msg})
        
        return JsonResponse({
            'success': True,
            'message': f'成功添加 {len(added)} 只股票到「{group_name}」',
            'added': added,
            'failed': failed,
            'current_count': current_count,
            'limit': limit,
            'group_name': group_name
        })
    
    def handle_delete_watchlist(
        self,
        form_data: Dict[str, list],
        headers: Dict[str, str]
    ) -> Response:
        """
        删除自选股 POST /api/watchlist/delete
        
        参数:
            stock_code: 股票代码
        """
        context = self.auth_middleware.authenticate(headers)
        
        if not context.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': '未登录', 'code': 'UNAUTHORIZED'},
                status=HTTPStatus.UNAUTHORIZED
            )
        
        stock_code = form_data.get('stock_code', [''])[0].strip()
        
        if not stock_code:
            return JsonResponse(
                {'success': False, 'error': '请指定股票代码'},
                status=HTTPStatus.BAD_REQUEST
            )
        
        success, msg = self.user_service.remove_from_watchlist(
            user_id=context.user_id,
            stock_code=stock_code
        )
        
        return JsonResponse({
            'success': success,
            'message': msg
        })


class JsonResponseWithCookie(Response):
    """带 Cookie 设置的 JSON 响应"""
    
    def __init__(
        self,
        data: Dict[str, Any],
        cookie_value: str,
        cookie_max_age: int,
        status: HTTPStatus = HTTPStatus.OK
    ):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        super().__init__(
            body=body,
            status=status,
            content_type='application/json; charset=utf-8'
        )
        self.cookie_value = cookie_value
        self.cookie_max_age = cookie_max_age
    
    def send(self, handler) -> None:
        """发送响应（带 Cookie）"""
        handler.send_response(self.status)
        handler.send_header('Content-Type', self.content_type)
        handler.send_header('Content-Length', str(len(self.body)))
        
        # 设置 Cookie
        middleware = get_auth_middleware()
        cookie_header = middleware.build_set_cookie_header(
            self.cookie_value, 
            self.cookie_max_age
        )
        handler.send_header('Set-Cookie', cookie_header)
        
        handler.end_headers()
        handler.wfile.write(self.body)


# === 处理器工厂 ===

_auth_page_handler: Optional[AuthPageHandler] = None
_auth_api_handler: Optional[AuthApiHandler] = None


def get_auth_page_handler() -> AuthPageHandler:
    """获取鉴权页面处理器"""
    global _auth_page_handler
    if _auth_page_handler is None:
        _auth_page_handler = AuthPageHandler()
    return _auth_page_handler


def get_auth_api_handler() -> AuthApiHandler:
    """获取鉴权 API 处理器"""
    global _auth_api_handler
    if _auth_api_handler is None:
        _auth_api_handler = AuthApiHandler()
    return _auth_api_handler
