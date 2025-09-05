# app/web/routes.py
from flask import Blueprint, jsonify
from app.web.handlers import WebhookHandler

def create_webhook_blueprint(handler: WebhookHandler) -> Blueprint:
    """创建企业微信回调蓝图"""
    bp = Blueprint('wecom', __name__, url_prefix='/wecom')
    
    @bp.route('/echo')
    def echo():
        """健康检查"""
        return "ok", 200
    
    @bp.route('/calc')
    def calc():
        """计算本地签名（调试用）"""
        from flask import request
        ts = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        
        local_sig = handler.crypto.calculate_local_signature(ts, nonce, echostr)
        
        return jsonify({
            "token_used": handler.crypto.token,
            "corp_used": handler.crypto.corp_id,
            "aes_len": len(handler.crypto.aes_key),
            "timestamp": ts,
            "nonce": nonce,
            "echostr_len": len(echostr),
            "local_sig": local_sig
        })
    
    @bp.route('/callback', methods=['GET', 'POST'])
    def callback():
        """企业微信回调处理"""
        from flask import request
        
        if request.method == 'GET':
            return handler.handle_verification()
        else:
            return handler.handle_message()
    
    return bp