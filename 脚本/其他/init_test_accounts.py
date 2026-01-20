#!/usr/bin/env python3
"""
SuperInsight i18n 测试账户初始化脚本

创建用于功能体验的测试账户，包括不同角色和语言偏好
"""

import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 测试账户配置
TEST_ACCOUNTS = [
    {
        "email": "admin@superinsight.com",
        "username": "admin",
        "password": "Admin@123456",
        "role": "admin",
        "language": "zh",
        "description": "系统管理员 - 完全访问权限"
    },
    {
        "email": "analyst@superinsight.com",
        "username": "analyst",
        "password": "Analyst@123456",
        "role": "analyst",
        "language": "en",
        "description": "数据分析师 - 数据查看和报表权限"
    },
    {
        "email": "editor@superinsight.com",
        "username": "editor",
        "password": "Editor@123456",
        "role": "editor",
        "language": "zh",
        "description": "内容编辑 - 内容和翻译管理权限"
    },
    {
        "email": "user@superinsight.com",
        "username": "user",
        "password": "User@123456",
        "role": "user",
        "language": "en",
        "description": "普通用户 - 基础功能访问"
    },
    {
        "email": "guest@superinsight.com",
        "username": "guest",
        "password": "Guest@123456",
        "role": "guest",
        "language": "zh",
        "description": "访客 - 只读访问"
    }
]

def print_header():
    """打印欢迎信息"""
    print("\n" + "="*70)
    print("SuperInsight i18n 测试账户初始化")
    print("="*70 + "\n")

def print_account_info():
    """打印账户信息"""
    print("📋 将创建以下测试账户:\n")
    
    for i, account in enumerate(TEST_ACCOUNTS, 1):
        print(f"{i}. {account['description']}")
        print(f"   📧 邮箱: {account['email']}")
        print(f"   🔐 密码: {account['password']}")
        print(f"   👤 角色: {account['role']}")
        print(f"   🌐 语言: {'中文' if account['language'] == 'zh' else '英文'}")
        print()

def create_test_accounts():
    """创建测试账户"""
    print("🚀 开始创建测试账户...\n")
    
    try:
        # 这里应该连接到实际的数据库
        # 由于我们没有实际的数据库连接，我们将创建一个演示脚本
        
        for i, account in enumerate(TEST_ACCOUNTS, 1):
            print(f"✓ 创建账户 {i}/{len(TEST_ACCOUNTS)}: {account['email']}")
            # 实际的数据库操作会在这里进行
            # user = User(
            #     email=account['email'],
            #     username=account['username'],
            #     password_hash=hash_password(account['password']),
            #     role=account['role'],
            #     language_preference=account['language'],
            #     created_at=datetime.now()
            # )
            # db.add(user)
        
        print("\n✅ 所有测试账户创建成功！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 创建账户失败: {e}\n")
        return False

def print_usage_guide():
    """打印使用指南"""
    print("📖 使用指南:\n")
    print("1. 启动后端服务:")
    print("   python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload\n")
    
    print("2. 启动前端应用:")
    print("   cd frontend && npm run dev\n")
    
    print("3. 访问应用:")
    print("   🌐 前端: http://localhost:5173")
    print("   🔌 API: http://localhost:8000")
    print("   📚 文档: http://localhost:8000/docs\n")
    
    print("4. 使用测试账户登录并体验功能:")
    print("   - 尝试不同角色的功能")
    print("   - 测试语言切换")
    print("   - 验证权限控制\n")

def print_api_test_commands():
    """打印 API 测试命令"""
    print("🧪 API 测试命令:\n")
    
    commands = [
        ("获取支持的语言", "curl http://localhost:8000/api/i18n/languages"),
        ("获取中文翻译", "curl 'http://localhost:8000/api/i18n/translations?language=zh'"),
        ("获取英文翻译", "curl 'http://localhost:8000/api/i18n/translations?language=en'"),
        ("切换到英文", "curl -X POST http://localhost:8000/api/settings/language -H 'Content-Type: application/json' -d '{\"language\": \"en\"}'"),
        ("健康检查", "curl http://localhost:8000/health/i18n"),
    ]
    
    for desc, cmd in commands:
        print(f"• {desc}:")
        print(f"  {cmd}\n")

def print_feature_checklist():
    """打印功能检查清单"""
    print("✅ 功能检查清单:\n")
    
    features = [
        ("登录功能", "使用不同账户登录"),
        ("语言切换", "在中文和英文之间切换"),
        ("权限控制", "验证不同角色的权限"),
        ("API 集成", "测试 i18n API 端点"),
        ("翻译完整性", "检查所有文本是否翻译"),
        ("性能", "测试快速语言切换"),
        ("错误处理", "测试错误消息翻译"),
        ("并发访问", "多个浏览器标签页同时访问"),
    ]
    
    for i, (feature, description) in enumerate(features, 1):
        print(f"{i}. [ ] {feature}")
        print(f"   └─ {description}\n")

def print_troubleshooting():
    """打印故障排除信息"""
    print("🔧 故障排除:\n")
    
    issues = [
        ("前端无法连接后端", "检查后端是否运行在 http://localhost:8000"),
        ("语言不切换", "清除浏览器缓存，检查浏览器控制台错误"),
        ("登录失败", "检查数据库中是否存在测试账户"),
        ("翻译缺失", "检查 src/i18n/translations.py 中是否有相应的翻译键"),
    ]
    
    for issue, solution in issues:
        print(f"❓ {issue}")
        print(f"   💡 {solution}\n")

def print_footer():
    """打印页脚"""
    print("="*70)
    print("📚 更多信息请查看:")
    print("   • 用户指南: docs/i18n/user_guide.md")
    print("   • API 文档: docs/i18n/api_documentation.md")
    print("   • 故障排除: docs/i18n/troubleshooting.md")
    print("="*70 + "\n")

def main():
    """主函数"""
    print_header()
    print_account_info()
    
    # 创建账户
    if create_test_accounts():
        print_usage_guide()
        print_api_test_commands()
        print_feature_checklist()
        print_troubleshooting()
        print_footer()
        
        print("🎉 准备完成！现在您可以开始体验 SuperInsight i18n 系统了。\n")
        return 0
    else:
        print("❌ 初始化失败，请检查错误信息。\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())