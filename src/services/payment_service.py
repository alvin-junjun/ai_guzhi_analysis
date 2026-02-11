# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 支付服务

提供微信支付 Native 支付（二维码支付）功能
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from src.config import get_config

logger = logging.getLogger(__name__)


class WechatPayService:
    """
    微信支付服务
    
    实现微信支付 Native 支付（二维码支付）
    
    文档参考: https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_1.shtml
    """
    
    # API 域名
    API_HOST = "https://api.mch.weixin.qq.com"
    
    def __init__(self):
        self.config = get_config()
        self._private_key = None
    
    @property
    def is_enabled(self) -> bool:
        """检查微信支付是否已配置"""
        return (
            self.config.wechat_pay_enabled and
            self.config.wechat_pay_mchid and
            self.config.wechat_pay_appid and
            self.config.wechat_pay_api_v3_key
        )
    
    def _get_private_key(self) -> Optional[str]:
        """获取商户私钥"""
        if self._private_key:
            return self._private_key
        
        if not self.config.wechat_pay_private_key_path:
            return None
        
        try:
            with open(self.config.wechat_pay_private_key_path, 'r') as f:
                self._private_key = f.read()
            return self._private_key
        except Exception as e:
            logger.error(f"读取微信支付私钥失败: {e}")
            return None
    
    def _sign(self, message: str) -> Optional[str]:
        """
        使用商户私钥对消息进行 SHA256-RSA2048 签名
        
        Args:
            message: 待签名的消息
            
        Returns:
            Base64 编码的签名
        """
        private_key = self._get_private_key()
        if not private_key:
            return None
        
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            import base64
            
            # 加载私钥
            key = serialization.load_pem_private_key(
                private_key.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            # 签名
            signature = key.sign(
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return base64.b64encode(signature).decode('utf-8')
        except ImportError:
            logger.error("缺少 cryptography 库，请安装: pip install cryptography")
            return None
        except Exception as e:
            logger.error(f"签名失败: {e}")
            return None
    
    def _build_authorization(
        self,
        method: str,
        url: str,
        body: str = ""
    ) -> Optional[str]:
        """
        构建请求头中的 Authorization
        
        Args:
            method: HTTP 方法
            url: 请求 URL（不含域名）
            body: 请求体
            
        Returns:
            Authorization 头值
        """
        timestamp = str(int(time.time()))
        nonce_str = secrets.token_hex(16)
        
        # 构建签名串
        message = f"{method}\n{url}\n{timestamp}\n{nonce_str}\n{body}\n"
        
        signature = self._sign(message)
        if not signature:
            return None
        
        # 构建 Authorization
        auth = (
            f'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.config.wechat_pay_mchid}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.config.wechat_pay_cert_serial_no}"'
        )
        
        return auth
    
    def create_native_order(
        self,
        order_no: str,
        description: str,
        amount: int,
        attach: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        创建 Native 支付订单（二维码支付）
        
        Args:
            order_no: 商户订单号
            description: 商品描述
            amount: 金额（单位：分）
            attach: 附加数据
            
        Returns:
            (是否成功, 消息, 二维码链接)
        """
        if not self.is_enabled:
            return False, '微信支付未配置', None
        
        try:
            import requests
        except ImportError:
            return False, '缺少 requests 库', None
        
        url = "/v3/pay/transactions/native"
        
        # 构建请求体
        body_dict = {
            "appid": self.config.wechat_pay_appid,
            "mchid": self.config.wechat_pay_mchid,
            "description": description,
            "out_trade_no": order_no,
            "notify_url": self.config.wechat_pay_notify_url or "",
            "amount": {
                "total": amount,
                "currency": "CNY"
            }
        }
        
        if attach:
            body_dict["attach"] = attach
        
        body = json.dumps(body_dict, ensure_ascii=False)
        
        # 构建 Authorization
        auth = self._build_authorization("POST", url, body)
        if not auth:
            return False, '签名失败', None
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": auth,
        }
        
        try:
            response = requests.post(
                f"{self.API_HOST}{url}",
                headers=headers,
                data=body.encode('utf-8'),
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200:
                code_url = result.get("code_url")
                if code_url:
                    logger.info(f"创建支付订单成功: order_no={order_no}")
                    return True, '创建成功', code_url
                else:
                    return False, '未返回支付链接', None
            else:
                error_msg = result.get("message", "未知错误")
                logger.error(f"创建支付订单失败: {error_msg}")
                return False, error_msg, None
                
        except Exception as e:
            logger.error(f"请求微信支付接口失败: {e}")
            return False, str(e), None
    
    def verify_notify_signature(
        self,
        timestamp: str,
        nonce: str,
        body: str,
        signature: str
    ) -> bool:
        """
        验证支付回调通知的签名
        
        Args:
            timestamp: 时间戳
            nonce: 随机字符串
            body: 请求体
            signature: 签名值
            
        Returns:
            是否验证通过
        """
        # TODO: 实现签名验证（需要微信支付平台证书）
        # 暂时返回 True，生产环境必须实现
        logger.warning("支付回调签名验证未实现，请在生产环境中实现")
        return True
    
    def decrypt_notify_resource(
        self,
        ciphertext: str,
        nonce: str,
        associated_data: str
    ) -> Optional[Dict[str, Any]]:
        """
        解密支付回调通知中的密文
        
        使用 AEAD_AES_256_GCM 算法解密
        
        Args:
            ciphertext: Base64 编码的密文
            nonce: 随机字符串
            associated_data: 附加数据
            
        Returns:
            解密后的数据
        """
        if not self.config.wechat_pay_api_v3_key:
            return None
        
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import base64
            
            key = self.config.wechat_pay_api_v3_key.encode('utf-8')
            
            # Base64 解码
            ciphertext_bytes = base64.b64decode(ciphertext)
            nonce_bytes = nonce.encode('utf-8')
            associated_data_bytes = associated_data.encode('utf-8') if associated_data else b''
            
            # 解密
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce_bytes, ciphertext_bytes, associated_data_bytes)
            
            return json.loads(plaintext.decode('utf-8'))
            
        except ImportError:
            logger.error("缺少 cryptography 库")
            return None
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return None
    
    def parse_notify(self, body: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        解析支付回调通知
        
        Args:
            body: 回调请求体（JSON）
            
        Returns:
            (是否成功, 消息, 支付结果数据)
        """
        try:
            data = json.loads(body)
            
            event_type = data.get("event_type")
            if event_type != "TRANSACTION.SUCCESS":
                return False, f"非成功支付通知: {event_type}", None
            
            resource = data.get("resource", {})
            ciphertext = resource.get("ciphertext")
            nonce = resource.get("nonce")
            associated_data = resource.get("associated_data", "")
            
            if not ciphertext or not nonce:
                return False, "缺少加密数据", None
            
            # 解密
            result = self.decrypt_notify_resource(ciphertext, nonce, associated_data)
            if not result:
                return False, "解密失败", None
            
            return True, "解析成功", result
            
        except json.JSONDecodeError:
            return False, "JSON 解析失败", None
        except Exception as e:
            logger.error(f"解析支付通知失败: {e}")
            return False, str(e), None
    
    def query_order(self, order_no: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        查询订单状态
        
        Args:
            order_no: 商户订单号
            
        Returns:
            (是否成功, 消息, 订单数据)
        """
        if not self.is_enabled:
            return False, '微信支付未配置', None
        
        try:
            import requests
        except ImportError:
            return False, '缺少 requests 库', None
        
        url = f"/v3/pay/transactions/out-trade-no/{order_no}?mchid={self.config.wechat_pay_mchid}"
        
        auth = self._build_authorization("GET", url)
        if not auth:
            return False, '签名失败', None
        
        headers = {
            "Accept": "application/json",
            "Authorization": auth,
        }
        
        try:
            response = requests.get(
                f"{self.API_HOST}{url}",
                headers=headers,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return True, '查询成功', result
            else:
                error_msg = result.get("message", "未知错误")
                return False, error_msg, None
                
        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            return False, str(e), None


class MockPaymentService:
    """
    模拟支付服务
    
    用于开发和测试环境，不需要真实的支付配置
    """
    
    def __init__(self):
        self._mock_orders = {}  # 存储模拟订单状态
    
    @property
    def is_enabled(self) -> bool:
        return True
    
    def create_native_order(
        self,
        order_no: str,
        description: str,
        amount: int,
        attach: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        创建模拟支付订单
        
        返回一个模拟的支付链接，实际使用时可以直接调用模拟支付
        """
        # 生成模拟二维码链接（实际是一个内部确认页面）
        mock_url = f"/api/payment/mock-pay?order_no={order_no}&amount={amount}"
        
        # 存储订单状态
        self._mock_orders[order_no] = {
            'order_no': order_no,
            'description': description,
            'amount': amount,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
        }
        
        logger.info(f"[模拟支付] 创建订单: order_no={order_no}, amount={amount}分")
        return True, '创建成功（模拟）', mock_url
    
    def mock_pay_success(self, order_no: str) -> bool:
        """模拟支付成功"""
        if order_no in self._mock_orders:
            self._mock_orders[order_no]['status'] = 'paid'
            self._mock_orders[order_no]['paid_at'] = datetime.now().isoformat()
            return True
        return False
    
    def query_order(self, order_no: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """查询模拟订单"""
        if order_no in self._mock_orders:
            order = self._mock_orders[order_no]
            return True, '查询成功', {
                'out_trade_no': order_no,
                'trade_state': 'SUCCESS' if order['status'] == 'paid' else 'NOTPAY',
                'trade_state_desc': '支付成功' if order['status'] == 'paid' else '未支付',
            }
        return False, '订单不存在', None


# 全局服务实例
_wechat_pay_service: Optional[WechatPayService] = None
_mock_payment_service: Optional[MockPaymentService] = None


def get_payment_service() -> WechatPayService | MockPaymentService:
    """
    获取支付服务实例
    
    如果微信支付已配置，返回真实支付服务
    否则返回模拟支付服务（用于开发测试）
    """
    global _wechat_pay_service, _mock_payment_service
    
    config = get_config()
    
    # 生产环境使用真实支付
    if config.wechat_pay_enabled:
        if _wechat_pay_service is None:
            _wechat_pay_service = WechatPayService()
        return _wechat_pay_service
    
    # 开发环境使用模拟支付
    if _mock_payment_service is None:
        _mock_payment_service = MockPaymentService()
    return _mock_payment_service
