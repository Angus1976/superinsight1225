#!/usr/bin/env python3
"""
测试进度追踪功能的脚本。

用法:
    python scripts/test_progress_tracking.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.progress_tracker import ProgressTracker


def test_progress_tracker():
    """测试进度追踪器的基本功能。"""
    print("=" * 70)
    print("测试进度追踪器")
    print("=" * 70)
    
    # 创建进度追踪器
    tracker = ProgressTracker("test-job-123")
    
    # 模拟步骤 1: 文件提取
    print("\n步骤 1: 文件内容提取")
    tracker.start_step(1, "正在提取 PDF 文件...")
    tracker.update_step(1, 30, "正在解析 PDF 结构...")
    tracker.update_step(1, 60, "正在提取文本内容...")
    tracker.update_step(1, 90, "正在清理格式...")
    tracker.complete_step(1, "提取完成: 1234 字符, 1 个文档")
    
    # 模拟步骤 2: Schema 推断
    print("\n步骤 2: Schema 推断")
    tracker.start_step(2, "正在加载 LLM 配置...")
    tracker.update_step(2, 30, "正在调用 LLM (gpt-3.5-turbo)...")
    tracker.update_step(2, 70, "正在解析 LLM 响应...")
    tracker.complete_step(2, "推断完成: 5 个字段")
    
    # 模拟步骤 3: Schema 确认
    print("\n步骤 3: Schema 确认")
    tracker.start_step(3, "正在确认 Schema...")
    tracker.complete_step(3, "Schema 已确认")
    
    # 模拟步骤 4: 实体提取
    print("\n步骤 4: 实体提取")
    tracker.start_step(4, "正在加载 LLM 配置...")
    tracker.update_step(4, 50, "正在提取实体 (内容: 1234 字符)...")
    tracker.complete_step(4, "提取完成: 10 条记录")
    
    # 模拟步骤 5: 记录存储
    print("\n步骤 5: 记录存储")
    tracker.start_step(5, "正在存储 10 条记录...")
    tracker.complete_step(5, "已存储 10 条记录")
    
    # 模拟步骤 6: 创建标注任务
    print("\n步骤 6: 创建标注任务")
    tracker.start_step(6, "正在创建标注任务...")
    tracker.complete_step(6, "标注任务已创建")
    
    # 完成管道
    tracker.complete_pipeline()
    
    # 打印最终进度
    print("\n" + "=" * 70)
    print("最终进度")
    print("=" * 70)
    tracker.print_progress()
    
    # 打印 JSON 格式
    print("\n" + "=" * 70)
    print("JSON 格式进度")
    print("=" * 70)
    import json
    print(json.dumps(tracker.get_progress_dict(), indent=2, ensure_ascii=False))


def test_failed_step():
    """测试步骤失败的情况。"""
    print("\n\n" + "=" * 70)
    print("测试步骤失败")
    print("=" * 70)
    
    tracker = ProgressTracker("test-job-456")
    
    # 步骤 1 成功
    tracker.start_step(1, "正在提取文件...")
    tracker.complete_step(1, "提取完成")
    
    # 步骤 2 失败
    tracker.start_step(2, "正在推断 Schema...")
    tracker.update_step(2, 50, "正在调用 LLM...")
    tracker.fail_step(2, "LLM API 超时: 连接超时 60 秒")
    
    # 标记管道失败
    tracker.fail_pipeline("Schema 推断失败")
    
    # 打印进度
    tracker.print_progress()


def main():
    """主函数。"""
    print("🧪 开始测试进度追踪功能\n")
    
    # 测试正常流程
    test_progress_tracker()
    
    # 测试失败流程
    test_failed_step()
    
    print("\n✅ 测试完成！")
    print("\n提示:")
    print("  - 查看上面的输出，确认进度信息正确")
    print("  - 使用 watch_structuring_progress.py 监控真实任务")
    print("  - 查看 API 响应中的 progress_info 字段")


if __name__ == "__main__":
    main()
