"""
Progress tracking for structuring pipeline.

Provides detailed progress information for long-running LLM tasks.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class StepProgress:
    """Progress information for a single pipeline step."""
    
    step_name: str
    step_number: int
    total_steps: int
    status: str  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    progress_percent: float = 0.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "step_name": self.step_name,
            "step_number": self.step_number,
            "total_steps": self.total_steps,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_seconds": self.elapsed_seconds,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "details": self.details,
        }
    
    @property
    def elapsed_seconds(self) -> Optional[float]:
        """Calculate elapsed time in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)


@dataclass
class PipelineProgress:
    """Overall pipeline progress tracking."""
    
    job_id: str
    current_step: int = 0
    total_steps: int = 6
    overall_status: str = "pending"
    start_time: Optional[float] = None
    steps: list[StepProgress] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize step progress objects."""
        if not self.steps:
            step_names = [
                "文件内容提取",
                "Schema 推断",
                "Schema 确认",
                "实体提取",
                "记录存储",
                "创建标注任务",
            ]
            self.steps = [
                StepProgress(
                    step_name=name,
                    step_number=i + 1,
                    total_steps=self.total_steps,
                    status="pending",
                )
                for i, name in enumerate(step_names)
            ]
    
    def start_step(self, step_number: int, message: str = "") -> None:
        """Mark a step as started."""
        if 1 <= step_number <= self.total_steps:
            step = self.steps[step_number - 1]
            step.status = "running"
            step.start_time = time.time()
            step.message = message
            self.current_step = step_number
            logger.info(f"[Job {self.job_id}] 步骤 {step_number}/{self.total_steps} 开始: {step.step_name}")
    
    def update_step(
        self,
        step_number: int,
        progress_percent: float = 0.0,
        message: str = "",
        details: Optional[dict] = None,
    ) -> None:
        """Update step progress."""
        if 1 <= step_number <= self.total_steps:
            step = self.steps[step_number - 1]
            step.progress_percent = min(100.0, max(0.0, progress_percent))
            if message:
                step.message = message
            if details:
                step.details.update(details)
            logger.info(
                f"[Job {self.job_id}] 步骤 {step_number}/{self.total_steps} "
                f"进度: {step.progress_percent:.1f}% - {message}"
            )
    
    def complete_step(self, step_number: int, message: str = "") -> None:
        """Mark a step as completed."""
        if 1 <= step_number <= self.total_steps:
            step = self.steps[step_number - 1]
            step.status = "completed"
            step.end_time = time.time()
            step.progress_percent = 100.0
            if message:
                step.message = message
            logger.info(
                f"[Job {self.job_id}] 步骤 {step_number}/{self.total_steps} 完成: "
                f"{step.step_name} (耗时: {step.elapsed_seconds}s)"
            )
    
    def fail_step(self, step_number: int, error: str) -> None:
        """Mark a step as failed."""
        if 1 <= step_number <= self.total_steps:
            step = self.steps[step_number - 1]
            step.status = "failed"
            step.end_time = time.time()
            step.message = f"错误: {error}"
            self.overall_status = "failed"
            logger.error(
                f"[Job {self.job_id}] 步骤 {step_number}/{self.total_steps} 失败: {error}"
            )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "overall_status": self.overall_status,
            "overall_progress_percent": self.overall_progress_percent,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "start_time": self.start_time,
            "steps": [step.to_dict() for step in self.steps],
        }
    
    @property
    def overall_progress_percent(self) -> float:
        """Calculate overall progress percentage."""
        if not self.steps:
            return 0.0
        total = sum(step.progress_percent for step in self.steps)
        return round(total / self.total_steps, 2)
    
    @property
    def elapsed_seconds(self) -> Optional[float]:
        """Calculate total elapsed time."""
        if self.start_time is None:
            return None
        return round(time.time() - self.start_time, 2)
    
    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time based on completed steps."""
        if self.start_time is None or self.current_step == 0:
            return None
        
        elapsed = self.elapsed_seconds
        if elapsed is None:
            return None
        
        completed_steps = sum(1 for s in self.steps if s.status == "completed")
        if completed_steps == 0:
            return None
        
        avg_time_per_step = elapsed / completed_steps
        remaining_steps = self.total_steps - completed_steps
        return round(avg_time_per_step * remaining_steps, 2)


class ProgressTracker:
    """Manages progress tracking for structuring jobs."""
    
    def __init__(self, job_id: str):
        """Initialize progress tracker for a job."""
        self.job_id = str(job_id)
        self.progress = PipelineProgress(job_id=self.job_id)
        self.progress.start_time = time.time()
        self.progress.overall_status = "running"
    
    def start_step(self, step_number: int, message: str = "") -> None:
        """Start a pipeline step."""
        self.progress.start_step(step_number, message)
    
    def update_step(
        self,
        step_number: int,
        progress_percent: float = 0.0,
        message: str = "",
        **details,
    ) -> None:
        """Update step progress."""
        self.progress.update_step(step_number, progress_percent, message, details)
    
    def complete_step(self, step_number: int, message: str = "") -> None:
        """Complete a pipeline step."""
        self.progress.complete_step(step_number, message)
    
    def fail_step(self, step_number: int, error: str) -> None:
        """Mark step as failed."""
        self.progress.fail_step(step_number, error)
    
    def complete_pipeline(self) -> None:
        """Mark entire pipeline as completed."""
        self.progress.overall_status = "completed"
        logger.info(
            f"[Job {self.job_id}] 管道完成 "
            f"(总耗时: {self.progress.elapsed_seconds}s)"
        )
    
    def fail_pipeline(self, error: str) -> None:
        """Mark entire pipeline as failed."""
        self.progress.overall_status = "failed"
        logger.error(f"[Job {self.job_id}] 管道失败: {error}")
    
    def get_progress_dict(self) -> dict:
        """Get progress as dictionary."""
        return self.progress.to_dict()
    
    def save_to_job(self, session, job) -> None:
        """Save progress to job's progress_info field."""
        if not hasattr(job, 'progress_info'):
            logger.warning(f"Job {self.job_id} does not have progress_info field")
            return
        
        job.progress_info = self.get_progress_dict()
        session.flush()
    
    def print_progress(self) -> None:
        """Print formatted progress to console."""
        progress = self.progress
        print(f"\n{'='*60}")
        print(f"任务进度: {self.job_id}")
        print(f"{'='*60}")
        print(f"总体状态: {progress.overall_status}")
        print(f"总体进度: {progress.overall_progress_percent:.1f}%")
        print(f"已用时间: {progress.elapsed_seconds}s")
        if progress.estimated_remaining_seconds:
            print(f"预计剩余: {progress.estimated_remaining_seconds}s")
        print(f"\n当前步骤: {progress.current_step}/{progress.total_steps}")
        print(f"{'-'*60}")
        
        for step in progress.steps:
            status_icon = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(step.status, "❓")
            
            print(f"{status_icon} 步骤 {step.step_number}: {step.step_name}")
            print(f"   状态: {step.status} | 进度: {step.progress_percent:.1f}%")
            if step.message:
                print(f"   信息: {step.message}")
            if step.elapsed_seconds:
                print(f"   耗时: {step.elapsed_seconds}s")
            if step.details:
                for key, value in step.details.items():
                    print(f"   {key}: {value}")
            print()
        
        print(f"{'='*60}\n")
