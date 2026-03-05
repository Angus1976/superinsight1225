#!/usr/bin/env python3
"""
实时监控结构化任务进度的命令行工具。

用法:
    python scripts/watch_structuring_progress.py <job_id>
    python scripts/watch_structuring_progress.py --latest
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.models.structuring import StructuringJob


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_progress_bar(percent: float, width: int = 40):
    """Print a progress bar."""
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percent:.1f}%"


def format_time(seconds: float) -> str:
    """Format seconds to human-readable time."""
    if seconds is None:
        return "N/A"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def print_job_progress(job: StructuringJob, refresh_count: int = 0):
    """Print formatted job progress."""
    clear_screen()
    
    print("=" * 70)
    print(f"  结构化任务进度监控 (刷新次数: {refresh_count})")
    print("=" * 70)
    print(f"\n任务 ID: {job.id}")
    print(f"文件名: {job.file_name}")
    print(f"文件类型: {job.file_type}")
    print(f"状态: {job.status}")
    print(f"创建时间: {job.created_at}")
    
    if job.error_message:
        print(f"\n❌ 错误信息: {job.error_message}")
    
    # Print progress info if available
    if hasattr(job, 'progress_info') and job.progress_info:
        progress = job.progress_info
        print(f"\n{'─' * 70}")
        print(f"总体进度: {print_progress_bar(progress.get('overall_progress_percent', 0))}")
        print(f"已用时间: {format_time(progress.get('elapsed_seconds'))}")
        if progress.get('estimated_remaining_seconds'):
            print(f"预计剩余: {format_time(progress.get('estimated_remaining_seconds'))}")
        
        print(f"\n当前步骤: {progress.get('current_step', 0)}/{progress.get('total_steps', 6)}")
        print(f"{'─' * 70}")
        
        steps = progress.get('steps', [])
        for step in steps:
            status_icon = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(step.get('status', 'pending'), "❓")
            
            step_num = step.get('step_number', 0)
            step_name = step.get('step_name', 'Unknown')
            step_status = step.get('status', 'pending')
            step_percent = step.get('progress_percent', 0)
            
            print(f"\n{status_icon} 步骤 {step_num}: {step_name}")
            print(f"   {print_progress_bar(step_percent, width=30)}")
            
            if step.get('message'):
                print(f"   💬 {step.get('message')}")
            
            if step.get('elapsed_seconds'):
                print(f"   ⏱️  耗时: {format_time(step.get('elapsed_seconds'))}")
            
            details = step.get('details', {})
            if details:
                for key, value in details.items():
                    print(f"   📊 {key}: {value}")
    else:
        print(f"\n⚠️  暂无详细进度信息")
        print(f"   (可能是旧版本任务或进度追踪未启用)")
    
    print(f"\n{'=' * 70}")
    
    # Show status-specific messages
    if job.status == 'completed':
        print(f"✅ 任务已完成！共提取 {job.record_count} 条记录")
        return True
    elif job.status == 'failed':
        print(f"❌ 任务失败")
        return True
    else:
        print(f"🔄 任务进行中... (按 Ctrl+C 退出)")
        return False


def watch_job(job_id: str, interval: int = 2):
    """Watch a job's progress in real-time."""
    refresh_count = 0
    
    try:
        while True:
            with db_manager.get_session() as session:
                job = session.query(StructuringJob).filter_by(id=job_id).first()
                
                if not job:
                    print(f"❌ 任务 {job_id} 不存在")
                    return
                
                is_finished = print_job_progress(job, refresh_count)
                
                if is_finished:
                    break
            
            refresh_count += 1
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n\n⏸️  监控已停止")


def get_latest_job():
    """Get the most recent structuring job."""
    with db_manager.get_session() as session:
        job = (
            session.query(StructuringJob)
            .order_by(StructuringJob.created_at.desc())
            .first()
        )
        return job


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="实时监控结构化任务进度",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 监控指定任务
  python scripts/watch_structuring_progress.py abc123-def456-...
  
  # 监控最新任务
  python scripts/watch_structuring_progress.py --latest
  
  # 自定义刷新间隔（秒）
  python scripts/watch_structuring_progress.py abc123 --interval 5
        """
    )
    
    parser.add_argument(
        'job_id',
        nargs='?',
        help='任务 ID (UUID)'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='监控最新的任务'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='刷新间隔（秒），默认 2 秒'
    )
    
    args = parser.parse_args()
    
    if args.latest:
        job = get_latest_job()
        if not job:
            print("❌ 没有找到任何任务")
            return
        print(f"📌 监控最新任务: {job.id}")
        time.sleep(1)
        watch_job(str(job.id), args.interval)
    elif args.job_id:
        watch_job(args.job_id, args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
