# core/model/source.py
from __future__ import annotations
from pydantic import BaseModel, field_validator
from pathlib import Path
from typing import Optional

class Source(BaseModel):
    """数据源模型：包含文件路径、键路径等信息"""
    name_key: str                    # 源别名
    file: str                        # 相对路径
    dot_path: Optional[str] = None   # 点路径（可选）
    enabled: bool = True             # 是否启用
    transform: Optional[str] = None  # 预留格式化器
    
    @field_validator("name_key")
    @classmethod
    def validate_name_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name_key cannot be empty")
        return v.strip()
    
    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("file path cannot be empty")
        return v.strip()

class Item(BaseModel):
    """更新项模型：JSON中的一个对象"""
    pushed: bool = False  # 是否已播报
    
    class Config:
        extra = "allow"  # 允许额外字段