# -*- coding: utf-8 -*-
"""
A股智能分析系统 - 系统配置模型

定义系统配置相关的数据模型
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, Text

from src.storage import Base


class SystemConfig(Base):
    """
    系统配置表
    
    存储动态配置项，可在运行时修改
    """
    __tablename__ = 'system_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 配置键值
    config_key = Column(String(100), unique=True, nullable=False, index=True, comment='配置键')
    config_value = Column(Text, nullable=True, comment='配置值')
    
    # 描述
    description = Column(String(255), nullable=True, comment='配置描述')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def __repr__(self):
        return f"<SystemConfig(key={self.config_key})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_int_value(self, default: int = 0) -> int:
        """获取整数值"""
        try:
            return int(self.config_value) if self.config_value else default
        except (ValueError, TypeError):
            return default
    
    def get_float_value(self, default: float = 0.0) -> float:
        """获取浮点数值"""
        try:
            return float(self.config_value) if self.config_value else default
        except (ValueError, TypeError):
            return default
    
    def get_bool_value(self, default: bool = False) -> bool:
        """获取布尔值"""
        if self.config_value is None:
            return default
        return self.config_value.lower() in ('true', '1', 'yes', 'on')
