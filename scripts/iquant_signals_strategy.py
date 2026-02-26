# -*- coding: gbk -*-
"""
国信 iQuant 策略：从 AI 分析系统拉取买入/加仓信号并自动下单。
整段复制到 iQuant 策略编辑器即可使用。实盘前请先用模拟模式验证。
"""
# ==================== 请修改以下配置后复制到 iQuant ====================
ACCOUNT_ID = '510600126129'                    # 您的资金账号（与 .env 中 BROKER_STOCK_ACCOUNT 一致）
SIGNALS_API_URL = 'https://www.guzhiaibot.online/api/trading/signals'   # 本系统信号接口地址
BUY_SHARES_PER_SIGNAL = 100                  # 每只信号买入股数（100 的整数倍）
TIMER_SECONDS = 60                           # 拉取信号间隔（秒）
# ======================================================================

def init(ContextInfo):
    ContextInfo.acc_id = ACCOUNT_ID
    ContextInfo.signals_url = SIGNALS_API_URL
    ContextInfo.buy_shares = BUY_SHARES_PER_SIGNAL
    ContextInfo.sent_codes = getattr(ContextInfo, 'sent_codes', set())
    ContextInfo.set_account(ContextInfo.acc_id)
    ContextInfo.run_time('on_timer', '%dnSecond' % TIMER_SECONDS, '2000-01-01 09:35:00', 'SH')

def on_timer(ContextInfo):
    import urllib.request
    import json
    try:
        req = urllib.request.Request(ContextInfo.signals_url)
        req.add_header('User-Agent', 'iQuant-Signals/1.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print('拉取信号失败: %s' % e)
        return
    if not data.get('success') or not data.get('signals'):
        return
    for s in data['signals']:
        code = s.get('code')
        if s.get('action') != 'buy' or not code or code in ContextInfo.sent_codes:
            continue
        code = str(code).strip()
        if '.' in code:
            code = code.split('.')[0]
        if not code.isdigit():
            continue
        stock_qmt = (code + '.SH') if code.startswith('6') else (code + '.SZ')
        passorder(23, 1101, ContextInfo.acc_id, stock_qmt, 5, 0, ContextInfo.buy_shares, ' ', 1, ' ', ContextInfo)
        ContextInfo.sent_codes.add(s.get('code'))
        print('已发买入: %s %s' % (stock_qmt, ContextInfo.buy_shares))

def handlebar(ContextInfo):
    pass
