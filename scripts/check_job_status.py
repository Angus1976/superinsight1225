#!/usr/bin/env python3
"""
检查结构化任务的状态和日志

用法:
    python scripts/check_job_status.py [job_id]
    
如果不提供 job_id，将显示最近的 5 个任务
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import db_manager
from src.models.structuring import StructuringJob


def check_job_status(job_id: str = None):
    """检查任务状态"""
    with db_manager.get_session() as session:
        if job_id:
            # 查询特定任务
            job = session.query(StructuringJob).filter_by(id=job_id).first()
            if not job:
                print(f"❌ 未找到任务: {job_id}")
                return
            
            print(f"\n{'='*60}")
            print(f"任务 ID: {job.id}")
            print(f"文件名: {job.file_name}")
            print(f"文件类型: {job.file_type}")
            print(f"状态: {job.status}")
            print(f"创建时间: {job.created_at}")
            print(f"更新时间: {job.updated_at}")
            
            if job.error_message:
                print(f"\n❌ 错误信息:")
                print(f"   {job.error_message}")
            
            if job.raw_content:
                content_preview = job.raw_content[:200] + "..." if len(job.raw_content) > 200 else job.raw_content
                print(f"\n📄 内容预览:")
                print(f"   {content_preview}")
            
            if job.inferred_schema:
                print(f"\n📋 推断的 Schema:")
                fields = job.inferred_schema.get('fields', [])
                print(f"   字段数: {len(fields)}")
                for field in fields[:5]:  # 只显示前 5 个字段
                    print(f"   - {field.get('name')}: {field.get('field_type')} ({field.get('description')})")
                if len(fields) > 5:
                    print(f"   ... 还有 {len(fields) - 5} 个字段")
            
            if job.record_count:
                print(f"\n✅ 提取的记录数: {job.record_count}")
            
            print(f"{'='*60}\n")
        else:
            # 显示最近的 5 个任务
            jobs = session.query(StructuringJob).order_by(
                StructuringJob.created_at.desc()
            ).limit(5).all()
            
            if not jobs:
                print("❌ 没有找到任何任务")
                return
            
            print(f"\n最近的 {len(jobs)} 个任务:")
            print(f"{'='*80}")
            print(f"{'ID':<40} {'文件名':<20} {'状态':<15} {'创建时间'}")
            print(f"{'-'*80}")
            
            for job in jobs:
                print(f"{job.id:<40} {job.file_name:<20} {job.status:<15} {job.created_at}")
            
            print(f"{'='*80}\n")
            print("💡 使用 'python scripts/check_job_status.py <job_id>' 查看详细信息")


if __name__ == "__main__":
    job_id = sys.argv[1] if len(sys.argv) > 1 else None
    check_job_status(job_id)
