# WebUI 功能升级方案

> 文档版本：v1.0  
> 创建日期：2026-02-04  
> 状态：待实施

---

## 目录

- [一、需求概述](#一需求概述)
- [二、现有架构分析](#二现有架构分析)
- [三、需求1：WebUI 鉴权功能](#三需求1webui-鉴权功能)
- [四、需求2：微信充值会员功能](#四需求2微信充值会员功能)
- [五、需求3：隐藏后端股票池配置](#五需求3隐藏后端股票池配置)
- [六、需求4：用户邮箱接收报告](#六需求4用户邮箱接收报告)
- [七、数据库设计](#七数据库设计)
- [八、实施计划](#八实施计划)
- [九、安全注意事项](#九安全注意事项)

---

## 一、需求概述

| 序号 | 需求 | 描述 | 优先级 |
|------|------|------|--------|
| 1 | WebUI 鉴权 | 只有注册手机号或白名单手机号才能使用 | 高 |
| 2 | 微信充值会员 | 按周/月/季度收费的会员套餐 | 中 |
| 3 | 隐藏股票池 | 界面不展示后端配置的股票池 | 高 |
| 4 | 用户邮箱 | 支持用户录入 QQ 邮箱接收分析报告 | 中 |

---

## 二、现有架构分析

### 2.1 技术栈

| 组件 | 技术方案 |
|------|----------|
| Web 服务 | Python `http.server.ThreadingHTTPServer` |
| 数据库 | SQLite + SQLAlchemy ORM |
| 配置管理 | `.env` 文件 + `dataclass` 单例 |
| 模板渲染 | Python 字符串拼接 HTML |

### 2.2 核心文件结构

```
daily_stock_analysis/
├── web/                          # WebUI 模块
│   ├── server.py                 # HTTP 服务器启动
│   ├── router.py                 # 路由分发
│   ├── handlers.py               # 请求处理器
│   ├── services.py               # 业务逻辑层
│   └── templates.py              # HTML 模板渲染
├── src/                          # 核心业务模块
│   ├── config.py                 # 全局配置（单例）
│   ├── storage.py                # 数据库管理（单例）
│   └── notification.py           # 通知推送（含邮件）
└── data/
    └── stock_analysis.db         # SQLite 数据库文件
```

### 2.3 数据库连接链路

```
.env 文件
  └── DATABASE_PATH=./data/stock_analysis.db
        ↓
src/config.py
  └── Config.database_path (默认: ./data/stock_analysis.db)
  └── Config.get_db_url() → "sqlite:///绝对路径"
        ↓
src/storage.py
  └── DatabaseManager.__init__()
  └── SQLAlchemy create_engine()
        ↓
SQLite 文件
  └── ./data/stock_analysis.db
```

### 2.4 现有数据模型

```python
# src/storage.py - StockDaily 表
class StockDaily(Base):
    __tablename__ = 'stock_daily'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10))      # 股票代码
    date = Column(Date)            # 交易日期
    open/high/low/close = Column(Float)  # OHLC
    volume = Column(Float)         # 成交量
    amount = Column(Float)         # 成交额
    pct_chg = Column(Float)        # 涨跌幅
    ma5/ma10/ma20 = Column(Float)  # 均线
    # ...
```

---

## 三、需求1：WebUI 鉴权功能

### 3.1 功能描述

- 用户访问 WebUI 需要先登录
- 支持手机号 + 验证码登录
- 手机号验证规则：
  1. 数据库 `users` 表中已注册
  2. 或 ENV 白名单 `PHONE_WHITELIST` 中存在

### 3.2 鉴权流程

```
┌─────────────────────────────────────────────────────────────┐
│                      鉴权流程图                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  用户访问任意页面                                            │
│         ↓                                                   │
│  检查 Cookie 中的 Session Token                             │
│         ↓                                                   │
│  ┌─────────────────┐                                        │
│  │ Token 有效?      │──── 否 ───→ 跳转 /login               │
│  └─────────────────┘                                        │
│         │ 是                                                │
│         ↓                                                   │
│  允许访问目标页面                                            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                      登录流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GET /login → 展示登录页面                                   │
│         ↓                                                   │
│  用户输入手机号，点击"发送验证码"                             │
│         ↓                                                   │
│  POST /api/sms/send → 验证手机号是否在白名单/已注册           │
│         ↓                                                   │
│  ┌─────────────────┐                                        │
│  │ 允许登录?        │──── 否 ───→ 返回错误提示               │
│  └─────────────────┘                                        │
│         │ 是                                                │
│         ↓                                                   │
│  生成验证码，存入 sms_codes 表，发送短信（或邮件）            │
│         ↓                                                   │
│  用户输入验证码，点击"登录"                                   │
│         ↓                                                   │
│  POST /login → 验证手机号+验证码                             │
│         ↓                                                   │
│  ┌─────────────────┐                                        │
│  │ 验证通过?        │──── 否 ───→ 返回错误提示               │
│  └─────────────────┘                                        │
│         │ 是                                                │
│         ↓                                                   │
│  创建/更新用户记录，生成 Session Token                       │
│         ↓                                                   │
│  Set-Cookie: session=xxx; HttpOnly; Secure                  │
│         ↓                                                   │
│  重定向到首页 /                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 新增文件

| 文件 | 说明 |
|------|------|
| `src/models/user.py` | 用户数据模型 (User, SmsCode) |
| `web/auth.py` | 鉴权中间件、Session 管理 |
| `web/handlers_auth.py` | 登录/登出处理器 |
| `web/templates_auth.py` | 登录页面模板 |

### 3.4 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/config.py` | 新增 `PHONE_WHITELIST`、`SESSION_SECRET_KEY` 等配置 |
| `src/storage.py` | 新增 User、SmsCode 表的 ORM 模型 |
| `web/router.py` | 新增登录路由、添加鉴权拦截 |
| `web/server.py` | 集成鉴权中间件 |

### 3.5 配置项

```env
# .env 新增配置

# 白名单手机号（逗号分隔）
PHONE_WHITELIST=13800138000,13900139000

# Session 配置
SESSION_SECRET_KEY=your-random-secret-key-at-least-32-chars
SESSION_EXPIRE_HOURS=24

# 短信服务配置（可选，不配置则使用邮件验证码）
SMS_PROVIDER=aliyun
SMS_ACCESS_KEY=xxx
SMS_SECRET_KEY=xxx
SMS_SIGN_NAME=xxx
SMS_TEMPLATE_CODE=xxx
```

### 3.6 简化方案（无短信）

如果不接入短信服务，可采用以下替代方案：

1. **邮件验证码**：用户输入邮箱，发送验证码到邮箱
2. **固定密码**：管理员为用户设置密码，用户使用手机号+密码登录
3. **白名单直接登录**：白名单用户输入手机号即可登录（仅限内部使用）

---

## 四、需求2：微信充值会员功能

### 4.1 功能描述

- 提供多档位会员套餐（周卡/月卡/季卡）
- 支持微信扫码支付
- 会员享有更多分析次数和功能

### 4.2 套餐设计

| 套餐 | 价格 | 有效期 | 每日分析次数 | 其他权益 |
|------|------|--------|--------------|----------|
| 免费用户 | ¥0 | - | 5次 | 精简报告 |
| 周卡 | ¥19.9 | 7天 | 50次 | 完整报告、邮件推送 |
| 月卡 | ¥49.9 | 30天 | 100次 | 完整报告、邮件推送 |
| 季卡 | ¥99.9 | 90天 | 不限 | 完整报告、邮件推送、优先响应 |

### 4.3 支付流程

```
┌─────────────────────────────────────────────────────────────┐
│                     微信支付流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  用户点击"购买会员"                                          │
│         ↓                                                   │
│  展示套餐列表，用户选择套餐                                   │
│         ↓                                                   │
│  POST /api/pay/create                                       │
│  参数: { plan_id: 1 }                                       │
│         ↓                                                   │
│  后端调用微信支付 Native API                                 │
│  生成支付二维码 URL                                          │
│         ↓                                                   │
│  返回 { order_no, qrcode_url, amount }                      │
│         ↓                                                   │
│  前端展示二维码，用户微信扫码支付                             │
│         ↓                                                   │
│  前端轮询 GET /api/pay/status?order_no=xxx                  │
│         ↓                                                   │
│  ┌─────────────────┐                                        │
│  │ 支付完成?        │──── 否 ───→ 继续等待                   │
│  └─────────────────┘                                        │
│         │ 是                                                │
│         ↓                                                   │
│  展示支付成功，刷新会员状态                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                   微信支付回调处理                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  微信服务器 POST /api/pay/notify                            │
│         ↓                                                   │
│  验证签名                                                    │
│         ↓                                                   │
│  ┌─────────────────┐                                        │
│  │ 签名有效?        │──── 否 ───→ 返回失败                   │
│  └─────────────────┘                                        │
│         │ 是                                                │
│         ↓                                                   │
│  更新订单状态为"已支付"                                       │
│         ↓                                                   │
│  创建用户会员记录                                            │
│         ↓                                                   │
│  返回成功响应给微信                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 新增文件

| 文件 | 说明 |
|------|------|
| `src/models/membership.py` | 会员/订单/套餐数据模型 |
| `src/payment/wechat_pay.py` | 微信支付 Native 支付封装 |
| `web/handlers_pay.py` | 支付相关处理器 |
| `web/templates_pay.py` | 会员页面、支付弹窗模板 |

### 4.5 配置项

```env
# .env 新增配置

# 微信支付配置（Native 支付 - 商户模式）
WECHAT_PAY_APP_ID=wxXXXXXXXXXXXXXXXX
WECHAT_PAY_MCH_ID=1XXXXXXXXX
WECHAT_PAY_API_KEY_V3=your-api-v3-key
WECHAT_PAY_SERIAL_NO=证书序列号
WECHAT_PAY_CERT_PATH=./certs/apiclient_cert.pem
WECHAT_PAY_KEY_PATH=./certs/apiclient_key.pem
WECHAT_PAY_NOTIFY_URL=https://your-domain.com/api/pay/notify
```

### 4.6 微信支付申请要求

| 要求 | 说明 |
|------|------|
| 企业资质 | 需要企业营业执照 |
| 微信商户号 | 在 pay.weixin.qq.com 申请 |
| 公众号/小程序 | 需要已认证的公众号或小程序 |
| HTTPS 域名 | 支付回调地址必须是 HTTPS |

### 4.7 依赖库

```txt
# requirements.txt 新增
wechatpay-python>=0.1.0  # 微信支付 SDK
qrcode>=7.0              # 二维码生成
```

---

## 五、需求3：隐藏后端股票池配置

### 5.1 当前问题

当前首页展示了后端 `.env` 中的 `STOCK_LIST` 配置，并允许用户修改：

```html
<!-- web/templates.py render_config_page() -->
<form method="post" action="/update">
  <label>📋 自选股列表</label>
  <textarea name="stock_list">{stock_list}</textarea>
  <button type="submit">💾 保存</button>
</form>
```

### 5.2 方案选择

| 方案 | 描述 | 推荐 |
|------|------|------|
| A | 直接删除该区域 HTML | 简单快速 |
| B | 根据用户权限条件渲染（管理员可见） | 推荐 |
| C | 改为用户个人股票池（存数据库） | 功能最完整 |

### 5.3 推荐方案 B 实现

修改 `web/templates.py`：

```python
def render_config_page(
    stock_list: str,
    env_filename: str,
    message: Optional[str] = None,
    is_admin: bool = False  # 新增参数
) -> bytes:
    
    # 管理员才展示股票池配置
    stock_config_html = ""
    if is_admin:
        stock_config_html = f"""
        <hr class="section-divider">
        <form method="post" action="/update">
          <div class="form-group">
            <label>📋 自选股列表</label>
            <textarea name="stock_list">{stock_list}</textarea>
          </div>
          <button type="submit">💾 保存</button>
        </form>
        """
    
    content = f"""
    <div class="container">
      <!-- 分析区域 -->
      ...
      {stock_config_html}
    </div>
    """
```

### 5.4 修改文件

| 文件 | 修改内容 |
|------|----------|
| `web/templates.py` | `render_config_page` 添加 `is_admin` 参数 |
| `web/handlers.py` | `handle_index` 传入当前用户是否为管理员 |
| `web/router.py` | `/update` 路由添加管理员权限检查 |

---

## 六、需求4：用户邮箱接收报告

### 6.1 功能描述

- 用户可在设置页面填写 QQ 邮箱
- 分析完成后自动发送报告到用户邮箱
- 可开关邮件推送功能

### 6.2 用户设置页面

```
┌─────────────────────────────────────────────┐
│           ⚙️ 个人设置                        │
├─────────────────────────────────────────────┤
│                                             │
│  手机号：138****8000                         │
│                                             │
│  📧 接收邮箱                                 │
│  ┌─────────────────────────────────────┐   │
│  │ example@qq.com                      │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ☑️ 启用邮件推送                             │
│     分析完成后自动发送报告到邮箱              │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │           💾 保存设置                │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 6.3 推送流程

```
分析任务完成
     ↓
获取当前用户信息
     ↓
┌─────────────────┐
│ 用户配置了邮箱?  │──── 否 ───→ 结束
└─────────────────┘
     │ 是
     ↓
┌─────────────────┐
│ 启用邮件推送?    │──── 否 ───→ 结束
└─────────────────┘
     │ 是
     ↓
调用 notification.send_to_email()
参数: content=报告内容, receivers=[用户邮箱]
     ↓
发送完成
```

### 6.4 新增文件

| 文件 | 说明 |
|------|------|
| `web/handlers_user.py` | 用户设置处理器 |
| `web/templates_user.py` | 用户设置页面模板 |

### 6.5 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/models/user.py` | User 模型添加 `email`、`email_notify_enabled` 字段 |
| `web/router.py` | 新增 `/user/settings` 路由 |
| `web/services.py` | `_run_analysis` 完成后检查并发送用户邮件 |
| `src/notification.py` | `send_to_email` 支持自定义收件人列表 |

### 6.6 邮件发送逻辑

```python
# web/services.py - AnalysisService._run_analysis()

def _run_analysis(self, code, task_id, report_type, source_user=None):
    # ... 执行分析 ...
    
    if result and source_user:
        # 发送用户个人邮件
        self._send_user_email(source_user, result)
    
    return result

def _send_user_email(self, user, result):
    """发送分析报告到用户邮箱"""
    if not user.email or not user.email_notify_enabled:
        return
    
    from src.notification import get_notifier
    notifier = get_notifier()
    
    # 格式化报告内容
    content = self._format_email_report(result)
    subject = f"📈 {result.name}({result.code}) 分析报告"
    
    try:
        notifier.send_to_email(
            content=content,
            subject=subject,
            receivers=[user.email]
        )
        logger.info(f"已发送分析报告到 {user.email}")
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
```

---

## 七、数据库设计

### 7.1 新增表结构

```sql
-- =============================================
-- 用户表
-- =============================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(20) UNIQUE NOT NULL,          -- 手机号（登录凭证）
    nickname VARCHAR(50),                        -- 昵称
    email VARCHAR(100),                          -- 接收邮箱
    email_notify_enabled BOOLEAN DEFAULT FALSE,  -- 是否启用邮件推送
    is_admin BOOLEAN DEFAULT FALSE,              -- 是否管理员
    status VARCHAR(20) DEFAULT 'active',         -- 状态: active/disabled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME,
    
    INDEX ix_users_phone (phone)
);

-- =============================================
-- 短信/邮件验证码表
-- =============================================
CREATE TABLE verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(20) NOT NULL,                  -- 手机号
    code VARCHAR(10) NOT NULL,                   -- 验证码
    type VARCHAR(20) DEFAULT 'sms',              -- 类型: sms/email
    expires_at DATETIME NOT NULL,                -- 过期时间
    used BOOLEAN DEFAULT FALSE,                  -- 是否已使用
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX ix_verification_codes_phone (phone)
);

-- =============================================
-- 会员套餐表
-- =============================================
CREATE TABLE membership_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,                   -- 套餐名称
    price DECIMAL(10,2) NOT NULL,                -- 价格（元）
    duration_days INTEGER NOT NULL,              -- 有效天数
    daily_analysis_limit INTEGER DEFAULT -1,     -- 每日分析次数（-1表示不限）
    features TEXT,                               -- 功能说明 JSON
    sort_order INTEGER DEFAULT 0,                -- 排序
    is_active BOOLEAN DEFAULT TRUE,              -- 是否上架
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 订单表
-- =============================================
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no VARCHAR(50) UNIQUE NOT NULL,        -- 订单号
    user_id INTEGER NOT NULL,                    -- 用户ID
    plan_id INTEGER NOT NULL,                    -- 套餐ID
    amount DECIMAL(10,2) NOT NULL,               -- 实付金额
    payment_method VARCHAR(20) DEFAULT 'wechat', -- 支付方式
    payment_status VARCHAR(20) DEFAULT 'pending',-- pending/paid/failed/refunded
    transaction_id VARCHAR(100),                 -- 第三方交易号
    paid_at DATETIME,                            -- 支付时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_id) REFERENCES membership_plans(id),
    INDEX ix_orders_user_id (user_id),
    INDEX ix_orders_order_no (order_no)
);

-- =============================================
-- 用户会员表
-- =============================================
CREATE TABLE user_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,                    -- 用户ID
    plan_id INTEGER NOT NULL,                    -- 套餐ID
    order_id INTEGER,                            -- 关联订单ID
    start_date DATETIME NOT NULL,                -- 开始时间
    end_date DATETIME NOT NULL,                  -- 到期时间
    status VARCHAR(20) DEFAULT 'active',         -- active/expired/cancelled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_id) REFERENCES membership_plans(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    INDEX ix_user_memberships_user_id (user_id)
);

-- =============================================
-- 用户每日使用量表
-- =============================================
CREATE TABLE daily_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    usage_date DATE NOT NULL,
    analysis_count INTEGER DEFAULT 0,            -- 当日分析次数
    
    UNIQUE(user_id, usage_date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =============================================
-- 用户 Session 表（可选，也可用 Cookie 加密存储）
-- =============================================
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token VARCHAR(100) UNIQUE NOT NULL,          -- Session Token
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX ix_user_sessions_token (token)
);
```

### 7.2 数据模型关系图

```
                    ┌─────────────────┐
                    │     users       │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ daily_usage   │   │    orders     │   │user_sessions  │
└───────────────┘   └───────┬───────┘   └───────────────┘
                            │
                            ▼
                   ┌───────────────┐
                   │user_memberships│
                   └───────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │membership_plans│
                  └────────────────┘

┌─────────────────────┐
│ verification_codes  │  (独立表)
└─────────────────────┘
```

### 7.3 初始化数据

```sql
-- 初始化套餐数据
INSERT INTO membership_plans (name, price, duration_days, daily_analysis_limit, sort_order) VALUES
('周卡', 19.90, 7, 50, 1),
('月卡', 49.90, 30, 100, 2),
('季卡', 99.90, 90, -1, 3);
```

---

## 八、实施计划

### 8.1 阶段划分

| 阶段 | 内容 | 预估工作量 | 依赖 |
|------|------|------------|------|
| **阶段1** | 鉴权系统 + 隐藏股票池 | 中 | 无 |
| **阶段2** | 用户设置 + 邮箱推送 | 小 | 阶段1 |
| **阶段3** | 会员系统 + 微信支付 | 大 | 阶段1 |

### 8.2 阶段1：鉴权系统

**目标**：实现用户登录、Session 管理、权限控制

**任务清单**：
- [ ] 新建 `src/models/user.py`，定义 User、VerificationCode 模型
- [ ] 修改 `src/storage.py`，注册新模型到 SQLAlchemy
- [ ] 新建 `web/auth.py`，实现 Session 管理
- [ ] 新建 `web/handlers_auth.py`，实现登录/登出处理器
- [ ] 新建 `web/templates_auth.py`，实现登录页面
- [ ] 修改 `web/router.py`，添加鉴权路由和中间件
- [ ] 修改 `web/templates.py`，隐藏股票池配置区域
- [ ] 修改 `src/config.py`，添加白名单等配置
- [ ] 编写测试用例

### 8.3 阶段2：用户设置

**目标**：用户可配置邮箱，分析完成后发送报告

**任务清单**：
- [ ] 修改 User 模型，添加 email 相关字段
- [ ] 新建 `web/handlers_user.py`，用户设置处理器
- [ ] 新建 `web/templates_user.py`，用户设置页面
- [ ] 修改 `web/router.py`，添加设置路由
- [ ] 修改 `web/services.py`，分析完成后发送邮件
- [ ] 编写测试用例

### 8.4 阶段3：会员系统

**目标**：实现套餐购买、微信支付、会员权益

**任务清单**：
- [ ] 新建 `src/models/membership.py`，会员相关模型
- [ ] 新建 `src/payment/wechat_pay.py`，微信支付封装
- [ ] 新建 `web/handlers_pay.py`，支付处理器
- [ ] 新建 `web/templates_pay.py`，会员页面
- [ ] 修改 `web/router.py`，添加支付路由
- [ ] 实现每日使用量限制逻辑
- [ ] 编写测试用例

---

## 九、安全注意事项

### 9.1 鉴权安全

| 风险 | 措施 |
|------|------|
| Session 劫持 | Token 使用 HMAC 签名，设置 HttpOnly、Secure 标志 |
| 验证码爆破 | 限制发送频率（60秒/次）、错误次数锁定 |
| 越权访问 | 每个请求验证用户身份和权限 |

### 9.2 支付安全

| 风险 | 措施 |
|------|------|
| 回调伪造 | 验证微信签名 |
| 重复通知 | 幂等处理，检查订单状态 |
| 金额篡改 | 服务端存储套餐价格，不信任前端传参 |

### 9.3 数据安全

| 风险 | 措施 |
|------|------|
| 敏感信息泄露 | API Key、Secret 不写入代码，使用环境变量 |
| SQL 注入 | 使用 SQLAlchemy ORM，避免拼接 SQL |
| XSS 攻击 | HTML 输出使用 `html.escape()` 转义 |

### 9.4 配置示例

```env
# =============================================
# 新增配置项汇总
# =============================================

# --- 鉴权配置 ---
PHONE_WHITELIST=13800138000,13900139000
SESSION_SECRET_KEY=your-32-chars-random-secret-key
SESSION_EXPIRE_HOURS=24

# --- 短信服务（可选）---
SMS_PROVIDER=aliyun
SMS_ACCESS_KEY=
SMS_SECRET_KEY=
SMS_SIGN_NAME=
SMS_TEMPLATE_CODE=

# --- 微信支付（会员功能需要）---
WECHAT_PAY_APP_ID=
WECHAT_PAY_MCH_ID=
WECHAT_PAY_API_KEY_V3=
WECHAT_PAY_SERIAL_NO=
WECHAT_PAY_CERT_PATH=./certs/apiclient_cert.pem
WECHAT_PAY_KEY_PATH=./certs/apiclient_key.pem
WECHAT_PAY_NOTIFY_URL=https://your-domain.com/api/pay/notify
```

---

## 附录

### A. 新增路由汇总

| 路由 | 方法 | 说明 | 鉴权 |
|------|------|------|------|
| `/login` | GET | 登录页面 | 无 |
| `/login` | POST | 提交登录 | 无 |
| `/logout` | GET | 登出 | 需要 |
| `/api/sms/send` | POST | 发送验证码 | 无 |
| `/user/settings` | GET | 用户设置页 | 需要 |
| `/user/settings` | POST | 保存设置 | 需要 |
| `/membership` | GET | 会员中心 | 需要 |
| `/api/pay/create` | POST | 创建支付 | 需要 |
| `/api/pay/status` | GET | 查询订单 | 需要 |
| `/api/pay/notify` | POST | 微信回调 | 签名验证 |

### B. 文件变更清单

**新增文件**：
- `src/models/user.py`
- `src/models/membership.py`
- `src/payment/wechat_pay.py`
- `web/auth.py`
- `web/handlers_auth.py`
- `web/handlers_user.py`
- `web/handlers_pay.py`
- `web/templates_auth.py`
- `web/templates_user.py`
- `web/templates_pay.py`

**修改文件**：
- `src/config.py`
- `src/storage.py`
- `web/router.py`
- `web/server.py`
- `web/handlers.py`
- `web/services.py`
- `web/templates.py`

---

> **下一步**：确认方案后，按阶段逐步实施。建议从阶段1（鉴权系统）开始。
