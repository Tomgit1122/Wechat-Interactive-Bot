# app/adapters/wecom/crypto.py
import hashlib
import logging
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise import parse_message, create_reply

log = logging.getLogger(__name__)

class WeChatCryptoAdapter:
    """企业微信加解密适配器"""
    
    def __init__(self, token: str, aes_key: str, corp_id: str):
        self.token = token
        self.aes_key = aes_key
        self.corp_id = corp_id
        self.crypto = WeChatCrypto(token, aes_key, corp_id)
    
    def _sha1(self, s: str) -> str:
        """SHA1哈希计算"""
        return hashlib.sha1(s.encode("utf-8")).hexdigest()
    
    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证签名并解密echostr"""
        try:
            echo_plain = self.crypto.check_signature(msg_signature, timestamp, nonce, echostr)
            log.info(f"Signature verification successful, echo_len={len(echo_plain or '')}")
            return echo_plain
        except Exception as e:
            log.error(f"Signature verification failed: {e}")
            raise
    
    def decrypt_message(self, encrypted_data: bytes, msg_signature: str, timestamp: str, nonce: str):
        """解密消息"""
        try:
            msg_xml = self.crypto.decrypt_message(encrypted_data, msg_signature, timestamp, nonce)
            msg = parse_message(msg_xml)
            log.info(f"Message decrypted successfully, type={msg.type}")
            return msg
        except Exception as e:
            log.error(f"Message decryption failed: {e}")
            raise
    
    def encrypt_reply(self, reply_msg, nonce: str, timestamp: str) -> str:
        """加密回复消息"""
        try:
            xml = self.crypto.encrypt_message(reply_msg.render(), nonce, timestamp)
            log.info(f"Reply encrypted successfully, xml_len={len(xml or '')}")
            return xml
        except Exception as e:
            log.error(f"Reply encryption failed: {e}")
            raise
    
    def create_text_reply(self, content: str, original_msg) -> object:
        """创建文本回复"""
        return create_reply(content, original_msg)
    
    def calculate_local_signature(self, timestamp: str, nonce: str, echostr: str) -> str:
        """计算本地签名（用于调试）"""
        return self._sha1("".join(sorted([self.token, timestamp, nonce, echostr])))