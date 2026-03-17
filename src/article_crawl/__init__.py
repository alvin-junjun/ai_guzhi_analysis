# -*- coding: utf-8 -*-
"""
文章/提示词抓取股票模块

从指定 URL 抓取文章或用户输入的提示词，经多模型分析得到股票列表，供后续接入本系统的单股分析。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_article_crawl_config() -> Dict[str, Any]:
    """
    获取文章抓取与多模型分析配置。
    优先从 Config.article_crawl_yaml_path 指定的 YAML 加载；
    若未配置或文件不存在，则从当前项目 Config 的 env 回退字段构建。
    """
    try:
        from src.config import get_config
        import yaml
    except ImportError:
        yaml = None
        get_config = None

    cfg = get_config() if get_config else None
    if not cfg:
        return {"timeout": 60, "max_content_length": 12000, "deepseek": {}, "tongyi": {}, "doubao": {}, "coze": {}}

    yaml_path = getattr(cfg, "article_crawl_yaml_path", None)
    if yaml_path and yaml:
        p = Path(yaml_path)
        if not p.is_absolute():
            # 相对路径相对于项目根目录（src/article_crawl -> 上级两级为项目根）
            p = Path(__file__).resolve().parent.parent.parent / yaml_path
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}
                # 若 YAML 顶层包含 article_crawl 键，使用其内容为扁平 config（与 env 回退一致）
                if isinstance(raw, dict) and "article_crawl" in raw:
                    raw = raw["article_crawl"] or {}
                if isinstance(raw, dict):
                    return raw
                return {}
            except Exception as e:
                logger.warning("加载文章抓取 YAML 配置失败: %s", e)

    # 从 Config 的 env 回退构建（与 jiangyan_guzhi config.example.yaml 结构一致）
    timeout = getattr(cfg, "article_crawl_timeout", 60)
    max_content_length = getattr(cfg, "article_crawl_max_content_length", 12000)
    deepseek = {
        "enabled": getattr(cfg, "article_crawl_deepseek_enabled", False),
        "api_key": getattr(cfg, "article_crawl_deepseek_api_key", None),
        "base_url": getattr(cfg, "article_crawl_deepseek_base_url", "https://api.deepseek.com"),
        "model": getattr(cfg, "article_crawl_deepseek_model", "deepseek-chat"),
    }
    tongyi = {
        "enabled": getattr(cfg, "article_crawl_tongyi_enabled", False),
        "api_key": getattr(cfg, "article_crawl_tongyi_api_key", None),
        "model": getattr(cfg, "article_crawl_tongyi_model", "qwen-plus"),
    }
    doubao = {
        "enabled": getattr(cfg, "article_crawl_doubao_enabled", False),
        "api_key": getattr(cfg, "article_crawl_doubao_api_key", None),
        "base_url": getattr(cfg, "article_crawl_doubao_base_url", "https://ark.cn-beijing.volces.com/api/v3"),
        "model": getattr(cfg, "article_crawl_doubao_model", None),
    }
    coze = {
        "enabled": getattr(cfg, "article_crawl_coze_enabled", False),
        "api_key": getattr(cfg, "article_crawl_coze_api_key", None),
        "bot_id": getattr(cfg, "article_crawl_coze_bot_id", None),
        "base_url": getattr(cfg, "article_crawl_coze_base_url", "https://api.coze.cn"),
    }
    return {
        "timeout": timeout,
        "max_content_length": max_content_length,
        "deepseek": deepseek,
        "tongyi": tongyi,
        "doubao": doubao,
        "coze": coze,
    }


def has_any_analyzer_configured(config: Dict[str, Any] = None) -> bool:
    """
    检查是否已配置至少一个用于「文章/提示词 → 股票列表」的 AI 分析器。
    若未配置，前端会提示「未解析出股票」且日志中不会有任何大模型调用。
    """
    if config is None:
        config = get_article_crawl_config()
    ds = config.get("deepseek", {})
    if ds.get("enabled") and ds.get("api_key"):
        return True
    tq = config.get("tongyi", {})
    if tq.get("enabled") and tq.get("api_key"):
        return True
    db = config.get("doubao", {})
    if db.get("enabled") and db.get("api_key") and db.get("model"):
        return True
    cz = config.get("coze", {})
    if cz.get("enabled") and cz.get("api_key") and cz.get("bot_id"):
        return True
    return False


def extract_stocks_from_content(
    content: str,
    top_n: int = 5,
    config_override: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """
    从已有关键内容字符串（来自 URL 抓取或用户提示词）经多模型分析，合并排序后返回股票列表。

    Args:
        content: 待分析文本（文章摘要或用户输入的提示词）
        top_n: 返回前 N 只股票，默认 5
        config_override: 可选，覆盖 get_article_crawl_config() 的部分配置

    Returns:
        [{"code": "600519", "name": "贵州茅台", "count": 2, "sources": ["DeepSeek", "通义千问"]}, ...]
    """
    from src.article_crawl.ai_analyzers import run_all_analyzers
    from src.article_crawl.merge_results import merge_and_rank

    config = get_article_crawl_config()
    if config_override:
        for k, v in config_override.items():
            if k in config and isinstance(config[k], dict) and isinstance(v, dict):
                config[k] = {**config[k], **v}
            else:
                config[k] = v

    logger.info("[article_crawl] extract_stocks_from_content 开始 content_len=%s top_n=%s", len(content or ""), top_n)
    ai_results = run_all_analyzers(content, config)
    merged = merge_and_rank(ai_results, top_n=top_n)
    logger.info("[article_crawl] 多模型分析完成 合并后股票数=%s", len(merged))
    return merged


# 便于外部直接调用抓取 URL
def fetch_article(url: str, timeout: int = 30):
    from src.article_crawl.article_fetcher import fetch_article as _fetch
    return _fetch(url, timeout=timeout)


def extract_key_content(title: str, body: str, max_length: int = 12000):
    from src.article_crawl.article_fetcher import extract_key_content as _extract
    return _extract(title, body, max_length=max_length)
