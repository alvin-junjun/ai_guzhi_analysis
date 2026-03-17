# -*- coding: utf-8 -*-
"""合并各 AI 的股票列表，按出现次数排序，选出符合文章描述概率最高的前 N 只。"""

from collections import defaultdict
from typing import Any


def merge_and_rank(ai_results: dict, top_n: int = 5) -> list:
    """
    合并多路 AI 结果：同一股票代码可能对应不同名称，以「代码」为唯一键统计被推荐的次数。
    返回按「被推荐次数」降序的前 top_n 只，每项含 code, name, count, sources。
    """
    by_code = defaultdict(lambda: ("", 0, set()))

    for source, stocks in ai_results.items():
        for s in stocks:
            code = (s.get("code") or "").strip()
            name = (s.get("name") or "").strip()
            if not code:
                continue
            if len(code) != 6 and code.isdigit():
                code = code.zfill(6)
            prev_name, count, sources = by_code[code]
            by_code[code] = (name or prev_name or code, count + 1, sources | {source})

    sorted_items = sorted(
        by_code.items(),
        key=lambda x: (-x[1][1], x[0]),
    )
    result = []
    for code, (name, count, sources) in sorted_items[:top_n]:
        result.append({
            "code": code,
            "name": name or code,
            "count": count,
            "sources": sorted(sources),
        })
    return result
