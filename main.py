# app/main.py
import logging
from pathlib import Path
from flask import Flask
from app.web.routes import create_webhook_blueprint
from app.web.handlers import WebhookHandler
from app.adapters.wecom.crypto import WeChatCryptoAdapter
from core.registry.registry import SourceRegistry
from core.refresh.engine import RefreshEngine
from config.settings import Settings

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def create_app() -> Flask:
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 加载配置
    settings = Settings.load()
    
    # 验证配置
    settings.validate()
    
    # 初始化组件
    crypto_adapter = WeChatCryptoAdapter(
        token=settings.token,
        aes_key=settings.aes_key,
        corp_id=settings.corp_id
    )
    
    registry_file = Path(settings.bot_registry_file)
    registry = SourceRegistry(registry_file)
    
    refresh_engine = RefreshEngine(settings.json_base_dir)
    
    # 初始化处理器
    handler = WebhookHandler(crypto_adapter, registry, refresh_engine)
    
    # 注册路由
    app.register_blueprint(create_webhook_blueprint(handler))
    
    # 添加默认数据源（兼容旧版本）
    if not registry.list_sources():
        registry.register_source(
            name_key="default",
            file_path=settings.default_json_file,
            dot_path=None
        )
        log.info("Registered default source")
    
    log.info("Application initialized successfully")
    return app

def main():
    """应用入口点"""
    app = create_app()
    log.info("Starting WeChat Work Bot server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main()