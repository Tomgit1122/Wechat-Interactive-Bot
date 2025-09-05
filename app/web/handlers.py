# app/web/handlers.py
import uuid
import logging
from flask import request, make_response, jsonify
from app.adapters.wecom.crypto import WeChatCryptoAdapter
from core.registry.registry import SourceRegistry
from core.refresh.engine import RefreshEngine

log = logging.getLogger(__name__)

class WebhookHandler:
    """企业微信回调处理器"""
    
    def __init__(self, crypto_adapter: WeChatCryptoAdapter, 
                 registry: SourceRegistry, 
                 refresh_engine: RefreshEngine):
        self.crypto = crypto_adapter
        self.registry = registry
        self.engine = refresh_engine
    
    def handle_verification(self) -> tuple[str, int]:
        """处理URL验证"""
        rid = uuid.uuid4().hex[:8]
        
        msg_signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        
        log.info(f"[RID {rid}] URL verification request")
        log.info(f"[RID {rid}] msg_sig={msg_signature}")
        log.info(f"[RID {rid}] echostr_len={len(echostr)}")
        
        try:
            echo_plain = self.crypto.verify_signature(msg_signature, timestamp, nonce, echostr)
            resp = make_response(echo_plain)
            resp.headers["Content-Type"] = "text/plain; charset=utf-8"
            log.info(f"[RID {rid}] Verification successful")
            return resp, 200
        except Exception as e:
            local_sig = self.crypto.calculate_local_signature(timestamp, nonce, echostr)
            log.error(f"[RID {rid}] Verification failed: {e}")
            return f"signature verify failed: {e}; local_sig={local_sig}", 400
    
    def handle_message(self) -> tuple[str, int]:
        """处理用户消息"""
        rid = uuid.uuid4().hex[:8]
        
        msg_signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        
        log.info(f"[RID {rid}] Message received, content_length={request.content_length}")
        
        try:
            # 解密消息
            msg = self.crypto.decrypt_message(request.data, msg_signature, timestamp, nonce)
            
            # 处理消息
            reply_text = self._process_message(msg, rid)
            reply = self.crypto.create_text_reply(reply_text, msg)
            
            # 加密回复
            xml = self.crypto.encrypt_reply(reply, nonce, timestamp)
            resp = make_response(xml)
            resp.headers["Content-Type"] = "application/xml; charset=utf-8"
            
            log.info(f"[RID {rid}] Message processed successfully")
            return resp, 200
            
        except Exception as e:
            log.error(f"[RID {rid}] Message processing failed: {e}")
            return f"message processing failed: {e}", 500
    
    def _process_message(self, msg, rid: str) -> str:
        """处理具体的消息逻辑"""
        if msg.type != "text":
            log.info(f"[RID {rid}] Non-text message type: {msg.type}")
            return "仅支持文本消息。发送 /refresh 查看用法。"
        
        content = (msg.content or "").strip()
        log.info(f"[RID {rid}] Text message: {content}")
        
        # 解析命令
        if content.startswith("/refresh"):
            return self._handle_refresh_command(content, rid)
        elif content.startswith("/bots"):
            return self._handle_bots_command(rid)
        elif content.startswith("/reset"):
            return self._handle_reset_command(content, rid)
        else:
            return self._get_help_text()
    
    def _handle_refresh_command(self, content: str, rid: str) -> str:
        """处理刷新命令"""
        parts = content.split()
        
        # 解析参数
        if len(parts) == 1:
            # /refresh - 刷新所有源
            sources = self.registry.get_enabled_sources()
            result = self.engine.refresh_multiple_sources(sources)
            log.info(f"[RID {rid}] Refresh all sources: {len(sources)} sources")
            return result
        
        # /refresh <name_key> - 刷新指定源
        name_key = parts[1].strip()
        source = self.registry.get_source(name_key)
        
        if not source:
            available = ", ".join(self.registry.list_sources().keys())
            return f"源 '{name_key}' 不存在。可用源: {available}"
        
        if not source.enabled:
            return f"源 '{name_key}' 已禁用"
        
        result = self.engine.refresh_source(source)
        log.info(f"[RID {rid}] Refresh source {name_key}")
        return result
    
    def _handle_bots_command(self, rid: str) -> str:
        """处理bots列表命令"""
        sources = self.registry.list_sources()
        if not sources:
            return "未配置任何数据源"
        
        lines = ["已注册的数据源:"]
        for name_key, source in sources.items():
            status = "启用" if source.enabled else "禁用"
            dot_info = f" (key={source.dot_path})" if source.dot_path else ""
            lines.append(f"- {name_key}: {source.file}{dot_info} [{status}]")
        
        log.info(f"[RID {rid}] List bots: {len(sources)} sources")
        return "\n".join(lines)
    
    def _handle_reset_command(self, content: str, rid: str) -> str:
        """处理重置命令"""
        parts = content.split()
        
        if len(parts) < 2:
            return "用法: /reset <源名称|all>"
        
        target = parts[1].strip()
        
        if target == "all":
            # 重置所有源
            sources = self.registry.get_enabled_sources()
            results = []
            for name_key, source in sources.items():
                result = self.engine.reset_source(source)
                if not result.startswith("[ERR]"):
                    results.append(result)
            
            if results:
                log.info(f"[RID {rid}] Reset all sources: {len(results)} sources reset")
                return "\n".join(results)
            else:
                return "没有源需要重置"
        else:
            # 重置指定源
            source = self.registry.get_source(target)
            if not source:
                available = ", ".join(self.registry.list_sources().keys())
                return f"源 '{target}' 不存在。可用源: {available}"
            
            result = self.engine.reset_source(source)
            log.info(f"[RID {rid}] Reset source {target}")
            return result
    
    def _get_help_text(self) -> str:
        """获取帮助文本"""
        return (
            "可用命令:\n"
            "/refresh - 刷新所有数据源\n"
            "/refresh <源名称> - 刷新指定数据源\n"
            "/bots - 列出所有已注册数据源\n"
            "/reset <源名称|all> - 重置推送状态\n"
            "\n示例:\n"
            "/refresh\n"
            "/refresh status\n"
            "/bots\n"
            "/reset status"
        )