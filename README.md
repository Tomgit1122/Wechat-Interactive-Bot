# 企业微信变更播报机器人

一个基于Flask的企业微信机器人，支持多数据源的变更播报功能。机器人可以从多个JSON文件中收集未推送的更新，并通过企业微信推送给用户，同时自动标记为已推送状态。

## 核心特性

- **多数据源管理**: 支持注册、管理多个JSON数据源
- **智能推送**: 自动识别未推送项目（`pushed != true`），推送后自动标记
- **灵活路径**: 支持JSON内部路径导航（如 `a.b[0].c`）
- **幂等操作**: 多次刷新不会重复推送相同内容
- **安全可靠**: 路径白名单、原子写入、签名验证
- **易于扩展**: 分层架构，支持自定义格式化和转换

## 项目结构

```
project-root/
├── app/                      # 应用层
│   ├── main.py              # 应用入口点
│   ├── web/                 # Web层
│   │   ├── handlers.py      # 消息处理器
│   │   └── routes.py        # 路由定义
│   └── adapters/
│       └── wecom/           # 企业微信适配器
│           └── crypto.py    # 加解密处理
├── core/                    # 核心业务层
│   ├── model/
│   │   └── source.py        # 数据模型
│   ├── registry/
│   │   └── registry.py      # 数据源注册表
│   └── refresh/
│       └── engine.py        # 刷新引擎
├── config/
│   ├── settings.py          # 配置管理
│   ├── config.json          # 配置文件
│   └── bot_registry.json    # 数据源注册表
├── data/                    # JSON数据目录
│   └── status.json          # 示例数据文件
├── scripts/
│   └── manage_bot.py        # 管理脚本
└── docs/
    └── README.md            # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置企业微信

编辑 `config/config.json`：

```json
{
  "corp_id": "ww你的企业ID",
  "token": "你的验证Token",
  "aes_key": "你的EncodingAESKey_43位字符",
  "agent_id": 你的应用ID,
  "json_base_dir": "./data",
  "default_json_file": "status.json",
  "bot_registry_file": "config/bot_registry.json"
}
```

### 3. 启动服务

```bash
python app/main.py
```

服务将在 `http://0.0.0.0:5000` 启动。
cloudflared.exe --loglevel info --config config.yml tunnel run d6b627d7-dd5f-4391-abf0-c91d4d58aaab  (后面为cloudflared的ID）
### 4. 配置企业微信回调URL

在企业微信管理后台设置回调URL：
- URL: `https://你的域名/wecom/callback`
- Token: 与配置文件中的token一致
- EncodingAESKey: 与配置文件中的aes_key一致

## 使用方法

### 企业微信聊天命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/refresh` | 刷新所有数据源 | `/refresh` |
| `/refresh <源名称>` | 刷新指定数据源 | `/refresh status` |
| `/bots` | 列出所有数据源 | `/bots` |
| `/reset <源名称\|all>` | 重置推送状态 | `/reset status` |

### 管理脚本使用

```bash
# 注册新数据源
python scripts/manage_bot.py set 源名称 相对路径 [--key JSON路径]

# 示例：注册基础数据源
python scripts/manage_bot.py set status status.json

# 示例：注册带路径的数据源
python scripts/manage_bot.py set products products.json --key items.new_products

# 列出所有数据源
python scripts/manage_bot.py list

# 移除数据源
python scripts/manage_bot.py remove 源名称

# 启用/禁用数据源
python scripts/manage_bot.py enable 源名称
python scripts/manage_bot.py disable 源名称

# 测试刷新功能
python scripts/manage_bot.py test [--name 源名称]

# 重置pushed状态
python scripts/manage_bot.py reset 源名称
python scripts/manage_bot.py reset all
```

### Set_Wechat_Bot 快捷函数（兼容旧版本）

为了方便使用，可以定义这个快捷函数：

```python
def Set_Wechat_Bot(json_path: str, name_key: str, dot_path: str = None):
    """注册企业微信机器人数据源的快捷函数"""
    import subprocess
    import sys
    
    cmd = [sys.executable, "scripts/manage_bot.py", "set", name_key, json_path]
    if dot_path:
        cmd.extend(["--key", dot_path])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ 数据源 '{name_key}' 注册成功")
        return True
    else:
        print(f"✗ 注册失败: {result.stderr}")
        return False

# 使用示例
Set_Wechat_Bot("status.json", "status")
Set_Wechat_Bot("products.json", "products", "items.new_arrivals")
```

## 数据格式要求

### JSON数据结构

机器人支持以下两种JSON结构：

**1. 对象数组**
```json
[
  {
    "id": 1,
    "title": "新功能发布",
    "content": "添加了用户管理功能",
    "pushed": false
  },
  {
    "id": 2,
    "title": "Bug修复",
    "content": "修复了登录问题",
    "pushed": true
  }
]
```

**2. 对象集合**
```json
{
  "item_1": {
    "title": "系统升级",
    "content": "系统将在今晚升级",
    "pushed": false
  },
  "item_2": {
    "title": "维护通知",
    "content": "定期维护完成",
    "pushed": true
  }
}
```

**3. 嵌套结构（使用dot_path）**
```json
{
  "notifications": {
    "urgent": [
      {
        "title": "紧急通知",
        "content": "服务器故障已修复",
        "pushed": false
      }
    ]
  }
}
```

### pushed 字段规则

- `pushed: false` 或 `pushed` 字段不存在 → **未推送**，将被收集和推送
- `pushed: true` → **已推送**，不会再次推送
- 推送完成后，机器人自动将 `pushed` 设置为 `true`

## 配置说明

### 主配置文件 (config/config.json)

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `corp_id` | string | ✓ | 企业ID，以"ww"开头 |
| `token` | string | ✓ | 企业微信验证Token |
| `aes_key` | string | ✓ | EncodingAESKey，43位字符 |
| `agent_id` | number | | 应用ID |
| `json_base_dir` | string | | JSON文件基础目录 |
| `default_json_file` | string | | 默认JSON文件名 |
| `bot_registry_file` | string | | 注册表文件路径 |

### 数据源注册表 (config/bot_registry.json)

```json
{
  "items": {
    "status": {
      "file": "status.json",
      "dot_path": null,
      "enabled": true,
      "transform": null
    },
    "products": {
      "file": "products.json",
      "dot_path": "items.new_arrivals",
      "enabled": true,
      "transform": null
    }
  }
}
```

## 开发和调试

### 健康检查

```bash
# 检查服务状态
curl http://localhost:5000/wecom/echo

# 计算签名（调试用）
curl "http://localhost:5000/wecom/calc?timestamp=1234567890&nonce=abc123&echostr=test"
```

### 日志监控

应用使用标准Python logging，可以通过环境变量控制日志级别：

```bash
export PYTHONPATH="."
export LOGGING_LEVEL="DEBUG"
python app/main.py
```

### 测试数据源

```bash
# 测试所有数据源
python scripts/manage_bot.py test

# 测试特定数据源
python scripts/manage_bot.py test --name status

# 重置数据用于重复测试
python scripts/manage_bot.py reset all
```

## 故障排查

### 常见问题

1. **签名验证失败**
   - 检查token是否与企业微信后台一致
   - 使用 `/wecom/calc` 接口对比本地签名

2. **消息解密失败**
   - 验证aes_key长度为43位
   - 确认corp_id格式正确（以ww开头）

3. **文件不存在错误**
   - 确认JSON文件在白名单目录内
   - 检查文件路径拼写是否正确

4. **dot_path路径错误**
   - 使用 `a.b[0].c` 格式访问嵌套数据
   - 确认路径存在且指向对象或数组

### 错误码说明

- `[ERR] JSON not found`: 数据文件不存在
- `[ERR] write failed`: 文件写入失败（权限或磁盘问题）
- `VERIFY_FAIL`: 签名验证失败
- `DECRYPT_FAIL`: 消息解密失败
- `ENCRYPT_FAIL`: 回复加密失败

## 安全考虑

- **路径安全**: 使用白名单机制防止路径逃逸攻击
- **数据完整性**: 原子写入确保数据一致性
- **敏感信息**: 配置文件中的敏感信息在日志中被掩码处理
- **访问控制**: 仅处理来自已验证的企业微信请求

## 扩展和自定义

### 添加自定义格式化器

```python
# 在 core/refresh/engine.py 中扩展 _format_items 方法
def _format_items(self, items: List[Dict], source_name: str = "") -> str:
    # 自定义格式化逻辑
    if source_name == "products":
        return self._format_products(items)
    else:
        return self._default_format(items)
```

### 添加新的数据源类型

通过继承 `RefreshEngine` 类可以支持其他数据源：

```python
class HttpRefreshEngine(RefreshEngine):
    def refresh_http_source(self, url: str) -> str:
        # 从HTTP API获取数据的逻辑
        pass
```

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---


**支持**: 如有问题请在项目仓库提交Issue或联系维护团队。
