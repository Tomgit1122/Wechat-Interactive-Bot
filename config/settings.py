# config/settings.py
from __future__ import annotations
import json
import os
import re
import base64
import logging
from pathlib import Path
from pydantic import BaseModel, field_validator

log = logging.getLogger(__name__)

class Settings(BaseModel):
    """配置设置"""
    # 企业微信配置
    corp_id: str                                  # 企业ID
    token: str                                    # 验证Token
    aes_key: str                                  # 加密密钥
    agent_id: int = 0                            # 应用ID
    
    # 业务配置
    json_base_dir: Path = Path("./data")         # JSON文件基础目录
    default_json_file: str = "status.json"       # 默认JSON文件
    bot_registry_file: str = "config/bot_registry.json"  # 注册表文件
    
    @field_validator("corp_id")
    @classmethod
    def validate_corp_id(cls, v: str) -> str:
        if not (v and v.startswith("ww")):
            raise ValueError("corp_id must start with 'ww'")
        return v
    
    @field_validator("aes_key")
    @classmethod
    def validate_aes_key(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9]{43}", v or ""):
            raise ValueError("aes_key must be 43 alnum chars")
        try:
            if len(base64.b64decode((v or "") + "=")) != 32:
                raise ValueError("aes_key base64 decode != 32 bytes")
        except Exception as e:
            raise ValueError(f"aes_key invalid base64: {e}")
        return v
    
    @field_validator("json_base_dir", mode="before")
    @classmethod
    def validate_base_dir(cls, v) -> Path:
        return Path(v or "./data").expanduser().resolve()
    
    @classmethod
    def load(cls, config_file: str = None) -> Settings:
        """加载配置文件"""
        config_path = config_file or os.getenv("WECOM_CONFIG_FILE", "config/config.json")
        p = Path(config_path).expanduser().resolve()
        
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        settings = cls(**data)
        log.info(f"Configuration loaded from {p}")
        return settings
    
    def validate(self):
        """验证配置有效性"""
        def mask(s: str, head=4, tail=4) -> str:
            if not s:
                return "EMPTY"
            if len(s) <= head + tail:
                return s
            return f"{s[:head]}...{s[-tail:]}"
        
        # 验证基本配置
        errors = []
        
        if not self.token:
            errors.append("TOKEN is empty")
        
        if not (self.corp_id and self.corp_id.startswith("ww")):
            errors.append(f"CORP_ID looks wrong: {self.corp_id}")
        
        if not re.fullmatch(r"[A-Za-z0-9]{43}", self.aes_key or ""):
            errors.append(f"AES_KEY length/format error: len={len(self.aes_key or '')}")
        else:
            try:
                if len(base64.b64decode(self.aes_key + "=")) != 32:
                    errors.append("AES_KEY base64 decoded bytes != 32")
            except Exception as e:
                errors.append(f"AES_KEY base64 decode error: {e}")
        
        # 输出配置信息（掩码）
        log.info(f"Config validation:")
        log.info(f"  token: {self.token!r}")
        log.info(f"  corp_id: {mask(self.corp_id)}")
        log.info(f"  aes_key: {mask(self.aes_key)} (len={len(self.aes_key or '')})")
        log.info(f"  json_base_dir: {self.json_base_dir}")
        log.info(f"  default_json_file: {self.default_json_file}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise RuntimeError(error_msg)