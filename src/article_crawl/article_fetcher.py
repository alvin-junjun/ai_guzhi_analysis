# -*- coding: utf-8 -*-
"""抓取并解析文章内容，提取与 A 股板块、趋势相关的关键内容。"""

import re
import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 模拟浏览器，降低被反爬概率
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_article(url: str, timeout: int = 30) -> tuple:
    """
    请求文章 URL，解析 HTML，返回标题和正文纯文本。
    :return: (title, body_text)
    """
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    title = ""
    title_tag = soup.find("h2", class_="rich_media_title") or soup.find("h1") or soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # 微信公众号正文通常在 id="js_content" 的 div 中
    content_div = soup.find("div", id="js_content") or soup.find("article") or soup.find("main")
    if not content_div:
        content_div = soup.find("body")

    if content_div:
        # 去掉 script、style
        for tag in content_div.find_all(["script", "style"]):
            tag.decompose()
        body = content_div.get_text(separator="\n", strip=True)
    else:
        body = soup.get_text(separator="\n", strip=True)

    # 合并多行空行、去除首尾空白
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return title, body


def extract_key_content(title: str, body: str, max_length: int = 12000) -> str:
    """
    从标题和正文中提取与 A 股、板块、趋势相关的关键内容，便于发给 AI 分析。
    若未做关键词过滤，则对正文做简单截断与清理；可后续扩展关键词高亮或筛选。
    """
    key_keywords = [
        "A股", "板块", "概念", "龙头", "涨停", "趋势", "看好", "推荐", "标的",
        "股票", "代码", "行情", "涨幅", "资金", "主力", "题材", "热点",
        "沪指", "深成指", "创业板", "北向", "机构", "研报", "业绩",
    ]
    lines = body.split("\n")
    kept = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        # 优先保留含关键词的段落
        if any(kw in line for kw in key_keywords):
            kept.append(line)
        else:
            # 也保留一定比例非关键词句，避免遗漏上下文（例如公司名、代码附近句子）
            kept.append(line)

    combined = "\n".join([f"【标题】{title}", "", "【正文摘要】", "\n".join(kept)])
    if len(combined) > max_length:
        combined = combined[:max_length] + "\n\n[内容已截断]"
    return combined
