# core/registry/registry.py
import json
from pathlib import Path
from typing import Dict, List, Optional
from core.model.source import Source
import logging

log = logging.getLogger(__name__)

class SourceRegistry:
    """数据源注册表管理"""
    
    def __init__(self, registry_file: Path):
        self.registry_file = registry_file
        self._sources: Dict[str, Source] = {}
        self._load_sources()
    
    def _load_sources(self):
        """从注册表文件加载数据源"""
        if not self.registry_file.exists():
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_sources()
            return
        
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            sources_data = data.get("items", {})
            for name_key, source_data in sources_data.items():
                source_data["name_key"] = name_key
                self._sources[name_key] = Source(**source_data)
            
            log.info(f"Loaded {len(self._sources)} sources from registry")
        except Exception as e:
            log.error(f"Failed to load registry: {e}")
            self._sources = {}
    
    def _save_sources(self):
        """保存数据源到注册表文件"""
        data = {
            "items": {
                name_key: {
                    "file": source.file,
                    "dot_path": source.dot_path,
                    "enabled": source.enabled,
                    "transform": source.transform
                }
                for name_key, source in self._sources.items()
            }
        }
        
        # 原子写入
        tmp_file = self.registry_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_file.replace(self.registry_file)
    
    def register_source(self, name_key: str, file_path: str, dot_path: Optional[str] = None) -> bool:
        """注册新的数据源"""
        try:
            source = Source(
                name_key=name_key,
                file=file_path,
                dot_path=dot_path
            )
            self._sources[name_key] = source
            self._save_sources()
            log.info(f"Registered source: {name_key} -> {file_path}")
            return True
        except Exception as e:
            log.error(f"Failed to register source {name_key}: {e}")
            return False
    
    def remove_source(self, name_key: str) -> bool:
        """移除数据源"""
        if name_key in self._sources:
            del self._sources[name_key]
            self._save_sources()
            log.info(f"Removed source: {name_key}")
            return True
        return False
    
    def get_source(self, name_key: str) -> Optional[Source]:
        """获取指定数据源"""
        return self._sources.get(name_key)
    
    def get_enabled_sources(self) -> Dict[str, Source]:
        """获取所有启用的数据源"""
        return {k: v for k, v in self._sources.items() if v.enabled}
    
    def list_sources(self) -> Dict[str, Source]:
        """列出所有数据源"""
        return self._sources.copy()
    
    def enable_source(self, name_key: str, enabled: bool = True) -> bool:
        """启用/禁用数据源"""
        if name_key in self._sources:
            self._sources[name_key].enabled = enabled
            self._save_sources()
            return True
        return False