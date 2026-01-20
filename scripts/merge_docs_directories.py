#!/usr/bin/env python3
"""
Merge docs/ and 文档/ directories into a single unified 文档/ directory.
All files are renamed to Chinese names and properly categorized.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of source files to target categories and new names
FILE_MAPPING = {
    # Root level files from docs/
    "docs/API.md": ("功能实现", "API文档.md"),
    "docs/i18n_thread_safety.md": ("国际化翻译", "国际化线程安全.md"),
    "docs/llm-integration-guide.md": ("功能实现", "LLM集成指南.md"),
    "docs/ORACLE_SETUP.md": ("部署指南", "Oracle设置指南.md"),
    "docs/plugin-development-guide.md": ("功能实现", "插件开发指南.md"),
    "docs/SECURITY.md": ("系统集成", "安全指南.md"),
    "docs/SQLALCHEMY_MIGRATION.md": ("系统集成", "SQLAlchemy迁移指南.md"),
    "docs/text-to-sql-plugin-guide.md": ("功能实现", "文本转SQL插件指南.md"),
    "docs/version-control-guide.md": ("依赖版本", "版本控制指南.md"),
    
    # api/ directory
    "docs/api/ai-annotation.md": ("功能实现", "AI标注.md"),
    "docs/api/error-codes.md": ("功能实现", "错误代码.md"),
    "docs/api/extraction.md": ("功能实现", "数据提取.md"),
    "docs/api/integration-guide.md": ("功能实现", "API集成指南.md"),
    "docs/api/README.md": ("功能实现", "API说明.md"),
    
    # business-logic/ directory
    "docs/business-logic/algorithm-principles.md": ("功能实现", "算法原理.md"),
    "docs/business-logic/api-reference.md": ("功能实现", "业务逻辑API参考.md"),
    "docs/business-logic/faq.md": ("其他", "业务逻辑常见问题.md"),
    "docs/business-logic/README.md": ("功能实现", "业务逻辑说明.md"),
    "docs/business-logic/troubleshooting.md": ("问题修复", "业务逻辑故障排除.md"),
    "docs/business-logic/user-guides/admin-configuration.md": ("功能实现", "管理员配置指南.md"),
    "docs/business-logic/user-guides/business-analyst-guide.md": ("功能实现", "业务分析师指南.md"),
    "docs/business-logic/user-guides/custom-algorithms.md": ("功能实现", "自定义算法.md"),
    "docs/business-logic/user-guides/integration-guide.md": ("功能实现", "业务逻辑集成指南.md"),
    "docs/business-logic/user-guides/monitoring-maintenance.md": ("服务管理", "监控维护.md"),
    "docs/business-logic/user-guides/performance-optimization.md": ("功能实现", "性能优化.md"),
    
    # data-sync/ directory
    "docs/data-sync/API_REFERENCE.md": ("功能实现", "数据同步API参考.md"),
    "docs/data-sync/ARCHITECTURE.md": ("功能实现", "数据同步架构.md"),
    "docs/data-sync/USER_GUIDE.md": ("功能实现", "数据同步用户指南.md"),
    
    # deployment/ directory
    "docs/deployment/tcb-deployment-guide.md": ("部署指南", "TCB部署指南.md"),
    "docs/deployment/tcb-operations.md": ("服务管理", "TCB操作指南.md"),
    "docs/deployment/tcb-troubleshooting.md": ("问题修复", "TCB故障排除.md"),
    
    # frontend/ directory
    "docs/frontend/DEVELOPER_GUIDE.md": ("前端开发", "前端开发者指南.md"),
    "docs/frontend/USER_MANUAL.md": ("前端开发", "前端用户手册.md"),
    
    # i18n/ directory
    "docs/i18n/api_documentation.md": ("国际化翻译", "国际化API文档.md"),
    "docs/i18n/architecture.md": ("国际化翻译", "国际化架构.md"),
    "docs/i18n/configuration.md": ("国际化翻译", "国际化配置.md"),
    "docs/i18n/deployment_guide.md": ("国际化翻译", "国际化部署指南.md"),
    "docs/i18n/extension_guide.md": ("国际化翻译", "国际化扩展指南.md"),
    "docs/i18n/integration_examples.md": ("国际化翻译", "国际化集成示例.md"),
    "docs/i18n/label-studio-chinese-validation.md": ("国际化翻译", "Label Studio中文验证.md"),
    "docs/i18n/testing_procedures.md": ("国际化翻译", "国际化测试程序.md"),
    "docs/i18n/troubleshooting.md": ("国际化翻译", "国际化故障排除.md"),
    "docs/i18n/user_guide.md": ("国际化翻译", "国际化用户指南.md"),
    
    # knowledge-graph/ directory
    "docs/knowledge-graph/API_REFERENCE.md": ("功能实现", "知识图谱API参考.md"),
    
    # quality-billing/ directory
    "docs/quality-billing/API_REFERENCE.md": ("功能实现", "质量计费API参考.md"),
    "docs/quality-billing/ARCHITECTURE.md": ("功能实现", "质量计费架构.md"),
    "docs/quality-billing/DEPLOYMENT.md": ("部署指南", "质量计费部署指南.md"),
    "docs/quality-billing/USER_GUIDE.md": ("功能实现", "质量计费用户指南.md"),
    
    # label-studio/ directory
    "docs/label-studio/api-reference.md": ("功能实现", "Label Studio API参考.md"),
    "docs/label-studio/best-practices.md": ("功能实现", "Label Studio最佳实践.md"),
    "docs/label-studio/deployment-guide.md": ("部署指南", "Label Studio部署指南.md"),
    "docs/label-studio/environment-setup.md": ("部署指南", "Label Studio环境设置.md"),
    "docs/label-studio/faq.md": ("其他", "Label Studio常见问题.md"),
    "docs/label-studio/iframe-deployment-verification.md": ("功能实现", "Label Studio iframe部署验证.md"),
    "docs/label-studio/iframe-integration-api.md": ("功能实现", "Label Studio iframe集成API.md"),
    "docs/label-studio/iframe-integration-guide.md": ("功能实现", "Label Studio iframe集成指南.md"),
    "docs/label-studio/iframe-templates-guide.md": ("功能实现", "Label Studio iframe模板指南.md"),
    "docs/label-studio/iframe-troubleshooting.md": ("问题修复", "Label Studio iframe故障排除.md"),
    "docs/label-studio/iframe-user-guide.md": ("功能实现", "Label Studio iframe用户指南.md"),
    "docs/label-studio/iframe-version-management.md": ("功能实现", "Label Studio iframe版本管理.md"),
    "docs/label-studio/integration-guide.md": ("功能实现", "Label Studio集成指南.md"),
    "docs/label-studio/README.md": ("功能实现", "Label Studio说明.md"),
    "docs/label-studio/troubleshooting.md": ("问题修复", "Label Studio故障排除.md"),
    "docs/label-studio/user-manual.md": ("功能实现", "Label Studio用户手册.md"),
    
    # Chinese directories from docs/
    "docs/Docker相关/Docker完整栈分析.md": ("Docker", "Docker完整栈分析.md"),
    "docs/Docker相关/Docker完整栈完成指南.md": ("Docker", "Docker完整栈完成指南.md"),
    "docs/部署文档/本地部署指南.md": ("部署指南", "本地部署指南.md"),
    "docs/部署文档/本地测试指南.md": ("部署指南", "本地测试指南.md"),
    "docs/部署文档/本地访问指南.md": ("部署指南", "本地访问指南.md"),
    "docs/部署文档/本地启动指南.md": ("部署指南", "本地启动指南.md"),
    "docs/部署文档/本地验证报告.md": ("执行报告", "本地验证报告.md"),
    "docs/部署文档/本地Docker全栈启动.md": ("Docker", "本地Docker全栈启动.md"),
    "docs/部署文档/部署说明.txt": ("部署指南", "部署说明.txt"),
    "docs/部署文档/部署说明文档.md": ("部署指南", "部署说明文档.md"),
    "docs/部署文档/部署完成.md": ("执行报告", "部署完成.md"),
    "docs/部署文档/部署摘要.md": ("执行报告", "部署摘要.md"),
    "docs/部署文档/生产就绪报告.md": ("执行报告", "生产就绪报告.md"),
    "docs/快速开始/快速参考卡.md": ("快速开始", "快速参考卡.md"),
    "docs/快速开始/快速登录指南.md": ("快速开始", "快速登录指南.md"),
    "docs/快速开始/快速启动参考.md": ("快速开始", "快速启动参考.md"),
    "docs/快速开始/快速启动现在.md": ("快速开始", "快速启动现在.md"),
    "docs/快速开始/快速启动指南.md": ("快速开始", "快速启动指南.md"),
    "docs/快速开始/快速修复指南.md": ("快速开始", "快速修复指南.md"),
    "docs/快速开始/快速重启指南_2026_01_20.md": ("快速开始", "快速重启指南.md"),
    "docs/快速开始/快速Docker启动.md": ("Docker", "快速Docker启动.md"),
}

def merge_docs():
    """Execute the merge operation."""
    base_path = Path(".")
    docs_path = base_path / "docs"
    target_path = base_path / "文档"
    
    # Statistics
    stats = {
        "copied": 0,
        "skipped": 0,
        "errors": 0,
        "duplicates": 0,
    }
    
    print("=" * 60)
    print("开始合并 docs/ 和 文档/ 目录")
    print("=" * 60)
    
    # Create target directories if they don't exist
    for category in set(mapping[0] for mapping in FILE_MAPPING.values()):
        category_path = target_path / category
        category_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {category}")
    
    print("\n" + "=" * 60)
    print("复制和重命名文件")
    print("=" * 60)
    
    # Copy and rename files
    for source_file, (category, new_name) in FILE_MAPPING.items():
        source_path = base_path / source_file
        target_file_path = target_path / category / new_name
        
        if not source_path.exists():
            print(f"✗ 源文件不存在: {source_file}")
            stats["errors"] += 1
            continue
        
        # Check if target file already exists
        if target_file_path.exists():
            print(f"⚠ 文件已存在 (跳过): {category}/{new_name}")
            stats["duplicates"] += 1
            continue
        
        try:
            shutil.copy2(source_path, target_file_path)
            print(f"✓ 复制: {source_file} → {category}/{new_name}")
            stats["copied"] += 1
        except Exception as e:
            print(f"✗ 错误: {source_file} - {str(e)}")
            stats["errors"] += 1
    
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    print(f"✓ 成功复制: {stats['copied']} 个文件")
    print(f"⚠ 已存在: {stats['duplicates']} 个文件")
    print(f"✗ 错误: {stats['errors']} 个文件")
    print(f"总计: {stats['copied'] + stats['duplicates'] + stats['errors']} 个文件")
    
    return stats

if __name__ == "__main__":
    merge_docs()
