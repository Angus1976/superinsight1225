#!/usr/bin/env python3
"""
i18n 功能测试脚本
验证多语言支持的基本功能
"""

import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from i18n import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations,
    get_supported_languages,
    get_manager
)

def test_basic_functions():
    """测试基础函数"""
    print("=" * 60)
    print("测试 1: 基础函数")
    print("=" * 60)
    
    # 测试获取支持的语言
    languages = get_supported_languages()
    print(f"✓ 支持的语言: {languages}")
    assert languages == ['zh', 'en'], "语言列表不正确"
    
    # 测试获取当前语言（默认中文）
    current = get_current_language()
    print(f"✓ 当前语言: {current}")
    assert current == 'zh', "默认语言应该是中文"
    
    # 测试获取翻译
    text = get_translation('app_name')
    print(f"✓ 中文翻译 (app_name): {text}")
    assert text == 'SuperInsight 平台', "中文翻译不正确"
    
    # 测试设置语言
    set_language('en')
    current = get_current_language()
    print(f"✓ 设置语言后: {current}")
    assert current == 'en', "语言设置失败"
    
    # 测试英文翻译
    text = get_translation('app_name')
    print(f"✓ 英文翻译 (app_name): {text}")
    assert text == 'SuperInsight Platform', "英文翻译不正确"
    
    # 测试指定语言的翻译
    text = get_translation('login', 'zh')
    print(f"✓ 指定语言翻译 (login, zh): {text}")
    assert text == '登录', "指定语言翻译不正确"
    
    print("✓ 所有基础函数测试通过\n")

def test_translation_manager():
    """测试翻译管理器"""
    print("=" * 60)
    print("测试 2: 翻译管理器")
    print("=" * 60)
    
    # 获取管理器实例
    manager = get_manager(default_language='zh')
    print(f"✓ 创建管理器实例")
    
    # 测试设置语言
    manager.set_language('en')
    current = manager.get_language()
    print(f"✓ 管理器当前语言: {current}")
    assert current == 'en', "管理器语言设置失败"
    
    # 测试翻译方法
    text = manager.translate('logout')
    print(f"✓ 翻译 (logout): {text}")
    assert text == 'Logout', "管理器翻译不正确"
    
    # 测试简写方法
    text = manager.t('login')
    print(f"✓ 简写翻译 (login): {text}")
    assert text == 'Login', "简写翻译不正确"
    
    # 测试获取所有翻译
    all_trans = manager.get_all('zh')
    print(f"✓ 获取所有翻译 (zh): {len(all_trans)} 个翻译键")
    assert len(all_trans) > 0, "翻译字典为空"
    assert 'app_name' in all_trans, "翻译字典缺少 app_name"
    
    # 测试获取支持的语言
    languages = manager.get_supported_languages()
    print(f"✓ 支持的语言: {languages}")
    assert languages == ['zh', 'en'], "语言列表不正确"
    
    print("✓ 所有管理器测试通过\n")

def test_translations_coverage():
    """测试翻译覆盖"""
    print("=" * 60)
    print("测试 3: 翻译覆盖")
    print("=" * 60)
    
    # 获取所有翻译键
    zh_trans = get_all_translations('zh')
    en_trans = get_all_translations('en')
    
    print(f"✓ 中文翻译键数: {len(zh_trans)}")
    print(f"✓ 英文翻译键数: {len(en_trans)}")
    
    # 检查两种语言的键是否一致
    zh_keys = set(zh_trans.keys())
    en_keys = set(en_trans.keys())
    
    missing_in_en = zh_keys - en_keys
    missing_in_zh = en_keys - zh_keys
    
    if missing_in_en:
        print(f"⚠ 英文缺少的键: {missing_in_en}")
    if missing_in_zh:
        print(f"⚠ 中文缺少的键: {missing_in_zh}")
    
    assert zh_keys == en_keys, "两种语言的翻译键不一致"
    print("✓ 两种语言的翻译键完全一致\n")

def test_sample_translations():
    """测试示例翻译"""
    print("=" * 60)
    print("测试 4: 示例翻译")
    print("=" * 60)
    
    test_keys = [
        'app_name',
        'login',
        'logout',
        'username',
        'password',
        'healthy',
        'extraction',
        'quality',
        'ai_annotation',
        'billing',
        'knowledge_graph',
        'pending',
        'in_progress',
        'completed'
    ]
    
    print("\n中文翻译:")
    set_language('zh')
    for key in test_keys:
        text = get_translation(key)
        print(f"  {key:20} -> {text}")
    
    print("\n英文翻译:")
    set_language('en')
    for key in test_keys:
        text = get_translation(key)
        print(f"  {key:20} -> {text}")
    
    print("\n✓ 示例翻译测试完成\n")

def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  SuperInsight i18n 功能测试".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        test_basic_functions()
        test_translation_manager()
        test_translations_coverage()
        test_sample_translations()
        
        print("=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)
        print()
        return 0
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
