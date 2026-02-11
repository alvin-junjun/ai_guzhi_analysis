# -*- coding: utf-8 -*-
"""
===================================
Web 鉴权页面模板
===================================

职责：
1. 登录页面
2. 注册页面
3. 用户中心页面
"""

from typing import Dict, Any, Optional


def render_login_page(
    redirect_url: str = '/',
    error: str = ''
) -> bytes:
    """
    渲染登录页面
    
    Args:
        redirect_url: 登录成功后跳转地址
        error: 错误消息
    """
    error_html = f'<div class="error-msg">{error}</div>' if error else ''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - A股智能分析系统</title>
    <style>
        {_get_common_styles()}
        .login-container {{
            max-width: 400px;
            margin: 80px auto;
            padding: 40px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .login-title {{
            text-align: center;
            margin-bottom: 30px;
            color: #1a1a2e;
        }}
        .login-title h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}
        .login-title p {{
            color: #666;
            font-size: 14px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-size: 14px;
        }}
        .form-group input {{
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }}
        .form-group input:focus {{
            outline: none;
            border-color: #4a90d9;
        }}
        .submit-btn {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #4a90d9, #357abd);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .submit-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(74, 144, 217, 0.4);
        }}
        .submit-btn:disabled {{
            background: #ccc;
            transform: none;
            box-shadow: none;
            cursor: not-allowed;
        }}
        .links {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }}
        .links a {{
            color: #4a90d9;
            text-decoration: none;
        }}
        .links a:hover {{
            text-decoration: underline;
        }}
        .error-msg {{
            background: #fff0f0;
            border: 1px solid #ffccc7;
            color: #cf1322;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .password-toggle {{
            position: relative;
        }}
        .password-toggle input {{
            padding-right: 45px;
        }}
        .toggle-btn {{
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            cursor: pointer;
            color: #999;
            font-size: 14px;
            padding: 4px;
        }}
        .toggle-btn:hover {{
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-title">
            <h1>欢迎回来</h1>
            <p>使用手机号或QQ邮箱登录</p>
        </div>
        
        {error_html}
        
        <form id="loginForm">
            <input type="hidden" name="redirect" value="{redirect_url}">
            
            <div class="form-group">
                <label for="target">手机号 / QQ邮箱</label>
                <input type="text" id="target" name="target" 
                       placeholder="请输入手机号或QQ邮箱" required autocomplete="username">
            </div>
            
            <div class="form-group">
                <label for="password">密码</label>
                <div class="password-toggle">
                    <input type="password" id="password" name="password" 
                           placeholder="请输入密码" required autocomplete="current-password">
                    <button type="button" class="toggle-btn" onclick="togglePassword('password', this)">显示</button>
                </div>
            </div>
            
            <button type="submit" class="submit-btn">登 录</button>
        </form>
        
        <div class="links">
            还没有账号？<a href="/register">立即注册</a>
        </div>
    </div>
    
    <script>
        function togglePassword(inputId, btn) {{
            const input = document.getElementById(inputId);
            if (input.type === 'password') {{
                input.type = 'text';
                btn.textContent = '隐藏';
            }} else {{
                input.type = 'password';
                btn.textContent = '显示';
            }}
        }}
        
        const loginForm = document.getElementById('loginForm');
        const submitBtn = loginForm.querySelector('.submit-btn');
        
        document.getElementById('loginForm').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const target = document.getElementById('target').value.trim();
            const password = document.getElementById('password').value;
            const redirect = '{redirect_url}';
            
            if (!target || !password) {{
                showMessage('请填写完整信息', 'error');
                return;
            }}
            
            // 禁用提交按钮
            submitBtn.disabled = true;
            submitBtn.textContent = '登录中...';
            
            try {{
                const response = await fetch('/api/auth/login', {{
                    method: 'POST',
                    credentials: 'include',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: `target=${{encodeURIComponent(target)}}&password=${{encodeURIComponent(password)}}`
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    if (data.session_token) {{
                        try {{ sessionStorage.setItem('session_token', data.session_token); }} catch (e) {{}}
                    }}
                    showMessage('登录成功，正在跳转...', 'success');
                    let path = redirect || '/';
                    try {{
                        if (path.indexOf('http') === 0) {{
                            const u = new URL(path);
                            path = (u.origin === window.location.origin) ? (u.pathname + u.search) : '/';
                        }} else if (path.charAt(0) !== '/') {{
                            path = '/' + path;
                        }}
                    }} catch (e) {{ path = '/'; }}
                    var targetUrl = window.location.origin + path;
                    setTimeout(() => {{
                        window.location.href = targetUrl;
                    }}, 500);
                }} else {{
                    showMessage(data.error || '登录失败', 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = '登 录';
                }}
            }} catch (err) {{
                showMessage('网络错误，请重试', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = '登 录';
            }}
        }});
        
        function showMessage(msg, type) {{
            // 移除之前的消息
            const oldMsg = document.querySelector('.toast-msg');
            if (oldMsg) oldMsg.remove();
            
            const msgEl = document.createElement('div');
            msgEl.className = 'toast-msg ' + type;
            msgEl.textContent = msg;
            msgEl.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                z-index: 1000;
                animation: slideIn 0.3s ease;
            `;
            if (type === 'error') {{
                msgEl.style.background = '#fff0f0';
                msgEl.style.color = '#cf1322';
                msgEl.style.border = '1px solid #ffccc7';
            }} else {{
                msgEl.style.background = '#f6ffed';
                msgEl.style.color = '#52c41a';
                msgEl.style.border = '1px solid #b7eb8f';
            }}
            document.body.appendChild(msgEl);
            
            setTimeout(() => msgEl.remove(), 3000);
        }}
    </script>
    <style>
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-50%) translateY(-20px); }}
            to {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
        }}
    </style>
</body>
</html>'''
    
    return html.encode('utf-8')


def render_register_page(error: str = '') -> bytes:
    """
    渲染注册页面
    
    Args:
        error: 错误消息
    """
    error_html = f'<div class="error-msg">{error}</div>' if error else ''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 - A股智能分析系统</title>
    <style>
        {_get_common_styles()}
        .register-container {{
            max-width: 400px;
            margin: 60px auto;
            padding: 40px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .register-title {{
            text-align: center;
            margin-bottom: 30px;
            color: #1a1a2e;
        }}
        .register-title h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}
        .register-title p {{
            color: #666;
            font-size: 14px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-size: 14px;
        }}
        .form-group input {{
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }}
        .form-group input:focus {{
            outline: none;
            border-color: #4a90d9;
        }}
        .submit-btn {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #52c41a, #389e0d);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .submit-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
        }}
        .submit-btn:disabled {{
            background: #ccc;
            transform: none;
            box-shadow: none;
            cursor: not-allowed;
        }}
        .links {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }}
        .links a {{
            color: #4a90d9;
            text-decoration: none;
        }}
        .links a:hover {{
            text-decoration: underline;
        }}
        .error-msg {{
            background: #fff0f0;
            border: 1px solid #ffccc7;
            color: #cf1322;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .tips {{
            background: #e6f7ff;
            border: 1px solid #91d5ff;
            color: #1890ff;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
        }}
        .password-toggle {{
            position: relative;
        }}
        .password-toggle input {{
            padding-right: 45px;
        }}
        .toggle-btn {{
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            cursor: pointer;
            color: #999;
            font-size: 14px;
            padding: 4px;
        }}
        .toggle-btn:hover {{
            color: #666;
        }}
        .password-hint {{
            font-size: 12px;
            color: #999;
            margin-top: 6px;
        }}
        .email-hint {{
            font-size: 12px;
            color: #1890ff;
            margin-top: 6px;
        }}
        .email-group {{
            animation: slideDown 0.3s ease;
        }}
        @keyframes slideDown {{
            from {{ opacity: 0; max-height: 0; }}
            to {{ opacity: 1; max-height: 100px; }}
        }}
        .required {{
            color: #ff4d4f;
        }}
        .input-error {{
            border-color: #ff4d4f !important;
        }}
        .input-error:focus {{
            border-color: #ff4d4f !important;
            box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.2);
        }}
        .error-hint {{
            font-size: 12px;
            color: #ff4d4f;
            margin-top: 4px;
            display: none;
        }}
        .error-hint.show {{
            display: block;
        }}
        /* 邮箱输入框包装器 */
        .email-input-wrapper {{
            position: relative;
            display: flex;
            align-items: center;
        }}
        .email-input-wrapper input {{
            padding-right: 40px;
        }}
        .preview-icon {{
            position: absolute;
            right: 12px;
            cursor: pointer;
            font-size: 16px;
            opacity: 0.6;
            transition: opacity 0.2s;
        }}
        .preview-icon:hover {{
            opacity: 1;
        }}
        .preview-link {{
            color: #1890ff;
            text-decoration: none;
            margin-left: 4px;
        }}
        .preview-link:hover {{
            text-decoration: underline;
        }}
        /* 报告预览弹窗 */
        .report-preview-modal {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            animation: fadeIn 0.2s ease;
        }}
        .report-preview-modal.show {{
            display: flex;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        .preview-content {{
            background: white;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.3s ease;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
        .preview-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid #f0f0f0;
            background: linear-gradient(135deg, #4a90d9, #357abd);
            color: white;
        }}
        .preview-title {{
            font-size: 16px;
            font-weight: 500;
        }}
        .preview-close {{
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: white;
            opacity: 0.8;
            transition: opacity 0.2s;
            line-height: 1;
        }}
        .preview-close:hover {{
            opacity: 1;
        }}
        .preview-body {{
            padding: 0;
            max-height: 60vh;
            overflow-y: auto;
        }}
        .preview-image {{
            display: block;
            width: 100%;
            max-width: 600px;
            height: auto;
        }}
        .preview-footer {{
            padding: 16px 20px;
            background: #f9f9f9;
            border-top: 1px solid #f0f0f0;
        }}
        .preview-footer p {{
            font-size: 14px;
            color: #333;
            margin-bottom: 8px;
        }}
        .preview-footer ul {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
        }}
        .preview-footer li {{
            font-size: 13px;
            color: #666;
        }}
        @media (max-width: 600px) {{
            .preview-content {{
                max-width: 95%;
                margin: 10px;
            }}
            .preview-footer ul {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="register-container">
        <div class="register-title">
            <h1>创建账号</h1>
            <p>注册后即可使用智能分析功能</p>
        </div>
        
        {error_html}
        
        <div class="tips">
            注册即可获得免费版权益：每日5次分析，10只自选股
        </div>
        
        <form id="registerForm">
            <div class="form-group">
                <label for="target">手机号 / QQ邮箱</label>
                <input type="text" id="target" name="target" 
                       placeholder="请输入手机号或QQ邮箱" required autocomplete="username"
                       oninput="checkTargetType()">
            </div>
            
            <div class="form-group email-group" id="emailGroup" style="display: none;">
                <label for="reportEmail">接收报告的QQ邮箱 <span class="required">*</span></label>
                <div class="email-input-wrapper">
                    <input type="email" id="reportEmail" name="reportEmail" 
                           placeholder="请输入用于接收分析报告的QQ邮箱">
                    <span class="preview-icon" onclick="toggleReportPreview()" title="点击查看报告样例">👁️</span>
                </div>
                <p class="email-hint">分析报告将发送到此邮箱，仅支持QQ邮箱 <a href="javascript:void(0)" onclick="showReportPreview()" class="preview-link">查看报告样例</a></p>
            </div>
            
            <!-- 报告预览弹窗 -->
            <div class="report-preview-modal" id="reportPreviewModal" onclick="hideReportPreview()">
                <div class="preview-content" onclick="event.stopPropagation()">
                    <div class="preview-header">
                        <span class="preview-title">📧 分析报告样例</span>
                        <button class="preview-close" onclick="hideReportPreview()">&times;</button>
                    </div>
                    <div class="preview-body">
                        <img src="/sources/report_preview.png" alt="分析报告样例" class="preview-image">
                    </div>
                    <div class="preview-footer">
                        <p>分析完成后，您将收到类似上图的邮件报告，包含：</p>
                        <ul>
                            <li>🎯 核心结论与操作建议</li>
                            <li>📊 重要信息（业绩预期、舆情情绪）</li>
                            <li>⚠️ 风险警报与利好催化</li>
                            <li>💡 详细操作点位参考</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="form-group">
                <label for="password">设置密码</label>
                <div class="password-toggle">
                    <input type="password" id="password" name="password" 
                           placeholder="请设置登录密码" required autocomplete="new-password" minlength="6" maxlength="32">
                    <button type="button" class="toggle-btn" onclick="togglePassword('password', this)">显示</button>
                </div>
                <p class="password-hint">密码长度 6-32 位</p>
            </div>
            
            <div class="form-group">
                <label for="confirmPassword">确认密码</label>
                <div class="password-toggle">
                    <input type="password" id="confirmPassword" name="confirmPassword" 
                           placeholder="请再次输入密码" required autocomplete="new-password">
                    <button type="button" class="toggle-btn" onclick="togglePassword('confirmPassword', this)">显示</button>
                </div>
            </div>
            
            <div class="form-group">
                <label for="nickname">昵称（可选）</label>
                <input type="text" id="nickname" name="nickname" 
                       placeholder="给自己起个名字吧">
            </div>
            
            <button type="submit" class="submit-btn">注 册</button>
        </form>
        
        <div class="links">
            已有账号？<a href="/login">立即登录</a>
        </div>
    </div>
    
    <script>
        // 正则表达式
        const phoneRegex = /^1[3-9]\d{{9}}$/;
        const emailRegex = /^[1-9]\d{{4,10}}@qq\.com$/i;
        
        // 预览弹窗控制
        let previewHideTimeout = null;
        
        function showReportPreview() {{
            // 清除隐藏计时器
            if (previewHideTimeout) {{
                clearTimeout(previewHideTimeout);
                previewHideTimeout = null;
            }}
            document.getElementById('reportPreviewModal').classList.add('show');
        }}
        
        function hideReportPreview() {{
            document.getElementById('reportPreviewModal').classList.remove('show');
        }}
        
        function hideReportPreviewDelayed() {{
            // 延迟隐藏，给用户点击弹窗的时间
            previewHideTimeout = setTimeout(() => {{
                hideReportPreview();
            }}, 200);
        }}
        
        function toggleReportPreview() {{
            const modal = document.getElementById('reportPreviewModal');
            if (modal.classList.contains('show')) {{
                hideReportPreview();
            }} else {{
                showReportPreview();
            }}
        }}
        
        // ESC 键关闭弹窗
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                hideReportPreview();
            }}
        }});
        
        function togglePassword(inputId, btn) {{
            const input = document.getElementById(inputId);
            if (input.type === 'password') {{
                input.type = 'text';
                btn.textContent = '隐藏';
            }} else {{
                input.type = 'password';
                btn.textContent = '显示';
            }}
        }}
        
        // 检测输入类型，动态显示/隐藏邮箱输入框
        function checkTargetType() {{
            const target = document.getElementById('target').value.trim();
            const emailGroup = document.getElementById('emailGroup');
            const reportEmailInput = document.getElementById('reportEmail');
            
            if (phoneRegex.test(target)) {{
                // 手机号注册，显示邮箱输入框
                emailGroup.style.display = 'block';
                reportEmailInput.required = true;
            }} else {{
                // QQ邮箱注册或其他情况，隐藏邮箱输入框
                emailGroup.style.display = 'none';
                reportEmailInput.required = false;
                reportEmailInput.value = '';
                reportEmailInput.classList.remove('input-error');
            }}
        }}
        
        // 验证QQ邮箱格式
        function validateQQEmail(email) {{
            return emailRegex.test(email);
        }}
        
        const registerForm = document.getElementById('registerForm');
        const submitBtn = registerForm.querySelector('.submit-btn');
        
        // 邮箱输入框失焦验证
        document.getElementById('reportEmail').addEventListener('blur', function() {{
            const email = this.value.trim();
            if (email && !validateQQEmail(email)) {{
                this.classList.add('input-error');
                showMessage('请输入正确的QQ邮箱格式（如：123456@qq.com）', 'error');
            }} else {{
                this.classList.remove('input-error');
            }}
        }});
        
        document.getElementById('registerForm').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const target = document.getElementById('target').value.trim();
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const nickname = document.getElementById('nickname').value.trim();
            const reportEmail = document.getElementById('reportEmail').value.trim();
            
            if (!target || !password) {{
                showMessage('请填写完整信息', 'error');
                return;
            }}
            
            // 验证手机号或邮箱格式
            const isPhone = phoneRegex.test(target);
            const isEmail = emailRegex.test(target);
            
            if (!isPhone && !isEmail) {{
                showMessage('请输入正确的手机号或QQ邮箱', 'error');
                return;
            }}
            
            // 如果是手机号注册，验证报告接收邮箱
            let finalEmail = '';
            if (isPhone) {{
                if (!reportEmail) {{
                    showMessage('请填写接收报告的QQ邮箱', 'error');
                    document.getElementById('reportEmail').focus();
                    return;
                }}
                if (!validateQQEmail(reportEmail)) {{
                    showMessage('请输入正确的QQ邮箱格式（如：123456@qq.com）', 'error');
                    document.getElementById('reportEmail').classList.add('input-error');
                    document.getElementById('reportEmail').focus();
                    return;
                }}
                finalEmail = reportEmail;
            }} else {{
                // QQ邮箱注册，email就是target
                finalEmail = target;
            }}
            
            // 验证密码长度
            if (password.length < 6) {{
                showMessage('密码长度至少6位', 'error');
                return;
            }}
            
            if (password.length > 32) {{
                showMessage('密码长度不能超过32位', 'error');
                return;
            }}
            
            // 验证两次密码一致
            if (password !== confirmPassword) {{
                showMessage('两次输入的密码不一致', 'error');
                return;
            }}
            
            // 禁用提交按钮
            submitBtn.disabled = true;
            submitBtn.textContent = '注册中...';
            
            try {{
                const response = await fetch('/api/auth/register', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: `target=${{encodeURIComponent(target)}}&password=${{encodeURIComponent(password)}}&nickname=${{encodeURIComponent(nickname)}}&email=${{encodeURIComponent(finalEmail)}}`
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    showMessage('注册成功！正在跳转到登录页...', 'success');
                    setTimeout(() => {{
                        window.location.href = '/login';
                    }}, 1500);
                }} else {{
                    showMessage(data.error || '注册失败', 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = '注 册';
                }}
            }} catch (err) {{
                showMessage('网络错误，请重试', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = '注 册';
            }}
        }});
        
        function showMessage(msg, type) {{
            // 移除之前的消息
            const oldMsg = document.querySelector('.toast-msg');
            if (oldMsg) oldMsg.remove();
            
            const msgEl = document.createElement('div');
            msgEl.className = 'toast-msg ' + type;
            msgEl.textContent = msg;
            msgEl.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                z-index: 1000;
                animation: slideIn 0.3s ease;
            `;
            if (type === 'error') {{
                msgEl.style.background = '#fff0f0';
                msgEl.style.color = '#cf1322';
                msgEl.style.border = '1px solid #ffccc7';
            }} else {{
                msgEl.style.background = '#f6ffed';
                msgEl.style.color = '#52c41a';
                msgEl.style.border = '1px solid #b7eb8f';
            }}
            document.body.appendChild(msgEl);
            
            setTimeout(() => msgEl.remove(), 3000);
        }}
    </script>
    <style>
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-50%) translateY(-20px); }}
            to {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
        }}
    </style>
</body>
</html>'''
    
    return html.encode('utf-8')


def render_user_center_page(
    user_info: Dict[str, Any],
    benefits: Dict[str, Any],
    usage_info: Dict[str, Any]
) -> bytes:
    """
    渲染用户中心页面
    
    Args:
        user_info: 用户信息
        benefits: 权益信息
        usage_info: 使用量信息
    """
    # 会员状态
    is_vip = benefits.get('level') == 'vip'
    level_text = benefits.get('plan_name', '免费版')
    level_class = 'vip' if is_vip else 'free'
    
    # 剩余天数（None 表示长期有效）
    days_remaining = benefits.get('days_remaining', 0)
    expire_text = ('长期有效' if days_remaining is None else f'{days_remaining}天后到期') if is_vip else ''
    
    # 使用量
    used = usage_info.get('used', 0)
    limit = usage_info.get('limit', 5)
    limit_text = str(limit) if limit != -1 else '不限'
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户中心 - A股智能分析系统</title>
    <style>
        {_get_common_styles()}
        .user-container {{
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        .user-header {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: white;
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 24px;
        }}
        .user-info {{
            display: flex;
            align-items: center;
            gap: 24px;
        }}
        .avatar {{
            width: 80px;
            height: 80px;
            background: #4a90d9;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            color: white;
        }}
        .user-details h2 {{
            margin: 0 0 8px 0;
            font-size: 24px;
        }}
        .user-details p {{
            margin: 0;
            opacity: 0.8;
        }}
        .membership-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 12px;
        }}
        .membership-badge.vip {{
            background: linear-gradient(135deg, #f5a623, #f7931a);
            color: white;
        }}
        .membership-badge.free {{
            background: #f0f0f0;
            color: #666;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .card-title {{
            font-size: 16px;
            color: #333;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #1a1a2e;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-top: 4px;
        }}
        .action-buttons {{
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }}
        .action-btn {{
            flex: 1;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .action-btn.primary {{
            background: linear-gradient(135deg, #f5a623, #f7931a);
            color: white;
        }}
        .action-btn.primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(245, 166, 35, 0.4);
        }}
        .action-btn.secondary {{
            background: #f0f0f0;
            color: #333;
        }}
        .action-btn.secondary:hover {{
            background: #e0e0e0;
        }}
        .action-btn.danger {{
            background: #ff4d4f;
            color: white;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #4a90d9;
            text-decoration: none;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="user-container">
        <a href="/" class="back-link">← 返回首页</a>
        
        <div class="user-header">
            <div class="user-info">
                <div class="avatar">
                    {user_info.get('nickname', '用户')[0] if user_info.get('nickname') else '👤'}
                </div>
                <div class="user-details">
                    <h2>
                        {user_info.get('nickname') or '用户' + str(user_info.get('id', ''))}
                        <span class="membership-badge {level_class}">{level_text}</span>
                    </h2>
                    <p>{user_info.get('phone') or user_info.get('email') or ''}</p>
                    {'<p style="font-size:12px;margin-top:8px;opacity:0.7;">' + expire_text + '</p>' if expire_text else ''}
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">今日使用情况</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{used}</div>
                    <div class="stat-label">已分析次数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{limit_text}</div>
                    <div class="stat-label">每日限额</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{user_info.get('total_analysis_count', 0)}</div>
                    <div class="stat-label">累计分析</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">会员权益</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{limit_text}</div>
                    <div class="stat-label">每日分析次数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{benefits.get('watchlist_limit', 10)}</div>
                    <div class="stat-label">自选股上限</div>
                </div>
            </div>
            
            <div class="action-buttons">
                {'<a href="/membership" class="action-btn primary">升级会员</a>' if not is_vip else '<a href="/membership" class="action-btn secondary">续费/升级</a>'}
                <button class="action-btn danger" onclick="logout()">退出登录</button>
            </div>
        </div>
    </div>
    
    <script>
        async function logout() {{
            if (!confirm('确定要退出登录吗？')) return;
            
            try {{
                const response = await fetch('/api/auth/logout', {{
                    method: 'POST'
                }});
                window.location.href = '/';
            }} catch (err) {{
                alert('操作失败，请重试');
            }}
        }}
    </script>
</body>
</html>'''
    
    return html.encode('utf-8')


def render_membership_page(
    user_info: Dict[str, Any],
    benefits: Dict[str, Any],
    plans: list,
    current_order: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    渲染会员套餐充值页面
    
    Args:
        user_info: 用户信息
        benefits: 当前权益
        plans: 套餐列表
        current_order: 当前待支付订单（如有）
    """
    # 当前会员状态（days_remaining 为 None 表示长期有效）
    is_vip = benefits.get('level') == 'vip'
    level_text = benefits.get('plan_name', '免费版')
    days_remaining = benefits.get('days_remaining', 0)
    
    # 构建套餐卡片
    plans_html = ''
    for plan in plans:
        if plan.get('price', 0) == 0:
            continue  # 跳过免费套餐
        
        is_recommended = plan.get('is_recommended', False)
        badge = '<span class="badge recommend">推荐</span>' if is_recommended else ''
        
        # 功能列表
        features = plan.get('features', [])
        features_html = ''.join([f'<li>{f}</li>' for f in features[:5]])
        
        # 价格显示
        price = plan.get('price', 0)
        original_price = plan.get('original_price')
        price_html = f'<span class="price">¥{price:.2f}</span>'
        if original_price and original_price > price:
            price_html += f'<span class="original-price">¥{original_price:.2f}</span>'
        
        # 时长
        duration = plan.get('duration_days', 30)
        duration_text = f'{duration}天'
        
        plans_html += f'''
        <div class="plan-card {'recommended' if is_recommended else ''}" data-plan-id="{plan['id']}">
            <div class="plan-header">
                <h3>{plan['name']}{badge}</h3>
                <p class="plan-duration">{duration_text}</p>
            </div>
            <div class="plan-price">
                {price_html}
            </div>
            <div class="plan-desc">{plan.get('description', '')}</div>
            <ul class="plan-features">
                {features_html}
            </ul>
            <button class="plan-btn" onclick="selectPlan({plan['id']}, '{plan['name']}', {price})">
                立即开通
            </button>
        </div>
        '''
    
    # 待支付订单提示
    order_html = ''
    if current_order and current_order.get('status') == 'pending':
        order_html = f'''
        <div class="pending-order">
            <p>您有一笔待支付订单</p>
            <p>订单号：{current_order.get('order_no', '')}</p>
            <p>金额：¥{current_order.get('pay_amount', 0):.2f}</p>
            <button onclick="continuePayOrder('{current_order.get('order_no', '')}')">继续支付</button>
            <button class="btn-cancel" onclick="cancelOrder('{current_order.get('order_no', '')}')">取消订单</button>
        </div>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>会员充值 - A股智能分析系统</title>
    <style>
        {_get_common_styles()}
        .membership-container {{
            max-width: 1000px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        .membership-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .membership-header h1 {{
            font-size: 32px;
            color: #1a1a2e;
            margin-bottom: 12px;
        }}
        .membership-header p {{
            color: #666;
            font-size: 16px;
        }}
        .current-status {{
            background: linear-gradient(135deg, #f6f8fc, #eef2f7);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .current-status .status-info h3 {{
            font-size: 18px;
            color: #333;
            margin-bottom: 4px;
        }}
        .current-status .status-info p {{
            color: #666;
            font-size: 14px;
        }}
        .status-badge {{
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        .status-badge.free {{
            background: #f0f0f0;
            color: #666;
        }}
        .status-badge.vip {{
            background: linear-gradient(135deg, #f5a623, #f7931a);
            color: white;
        }}
        .plans-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .plan-card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            transition: all 0.3s;
            border: 2px solid transparent;
            position: relative;
        }}
        .plan-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .plan-card.recommended {{
            border-color: #f5a623;
        }}
        .plan-card.selected {{
            border-color: #4a90d9;
            background: #f8faff;
        }}
        .plan-header {{
            text-align: center;
            margin-bottom: 16px;
        }}
        .plan-header h3 {{
            font-size: 20px;
            color: #333;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .plan-duration {{
            color: #999;
            font-size: 14px;
        }}
        .badge {{
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 10px;
            background: #ff6b6b;
            color: white;
        }}
        .badge.recommend {{
            background: linear-gradient(135deg, #f5a623, #f7931a);
        }}
        .plan-price {{
            text-align: center;
            margin-bottom: 16px;
        }}
        .plan-price .price {{
            font-size: 36px;
            font-weight: bold;
            color: #e74c3c;
        }}
        .plan-price .original-price {{
            font-size: 16px;
            color: #999;
            text-decoration: line-through;
            margin-left: 8px;
        }}
        .plan-desc {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 16px;
            min-height: 40px;
        }}
        .plan-features {{
            list-style: none;
            padding: 0;
            margin: 0 0 20px 0;
        }}
        .plan-features li {{
            padding: 8px 0;
            font-size: 14px;
            color: #555;
            border-bottom: 1px dashed #eee;
            display: flex;
            align-items: center;
        }}
        .plan-features li:before {{
            content: '✓';
            color: #52c41a;
            margin-right: 8px;
            font-weight: bold;
        }}
        .plan-btn {{
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            background: linear-gradient(135deg, #4a90d9, #357abd);
            color: white;
        }}
        .plan-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(74, 144, 217, 0.4);
        }}
        .plan-card.recommended .plan-btn {{
            background: linear-gradient(135deg, #f5a623, #f7931a);
        }}
        .plan-card.recommended .plan-btn:hover {{
            box-shadow: 0 4px 12px rgba(245, 166, 35, 0.4);
        }}
        .pending-order {{
            background: #fff7e6;
            border: 1px solid #ffd591;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .pending-order p {{
            margin: 4px 0;
            color: #d48806;
        }}
        .pending-order button {{
            margin: 8px 4px 0;
            padding: 8px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }}
        .pending-order button:first-of-type {{
            background: #f5a623;
            color: white;
        }}
        .pending-order .btn-cancel {{
            background: #f0f0f0;
            color: #666;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #4a90d9;
            text-decoration: none;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        /* 支付弹窗 */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }}
        .modal-overlay.show {{
            display: flex;
        }}
        .modal-content {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            max-width: 400px;
            width: 90%;
            text-align: center;
        }}
        .modal-content h3 {{
            font-size: 20px;
            margin-bottom: 20px;
            color: #333;
        }}
        .qrcode-container {{
            margin: 20px 0;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 12px;
        }}
        .qrcode-container img {{
            max-width: 200px;
            height: auto;
        }}
        .qrcode-placeholder {{
            width: 200px;
            height: 200px;
            margin: 0 auto;
            background: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            color: #999;
        }}
        .pay-amount {{
            font-size: 24px;
            color: #e74c3c;
            font-weight: bold;
            margin: 16px 0;
        }}
        .pay-tips {{
            font-size: 14px;
            color: #666;
            margin-bottom: 20px;
        }}
        .modal-close {{
            padding: 12px 40px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            color: #666;
        }}
        .modal-close:hover {{
            background: #e0e0e0;
        }}
        /* 模拟支付按钮 */
        .mock-pay-btn {{
            display: block;
            width: 100%;
            padding: 12px;
            margin-top: 12px;
            background: #52c41a;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }}
        .mock-pay-btn:hover {{
            background: #389e0d;
        }}
        .dev-tip {{
            font-size: 12px;
            color: #ff6b6b;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="membership-container">
        <a href="/user" class="back-link">← 返回用户中心</a>
        
        <div class="membership-header">
            <h1>升级会员</h1>
            <p>解锁更多分析次数，获取更全面的投资洞察</p>
        </div>
        
        <div class="current-status">
            <div class="status-info">
                <h3>当前等级：{level_text}</h3>
                <p>{'长期有效' if is_vip and days_remaining is None else ('会员剩余' + str(days_remaining) + '天' if is_vip else '升级会员享受更多权益')}</p>
            </div>
            <span class="status-badge {'vip' if is_vip else 'free'}">{level_text}</span>
        </div>
        
        {order_html}
        
        <div class="plans-grid">
            {plans_html}
        </div>
    </div>
    
    <!-- 支付弹窗 -->
    <div class="modal-overlay" id="payModal">
        <div class="modal-content">
            <h3 id="modalTitle">微信支付</h3>
            <div class="qrcode-container">
                <div class="qrcode-placeholder" id="qrcodeArea">
                    正在生成支付码...
                </div>
            </div>
            <div class="pay-amount" id="payAmount">¥0.00</div>
            <div class="pay-tips">请使用微信扫码支付</div>
            <div id="personalPayTip" style="display:none; margin-top:8px; padding:8px; background:#f0f9ff; border-radius:6px; color:#0369a1; font-size:13px;">付款后请截图并联系管理员确认开通</div>
            <div id="mockPayArea" style="display:none;">
                <button class="mock-pay-btn" onclick="mockPaySuccess()">模拟支付成功</button>
                <p class="dev-tip">（开发模式 - 点击模拟支付完成）</p>
            </div>
            <button class="modal-close" onclick="closePayModal()">关闭</button>
        </div>
    </div>
    
    <script>
        let currentOrderNo = '';
        let pollTimer = null;
        
        function selectPlan(planId, planName, price) {{
            // 创建订单
            fetch('/api/membership/create-order', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: `plan_id=${{planId}}`
            }})
            .then(r => r.json())
            .then(data => {{
                if (data.success) {{
                    currentOrderNo = data.order.order_no;
                    showPayModal(planName, price, data.qrcode_url, data.is_mock, data.is_personal, data.personal_qr_url);
                    // 开始轮询订单状态（个人收款码模式下需管理员后台确认后才会变为已支付）
                    startPollOrderStatus();
                }} else {{
                    alert(data.error || '创建订单失败');
                }}
            }})
            .catch(err => {{
                alert('网络错误，请重试');
            }});
        }}
        
        function showPayModal(planName, price, qrcodeUrl, isMock, isPersonal, personalQrUrl) {{
            document.getElementById('modalTitle').textContent = planName + ' - 微信支付';
            document.getElementById('payAmount').textContent = '¥' + price.toFixed(2);
            
            const qrcodeArea = document.getElementById('qrcodeArea');
            const mockPayArea = document.getElementById('mockPayArea');
            const personalPayTip = document.getElementById('personalPayTip');
            
            if (personalPayTip) personalPayTip.style.display = 'none';
            if (isMock) {{
                // 模拟支付模式
                qrcodeArea.innerHTML = '<div style="padding:40px;color:#666;">开发模式<br>无需扫码</div>';
                mockPayArea.style.display = 'block';
            }} else if (isPersonal && personalQrUrl) {{
                // 个人收款码：直接展示配置的二维码图片
                qrcodeArea.innerHTML = '<img src="' + personalQrUrl + '" alt="微信收款码" style="max-width:220px;height:auto;" />';
                mockPayArea.style.display = 'none';
                if (personalPayTip) personalPayTip.style.display = 'block';
            }} else if (qrcodeUrl) {{
                // 商户号支付：根据 URL 生成二维码
                const qrImgUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(qrcodeUrl);
                qrcodeArea.innerHTML = '<img src="' + qrImgUrl + '" alt="支付二维码" />';
                mockPayArea.style.display = 'none';
            }} else {{
                qrcodeArea.innerHTML = '<div style="color:#999;">生成二维码失败</div>';
                mockPayArea.style.display = 'none';
            }}
            
            document.getElementById('payModal').classList.add('show');
        }}
        
        function closePayModal() {{
            document.getElementById('payModal').classList.remove('show');
            if (pollTimer) {{
                clearInterval(pollTimer);
                pollTimer = null;
            }}
        }}
        
        function startPollOrderStatus() {{
            if (pollTimer) clearInterval(pollTimer);
            
            pollTimer = setInterval(() => {{
                if (!currentOrderNo) return;
                
                fetch('/api/membership/order-status?order_no=' + encodeURIComponent(currentOrderNo))
                .then(r => r.json())
                .then(data => {{
                    if (data.success && data.order) {{
                        if (data.order.payment_status === 'paid') {{
                            clearInterval(pollTimer);
                            pollTimer = null;
                            alert('支付成功！会员已开通');
                            window.location.reload();
                        }}
                    }}
                }});
            }}, 3000);
        }}
        
        function mockPaySuccess() {{
            fetch('/api/payment/mock-pay', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: `order_no=${{currentOrderNo}}`
            }})
            .then(r => r.json())
            .then(data => {{
                if (data.success) {{
                    alert('支付成功！会员已开通');
                    window.location.reload();
                }} else {{
                    alert(data.error || '支付失败');
                }}
            }});
        }}
        
        function continuePayOrder(orderNo) {{
            currentOrderNo = orderNo;
            // 获取订单信息并显示支付弹窗
            fetch('/api/membership/order-status?order_no=' + encodeURIComponent(orderNo))
            .then(r => r.json())
            .then(data => {{
                if (data.success && data.order) {{
                    showPayModal(
                        data.order.plan_name || '会员套餐',
                        data.order.pay_amount,
                        data.qrcode_url,
                        data.is_mock
                    );
                    startPollOrderStatus();
                }}
            }});
        }}
        
        function cancelOrder(orderNo) {{
            if (!confirm('确定要取消该订单吗？')) return;
            
            fetch('/api/membership/cancel-order', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: `order_no=${{orderNo}}`
            }})
            .then(r => r.json())
            .then(data => {{
                if (data.success) {{
                    window.location.reload();
                }} else {{
                    alert(data.error || '取消失败');
                }}
            }});
        }}
    </script>
</body>
</html>'''
    
    return html.encode('utf-8')


def _get_common_styles() -> str:
    """获取通用样式"""
    return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                         'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            min-height: 100vh;
        }
    '''


def _get_auth_scripts() -> str:
    """获取鉴权相关的 JavaScript"""
    return '''
        let countdown = 0;
        let timer = null;
        
        async function sendCode(purpose = 'login') {
            const target = document.getElementById('target').value.trim();
            if (!target) {
                alert('请先输入手机号或邮箱');
                return;
            }
            
            const btn = document.getElementById('sendCodeBtn');
            btn.disabled = true;
            
            try {
                const response = await fetch('/api/auth/send-code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `target=${encodeURIComponent(target)}&purpose=${purpose}`
                });
                
                const data = await response.json();
                
                if (data.success) {
                    startCountdown();
                    
                    // 开发模式显示验证码
                    if (data.debug_code) {
                        const debugEl = document.getElementById('debugCode');
                        debugEl.textContent = `[开发模式] 验证码: ${data.debug_code}`;
                        debugEl.style.display = 'block';
                    }
                } else {
                    alert(data.message || '发送失败');
                    btn.disabled = false;
                }
            } catch (err) {
                alert('网络错误，请重试');
                btn.disabled = false;
            }
        }
        
        function startCountdown() {
            countdown = 60;
            updateCountdownBtn();
            
            timer = setInterval(() => {
                countdown--;
                if (countdown <= 0) {
                    clearInterval(timer);
                    document.getElementById('sendCodeBtn').disabled = false;
                    document.getElementById('sendCodeBtn').textContent = '获取验证码';
                } else {
                    updateCountdownBtn();
                }
            }, 1000);
        }
        
        function updateCountdownBtn() {
            document.getElementById('sendCodeBtn').textContent = `${countdown}s 后重试`;
        }
    '''
