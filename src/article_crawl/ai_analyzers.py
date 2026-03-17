# -*- coding: utf-8 -*-
"""调用各 AI 分析文章内容，要求返回文中与 A 股相关的股票代码与名称。"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List

import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

STOCK_ANALYSIS_SYSTEM = """你是一位 A 股分析助手。用户提供的内容可能是以下两种之一，你都需要尽力推断并输出 A 股股票列表：
1) 文章摘要或段落：若提到具体股票则优先列出；若只提到板块/行业/概念（如 AIDC、数据中心、内蒙古、亚马逊、腾讯、遂原科技等），则根据该方向推断 A 股龙头或代表标的。
2) 用户的直接提问或主题描述（例如「帮我分析 AIDC/内蒙古+亚马逊/腾讯+遂原科技 的龙头股票」）：请把问题中的关键词视为主题（如 AIDC、内蒙古、亚马逊、腾讯、遂原科技 等），推断与之相关的 A 股龙头或代表标的并列出，不要因为输入是「问题句式」就返回空数组。
只输出一个 JSON 数组，不要其他解释。每个元素格式：{"code": "股票代码", "name": "股票名称"}。股票代码为 6 位数字（沪市 60、深市 00/30、北交所 8 开头等）。
仅当内容与 A 股完全无关、且无法从任何关键词推断出标的时，才输出空数组 []。只要能从主题/概念推断出相关标的，就应输出 3～8 只。
示例：[{"code": "600519", "name": "贵州茅台"}, {"code": "000858", "name": "五粮液"}]"""

STOCK_ANALYSIS_USER_TEMPLATE = """请根据以下内容推断与 A 股相关且方向一致的股票并列出。
内容可能是：文章摘要、板块/概念描述，或用户的提问（如「帮我分析…龙头股票」）。若为提问或主题，请根据其中的关键词（如 AIDC、内蒙古、亚马逊、腾讯、遂原科技 等）推断相关 A 股龙头或代表标的，不要因是问句就返回空数组。
仅输出 JSON 数组，格式 [{"code":"六位代码","name":"股票名称"}]，无法推断时再输出 []。

%s"""


def _normalize_response_text(text: str) -> str:
    """去掉 markdown 代码块包裹，便于解析 JSON 数组。"""
    text = (text or "").strip()
    if not text:
        return ""
    # 去掉 ```json ... ``` 或 ``` ... ```
    for marker in ("```json", "```"):
        if marker in text:
            idx = text.find(marker)
            rest = text[idx + len(marker) :].strip()
            end = rest.find("```")
            if end != -1:
                text = rest[:end].strip()
            else:
                text = rest
            break
    return text.strip()


def _parse_stocks_from_response(text: str) -> List[Dict[str, str]]:
    """从 AI 返回的文本中解析出 [{"code":"...","name":"..."}]。"""
    text = _normalize_response_text(text or "")
    if not text:
        return []
    start = text.find("[")
    if start == -1:
        return []
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return []
    try:
        arr = json.loads(text[start:end])
        if not isinstance(arr, list):
            return []
        result = []
        for item in arr:
            if isinstance(item, dict):
                code = (item.get("code") or item.get("股票代码") or "").strip()
                name = (item.get("name") or item.get("股票名称") or item.get("名称") or "").strip()
                if isinstance(code, (int, float)):
                    code = str(int(code))
                if code and name:
                    if len(code) != 6 and code.isdigit():
                        code = code.zfill(6)
                    result.append({"code": code, "name": name})
        return result
    except json.JSONDecodeError:
        return []


def call_deepseek(content: str, api_key: str, base_url: str, model: str, timeout: int) -> List[Dict[str, str]]:
    """DeepSeek：OpenAI 兼容接口。"""
    user_content = STOCK_ANALYSIS_USER_TEMPLATE % content
    logger.info(
        "[LLM调用/DeepSeek] 输入: model=%s, base_url=%s, content_len=%d, user_msg_len=%d",
        model, base_url, len(content), len(user_content),
    )
    logger.info("[LLM调用/DeepSeek] user 内容预览: %s", (user_content[:600] + "...") if len(user_content) > 600 else user_content)
    logger.debug("[LLM调用/DeepSeek] 完整 user 内容: %s", user_content)
    client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": STOCK_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        timeout=timeout,
    )
    elapsed = time.time() - t0
    text = (resp.choices[0].message.content or "").strip()
    stocks = _parse_stocks_from_response(text)
    logger.info(
        "[LLM调用/DeepSeek] 输出: 耗时=%.2fs, 原始长度=%d, 解析股票数=%d",
        elapsed, len(text), len(stocks),
    )
    logger.info("[LLM调用/DeepSeek] 原始响应预览: %s", (text[:600] + "...") if len(text) > 600 else text)
    logger.debug("[LLM调用/DeepSeek] 完整原始响应: %s", text)
    if not stocks and text:
        logger.debug("[article_crawl] DeepSeek 原始返回(解析 0 只): %s", text[:500])
    return stocks


def call_tongyi(content: str, api_key: str, model: str, timeout: int) -> List[Dict[str, str]]:
    """通义千问：DashScope。"""
    try:
        import dashscope
        from dashscope import Generation
    except ImportError:
        logger.warning("未安装 dashscope，跳过通义千问")
        return []
    user_content = STOCK_ANALYSIS_USER_TEMPLATE % content
    logger.info(
        "[LLM调用/通义千问] 输入: model=%s, content_len=%d, user_msg_len=%d",
        model, len(content), len(user_content),
    )
    logger.info("[LLM调用/通义千问] user 内容预览: %s", (user_content[:600] + "...") if len(user_content) > 600 else user_content)
    logger.debug("[LLM调用/通义千问] 完整 user 内容: %s", user_content)
    dashscope.api_key = api_key
    t0 = time.time()
    resp = Generation.call(
        model=model,
        messages=[
            {"role": "system", "content": STOCK_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        result_format="message",
    )
    elapsed = time.time() - t0
    if resp.status_code != 200:
        logger.warning("[LLM调用/通义千问] 调用失败: status_code=%s, resp=%s", resp.status_code, resp)
        return []
    text = (resp.output.choices[0].message.content or "").strip()
    stocks = _parse_stocks_from_response(text)
    logger.info(
        "[LLM调用/通义千问] 输出: 耗时=%.2fs, 原始长度=%d, 解析股票数=%d",
        elapsed, len(text), len(stocks),
    )
    logger.info("[LLM调用/通义千问] 原始响应预览: %s", (text[:600] + "...") if len(text) > 600 else text)
    logger.debug("[LLM调用/通义千问] 完整原始响应: %s", text)
    if not stocks and text:
        logger.debug("[article_crawl] 通义千问 原始返回(解析 0 只): %s", text[:500])
    return stocks


def call_doubao(content: str, api_key: str, base_url: str, model: str, timeout: int) -> List[Dict[str, str]]:
    """豆包：火山方舟 OpenAI 兼容接口。支持 v3，若 404 则自动尝试 v1。"""
    user_content = STOCK_ANALYSIS_USER_TEMPLATE % content
    logger.info(
        "[LLM调用/豆包] 输入: model=%s, base_url=%s, content_len=%d, user_msg_len=%d",
        model, base_url, len(content), len(user_content),
    )
    logger.info("[LLM调用/豆包] user 内容预览: %s", (user_content[:600] + "...") if len(user_content) > 600 else user_content)
    logger.debug("[LLM调用/豆包] 完整 user 内容: %s", user_content)
    base = base_url.rstrip("/")
    url = base + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": STOCK_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_content},
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    t0 = time.time()
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code == 404 and "/api/v3" in base:
        base_v1 = base.replace("/api/v3", "/api/v1")
        url_v1 = base_v1 + "/chat/completions"
        logger.info("[article_crawl] 豆包 v3 返回 404，尝试 v1: %s", url_v1)
        resp = requests.post(url_v1, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        if resp.status_code == 404:
            logger.warning(
                "[article_crawl] 豆包 404，请确认：1) base_url 与火山方舟控制台中「推理接入点」的调用地址一致；2) model 为接入点 ID（如 ep-xxxxx）。响应: %s",
                resp.text[:300] if resp.text else resp.status_code,
            )
        else:
            logger.warning("[article_crawl] 豆包 HTTP %s: %s", resp.status_code, resp.text[:300] if resp.text else "")
        resp.raise_for_status()
    elapsed = time.time() - t0
    data = resp.json()
    text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    stocks = _parse_stocks_from_response(text)
    logger.info(
        "[LLM调用/豆包] 输出: 耗时=%.2fs, 原始长度=%d, 解析股票数=%d",
        elapsed, len(text), len(stocks),
    )
    logger.info("[LLM调用/豆包] 原始响应预览: %s", (text[:600] + "...") if len(text) > 600 else text)
    logger.debug("[LLM调用/豆包] 完整原始响应: %s", text)
    if not stocks and text:
        logger.debug("[article_crawl] 豆包 原始返回(解析 0 只): %s", text[:500])
    return stocks


def call_coze(content: str, api_key: str, bot_id: str, base_url: str, timeout: int) -> List[Dict[str, str]]:
    """扣子 Coze：先发 chat 再轮询取结果。"""
    user_content = STOCK_ANALYSIS_USER_TEMPLATE % content
    logger.info(
        "[LLM调用/扣子] 输入: bot_id=%s, base_url=%s, content_len=%d, query_len=%d",
        bot_id, base_url, len(content), len(user_content),
    )
    logger.info("[LLM调用/扣子] query 预览: %s", (user_content[:600] + "...") if len(user_content) > 600 else user_content)
    logger.debug("[LLM调用/扣子] 完整 query: %s", user_content)
    chat_url = base_url.rstrip("/") + "/open_api/v2/chat"
    user_id = str(uuid.uuid4())
    payload = {
        "bot_id": bot_id,
        "user_id": user_id,
        "stream": False,
        "auto_save_history": True,
        "query": user_content,
    }
    t0 = time.time()
    r = requests.post(
        chat_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        logger.warning("[LLM调用/扣子] chat 返回错误: %s", data)
        return []
    conv_id = data.get("data", {}).get("conversation_id")
    chat_id = data.get("data", {}).get("id")
    if not conv_id or not chat_id:
        logger.warning("[LLM调用/扣子] 未返回 conversation_id/chat_id: %s", data)
        return []

    msg_url = base_url.rstrip("/") + "/open_api/v2/chat/retrieve"
    for _ in range(30):
        time.sleep(1.5)
        mr = requests.post(
            msg_url,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={"conversation_id": conv_id, "chat_id": chat_id},
            timeout=timeout,
        )
        mr.raise_for_status()
        md = mr.json()
        if md.get("code") != 0:
            continue
        status = md.get("data", {}).get("status")
        if status == "completed":
            elapsed = time.time() - t0
            messages = md.get("data", {}).get("message", {}).get("content", []) or []
            for m in messages:
                if m.get("type") == "answer":
                    text = (m.get("content", "") or "").strip()
                    stocks = _parse_stocks_from_response(text)
                    logger.info(
                        "[LLM调用/扣子] 输出: 耗时=%.2fs, 原始长度=%d, 解析股票数=%d",
                        elapsed, len(text), len(stocks),
                    )
                    logger.info("[LLM调用/扣子] 原始响应预览: %s", (text[:600] + "...") if len(text) > 600 else text)
                    logger.debug("[LLM调用/扣子] 完整原始响应: %s", text)
                    return stocks
            logger.info("[LLM调用/扣子] 输出: 耗时=%.2fs, 无 answer 消息", elapsed)
            return []
        if status in ("failed", "cancelled"):
            logger.warning("[LLM调用/扣子] 会话失败: %s", status)
            return []
    logger.warning("[LLM调用/扣子] 轮询超时")
    return []


def _is_deepseek_enabled(c: Dict[str, Any]) -> bool:
    return bool(c.get("enabled") and c.get("api_key"))


def _is_tongyi_enabled(c: Dict[str, Any]) -> bool:
    return bool(c.get("enabled") and c.get("api_key"))


def _is_doubao_enabled(c: Dict[str, Any]) -> bool:
    return bool(c.get("enabled") and c.get("api_key") and c.get("model"))


def _is_coze_enabled(c: Dict[str, Any]) -> bool:
    return bool(c.get("enabled") and c.get("api_key") and c.get("bot_id"))


def run_all_analyzers(
    content: str,
    config: Dict[str, Any],
) -> Dict[str, List[Dict[str, str]]]:
    """
    根据 config 依次调用已配置的 AI，返回 { "DeepSeek": [...], "通义千问": [...], ... }。
    以「是否启用」为唯一依据：凡被判定为已配置的分析器都会且仅会被调用一次，再整合结果。
    """
    timeout = config.get("timeout", 60)
    max_len = config.get("max_content_length", 12000)
    if len(content) > max_len:
        content = content[:max_len] + "\n\n[已截断]"
    results = {}

    # 统一：先确定哪些分析器已配置，再按该列表依次调用（保证每个都调用一次）
    analyzers = [
        ("DeepSeek", "deepseek", _is_deepseek_enabled),
        ("通义千问", "tongyi", _is_tongyi_enabled),
        ("豆包", "doubao", _is_doubao_enabled),
        ("扣子", "coze", _is_coze_enabled),
    ]
    enabled_names = []
    for name, key, is_enabled in analyzers:
        c = config.get(key, {})
        if isinstance(c, dict) and is_enabled(c):
            enabled_names.append((name, key))
    logger.info(
        "[article_crawl] 已配置的 AI 分析器: %s",
        [n for n, _ in enabled_names] if enabled_names else "无（未解析出股票将不调用任何大模型）",
    )

    for name, key in enabled_names:
        c = config.get(key, {}) or {}
        try:
            logger.info("[article_crawl] 开始调用 %s", name)
            if key == "deepseek":
                stocks = call_deepseek(
                    content,
                    api_key=c["api_key"],
                    base_url=c.get("base_url", "https://api.deepseek.com"),
                    model=c.get("model", "deepseek-chat"),
                    timeout=timeout,
                )
            elif key == "tongyi":
                stocks = call_tongyi(
                    content,
                    api_key=c["api_key"],
                    model=c.get("model", "qwen-plus"),
                    timeout=timeout,
                )
            elif key == "doubao":
                stocks = call_doubao(
                    content,
                    api_key=c["api_key"],
                    base_url=c.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"),
                    model=c["model"],
                    timeout=timeout,
                )
            elif key == "coze":
                stocks = call_coze(
                    content,
                    api_key=c["api_key"],
                    bot_id=c["bot_id"],
                    base_url=c.get("base_url", "https://api.coze.cn"),
                    timeout=timeout,
                )
            else:
                stocks = []
            results[name] = stocks
            if len(stocks) == 0:
                logger.info(
                    "[article_crawl] %s 返回 0 只股票（若需排查请将 log_level 设为 DEBUG 查看原始返回）",
                    name,
                )
            else:
                logger.info("[article_crawl] %s 返回 %s 只股票", name, len(stocks))
        except Exception as e:
            logger.exception("[article_crawl] %s 调用异常: %s", name, e)
            results[name] = []

    logger.info("[article_crawl] run_all_analyzers 完成 共 %s 路结果", len(results))
    return results
