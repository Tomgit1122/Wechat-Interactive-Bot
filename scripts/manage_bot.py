#!/usr/bin/env python3
# scripts/manage_bot.py
"""
企业微信机器人管理脚本
支持注册、移除、列表、启用/禁用数据源等操作
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.registry.registry import SourceRegistry
from core.refresh.engine import RefreshEngine
from config.settings import Settings

def set_source(args):
    """注册/更新数据源"""
    settings = Settings.load()
    registry = SourceRegistry(Path(settings.bot_registry_file))
    
    success = registry.register_source(
        name_key=args.name,
        file_path=args.file,
        dot_path=args.key
    )
    
    if success:
        print(f"✓ 数据源 '{args.name}' 注册成功")
        print(f"  文件: {args.file}")
        if args.key:
            print(f"  路径: {args.key}")
    else:
        print(f"✗ 数据源 '{args.name}' 注册失败")
        sys.exit(1)

def remove_source(args):
    """移除数据源"""
    settings = Settings.load()
    registry = SourceRegistry(Path(settings.bot_registry_file))
    
    if registry.remove_source(args.name):
        print(f"✓ 数据源 '{args.name}' 已移除")
    else:
        print(f"✗ 数据源 '{args.name}' 不存在")
        sys.exit(1)

def list_sources(args):
    """列出所有数据源"""
    settings = Settings.load()
    registry = SourceRegistry(Path(settings.bot_registry_file))
    sources = registry.list_sources()
    
    if not sources:
        print("未配置任何数据源")
        return
    
    print(f"已注册的数据源 ({len(sources)}):")
    print("-" * 60)
    for name_key, source in sources.items():
        status = "启用" if source.enabled else "禁用"
        print(f"名称: {name_key}")
        print(f"文件: {source.file}")
        if source.dot_path:
            print(f"路径: {source.dot_path}")
        print(f"状态: {status}")
        print("-" * 60)

def enable_source(args):
    """启用/禁用数据源"""
    settings = Settings.load()
    registry = SourceRegistry(Path(settings.bot_registry_file))
    
    if registry.enable_source(args.name, not args.disable):
        action = "禁用" if args.disable else "启用"
        print(f"✓ 数据源 '{args.name}' 已{action}")
    else:
        print(f"✗ 数据源 '{args.name}' 不存在")
        sys.exit(1)

def test_refresh(args):
    """测试刷新功能"""
    settings = Settings.load()
    registry = SourceRegistry(Path(settings.bot_registry_file))
    engine = RefreshEngine(settings.json_base_dir)
    
    if args.name:
        # 刷新指定源
        source = registry.get_source(args.name)
        if not source:
            print(f"✗ 数据源 '{args.name}' 不存在")
            sys.exit(1)
        
        print(f"刷新数据源: {args.name}")
        result = engine.refresh_source(source)
    else:
        # 刷新所有源
        sources = registry.get_enabled_sources()
        print(f"刷新所有启用的数据源 ({len(sources)})...")
        result = engine.refresh_multiple_sources(sources)
    
    print("=" * 60)
    print(result)
    print("=" * 60)

def reset_source(args):
    """重置数据源pushed状态"""
    settings = Settings.load()
    registry = SourceRegistry(Path(settings.bot_registry_file))
    engine = RefreshEngine(settings.json_base_dir)
    
    if args.name == "all":
        # 重置所有源
        sources = registry.get_enabled_sources()
        print(f"重置所有数据源 ({len(sources)})...")
        for name_key, source in sources.items():
            result = engine.reset_source(source)
            print(f"  {name_key}: {result}")
    else:
        # 重置指定源
        source = registry.get_source(args.name)
        if not source:
            print(f"✗ 数据源 '{args.name}' 不存在")
            sys.exit(1)
        
        print(f"重置数据源: {args.name}")
        result = engine.reset_source(source)
        print(result)

def main():
    parser = argparse.ArgumentParser(description="企业微信机器人管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # set 命令
    set_parser = subparsers.add_parser("set", help="注册/更新数据源")
    set_parser.add_argument("name", help="数据源名称")
    set_parser.add_argument("file", help="JSON文件相对路径")
    set_parser.add_argument("--key", help="JSON内部路径 (如 a.b[0].c)")
    set_parser.set_defaults(func=set_source)
    
    # remove 命令
    remove_parser = subparsers.add_parser("remove", help="移除数据源")
    remove_parser.add_argument("name", help="数据源名称")
    remove_parser.set_defaults(func=remove_source)
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有数据源")
    list_parser.set_defaults(func=list_sources)
    
    # enable/disable 命令
    enable_parser = subparsers.add_parser("enable", help="启用数据源")
    enable_parser.add_argument("name", help="数据源名称")
    enable_parser.set_defaults(func=enable_source)
    
    disable_parser = subparsers.add_parser("disable", help="禁用数据源")
    disable_parser.add_argument("name", help="数据源名称")
    disable_parser.add_argument("--disable", action="store_true", default=True)
    disable_parser.set_defaults(func=enable_source)
    
    # test 命令
    test_parser = subparsers.add_parser("test", help="测试刷新功能")
    test_parser.add_argument("--name", help="指定数据源名称，不指定则刷新全部")
    test_parser.set_defaults(func=test_refresh)
    
    # reset 命令
    reset_parser = subparsers.add_parser("reset", help="重置pushed状态")
    reset_parser.add_argument("name", help="数据源名称或'all'")
    reset_parser.set_defaults(func=reset_source)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        print(f"✗ 执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()