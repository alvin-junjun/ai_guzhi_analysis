# -*- coding: utf-8 -*-
"""
===================================
Web 处理器层 - 请求处理
===================================

职责：
1. 处理各类 HTTP 请求
2. 调用服务层执行业务逻辑
3. 返回响应数据

处理器分类：
- PageHandler: 页面请求处理
- ApiHandler: API 接口处理
"""

from __future__ import annotations

import json
import re
import logging
from http import HTTPStatus
from datetime import datetime
from typing import Dict, Any, TYPE_CHECKING

from web.services import get_config_service, get_analysis_service
from web.templates import render_config_page
from src.enums import ReportType

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ============================================================
# 响应辅助类
# ============================================================

class Response:
    """HTTP 响应封装"""
    
    def __init__(
        self,
        body: bytes,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "text/html; charset=utf-8"
    ):
        self.body = body
        self.status = status
        self.content_type = content_type
    
    def send(self, handler: 'BaseHTTPRequestHandler') -> None:
        """发送响应到客户端"""
        handler.send_response(self.status)
        handler.send_header("Content-Type", self.content_type)
        handler.send_header("Content-Length", str(len(self.body)))
        handler.end_headers()
        handler.wfile.write(self.body)


class JsonResponse(Response):
    """JSON 响应封装"""
    
    def __init__(
        self,
        data: Dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK
    ):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        super().__init__(
            body=body,
            status=status,
            content_type="application/json; charset=utf-8"
        )


class HtmlResponse(Response):
    """HTML 响应封装"""
    
    def __init__(
        self,
        body: bytes,
        status: HTTPStatus = HTTPStatus.OK
    ):
        super().__init__(
            body=body,
            status=status,
            content_type="text/html; charset=utf-8"
        )


class StaticFileResponse(Response):
    """静态文件响应封装"""
    
    # MIME 类型映射
    MIME_TYPES = {
        '.html': 'text/html; charset=utf-8',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.css': 'text/css; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.txt': 'text/plain; charset=utf-8',
    }
    
    def __init__(
        self,
        body: bytes,
        filename: str,
        status: HTTPStatus = HTTPStatus.OK
    ):
        import os
        ext = os.path.splitext(filename)[1].lower()
        content_type = self.MIME_TYPES.get(ext, 'application/octet-stream')
        super().__init__(
            body=body,
            status=status,
            content_type=content_type
        )


# ============================================================
# 静态文件处理器
# ============================================================

class StaticFileHandler:
    """静态文件处理器"""
    
    def __init__(self, base_dir: str = "sources"):
        import os
        # 获取项目根目录
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            base_dir
        )
    
    def handle_static(self, path: str) -> Response:
        """
        处理静态文件请求
        
        Args:
            path: 文件路径（相对于 base_dir）
        """
        import os
        
        # 安全检查：防止路径遍历攻击
        safe_path = os.path.normpath(path).lstrip(os.sep).lstrip('/')
        if '..' in safe_path:
            return JsonResponse(
                {'error': 'Invalid path'},
                status=HTTPStatus.FORBIDDEN
            )
        
        full_path = os.path.join(self.base_dir, safe_path)
        
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return JsonResponse(
                {'error': 'File not found'},
                status=HTTPStatus.NOT_FOUND
            )
        
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            return StaticFileResponse(content, safe_path)
        except Exception as e:
            logger.error(f"读取静态文件失败: {full_path} - {e}")
            return JsonResponse(
                {'error': 'Failed to read file'},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


# ============================================================
# 页面处理器
# ============================================================

class PageHandler:
    """页面请求处理器"""
    
    def __init__(self):
        self.config_service = get_config_service()
    
    def handle_index(self, headers: dict = None) -> Response:
        """处理首页请求 GET /。始终做服务端鉴权并直出导航栏，避免首屏一直显示「加载中」。"""
        nav_ssr = None
        if headers:
            from web.auth import get_auth_middleware
            middleware = get_auth_middleware()
            context = middleware.authenticate(headers)
            if context.is_authenticated and context.user:
                u = context.user
                benefits = context.benefits or {}
                display_name = u.nickname or u.email or u.phone or '用户'
                plan = benefits.get('plan_name')
                level_text = plan if plan else ('会员' if (getattr(u, 'membership_level', None) and u.membership_level != 'free') else '免费版')
                nav_ssr = {
                    'display_name': display_name,
                    'level_text': level_text or '免费版',
                    'is_vip': benefits.get('level') == 'vip',
                }
            else:
                # 未登录时也直出「未登录」+ 登录/注册链接，避免一直显示加载中
                nav_ssr = {'unauthenticated': True}
        body = render_config_page(nav_ssr=nav_ssr)
        return HtmlResponse(body)
    
    def handle_update(self, form_data: Dict[str, list]) -> Response:
        """
        处理配置更新 POST /update
        
        Args:
            form_data: 表单数据
        """
        stock_list = form_data.get("stock_list", [""])[0]
        self.config_service.set_stock_list(stock_list)
        body = render_config_page(message="已保存")
        return HtmlResponse(body)


# ============================================================
# API 处理器
# ============================================================

class ApiHandler:
    """API 请求处理器"""
    
    def __init__(self):
        self.analysis_service = get_analysis_service()
    
    def handle_health(self) -> Response:
        """
        健康检查 GET /health
        
        返回:
            {
                "status": "ok",
                "timestamp": "2026-01-19T10:30:00",
                "service": "stock-analysis-webui"
            }
        """
        data = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "service": "stock-analysis-webui"
        }
        return JsonResponse(data)
    
    def handle_analysis(self, query: Dict[str, list], headers: Dict[str, str] = None) -> Response:
        """
        触发股票分析 GET /analysis?code=xxx
        
        Args:
            query: URL 查询参数
            headers: HTTP 请求头（用于身份验证）
            
        返回:
            {
                "success": true,
                "message": "分析任务已提交",
                "code": "600519",
                "task_id": "600519_20260119_103000"
            }
        """
        headers = headers or {}
        
        # === 1. 身份验证和限额检查 ===
        from web.auth import get_auth_middleware
        middleware = get_auth_middleware()
        context = middleware.authenticate(headers)
        
        # 检查是否已登录（如果鉴权已启用）
        if not context.is_authenticated:
            return JsonResponse(
                {
                    "success": False, 
                    "error": "请先登录后再进行股票分析",
                    "code": "UNAUTHORIZED",
                    "redirect": "/login"
                },
                status=HTTPStatus.UNAUTHORIZED
            )
        
        # 检查分析次数限额
        can_continue, msg = middleware.check_analysis_limit(context)
        if not can_continue:
            return JsonResponse(
                {
                    "success": False, 
                    "error": msg,
                    "code": "LIMIT_EXCEEDED",
                    "redirect": "/membership"
                },
                status=HTTPStatus.FORBIDDEN
            )
        
        # === 2. 参数验证 ===
        # 获取股票代码参数
        code_list = query.get("code", [])
        if not code_list or not code_list[0].strip():
            return JsonResponse(
                {"success": False, "error": "缺少必填参数: code (股票代码)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        code = code_list[0].strip()

        # 验证股票代码格式：A股(6位数字) / 港股(HK+5位数字) / 美股(1-5个大写字母+.+2个后缀字母)
        code = code.upper()
        is_a_stock = re.match(r'^\d{6}$', code)
        is_hk_stock = re.match(r'^HK\d{5}$', code)
        is_us_stock = re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', code.upper())

        if not (is_a_stock or is_hk_stock or is_us_stock):
            return JsonResponse(
                {"success": False, "error": f"无效的股票代码格式: {code} (A股6位数字 / 港股HK+5位数字 / 美股1-5个字母)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 获取报告类型参数（默认精简报告）
        report_type_str = query.get("report_type", ["simple"])[0]
        report_type = ReportType.from_str(report_type_str)
        
        # === 3. 提交异步分析任务（传入 user_id）===
        try:
            result = self.analysis_service.submit_analysis(
                code, 
                report_type=report_type,
                user_id=context.user_id  # 传入用户 ID，用于持久化和使用量统计
            )
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"[ApiHandler] 提交分析任务失败: {e}")
            return JsonResponse(
                {"success": False, "error": f"提交任务失败: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
    
    def handle_tasks(self, query: Dict[str, list]) -> Response:
        """
        查询任务列表 GET /tasks
        
        Args:
            query: URL 查询参数 (可选 limit)
            
        返回:
            {
                "success": true,
                "tasks": [...]
            }
        """
        limit_list = query.get("limit", ["20"])
        try:
            limit = int(limit_list[0])
        except ValueError:
            limit = 20
        
        tasks = self.analysis_service.list_tasks(limit=limit)
        return JsonResponse({"success": True, "tasks": tasks})
    
    def handle_task_status(self, query: Dict[str, list]) -> Response:
        """
        查询单个任务状态 GET /task?id=xxx
        
        Args:
            query: URL 查询参数
        """
        task_id_list = query.get("id", [])
        if not task_id_list or not task_id_list[0].strip():
            return JsonResponse(
                {"success": False, "error": "缺少必填参数: id (任务ID)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        task_id = task_id_list[0].strip()
        task = self.analysis_service.get_task_status(task_id)
        
        if task is None:
            return JsonResponse(
                {"success": False, "error": f"任务不存在: {task_id}"},
                status=HTTPStatus.NOT_FOUND
            )
        
        return JsonResponse({"success": True, "task": task})

    def handle_article_extract(self, form_data: Dict[str, list], headers: Dict[str, str] = None) -> Response:
        """
        从文章 URL 或提示词抓取股票并提交分析 POST /api/article-extract
        
        会员与次数限制：与「输入股票代码分析」完全一致——先校验登录，再按会员等级校验今日分析次数，
        超出时返回 LIMIT_EXCEEDED 与 redirect=/membership。每次提交的多只股票会按只数扣减次数。
        
        参数: mode=url|prompt, url=xxx（mode=url 时必填）, content=xxx（mode=prompt 时必填）,
             report_type=simple|full, top_n=5（1-10）
        返回: { success, task_ids, source_type, message }
        """
        headers = headers or {}
        logger.info("[article-extract] 收到请求 path=/api/article-extract")
        from web.auth import get_auth_middleware
        middleware = get_auth_middleware()
        context = middleware.authenticate(headers)
        if not context.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "请先登录", "code": "UNAUTHORIZED", "redirect": "/login"},
                status=HTTPStatus.UNAUTHORIZED
            )
        # 与股票代码分析同一套限制逻辑：按会员等级做今日次数限制
        can_continue, msg = middleware.check_analysis_limit(context)
        if not can_continue:
            return JsonResponse(
                {"success": False, "error": msg, "code": "LIMIT_EXCEEDED", "redirect": "/membership"},
                status=HTTPStatus.FORBIDDEN
            )

        def _first(key: str, default: str = "") -> str:
            return (form_data.get(key) or [default])[0].strip() if form_data else default

        mode = _first("mode", "url")
        if mode not in ("url", "prompt"):
            mode = "url"
        report_type_str = _first("report_type", "simple")
        report_type = ReportType.from_str(report_type_str)
        try:
            top_n = min(max(int(_first("top_n", "5") or "5"), 1), 10)
        except (ValueError, TypeError):
            top_n = 5

        key_content = None
        source_type = "url_crawl"
        source_ref = ""

        if mode == "url":
            url = _first("url")
            if not url:
                return JsonResponse(
                    {"success": False, "error": "请输入文章 URL"},
                    status=HTTPStatus.BAD_REQUEST
                )
            if not url.startswith("http"):
                url = "https://" + url
            source_ref = url
            try:
                from src.article_crawl import fetch_article, extract_key_content, get_article_crawl_config
                config = get_article_crawl_config()
                timeout_sec = config.get("timeout", 60)
                title, body = fetch_article(url, timeout=timeout_sec)
                max_len = config.get("max_content_length", 12000)
                key_content = extract_key_content(title, body, max_length=max_len)
            except Exception as e:
                logger.exception("抓取文章失败: %s", e)
                return JsonResponse(
                    {"success": False, "error": "抓取文章失败，请检查 URL 或网络。若为微信文章，可能需在浏览器中打开验证后再试。"},
                    status=HTTPStatus.BAD_REQUEST
                )
        else:
            content = _first("content")
            if not content:
                return JsonResponse(
                    {"success": False, "error": "请输入提示词内容"},
                    status=HTTPStatus.BAD_REQUEST
                )
            source_type = "prompt_crawl"
            source_ref = "自定义提示词"
            from src.config import get_config
            cfg = get_config()
            max_len = getattr(cfg, "article_crawl_max_content_length", 12000)
            key_content = content if len(content) <= max_len else content[:max_len] + "\n\n[已截断]"

        logger.info(
            "[article-extract] 开始多模型分析 mode=%s source_type=%s content_len=%s top_n=%s",
            mode, source_type, len(key_content or ""), top_n
        )
        try:
            from src.article_crawl import extract_stocks_from_content, has_any_analyzer_configured, get_article_crawl_config
            stocks = extract_stocks_from_content(key_content, top_n=top_n)
        except Exception as e:
            logger.exception("多模型分析失败: %s", e)
            return JsonResponse(
                {"success": False, "error": "分析失败: " + str(e)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        if not stocks:
            cfg = get_article_crawl_config()
            has_analyzer = has_any_analyzer_configured(cfg)
            logger.info(
                "[article-extract] 未解析出股票 stocks=[] 已配置分析器=%s",
                has_analyzer
            )
            if not has_analyzer:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "未配置「文章/提示词 → 股票」分析用的 AI。请先配置至少一个：DeepSeek、通义千问、豆包或扣子（.env 或 ARTICLE_CRAWL_YAML_PATH 指定的 YAML），再试。",
                    },
                    status=HTTPStatus.BAD_REQUEST
                )
            return JsonResponse(
                {"success": True, "task_ids": [], "source_type": source_type, "message": "未解析出符合条件的股票，请尝试更换 URL 或提示词。"}
            )

        logger.info(
            "[article-extract] 解析出 %s 只股票 codes=%s",
            len(stocks), [s.get("code") for s in stocks]
        )

        task_ids = []
        for item in stocks:
            code = (item.get("code") or "").strip()
            if not code or len(code) != 6:
                continue
            try:
                result = self.analysis_service.submit_analysis(
                    code,
                    report_type=report_type,
                    user_id=context.user_id,
                    source_type=source_type,
                    source_ref=source_ref or None,
                )
                if result.get("success") and result.get("task_id"):
                    task_ids.append(result["task_id"])
            except Exception as e:
                logger.warning("提交股票 %s 分析失败: %s", code, e)

        return JsonResponse({
            "success": True,
            "task_ids": task_ids,
            "source_type": source_type,
            "message": f"已提交 {len(task_ids)} 只股票分析，请在下方面务列表中查看进度。",
        })

    def handle_trading_signals(self, query: Dict[str, list]) -> Response:
        """
        获取最新交易信号 GET /api/trading/signals

        支持两种模式：
        1) 传入股票池：GET /api/trading/signals?stocks=600519,000001,300750
           对传入的股票做一次分析，返回其中适合买入/加仓的信号（不读 .env 的 STOCK_LIST）。
        2) 不传股票池：返回最近一次持久化的信号（来自定时分析或 env 配置的股票列表）。

        供国信 iQuant 策略拉取买入/加仓信号，再在客户端内用 passorder 下单。
        仅当 TRADING_ENABLED=true 时返回有效数据，否则返回 403。
        """
        from src.config import get_config
        from src.trading.execution import get_trading_engine
        from src.trading.signals import build_signals_from_results
        from datetime import date, datetime

        cfg = get_config()
        if not getattr(cfg, "trading_enabled", False):
            return JsonResponse(
                {
                    "success": False,
                    "error": "自动交易未启用",
                    "code": "TRADING_DISABLED",
                    "signals": [],
                },
                status=HTTPStatus.FORBIDDEN
            )

        # 解析请求中的股票池（可选）：?stocks=600519,000001,300750
        stocks_param = (query.get("stocks") or [""])[0]
        if isinstance(stocks_param, list):
            stocks_param = (stocks_param[0] or "") if stocks_param else ""
        stock_codes = [
            c.strip() for c in str(stocks_param).split(",")
            if c and c.strip()
        ]

        if stock_codes:
            # 按传入的股票池实时分析，返回适合买入的信号（不使用 .env 的 STOCK_LIST）
            try:
                from src.core.pipeline import StockAnalysisPipeline
                pipeline = StockAnalysisPipeline()
                results = pipeline.run(
                    stock_codes=stock_codes,
                    dry_run=False,
                    send_notification=False,
                )
                signals = build_signals_from_results(
                    results,
                    only_buy=True,
                    source_date=date.today(),
                )
                now = datetime.now().isoformat()
                return JsonResponse({
                    "success": True,
                    "updated_at": now,
                    "count": len(signals),
                    "signals": [s.to_dict() for s in signals],
                })
            except Exception as e:
                return JsonResponse(
                    {
                        "success": False,
                        "error": str(e),
                        "signals": [],
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR
                )

        # 未传股票池：返回已持久化的最新信号（来自定时任务或 env 股票列表）
        engine = get_trading_engine()
        data = engine.load_latest_signals()
        return JsonResponse({
            "success": True,
            "updated_at": data.get("updated_at"),
            "count": data.get("count", 0),
            "signals": data.get("signals", []),
        })


# ============================================================
# Bot Webhook 处理器
# ============================================================

class BotHandler:
    """
    机器人 Webhook 处理器
    
    处理各平台的机器人回调请求。
    """
    
    def handle_webhook(self, platform: str, form_data: Dict[str, list], headers: Dict[str, str], body: bytes) -> Response:
        """
        处理 Webhook 请求
        
        Args:
            platform: 平台名称 (feishu, dingtalk, wecom, telegram)
            form_data: POST 数据（已解析）
            headers: HTTP 请求头
            body: 原始请求体
            
        Returns:
            Response 对象
        """
        try:
            from bot.handler import handle_webhook
            from bot.models import WebhookResponse
            
            # 调用 bot 模块处理
            webhook_response = handle_webhook(platform, headers, body)
            
            # 转换为 web 响应
            return JsonResponse(
                webhook_response.body,
                status=HTTPStatus(webhook_response.status_code)
            )
            
        except ImportError as e:
            logger.error(f"[BotHandler] Bot 模块未正确安装: {e}")
            return JsonResponse(
                {"error": "Bot module not available"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"[BotHandler] 处理 {platform} Webhook 失败: {e}")
            return JsonResponse(
                {"error": str(e)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


# ============================================================
# 处理器工厂
# ============================================================

_page_handler: PageHandler | None = None
_api_handler: ApiHandler | None = None
_bot_handler: BotHandler | None = None
_static_handler: StaticFileHandler | None = None


def get_page_handler() -> PageHandler:
    """获取页面处理器实例"""
    global _page_handler
    if _page_handler is None:
        _page_handler = PageHandler()
    return _page_handler


def get_api_handler() -> ApiHandler:
    """获取 API 处理器实例"""
    global _api_handler
    if _api_handler is None:
        _api_handler = ApiHandler()
    return _api_handler


def get_bot_handler() -> BotHandler:
    """获取 Bot 处理器实例"""
    global _bot_handler
    if _bot_handler is None:
        _bot_handler = BotHandler()
    return _bot_handler


def get_static_handler() -> StaticFileHandler:
    """获取静态文件处理器实例"""
    global _static_handler
    if _static_handler is None:
        _static_handler = StaticFileHandler()
    return _static_handler
