# -*- coding: utf-8 -*-
"""
===================================
Web 服务层 - 业务逻辑
===================================

职责：
1. 配置管理服务 (ConfigService)
2. 分析任务服务 (AnalysisService)
"""

from __future__ import annotations

import os
import re
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from src.enums import ReportType
from bot.models import BotMessage

logger = logging.getLogger(__name__)

# ============================================================
# 配置管理服务
# ============================================================

_ENV_PATH = os.getenv("ENV_FILE", ".env")

_STOCK_LIST_RE = re.compile(
    r"^(?P<prefix>\s*STOCK_LIST\s*=\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)


class ConfigService:
    """
    配置管理服务
    
    负责 .env 文件中 STOCK_LIST 的读写操作
    """
    
    def __init__(self, env_path: Optional[str] = None):
        self.env_path = env_path or _ENV_PATH
    
    def read_env_text(self) -> str:
        """读取 .env 文件内容"""
        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def write_env_text(self, text: str) -> None:
        """写入 .env 文件内容"""
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write(text)
    
    def get_stock_list(self) -> str:
        """获取当前自选股列表字符串"""
        env_text = self.read_env_text()
        return self._extract_stock_list(env_text)
    
    def set_stock_list(self, stock_list: str) -> str:
        """
        设置自选股列表
        
        Args:
            stock_list: 股票代码字符串（逗号或换行分隔）
            
        Returns:
            规范化后的股票列表字符串
        """
        env_text = self.read_env_text()
        normalized = self._normalize_stock_list(stock_list)
        updated = self._update_stock_list(env_text, normalized)
        self.write_env_text(updated)
        return normalized
    
    def get_env_filename(self) -> str:
        """获取 .env 文件名"""
        return os.path.basename(self.env_path)
    
    def _extract_stock_list(self, env_text: str) -> str:
        """从环境文件中提取 STOCK_LIST 值"""
        for line in env_text.splitlines():
            m = _STOCK_LIST_RE.match(line)
            if m:
                raw = m.group("value").strip()
                # 去除引号
                if (raw.startswith('"') and raw.endswith('"')) or \
                   (raw.startswith("'") and raw.endswith("'")):
                    raw = raw[1:-1]
                return raw
        return ""
    
    def _normalize_stock_list(self, value: str) -> str:
        """规范化股票列表格式"""
        parts = [p.strip() for p in value.replace("\n", ",").split(",")]
        parts = [p for p in parts if p]
        return ",".join(parts)
    
    def _update_stock_list(self, env_text: str, new_value: str) -> str:
        """更新环境文件中的 STOCK_LIST"""
        lines = env_text.splitlines(keepends=False)
        out_lines: List[str] = []
        replaced = False
        
        for line in lines:
            m = _STOCK_LIST_RE.match(line)
            if not m:
                out_lines.append(line)
                continue
            
            out_lines.append(f"{m.group('prefix')}{new_value}{m.group('suffix')}")
            replaced = True
        
        if not replaced:
            if out_lines and out_lines[-1].strip() != "":
                out_lines.append("")
            out_lines.append(f"STOCK_LIST={new_value}")
        
        trailing_newline = env_text.endswith("\n") if env_text else True
        out = "\n".join(out_lines)
        return out + ("\n" if trailing_newline else "")


# ============================================================
# 分析任务服务
# ============================================================

class AnalysisService:
    """
    分析任务服务
    
    负责：
    1. 管理异步分析任务
    2. 执行股票分析
    3. 触发通知推送
    4. 任务持久化（支持 MySQL / 内存存储）
    """
    
    _instance: Optional['AnalysisService'] = None
    _lock = threading.Lock()
    
    def __init__(self, max_workers: int = 3, persist_to_db: bool = True):
        """
        初始化分析任务服务
        
        Args:
            max_workers: 线程池最大工作线程数
            persist_to_db: 是否持久化任务到数据库
        """
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers
        self._tasks: Dict[str, Dict[str, Any]] = {}  # 内存缓存
        self._tasks_lock = threading.Lock()
        self._persist_to_db = persist_to_db
        
        # 延迟初始化数据库相关组件
        self._db_initialized = False
    
    def _init_db(self):
        """延迟初始化数据库连接"""
        if self._db_initialized:
            return
        try:
            from src.config import get_config
            config = get_config()
            self._persist_to_db = self._persist_to_db and config.is_mysql()
            self._db_initialized = True
        except Exception as e:
            logger.warning(f"数据库初始化失败，使用内存存储: {e}")
            self._persist_to_db = False
            self._db_initialized = True
    
    @classmethod
    def get_instance(cls) -> 'AnalysisService':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @property
    def executor(self) -> ThreadPoolExecutor:
        """获取或创建线程池"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="analysis_"
            )
        return self._executor
    
    def submit_analysis(
        self, 
        code: str, 
        report_type: Union[ReportType, str] = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        提交异步分析任务
        
        Args:
            code: 股票代码
            report_type: 报告类型枚举
            source_message: 来源消息（用于机器人回调）
            user_id: 用户 ID（用于持久化和使用量统计）
            
        Returns:
            任务信息字典
        """
        self._init_db()
        
        # 确保 report_type 是枚举类型
        if isinstance(report_type, str):
            report_type = ReportType.from_str(report_type)
        
        task_id = f"{code}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 创建任务记录
        task_data = {
            "task_id": task_id,
            "code": code,
            "status": "pending",
            "start_time": datetime.now().isoformat(),
            "result": None,
            "error": None,
            "report_type": report_type.value,
            "user_id": user_id,
        }
        
        # 保存到内存
        with self._tasks_lock:
            self._tasks[task_id] = task_data.copy()
        
        # 持久化到数据库
        if self._persist_to_db:
            self._persist_task_create(task_id, code, user_id, report_type)
        
        # 立即增加用户分析次数（在任务提交时，而不是完成后）
        if user_id:
            self._increment_user_analysis_count(user_id)
        
        # 提交到线程池
        self.executor.submit(
            self._run_analysis, code, task_id, report_type, source_message, user_id
        )
        
        logger.info(f"[AnalysisService] 已提交股票 {code} 的分析任务, task_id={task_id}, report_type={report_type.value}, user_id={user_id}")
        
        return {
            "success": True,
            "message": "分析任务已提交，将异步执行并推送通知",
            "code": code,
            "task_id": task_id,
            "report_type": report_type.value
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 优先从内存获取
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                return task
        
        # 从数据库获取
        if self._persist_to_db:
            return self._load_task_from_db(task_id)
        
        return None
    
    def list_tasks(self, limit: int = 20, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        列出最近的任务
        
        Args:
            limit: 返回数量限制
            user_id: 用户 ID（如果指定，只返回该用户的任务）
        """
        # 如果持久化到数据库，从数据库查询
        if self._persist_to_db:
            return self._list_tasks_from_db(limit, user_id)
        
        # 从内存获取
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        
        # 过滤用户
        if user_id:
            tasks = [t for t in tasks if t.get('user_id') == user_id]
        
        # 按开始时间倒序
        tasks.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        return tasks[:limit]
    
    def _run_analysis(
        self, 
        code: str, 
        task_id: str, 
        report_type: ReportType = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行单只股票分析
        
        内部方法，在线程池中运行
        
        Args:
            code: 股票代码
            task_id: 任务ID
            report_type: 报告类型枚举
            source_message: 来源消息
            user_id: 用户 ID
        """
        # 更新任务状态为运行中
        self._update_task_status(task_id, "running")
        
        try:
            # 延迟导入避免循环依赖
            from src.config import get_config
            from main import StockAnalysisPipeline
            
            logger.info(f"[AnalysisService] 开始分析股票: {code}")
            
            # 创建分析管道
            config = get_config()
            pipeline = StockAnalysisPipeline(
                config=config,
                max_workers=1,
                source_message=source_message
            )
            
            # 执行单只股票分析（启用单股推送）
            result = pipeline.process_single_stock(
                code=code,
                skip_analysis=False,
                single_stock_notify=True,
                report_type=report_type
            )
            
            if result:
                result_data = {
                    "code": result.code,
                    "name": result.name,
                    "sentiment_score": result.sentiment_score,
                    "operation_advice": result.operation_advice,
                    "trend_prediction": result.trend_prediction,
                    "analysis_summary": result.analysis_summary,
                }
                
                # 更新任务状态
                self._update_task_status(task_id, "completed", result_data=result_data)
                
                # 注意：用户分析次数已在 submit_analysis 中递增，这里不再重复
                
                # 保存分析历史
                if user_id and self._persist_to_db:
                    self._save_analysis_history(
                        user_id, task_id, code, result.name, result_data
                    )
                
                # 发送分析报告到用户邮箱
                if user_id:
                    self._send_report_to_user_email(user_id, result, report_type, pipeline)
                
                logger.info(f"[AnalysisService] 股票 {code} 分析完成: {result.operation_advice}")
                return {"success": True, "task_id": task_id, "result": result_data}
            else:
                self._update_task_status(task_id, "failed", error="分析返回空结果")
                
                logger.warning(f"[AnalysisService] 股票 {code} 分析失败: 返回空结果")
                return {"success": False, "task_id": task_id, "error": "分析返回空结果"}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AnalysisService] 股票 {code} 分析异常: {error_msg}")
            
            self._update_task_status(task_id, "failed", error=error_msg)
            
            return {"success": False, "task_id": task_id, "error": error_msg}
    
    def _update_task_status(
        self,
        task_id: str,
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """更新任务状态（内存 + 数据库）"""
        # 更新内存
        with self._tasks_lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = status
                if status in ("completed", "failed"):
                    self._tasks[task_id]["end_time"] = datetime.now().isoformat()
                if result_data:
                    self._tasks[task_id]["result"] = result_data
                if error:
                    self._tasks[task_id]["error"] = error
        
        # 更新数据库
        if self._persist_to_db:
            self._persist_task_update(task_id, status, result_data, error)
    
    # === 数据库持久化方法 ===
    
    def _persist_task_create(
        self,
        task_id: str,
        code: str,
        user_id: Optional[int],
        report_type: ReportType
    ):
        """持久化创建任务记录"""
        try:
            from src.storage import get_db
            from src.models.task import AnalysisTask
            
            db = get_db()
            with db.get_session() as session:
                task = AnalysisTask(
                    task_id=task_id,
                    user_id=user_id,
                    task_type='single',
                    status='pending',
                    total_count=1,
                )
                task.set_stock_codes([code])
                task.set_params({'report_type': report_type.value})
                session.add(task)
                session.commit()
        except Exception as e:
            logger.error(f"持久化任务创建失败: {e}")
    
    def _persist_task_update(
        self,
        task_id: str,
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """持久化更新任务状态"""
        try:
            from sqlalchemy import select
            from src.storage import get_db
            from src.models.task import AnalysisTask
            
            db = get_db()
            with db.get_session() as session:
                task = session.execute(
                    select(AnalysisTask).where(AnalysisTask.task_id == task_id)
                ).scalar_one_or_none()
                
                if task:
                    if status == 'running':
                        task.start()
                    elif status == 'completed':
                        task.complete(result_data)
                    elif status == 'failed':
                        task.fail(error)
                    else:
                        task.status = status
                    
                    session.commit()
        except Exception as e:
            logger.error(f"持久化任务更新失败: {e}")
    
    def _load_task_from_db(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载任务"""
        try:
            from sqlalchemy import select
            from src.storage import get_db
            from src.models.task import AnalysisTask
            
            db = get_db()
            with db.get_session() as session:
                task = session.execute(
                    select(AnalysisTask).where(AnalysisTask.task_id == task_id)
                ).scalar_one_or_none()
                
                if task:
                    return task.to_dict()
        except Exception as e:
            logger.error(f"从数据库加载任务失败: {e}")
        return None
    
    def _list_tasks_from_db(
        self,
        limit: int = 20,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """从数据库列出任务"""
        try:
            from sqlalchemy import select, and_
            from src.storage import get_db
            from src.models.task import AnalysisTask
            
            db = get_db()
            with db.get_session() as session:
                query = select(AnalysisTask)
                
                if user_id:
                    query = query.where(AnalysisTask.user_id == user_id)
                
                query = query.order_by(AnalysisTask.created_at.desc()).limit(limit)
                
                tasks = session.execute(query).scalars().all()
                return [task.to_dict() for task in tasks]
        except Exception as e:
            logger.error(f"从数据库列出任务失败: {e}")
        
        # 降级到内存查询
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        if user_id:
            tasks = [t for t in tasks if t.get('user_id') == user_id]
        tasks.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        return tasks[:limit]
    
    def _increment_user_analysis_count(self, user_id: int):
        """增加用户分析次数"""
        try:
            from src.services.user_service import get_user_service
            user_service = get_user_service()
            count = user_service.increment_analysis_count(user_id)
            logger.info(f"[AnalysisService] 用户 {user_id} 分析次数已更新: {count}")
        except Exception as e:
            logger.error(f"增加用户分析次数失败 user_id={user_id}: {e}", exc_info=True)
    
    def _save_analysis_history(
        self,
        user_id: int,
        task_id: str,
        code: str,
        name: str,
        result_data: Dict[str, Any]
    ):
        """保存分析历史"""
        try:
            from datetime import date
            from src.services.user_service import get_user_service
            
            user_service = get_user_service()
            
            # 确定情绪
            score = result_data.get('sentiment_score', 0)
            if score >= 70:
                sentiment = 'bullish'
            elif score <= 30:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'
            
            user_service.save_analysis_history(
                user_id=user_id,
                stock_code=code,
                stock_name=name,
                analysis_date=date.today(),
                analysis_result=result_data,
                ai_summary=result_data.get('analysis_summary'),
                score=score,
                sentiment=sentiment,
                task_id=task_id
            )
        except Exception as e:
            logger.error(f"保存分析历史失败: {e}")
    
    def _send_report_to_user_email(
        self,
        user_id: int,
        result,
        report_type: ReportType,
        pipeline
    ):
        """
        发送分析报告到用户的邮箱
        
        Args:
            user_id: 用户 ID
            result: 分析结果
            report_type: 报告类型
            pipeline: 分析管道实例
        """
        try:
            # 获取用户邮箱
            user_email = self._get_user_email(user_id)
            if not user_email:
                logger.info(f"[AnalysisService] 用户 {user_id} 未配置邮箱，跳过邮件发送")
                return
            
            # 检查邮件服务是否可用
            notifier = pipeline.notifier
            if not notifier._is_email_configured():
                logger.warning(f"[AnalysisService] 邮件服务未配置，跳过邮件发送")
                return
            
            # 生成报告内容
            if report_type == ReportType.FULL:
                report_content = notifier.generate_dashboard_report([result])
            else:
                report_content = notifier.generate_single_stock_report(result)
            
            # 生成邮件主题
            subject = f"📈 {result.name}({result.code}) 分析报告 - {result.operation_advice}"
            
            # 发送邮件到用户邮箱
            success = notifier.send_to_email(
                content=report_content,
                subject=subject,
                receivers=[user_email]
            )
            
            if success:
                logger.info(f"[AnalysisService] 分析报告已发送到用户邮箱: {user_email}")
            else:
                logger.warning(f"[AnalysisService] 发送邮件到 {user_email} 失败")
                
        except Exception as e:
            logger.error(f"[AnalysisService] 发送邮件到用户邮箱失败: {e}")
    
    def _get_user_email(self, user_id: int) -> Optional[str]:
        """
        获取用户的邮箱地址
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户的邮箱地址，如果未配置则返回 None
        """
        try:
            from sqlalchemy import select
            from src.storage import get_db
            from src.models.user import User
            
            db = get_db()
            with db.get_session() as session:
                user = session.execute(
                    select(User).where(User.id == user_id)
                ).scalar_one_or_none()
                
                if user and user.email:
                    return user.email
        except Exception as e:
            logger.error(f"获取用户邮箱失败: {e}")
        
        return None


# ============================================================
# 便捷函数
# ============================================================

def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    return ConfigService()


def get_analysis_service() -> AnalysisService:
    """获取分析服务单例"""
    return AnalysisService.get_instance()
