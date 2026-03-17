# -*- coding: utf-8 -*-
"""
===================================
Web 模板层 - HTML 页面生成
===================================

职责：
1. 生成 HTML 页面
2. 管理 CSS 样式
3. 提供可复用的页面组件
"""

from __future__ import annotations

import html
from typing import Optional


# ============================================================
# CSS 样式定义
# ============================================================

BASE_CSS = """
:root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #1e293b;
    --text-light: #64748b;
    --border: #e2e8f0;
    --success: #10b981;
    --error: #ef4444;
    --warning: #f59e0b;
}

* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: var(--bg);
    color: var(--text);
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    margin: 0;
    padding: 20px;
}

.container {
    background: var(--card);
    padding: 2rem;
    border-radius: 1rem;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    width: 100%;
    max-width: 500px;
}

h2 {
    margin-top: 0;
    color: var(--text);
    font-size: 1.5rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.subtitle {
    color: var(--text-light);
    font-size: 0.875rem;
    margin-bottom: 2rem;
    line-height: 1.5;
}

.code-badge {
    background: #f1f5f9;
    padding: 0.2rem 0.4rem;
    border-radius: 0.25rem;
    font-family: monospace;
    color: var(--primary);
}

.form-group {
    margin-bottom: 1.5rem;
}

label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text);
}

textarea, input[type="text"] {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    font-family: monospace;
    font-size: 0.875rem;
    line-height: 1.5;
    resize: vertical;
    transition: border-color 0.2s, box-shadow 0.2s;
}

textarea:focus, input[type="text"]:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

button {
    background-color: var(--primary);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    width: 100%;
    font-size: 1rem;
}

button:hover {
    background-color: var(--primary-hover);
    transform: translateY(-1px);
}

button:active {
    transform: translateY(0);
}

.btn-secondary {
    background-color: var(--text-light);
}

.btn-secondary:hover {
    background-color: var(--text);
}

.footer {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--text-light);
    font-size: 0.75rem;
    text-align: center;
}

/* Toast Notification */
.toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: white;
    border-left: 4px solid var(--success);
    padding: 1rem 1.5rem;
    border-radius: 0.5rem;
    box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    opacity: 0;
    z-index: 1000;
}

.toast.show {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
}

.toast.error {
    border-left-color: var(--error);
}

.toast.warning {
    border-left-color: var(--warning);
}

/* Helper classes */
.text-muted {
    font-size: 0.75rem;
    color: var(--text-light);
    margin-top: 0.5rem;
}

.mt-2 { margin-top: 0.5rem; }
.mt-4 { margin-top: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-4 { margin-bottom: 1rem; }

/* Section divider */
.section-divider {
    margin: 2rem 0;
    border: none;
    border-top: 1px solid var(--border);
}

/* Analysis section */
.analysis-section {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
}

.analysis-section h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--text);
}

.input-group {
    display: flex;
    gap: 0.5rem;
}

.input-group input {
    flex: 1;
    resize: none;
}

.input-group button {
    width: auto;
    padding: 0.75rem 1.25rem;
    white-space: nowrap;
}

.report-select {
    padding: 0.75rem 0.5rem;
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    font-size: 0.8rem;
    background: white;
    color: var(--text);
    cursor: pointer;
    min-width: 110px;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.report-select:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.btn-analysis {
    background-color: var(--success);
}

.btn-analysis:hover {
    background-color: #059669;
}

.btn-analysis:disabled {
    background-color: var(--text-light);
    cursor: not-allowed;
    transform: none;
}

/* Result box */
.result-box {
    margin-top: 1rem;
    padding: 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    display: none;
}

.result-box.show {
    display: block;
}

.result-box.success {
    background-color: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
}

.result-box.error {
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
}

.result-box.loading {
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1e40af;
}

.spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
    margin-right: 0.5rem;
    vertical-align: middle;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Task List Container */
.task-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-height: 400px;
    overflow-y: auto;
}

.task-list:empty::after {
    content: '暂无任务';
    display: block;
    text-align: center;
    color: var(--text-light);
    font-size: 0.8rem;
    padding: 1rem;
}

/* Task Card - Compact */
.task-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.75rem;
    background: var(--bg);
    border-radius: 0.5rem;
    border: 1px solid var(--border);
    font-size: 0.8rem;
    transition: all 0.2s;
}

.task-card:hover {
    border-color: var(--primary);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.task-card.running {
    border-color: var(--primary);
    background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
}

.task-card.completed {
    border-color: var(--success);
    background: linear-gradient(135deg, #ecfdf5 0%, #f8fafc 100%);
}

.task-card.failed {
    border-color: var(--error);
    background: linear-gradient(135deg, #fef2f2 0%, #f8fafc 100%);
}

/* Task Status Icon */
.task-status {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    flex-shrink: 0;
    font-size: 0.9rem;
}

.task-card.running .task-status {
    background: var(--primary);
    color: white;
}

.task-card.completed .task-status {
    background: var(--success);
    color: white;
}

.task-card.failed .task-status {
    background: var(--error);
    color: white;
}

.task-card.pending .task-status {
    background: var(--border);
    color: var(--text-light);
}

/* Task Main Info */
.task-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
}

.task-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    color: var(--text);
}

.task-title .code {
    font-family: monospace;
    background: rgba(0,0,0,0.05);
    padding: 0.1rem 0.3rem;
    border-radius: 0.25rem;
}

.task-title .name {
    color: var(--text-light);
    font-weight: 400;
    font-size: 0.75rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.task-meta {
    display: flex;
    gap: 0.75rem;
    font-size: 0.7rem;
    color: var(--text-light);
}

.task-meta span {
    display: flex;
    align-items: center;
    gap: 0.2rem;
}

/* Task Result Badge */
.task-result {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.15rem;
    flex-shrink: 0;
}

.task-advice {
    font-weight: 600;
    font-size: 0.75rem;
    padding: 0.15rem 0.4rem;
    border-radius: 0.25rem;
    background: var(--primary);
    color: white;
}

.task-advice.buy { background: #059669; }
.task-advice.sell { background: #dc2626; }
.task-advice.hold { background: #d97706; }
.task-advice.wait { background: #6b7280; }

.task-score {
    font-size: 0.7rem;
    color: var(--text-light);
}

/* Task Actions */
.task-actions {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
}

.task-btn {
    width: 24px;
    height: 24px;
    padding: 0;
    border-radius: 0.25rem;
    background: transparent;
    color: var(--text-light);
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
}

.task-btn:hover {
    background: rgba(0,0,0,0.05);
    color: var(--text);
    transform: none;
}

/* Spinner in task */
.task-card .spinner {
    width: 12px;
    height: 12px;
    border-width: 1.5px;
    margin: 0;
}

/* Empty state hint */
.task-hint {
    text-align: center;
    padding: 0.75rem;
    color: var(--text-light);
    font-size: 0.75rem;
    background: var(--bg);
    border-radius: 0.375rem;
}

/* Task detail expand */
.task-detail {
    display: none;
    padding: 0.5rem 0.75rem;
    padding-left: 3rem;
    background: rgba(0,0,0,0.02);
    border-radius: 0 0 0.5rem 0.5rem;
    margin-top: -0.5rem;
    font-size: 0.75rem;
    border: 1px solid var(--border);
    border-top: none;
}

.task-detail.show {
    display: block;
}

.task-detail-row {
    display: flex;
    justify-content: space-between;
    padding: 0.25rem 0;
}

.task-detail-row .label {
    color: var(--text-light);
}

.task-detail-summary {
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: white;
    border-radius: 0.25rem;
    line-height: 1.4;
}
"""


# ============================================================
# 页面模板
# ============================================================

def render_base(
    title: str,
    content: str,
    extra_css: str = "",
    extra_js: str = ""
) -> str:
    """
    渲染基础 HTML 模板

    Args:
        title: 页面标题
        content: 页面内容 HTML
        extra_css: 额外的 CSS 样式
        extra_js: 额外的 JavaScript
    """
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>{BASE_CSS}{extra_css}</style>
</head>
<body>
  {content}
  {extra_js}
</body>
</html>"""


def render_toast(message: str, toast_type: str = "success") -> str:
    """
    渲染 Toast 通知

    Args:
        message: 通知消息
        toast_type: 类型 (success, error, warning)
    """
    icon_map = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️"
    }
    icon = icon_map.get(toast_type, "ℹ️")
    type_class = f" {toast_type}" if toast_type != "success" else ""

    return f"""
    <div id="toast" class="toast show{type_class}">
        <span class="icon">{icon}</span> {html.escape(message)}
    </div>
    <script>
        setTimeout(() => {{
            document.getElementById('toast').classList.remove('show');
        }}, 3000);
    </script>
    """


def _build_nav_ssr_html(nav_ssr: dict) -> tuple:
    """根据服务端鉴权结果生成导航栏 HTML，用于首屏直出，避免登录后仍显示未登录。"""
    display_name = nav_ssr.get("display_name") or "用户"
    level_text = nav_ssr.get("level_text") or "免费版"
    is_vip = nav_ssr.get("is_vip", False)
    user_info_html = f'👤 {html.escape(display_name)} <span style="color:#999;font-size:12px;">({html.escape(level_text)})</span>'
    links = ['<a href="/user">👤 个人中心</a>', '<a href="/user/history">📋 历史记录</a>',
             '<a href="#" class="btn-share" onclick="copyShareLink(event)">📤 分享</a>']
    if not is_vip:
        links.append('<a href="/membership" class="btn-vip">⭐ 升级会员</a>')
    else:
        links.append('<a href="/membership">💎 会员中心</a>')
    links.append('<a href="#" class="btn-logout" onclick="logout()">退出</a>')
    nav_links_html = "".join(links)
    return user_info_html, nav_links_html


def render_config_page(
    stock_list: str = "",
    message: Optional[str] = None,
    nav_ssr: Optional[dict] = None,
) -> bytes:
    """
    渲染配置页面

    Args:
        stock_list: 当前自选股列表（已弃用，保留兼容）
        message: 可选的提示消息
        nav_ssr: 服务端鉴权结果，用于首屏渲染导航栏，避免首屏一直显示加载中。
                 格式: {"display_name", "level_text", "is_vip"} 已登录；
                       {"unauthenticated": True} 未登录；None 表示未传 headers 的兜底。
    """
    toast_html = render_toast(message) if message else ""
    if nav_ssr:
        if nav_ssr.get("unauthenticated"):
            nav_initial = '<span id="nav_user_info">未登录</span><div id="nav_links" class="nav-links"><a href="/login">🔑 登录</a><a href="/register">📝 注册</a></div>'
        else:
            nav_user_info_html, nav_links_html = _build_nav_ssr_html(nav_ssr)
            nav_initial = f'<span id="nav_user_info">{nav_user_info_html}</span><div id="nav_links" class="nav-links">{nav_links_html}</div>'
        nav_data_ssr = ' data-nav-ssr="1"'
    else:
        nav_initial = '<span id="nav_user_info">加载中...</span><div id="nav_links" class="nav-links"></div>'
        nav_data_ssr = ""

    # 分析组件的 JavaScript - 支持多任务
    analysis_js = """
<script>
(function() {
    const codeInput = document.getElementById('analysis_code');
    const submitBtn = document.getElementById('analysis_btn');
    const taskList = document.getElementById('task_list');
    const reportTypeSelect = document.getElementById('report_type');

    // 任务管理
    const tasks = new Map(); // taskId -> {task, pollCount}
    let pollInterval = null;
    const MAX_POLL_COUNT = 120; // 6 分钟超时：120 * 3000ms = 360000ms
    const POLL_INTERVAL_MS = 3000;
    const MAX_TASKS_DISPLAY = 10;

    // 允许输入数字和字母和点（支持港股 HKxxxxx 格式 美股AAPL/BRK.B）
    codeInput.addEventListener('input', function(e) {
        // 转大写，只保留字母和数字和点
        this.value = this.value.toUpperCase().replace(/[^A-Z0-9.]/g, '');
        if (this.value.length > 8) {
            this.value = this.value.slice(0, 8);
        }
        updateButtonState();
    });

    // 回车提交
    codeInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (!submitBtn.disabled) {
                submitAnalysis();
            }
        }
    });

    // 更新按钮状态 - 支持 A股(6位数字) 或 港股(HK+5位数字)
    function updateButtonState() {
        const code = codeInput.value.trim();
        const isAStock = /^\\d{6}$/.test(code);           // A股: 600519
        const isHKStock = /^HK\\d{5}$/.test(code);        // 港股: HK00700
        const isUSStock =  /^[A-Z]{1,5}(\.[A-Z]{1,2})?$/.test(code); // 美股: AAPL

        submitBtn.disabled = !(isAStock || isHKStock || isUSStock);
    }

    // 格式化时间
    function formatTime(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
    }

    // 计算耗时
    function calcDuration(start, end) {
        if (!start) return '-';
        const startTime = new Date(start).getTime();
        const endTime = end ? new Date(end).getTime() : Date.now();
        const seconds = Math.floor((endTime - startTime) / 1000);
        if (seconds < 60) return seconds + 's';
        const minutes = Math.floor(seconds / 60);
        const remainSec = seconds % 60;
        return minutes + 'm' + remainSec + 's';
    }

    // 获取建议样式类
    function getAdviceClass(advice) {
        if (!advice) return '';
        if (advice.includes('买') || advice.includes('加仓')) return 'buy';
        if (advice.includes('卖') || advice.includes('减仓')) return 'sell';
        if (advice.includes('持有')) return 'hold';
        return 'wait';
    }

    // 渲染单个任务卡片
    function renderTaskCard(taskId, taskData) {
        const task = taskData.task || {};
        const status = task.status || 'pending';
        const code = task.code || taskId.split('_')[0];
        const result = task.result || {};

        let statusIcon = '⏳';
        let statusText = '等待中';
        if (status === 'running') { statusIcon = '<span class="spinner"></span>'; statusText = '分析中'; }
        else if (status === 'completed') { statusIcon = '✓'; statusText = '完成'; }
        else if (status === 'failed') { statusIcon = '✗'; statusText = '失败'; }

        let resultHtml = '';
        if (status === 'completed' && result.operation_advice) {
            const adviceClass = getAdviceClass(result.operation_advice);
            resultHtml = '<div class="task-result">' +
                '<span class="task-advice ' + adviceClass + '">' + result.operation_advice + '</span>' +
                '<span class="task-score">' + (result.sentiment_score || '-') + '分</span>' +
                '</div>';
        } else if (status === 'failed') {
            resultHtml = '<div class="task-result"><span class="task-advice sell">失败</span></div>';
        }

        let detailHtml = '';
        if (status === 'completed') {
            detailHtml = '<div class="task-detail" id="detail_' + taskId + '">' +
                '<div class="task-detail-row"><span class="label">趋势</span><span>' + (result.trend_prediction || '-') + '</span></div>' +
                (result.analysis_summary ? '<div class="task-detail-summary">' + result.analysis_summary.substring(0, 100) + '...</div>' : '') +
                '</div>';
        }

        return '<div class="task-card ' + status + '" id="task_' + taskId + '" onclick="toggleDetail(\\''+taskId+'\\')">' +
            '<div class="task-status">' + statusIcon + '</div>' +
            '<div class="task-main">' +
                '<div class="task-title">' +
                    '<span class="code">' + code + '</span>' +
                    '<span class="name">' + (result.name || code) + '</span>' +
                '</div>' +
                '<div class="task-meta">' +
                    '<span>⏱ ' + formatTime(task.start_time) + '</span>' +
                    '<span>⏳ ' + calcDuration(task.start_time, task.end_time) + '</span>' +
                    '<span>' + (task.report_type === 'full' ? '📊完整' : '📝精简') + '</span>' +
                '</div>' +
            '</div>' +
            resultHtml +
            '<div class="task-actions">' +
                '<button class="task-btn" onclick="event.stopPropagation();removeTask(\\''+taskId+'\\')">×</button>' +
            '</div>' +
        '</div>' + detailHtml;
    }

    // 渲染所有任务
    function renderAllTasks() {
        if (tasks.size === 0) {
            taskList.innerHTML = '<div class="task-hint">💡 输入股票代码开始分析</div>';
            return;
        }

        let html = '';
        const sortedTasks = Array.from(tasks.entries())
            .sort((a, b) => (b[1].task?.start_time || '').localeCompare(a[1].task?.start_time || ''));

        sortedTasks.slice(0, MAX_TASKS_DISPLAY).forEach(([taskId, taskData]) => {
            html += renderTaskCard(taskId, taskData);
        });

        if (sortedTasks.length > MAX_TASKS_DISPLAY) {
            html += '<div class="task-hint">... 还有 ' + (sortedTasks.length - MAX_TASKS_DISPLAY) + ' 个任务</div>';
        }

        taskList.innerHTML = html;
    }

    // 切换详情显示
    window.toggleDetail = function(taskId) {
        const detail = document.getElementById('detail_' + taskId);
        if (detail) {
            detail.classList.toggle('show');
        }
    };

    // 移除任务
    window.removeTask = function(taskId) {
        tasks.delete(taskId);
        renderAllTasks();
        checkStopPolling();
    };

    // 轮询所有运行中的任务
    function pollAllTasks() {
        let hasRunning = false;

        tasks.forEach((taskData, taskId) => {
            const status = taskData.task?.status;
            if (status === 'running' || status === 'pending' || !status) {
                hasRunning = true;
                taskData.pollCount = (taskData.pollCount || 0) + 1;

                if (taskData.pollCount > MAX_POLL_COUNT) {
                    taskData.task = taskData.task || {};
                    taskData.task.status = 'failed';
                    taskData.task.error = '轮询超时';
                    return;
                }

                fetch('/task?id=' + encodeURIComponent(taskId))
                    .then(r => r.json())
                    .then(data => {
                        if (data.success && data.task) {
                            taskData.task = data.task;
                            renderAllTasks();
                        }
                    })
                    .catch(() => {});
            }
        });

        if (!hasRunning) {
            checkStopPolling();
        }
    }

    // 检查是否需要停止轮询
    function checkStopPolling() {
        let hasRunning = false;
        tasks.forEach((taskData) => {
            const status = taskData.task?.status;
            if (status === 'running' || status === 'pending' || !status) {
                hasRunning = true;
            }
        });

        if (!hasRunning && pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    // 开始轮询
    function startPolling() {
        if (!pollInterval) {
            pollInterval = setInterval(pollAllTasks, POLL_INTERVAL_MS);
        }
    }

    // 提交分析
    window.submitAnalysis = function() {
        const code = codeInput.value.trim();
        const isAStock = /^\d{6}$/.test(code);
        const isHKStock = /^HK\d{5}$/.test(code);
        const isUSStock = /^[A-Z]{1,5}(\.[A-Z]{1,2})?$/.test(code);

        if (!(isAStock || isHKStock || isUSStock)) {
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';

        const reportType = reportTypeSelect.value;
        const authHeaders = getAuthHeaders();
        fetch('/analysis?code=' + encodeURIComponent(code) + '&report_type=' + encodeURIComponent(reportType), { credentials: 'include', headers: authHeaders })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const taskId = data.task_id;
                    tasks.set(taskId, {
                        task: {
                            code: code,
                            status: 'running',
                            start_time: new Date().toISOString(),
                            report_type: reportType
                        },
                        pollCount: 0
                    });

                    renderAllTasks();
                    startPolling();
                    codeInput.value = '';

                    // 立即轮询一次
                    setTimeout(() => {
                        fetch('/task?id=' + encodeURIComponent(taskId))
                            .then(r => r.json())
                            .then(d => {
                                if (d.success && d.task) {
                                    tasks.get(taskId).task = d.task;
                                    renderAllTasks();
                                }
                            });
                    }, 500);
                } else {
                    const msg = data.error || '未知错误';
                    if (data.code === 'LIMIT_EXCEEDED' && data.redirect && confirm(msg + '\\n\\n是否前往会员页？')) {
                        window.location.href = data.redirect;
                    } else {
                        alert('提交失败: ' + msg);
                    }
                }
            })
            .catch(error => {
                alert('请求失败: ' + error.message);
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 分析';
                updateButtonState();
            });
    };

    // 供「文章/提示词抓取」区块使用：将返回的 task_id 列表加入当前任务列表并开始轮询
    window.addTasksFromArticleExtract = function(taskIds, reportType) {{
        if (!taskIds || taskIds.length === 0) return;
        var rt = reportType || (reportTypeSelect ? reportTypeSelect.value : 'simple');
        taskIds.forEach(function(tid) {{
            tasks.set(tid, {{ task: {{ code: tid.split('_')[0], status: 'running', start_time: new Date().toISOString(), report_type: rt }}, pollCount: 0 }});
        }});
        renderAllTasks();
        startPolling();
    }};

    // 初始化
    updateButtonState();
    renderAllTasks();
})();

// ========== 用户导航相关 ==========

// 鉴权请求头：优先使用 session_token（兼容 Cookie 不可用场景如部分 WebView）
function getAuthHeaders() {
    try {
        var t = sessionStorage.getItem('session_token');
        return t ? { 'Authorization': 'Bearer ' + t } : {};
    } catch (e) { return {}; }
}

// 页面加载时：优先加载导航再加载自选股，避免多请求竞争；若导航已 SSR 则先加载自选股，导航后台静默刷新
document.addEventListener('DOMContentLoaded', function() {
    var navEl = document.getElementById('user_nav');
    var isNavSsr = navEl && navEl.getAttribute('data-nav-ssr') === '1';
    function afterNav() {
        refreshWatchlist();
        loadWatchlistGroups();
    }
    if (isNavSsr) {
        afterNav();
        if (typeof requestIdleCallback !== 'undefined') {
            requestIdleCallback(function() { loadUserNav(); }, { timeout: 800 });
        } else {
            setTimeout(function() { loadUserNav(); }, 100);
        }
    } else {
        loadUserNav().then(afterNav).catch(function() { afterNav(); });
    }
});

// 加载用户导航信息
async function loadUserNav() {
    const userInfo = document.getElementById('nav_user_info');
    const navLinks = document.getElementById('nav_links');

    try {
        const response = await fetch('/api/auth/user', { credentials: 'include', headers: getAuthHeaders() });
        const data = await response.json();

        if (response.status === 401 || !data.success) {
            // 未登录
            userInfo.textContent = '未登录';
            navLinks.innerHTML = '<a href="/login">🔑 登录</a><a href="/register">📝 注册</a>';
        } else {
            // 已登录：等级以 benefits 为准（与后端 get_user_benefits 一致，含 users 表回退）
            const user = data.user;
            const benefits = data.benefits || {};
            const displayName = user.nickname || user.email || user.phone || '用户';
            const isVip = benefits.level === 'vip';
            const levelText = benefits.plan_name || (user.membership_level && user.membership_level !== 'free' ? '会员' : '免费版');

            userInfo.innerHTML = '👤 ' + displayName + ' <span style="color:#999;font-size:12px;">(' + levelText + ')</span>';

            let linksHtml = '<a href="/user">👤 个人中心</a>';
            linksHtml += '<a href="/user/history">📋 历史记录</a>';
            linksHtml += '<a href="#" class="btn-share" onclick="copyShareLink(event)">📤 分享</a>';
            if (!isVip) {
                linksHtml += '<a href="/membership" class="btn-vip">⭐ 升级会员</a>';
            } else {
                linksHtml += '<a href="/membership">💎 会员中心</a>';
            }
            linksHtml += '<a href="#" class="btn-logout" onclick="logout()">退出</a>';
            navLinks.innerHTML = linksHtml;
        }
    } catch (err) {
        console.error('加载用户信息失败:', err);
        userInfo.textContent = '加载失败';
        navLinks.innerHTML = '<a href="/login">🔑 登录</a>';
    }
}

// 复制邀请分享链接（需登录）
async function copyShareLink(e) {
    if (e) e.preventDefault();
    try {
        const res = await fetch('/api/referral/share-link', { credentials: 'include', headers: getAuthHeaders() });
        const data = await res.json();
        if (!data.success || !data.share_code) {
            alert(data.error || '获取分享链接失败');
            return;
        }
        const url = window.location.origin + '/register?ref=' + encodeURIComponent(data.share_code);
        await navigator.clipboard.writeText(url);
        if (typeof alert !== 'undefined') {
            alert('邀请链接已复制到剪贴板，好友通过此链接注册您将获得免费使用次数奖励');
        }
    } catch (err) {
        console.error('复制分享链接失败:', err);
        alert('复制失败，请重试');
    }
}

// 退出登录
async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'include', headers: getAuthHeaders() });
        try { sessionStorage.removeItem('session_token'); } catch (e) {}
        window.location.reload();
    } catch (err) {
        console.error('退出失败:', err);
    }
}

// ========== 用户自选股相关 ==========

// 加载用户分组列表
async function loadWatchlistGroups() {
    const select = document.getElementById('watchlist_group');

    try {
        const response = await fetch('/api/watchlist/groups', { credentials: 'include', headers: getAuthHeaders() });
        const data = await response.json();

        if (response.status === 401) {
            // 未登录，保持默认状态
            return;
        }

        if (data.success && data.groups && data.groups.length > 0) {
            // 清空并重新填充选项
            select.innerHTML = '<option value="">-- 请选择分组 --</option>';
            data.groups.forEach(group => {
                const option = document.createElement('option');
                option.value = group;
                option.textContent = group;
                select.appendChild(option);
            });
        }
    } catch (err) {
        console.error('加载分组失败:', err);
    }
}

// 分组下拉框变化时
function onGroupSelectChange() {
    const select = document.getElementById('watchlist_group');
    const newGroupInput = document.getElementById('new_group_name');

    if (select.value) {
        // 选择了分组，清空新分组输入框
        newGroupInput.value = '';
    }
}

// 新分组输入框输入时
function onNewGroupInput() {
    const select = document.getElementById('watchlist_group');
    const newGroupInput = document.getElementById('new_group_name');

    if (newGroupInput.value.trim()) {
        // 输入了新分组名，清除下拉框选择
        select.value = '';
    }
}

// 保存自选股
async function saveWatchlist() {
    const btn = document.getElementById('save_watchlist_btn');
    const textarea = document.getElementById('user_stocks');
    const stocks = textarea.value.trim();

    if (!stocks) {
        showToast('请输入股票代码', 'error');
        return;
    }

    // 获取分组信息
    const selectedGroup = document.getElementById('watchlist_group').value;
    const newGroupName = document.getElementById('new_group_name').value.trim();

    btn.disabled = true;
    btn.textContent = '保存中...';

    try {
        // 构建请求参数
        let bodyParams = 'stocks=' + encodeURIComponent(stocks);
        if (newGroupName) {
            bodyParams += '&new_group_name=' + encodeURIComponent(newGroupName);
        } else if (selectedGroup) {
            bodyParams += '&group_name=' + encodeURIComponent(selectedGroup);
        }

        const response = await fetch('/api/watchlist/save', {
            method: 'POST',
            credentials: 'include',
            headers: Object.assign({ 'Content-Type': 'application/x-www-form-urlencoded' }, getAuthHeaders()),
            body: bodyParams
        });

        const data = await response.json();

        if (response.status === 401) {
            showToast('请先登录', 'error');
            return;
        }

        if (data.success) {
            showToast(data.message, 'success');
            textarea.value = '';  // 清空股票输入框
            document.getElementById('new_group_name').value = '';  // 清空新分组输入框
            refreshWatchlist();   // 刷新列表
            loadWatchlistGroups(); // 刷新分组下拉框（可能有新分组）
        } else {
            showToast(data.error || '保存失败', 'error');
        }
    } catch (err) {
        showToast('网络错误', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '保存我的自选股';
    }
}

// 刷新自选股列表
async function refreshWatchlist() {
    const container = document.getElementById('watchlist_table');

    try {
        const response = await fetch('/api/watchlist?limit=20', { credentials: 'include', headers: getAuthHeaders() });
        const data = await response.json();

        if (response.status === 401) {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">请先 <a href="/login">登录</a> 查看自选股</p>';
            return;
        }

        if (!data.success) {
            container.innerHTML = '<p style="text-align: center; color: #f00; padding: 20px;">' + (data.error || '获取失败') + '</p>';
            return;
        }

        if (data.watchlist.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">暂无自选股，请在上方添加</p>';
            return;
        }

        // 渲染表格
        let html = '<table class="stock-table"><thead><tr><th>代码</th><th>名称</th><th>分组</th><th>添加时间</th><th>操作</th></tr></thead><tbody>';

        data.watchlist.forEach(item => {
            const addedTime = item.created_at ? new Date(item.created_at).toLocaleDateString('zh-CN') : '-';
            html += '<tr>';
            html += '<td><code>' + item.stock_code + '</code></td>';
            html += '<td>' + (item.stock_name || '-') + '</td>';
            html += '<td>' + (item.group_name || '默认分组') + '</td>';
            html += '<td>' + addedTime + '</td>';
            html += '<td>';
            html += '<button class="btn-icon" onclick="analyzeStock(\\'' + item.stock_code + '\\')" title="分析">📊</button>';
            html += '<button class="btn-icon btn-danger" onclick="deleteWatchlist(\\'' + item.stock_code + '\\')" title="删除">🗑️</button>';
            html += '</td>';
            html += '</tr>';
        });

        html += '</tbody></table>';

        if (data.total > 20) {
            html += '<p style="text-align: center; color: #666; font-size: 12px; margin-top: 10px;">显示前20条，共' + data.total + '条</p>';
        }

        container.innerHTML = html;

    } catch (err) {
        container.innerHTML = '<p style="text-align: center; color: #f00; padding: 20px;">网络错误</p>';
    }
}

// 删除自选股
async function deleteWatchlist(stockCode) {
    if (!confirm('确定删除 ' + stockCode + ' ？')) {
        return;
    }

    try {
        const response = await fetch('/api/watchlist/delete', {
            method: 'POST',
            credentials: 'include',
            headers: Object.assign({ 'Content-Type': 'application/x-www-form-urlencoded' }, getAuthHeaders()),
            body: 'stock_code=' + encodeURIComponent(stockCode)
        });

        const data = await response.json();

        if (data.success) {
            showToast('已删除', 'success');
            refreshWatchlist();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    } catch (err) {
        showToast('网络错误', 'error');
    }
}

// 分析股票
function analyzeStock(stockCode) {
    const input = document.getElementById('analysis_code');
    const btn = document.getElementById('analysis_btn');
    input.value = stockCode;
    btn.disabled = false;
    input.focus();
    // 触发分析
    if (typeof submitAnalysis === 'function') {
        submitAnalysis();
    }
}

// 显示提示
function showToast(message, type) {
    // 移除旧提示
    const oldToast = document.querySelector('.toast-msg');
    if (oldToast) oldToast.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-msg ' + type;
    toast.textContent = message;
    toast.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); padding: 12px 24px; border-radius: 8px; font-size: 14px; z-index: 1000; animation: slideIn 0.3s ease;';

    if (type === 'error') {
        toast.style.background = '#fff0f0';
        toast.style.color = '#cf1322';
        toast.style.border = '1px solid #ffccc7';
    } else {
        toast.style.background = '#f6ffed';
        toast.style.color = '#52c41a';
        toast.style.border = '1px solid #b7eb8f';
    }

    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
</script>
<style>
/* 自选股表格样式 */
.stock-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.stock-table th, .stock-table td {
    padding: 10px 8px;
    text-align: left;
    border-bottom: 1px solid #eee;
}
.stock-table th {
    background: #f9f9f9;
    font-weight: 500;
    color: #666;
}
.stock-table tr:hover {
    background: #f5f7fa;
}
.stock-table code {
    background: #e8f4fd;
    padding: 2px 6px;
    border-radius: 4px;
    color: #1890ff;
}
.btn-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 0.2s;
}
.btn-icon:hover {
    background: #f0f0f0;
}
.btn-icon.btn-danger:hover {
    background: #fff0f0;
}
.btn-small {
    padding: 4px 12px;
    font-size: 12px;
    background: #f0f0f0;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
.btn-small:hover {
    background: #e0e0e0;
}
@keyframes slideIn {
    from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
/* 用户导航栏 */
.user-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    margin-bottom: 15px;
    border-bottom: 1px solid #eee;
    font-size: 14px;
}
.user-nav #nav_user_info {
    color: #666;
}
.user-nav .nav-links {
    display: flex;
    gap: 15px;
}
.user-nav .nav-links a {
    color: #1890ff;
    text-decoration: none;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 0.2s;
}
.user-nav .nav-links a:hover {
    background: #e6f7ff;
}
.user-nav .nav-links a.btn-vip {
    background: linear-gradient(135deg, #ffd700, #ffb347);
    color: #8b4513;
    font-weight: 500;
}
.user-nav .nav-links a.btn-vip:hover {
    background: linear-gradient(135deg, #ffb347, #ffd700);
}
.user-nav .nav-links a.btn-logout {
    color: #999;
}
.user-nav .nav-links a.btn-logout:hover {
    background: #f5f5f5;
}
/* 首页服务公告入口 */
.announcement-banner {
    margin: -0.5rem 0 1rem 0;
    padding: 0.75rem 1rem;
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border: 1px solid #93c5fd;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(37, 99, 235, 0.12);
}
.announcement-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #1e40af;
    text-decoration: none;
    font-weight: 500;
    font-size: 0.95rem;
    transition: color 0.2s, opacity 0.2s;
}
.announcement-link:hover {
    color: #1d4ed8;
    opacity: 0.95;
}
.announcement-icon {
    font-size: 1.1rem;
}
.announcement-text {
    flex: 1;
}
.announcement-cta {
    font-size: 0.85rem;
    color: #3b82f6;
    white-space: nowrap;
}
</style>
"""

    content = f"""
  <div class="container">
    <!-- 服务公告入口 -->
    <div class="announcement-banner">
      <a href="/sources/announcement.html" class="announcement-link" target="_blank" rel="noopener noreferrer">
        <span class="announcement-icon">📢</span>
        <span class="announcement-text">智能股票分析服务公告</span>
        <span class="announcement-cta">点击查看 →</span>
      </a>
    </div>

    <!-- 顶部用户导航栏（支持服务端直出，登录后首屏即显示已登录） -->
    <div id="user_nav" class="user-nav"{nav_data_ssr}>
      {nav_initial}
    </div>

    <h2>📈 A股/港股/美股分析</h2>

    <!-- 快速分析区域 -->
    <div class="analysis-section" style="margin-top: 0; padding-top: 0; border-top: none;">
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <div class="input-group">
          <input
              type="text"
              id="analysis_code"
              placeholder="A股 600519 / 港股 HK00700 / 美股 AAPL"
              maxlength="8"
              autocomplete="off"
          />
          <select id="report_type" class="report-select" title="选择报告类型">
            <option value="simple">📝 精简报告</option>
            <option value="full">📊 完整报告</option>
          </select>
          <button type="button" id="analysis_btn" class="btn-analysis" onclick="submitAnalysis()" disabled>
            🚀 分析
          </button>
        </div>
      </div>

      <!-- 任务列表 -->
      <div id="task_list" class="task-list"></div>
      <p style="margin-top: 10px; font-size: 13px;">
        <a href="/user/history" id="link_history">📋 查看历史分析记录</a>
      </p>
    </div>

    <!-- 从文章/提示词抓取股票并分析 -->
    <div class="analysis-section article-extract-section">
      <h3>📄 从文章或提示词抓取股票并分析</h3>
      <p class="subtitle" style="font-size: 0.8rem; margin-bottom: 0.75rem;">支持输入文章 URL（如公众号链接）或自定义提示词，由多模型分析出股票后自动提交本系统分析</p>
      <div class="form-group" style="margin-bottom: 0.5rem;">
        <div style="display: flex; gap: 1rem; margin-bottom: 0.5rem;">
          <label style="display: flex; align-items: center; gap: 0.35rem; cursor: pointer;">
            <input type="radio" name="article_extract_mode" value="url" checked id="article_mode_url">
            <span>文章 URL</span>
          </label>
          <label style="display: flex; align-items: center; gap: 0.35rem; cursor: pointer;">
            <input type="radio" name="article_extract_mode" value="prompt" id="article_mode_prompt">
            <span>提示词</span>
          </label>
        </div>
      </div>
      <div id="article_url_wrap" class="form-group">
        <input type="text" id="article_extract_url" placeholder="https://mp.weixin.qq.com/s/xxxxx" style="width: 100%;">
      </div>
      <div id="article_prompt_wrap" class="form-group" style="display: none;">
        <textarea id="article_extract_content" rows="4" placeholder="例如：请列出当前热点板块（如人工智能、低空经济）的龙头股，仅输出代码与名称" style="width: 100%; resize: vertical;"></textarea>
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.75rem;">
        <select id="article_report_type" class="report-select" title="报告类型">
          <option value="simple">📝 精简报告</option>
          <option value="full">📊 完整报告</option>
        </select>
        <label style="display: flex; align-items: center; gap: 0.35rem; font-size: 0.85rem;">
          <span>取前</span>
          <select id="article_top_n" style="padding: 0.35rem 0.5rem; border-radius: 0.35rem; border: 1px solid var(--border);">
            <option value="2">2</option>
#             <option value="3" selected>3</option>
#             <option value="8">8</option>
#             <option value="10">10</option>
          </select>
          <span>只股票</span>
        </label>
      </div>
      <button type="button" id="article_extract_btn" class="btn-analysis">🔍 抓取并分析</button>
    </div>

    <hr class="section-divider">

    <!-- 用户自选股配置区域 -->
    <div class="form-group">
      <label for="user_stocks">📋 自选股列表</label>
      <p>登录后可保存到个人自选股列表</p>
      <textarea
          id="user_stocks"
          name="user_stocks"
          rows="4"
          placeholder="例如: 600519, 000001 (逗号或换行分隔)"
      ></textarea>
    </div>

    <!-- 分组选择区域 -->
    <div class="form-group" style="margin-top: 10px;">
      <label for="watchlist_group">📁 选择分组</label>
      <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
        <select id="watchlist_group" name="watchlist_group" style="flex: 1; min-width: 150px; max-width: 200px;" onchange="onGroupSelectChange()">
          <option value="">-- 请选择分组 --</option>
        </select>
        <span id="group_or_text" style="color: #666; font-size: 13px;">或</span>
        <input type="text" id="new_group_name" name="new_group_name"
               placeholder="输入新分组名（最多10字）"
               maxlength="10"
               style="flex: 1; min-width: 150px; max-width: 200px;"
               oninput="onNewGroupInput()">
      </div>
      <p style="font-size: 12px; color: #999; margin-top: 5px;">不选择分组时，可输入新分组名；都不填则使用"默认分组"</p>
    </div>

    <button type="button" id="save_watchlist_btn" onclick="saveWatchlist()">💾 保存</button>

    <!-- 用户自选股列表 -->
    <div id="watchlist_container" style="margin-top: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <label style="margin: 0;">📊 我的自选股</label>
        <button type="button" class="btn-small" onclick="refreshWatchlist()">🔄 刷新</button>
      </div>
      <div id="watchlist_table" class="watchlist-table">
        <p style="text-align: center; color: #999; padding: 20px;">请先登录查看自选股</p>
      </div>
    </div>

    <div class="footer">
      <p>API: <code>/health</code> · <code>/analysis?code=xxx</code> · <code>/tasks</code></p>
    </div>
  </div>

  {toast_html}
  {analysis_js}
  <script>
  (function() {{
    var modeUrl = document.getElementById('article_mode_url');
    var modePrompt = document.getElementById('article_mode_prompt');
    var wrapUrl = document.getElementById('article_url_wrap');
    var wrapPrompt = document.getElementById('article_prompt_wrap');
    if (modeUrl) modeUrl.addEventListener('change', function() {{ wrapUrl.style.display = 'block'; wrapPrompt.style.display = 'none'; }});
    if (modePrompt) modePrompt.addEventListener('change', function() {{ wrapUrl.style.display = 'none'; wrapPrompt.style.display = 'block'; }});

    var btn = document.getElementById('article_extract_btn');
    if (btn) {{
      btn.addEventListener('click', function() {{
        var mode = document.querySelector('input[name="article_extract_mode"]:checked');
        mode = mode ? mode.value : 'url';
        var url = (document.getElementById('article_extract_url') || {{ value: '' }}).value.trim();
        var content = (document.getElementById('article_extract_content') || {{ value: '' }}).value.trim();
        var reportType = (document.getElementById('article_report_type') || {{ value: 'simple' }}).value;
        var topN = (document.getElementById('article_top_n') || {{ value: '5' }}).value;

        if (mode === 'url' && !url) {{ alert('请输入文章 URL'); return; }}
        if (mode === 'prompt' && !content) {{ alert('请输入提示词内容'); return; }}

        btn.disabled = true;
        btn.textContent = '提交中...';
        var body = 'mode=' + encodeURIComponent(mode) + '&report_type=' + encodeURIComponent(reportType) + '&top_n=' + encodeURIComponent(topN);
        if (mode === 'url') body += '&url=' + encodeURIComponent(url);
        else body += '&content=' + encodeURIComponent(content);

        var headers = {{}};
        try {{ var t = sessionStorage.getItem('session_token'); if (t) headers['Authorization'] = 'Bearer ' + t; }} catch (e) {{}}
        headers['Content-Type'] = 'application/x-www-form-urlencoded';

        fetch('/api/article-extract', {{ method: 'POST', credentials: 'include', headers: headers, body: body }})
          .then(function(r) {{ return r.json(); }})
          .then(function(data) {{
            if (data.success) {{
              if (data.task_ids && data.task_ids.length > 0 && typeof window.addTasksFromArticleExtract === 'function') {{
                window.addTasksFromArticleExtract(data.task_ids, reportType);
              }}
              if (data.message) alert(data.message);
            }} else {{
              var msg = data.error || '请求失败';
              if (data.code === 'LIMIT_EXCEEDED' && data.redirect && confirm(msg + '\\n\\n是否前往会员页？')) {{
                window.location.href = data.redirect;
              }} else {{
                alert(msg);
              }}
            }}
          }})
          .catch(function(err) {{ alert('请求失败: ' + (err.message || err)); }})
          .finally(function() {{ btn.disabled = false; btn.textContent = '🔍 抓取并分析'; }});
      }});
    }}
  }})();
  </script>
"""

    page = render_base(
        title="A/H股自选配置 | WebUI",
        content=content
    )
    return page.encode("utf-8")


def render_error_page(
    status_code: int,
    message: str,
    details: Optional[str] = None
) -> bytes:
    """
    渲染错误页面

    Args:
        status_code: HTTP 状态码
        message: 错误消息
        details: 详细信息
    """
    details_html = f"<p class='text-muted'>{html.escape(details)}</p>" if details else ""

    content = f"""
  <div class="container" style="text-align: center;">
    <h2>😵 {status_code}</h2>
    <p>{html.escape(message)}</p>
    {details_html}
    <a href="/" style="color: var(--primary); text-decoration: none;">← 返回首页</a>
  </div>
"""

    page = render_base(
        title=f"错误 {status_code}",
        content=content
    )
    return page.encode("utf-8")
