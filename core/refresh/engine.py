# core/refresh/engine.py
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from core.model.source import Source
import logging

log = logging.getLogger(__name__)

class RefreshEngine:
    """刷新引擎：读取→过滤→写回→渲染"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def _safe_join(self, *paths: str) -> Path:
        """安全路径拼接，防止路径逃逸"""
        p = (self.base_dir / Path(*paths)).resolve()
        if not str(p).startswith(str(self.base_dir)):
            raise PermissionError("path escapes base dir")
        return p
    
    def _get_by_dot_path(self, data: Any, path: str) -> Any:
        """支持 a.b[0].c 取值"""
        tokens = []
        for part in path.split("."):
            tokens.extend(re.findall(r"[^\[\]]+|\[\d+\]", part))
        
        cur = data
        for t in tokens:
            if t.startswith("[") and t.endswith("]"):
                idx = int(t[1:-1])
                if not isinstance(cur, list):
                    raise KeyError(f"not list before index {idx}")
                cur = cur[idx]
            else:
                if not isinstance(cur, dict):
                    raise KeyError(f"not dict before key '{t}'")
                cur = cur[t]
        return cur
    
    def _atomic_write(self, path: Path, data_obj: Any):
        """原子写入JSON文件"""
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data_obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.replace(path)
    
    def _collect_unpushed_items(self, target: Any) -> tuple[List[Dict], bool]:
        """收集未推送项并标记为已推送"""
        unpushed_items = []
        changed = False
        
        def mark_and_collect_in_list(lst: List):
            nonlocal changed
            for i, item in enumerate(lst):
                if isinstance(item, dict):
                    if not item.get("pushed", False):
                        unpushed_items.append(item.copy())
                        lst[i]["pushed"] = True
                        changed = True
        
        def mark_and_collect_in_dict(dct: Dict):
            nonlocal changed
            for k, v in dct.items():
                if isinstance(v, dict):
                    if not v.get("pushed", False):
                        unpushed_items.append(v.copy())
                        dct[k]["pushed"] = True
                        changed = True
        
        if isinstance(target, list):
            mark_and_collect_in_list(target)
        elif isinstance(target, dict):
            # 判断是对象集合还是单个对象
            is_collection = any(isinstance(v, dict) for v in target.values()) and len(target) > 1
            if is_collection:
                mark_and_collect_in_dict(target)
            else:
                # 单对象处理
                if not target.get("pushed", False):
                    unpushed_items.append(target.copy())
                    target["pushed"] = True
                    changed = True
        else:
            raise ValueError("Selected JSON must be list/dict (of objects).")
        
        return unpushed_items, changed
    
    def refresh_source(self, source: Source) -> str:
        """刷新单个数据源"""
        try:
            json_path = self._safe_join(source.file)
            
            if not json_path.exists():
                return f"[ERR] JSON not found: {source.file}"
            
            # 读取JSON数据
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 定位到目标路径
            target = data if not source.dot_path else self._get_by_dot_path(data, source.dot_path)
            
            # 收集未推送项
            unpushed_items, changed = self._collect_unpushed_items(target)
            
            if not unpushed_items:
                return "No Any Update"
            
            # 写回文件
            if changed:
                self._atomic_write(json_path, data)
            
            # 格式化输出
            return self._format_items(unpushed_items, source.name_key)
            
        except Exception as e:
            log.error(f"Failed to refresh source {source.name_key}: {e}")
            return f"[ERR] {source.name_key}: {e}"
    
    def refresh_multiple_sources(self, sources: Dict[str, Source]) -> str:
        """刷新多个数据源"""
        if not sources:
            return "No sources configured"
        
        results = []
        for name_key, source in sources.items():
            result = self.refresh_source(source)
            if result != "No Any Update":
                if result.startswith("[ERR]"):
                    results.append(result)
                else:
                    results.append(f"[{name_key}]\n{result}")
        
        if not results:
            return "No Any Update"
        
        return "\n\n".join(results)
    
    def _format_items(self, items: List[Dict], source_name: str = "") -> str:
        """格式化输出项目"""
        if not items:
            return "No Any Update"
        
        # 简单JSON格式化，限制长度
        text = json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True)
        if len(text) > 4000:
            text = text[:4000] + "\n...[truncated]"
        
        return text
    
    def reset_source(self, source: Source) -> str:
        """重置数据源（将pushed设置为false）"""
        try:
            json_path = self._safe_join(source.file)
            
            if not json_path.exists():
                return f"[ERR] JSON not found: {source.file}"
            
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            target = data if not source.dot_path else self._get_by_dot_path(data, source.dot_path)
            
            # 重置pushed标记
            reset_count = self._reset_pushed_flags(target)
            
            if reset_count > 0:
                self._atomic_write(json_path, data)
                return f"Reset {reset_count} items in {source.name_key}"
            else:
                return f"No items to reset in {source.name_key}"
                
        except Exception as e:
            log.error(f"Failed to reset source {source.name_key}: {e}")
            return f"[ERR] {source.name_key}: {e}"
    
    def _reset_pushed_flags(self, target: Any) -> int:
        """重置pushed标记，返回重置数量"""
        reset_count = 0
        
        if isinstance(target, list):
            for item in target:
                if isinstance(item, dict) and item.get("pushed", False):
                    item["pushed"] = False
                    reset_count += 1
        elif isinstance(target, dict):
            is_collection = any(isinstance(v, dict) for v in target.values()) and len(target) > 1
            if is_collection:
                for v in target.values():
                    if isinstance(v, dict) and v.get("pushed", False):
                        v["pushed"] = False
                        reset_count += 1
            else:
                if target.get("pushed", False):
                    target["pushed"] = False
                    reset_count += 1
        
        return reset_count