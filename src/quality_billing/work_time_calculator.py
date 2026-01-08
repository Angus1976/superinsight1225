"""
精确工时统计算法模块

实现多维度工时计算、自动记录验证、异常检测和统计报表功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class WorkTimeType(str, Enum):
    """工时类型枚举"""
    EFFECTIVE = "effective"  # 有效工时
    PAUSE = "pause"  # 暂停时间
    OVERTIME = "overtime"  # 加班时间
    BREAK = "break"  # 休息时间
    MEETING = "meeting"  # 会议时间
    TRAINING = "training"  # 培训时间


class WorkTimeStatus(str, Enum):
    """工时状态枚举"""
    ACTIVE = "active"  # 活跃工作
    PAUSED = "paused"  # 暂停
    COMPLETED = "completed"  # 完成
    CANCELLED = "cancelled"  # 取消


class AnomalyType(str, Enum):
    """异常类型枚举"""
    EXCESSIVE_HOURS = "excessive_hours"  # 工时过长
    INSUFFICIENT_HOURS = "insufficient_hours"  # 工时不足
    IRREGULAR_PATTERN = "irregular_pattern"  # 不规律模式
    SUSPICIOUS_ACTIVITY = "suspicious_activity"  # 可疑活动
    MISSING_RECORDS = "missing_records"  # 记录缺失


@dataclass
class WorkTimeRecord:
    """工时记录数据类"""
    id: str
    user_id: str
    task_id: str
    project_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    work_type: WorkTimeType = WorkTimeType.EFFECTIVE
    status: WorkTimeStatus = WorkTimeStatus.ACTIVE
    duration_minutes: int = 0
    pause_duration_minutes: int = 0
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkTimeAnomaly:
    """工时异常数据类"""
    id: str
    record_id: str
    user_id: str
    anomaly_type: AnomalyType
    severity: str  # low, medium, high, critical
    description: str
    detected_at: datetime
    resolved: bool = False
    resolution_notes: str = ""
    auto_corrected: bool = False


@dataclass
class WorkTimeStatistics:
    """工时统计数据类"""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_effective_hours: float
    total_pause_hours: float
    total_overtime_hours: float
    average_daily_hours: float
    productivity_score: float
    efficiency_rating: str
    anomaly_count: int
    tasks_completed: int
    quality_score: float


class WorkTimeCalculator:
    """精确工时统计算法核心类"""
    
    def __init__(self):
        self.records: Dict[str, WorkTimeRecord] = {}
        self.anomalies: Dict[str, WorkTimeAnomaly] = {}
        self.active_sessions: Dict[str, WorkTimeRecord] = {}
        
        # 配置参数
        self.max_daily_hours = 12  # 最大日工时
        self.min_daily_hours = 4   # 最小日工时
        self.max_continuous_hours = 4  # 最大连续工时
        self.anomaly_thresholds = {
            'excessive_daily_hours': 10,
            'insufficient_daily_hours': 2,
            'long_pause_minutes': 120,
            'suspicious_activity_threshold': 0.3
        }
    
    def start_work_session(self, user_id: str, task_id: str, project_id: str, 
                          work_type: WorkTimeType = WorkTimeType.EFFECTIVE,
                          description: str = "") -> str:
        """开始工作会话"""
        session_id = f"{user_id}_{task_id}_{datetime.now().timestamp()}"
        
        # 检查是否有未结束的会话
        existing_session = self.get_active_session(user_id)
        if existing_session:
            logger.warning(f"User {user_id} has active session, ending previous session")
            # 结束之前的会话而不是暂停
            try:
                self.end_work_session(existing_session.id, "Auto-ended for new session")
            except Exception as e:
                logger.error(f"Failed to end previous session: {str(e)}")
                # 强制清理活跃会话
                if user_id in self.active_sessions:
                    del self.active_sessions[user_id]
        
        record = WorkTimeRecord(
            id=session_id,
            user_id=user_id,
            task_id=task_id,
            project_id=project_id,
            start_time=datetime.now(),
            work_type=work_type,
            description=description,
            metadata={
                'ip_address': self._get_client_ip(),
                'user_agent': self._get_user_agent(),
                'session_start_method': 'manual'
            }
        )
        
        self.records[session_id] = record
        self.active_sessions[user_id] = record
        
        logger.info(f"Started work session {session_id} for user {user_id}")
        return session_id
    
    def end_work_session(self, session_id: str, description: str = "") -> WorkTimeRecord:
        """结束工作会话"""
        if session_id not in self.records:
            raise ValueError(f"Work session {session_id} not found")
        
        record = self.records[session_id]
        if record.status != WorkTimeStatus.ACTIVE:
            raise ValueError(f"Work session {session_id} is not active")
        
        record.end_time = datetime.now()
        record.status = WorkTimeStatus.COMPLETED
        record.duration_minutes = self._calculate_duration_minutes(record.start_time, record.end_time)
        record.updated_at = datetime.now()
        
        if description:
            record.description += f" | End: {description}"
        
        # 从活跃会话中移除
        if record.user_id in self.active_sessions:
            del self.active_sessions[record.user_id]
        
        # 检测异常
        self._detect_session_anomalies(record)
        
        logger.info(f"Ended work session {session_id}, duration: {record.duration_minutes} minutes")
        return record
    
    def pause_work_session(self, session_id: str, reason: str = "") -> WorkTimeRecord:
        """暂停工作会话"""
        if session_id not in self.records:
            raise ValueError(f"Work session {session_id} not found")
        
        record = self.records[session_id]
        if record.status != WorkTimeStatus.ACTIVE:
            raise ValueError(f"Work session {session_id} is not active")
        
        # 记录暂停时间
        pause_start = datetime.now()
        record.metadata.setdefault('pause_periods', []).append({
            'start': pause_start.isoformat(),
            'reason': reason
        })
        
        record.status = WorkTimeStatus.PAUSED
        record.updated_at = datetime.now()
        
        logger.info(f"Paused work session {session_id}, reason: {reason}")
        return record
    
    def resume_work_session(self, session_id: str) -> WorkTimeRecord:
        """恢复工作会话"""
        if session_id not in self.records:
            raise ValueError(f"Work session {session_id} not found")
        
        record = self.records[session_id]
        if record.status != WorkTimeStatus.PAUSED:
            raise ValueError(f"Work session {session_id} is not paused")
        
        # 计算暂停时长
        pause_periods = record.metadata.get('pause_periods', [])
        if pause_periods:
            last_pause = pause_periods[-1]
            if 'end' not in last_pause:
                pause_end = datetime.now()
                last_pause['end'] = pause_end.isoformat()
                
                pause_start = datetime.fromisoformat(last_pause['start'])
                pause_duration = self._calculate_duration_minutes(pause_start, pause_end)
                record.pause_duration_minutes += pause_duration
        
        record.status = WorkTimeStatus.ACTIVE
        record.updated_at = datetime.now()
        
        logger.info(f"Resumed work session {session_id}")
        return record
    
    def calculate_multi_dimensional_hours(self, user_id: str, start_date: datetime, 
                                        end_date: datetime) -> Dict[str, float]:
        """计算多维度工时"""
        user_records = [r for r in self.records.values() 
                       if r.user_id == user_id and 
                       start_date <= r.start_time <= end_date and
                       r.status == WorkTimeStatus.COMPLETED]
        
        dimensions = {
            'effective_hours': 0.0,
            'pause_hours': 0.0,
            'overtime_hours': 0.0,
            'break_hours': 0.0,
            'meeting_hours': 0.0,
            'training_hours': 0.0,
            'total_hours': 0.0
        }
        
        for record in user_records:
            duration_hours = record.duration_minutes / 60.0
            pause_hours = record.pause_duration_minutes / 60.0
            
            # 按工时类型分类
            if record.work_type == WorkTimeType.EFFECTIVE:
                dimensions['effective_hours'] += duration_hours
            elif record.work_type == WorkTimeType.OVERTIME:
                dimensions['overtime_hours'] += duration_hours
            elif record.work_type == WorkTimeType.BREAK:
                dimensions['break_hours'] += duration_hours
            elif record.work_type == WorkTimeType.MEETING:
                dimensions['meeting_hours'] += duration_hours
            elif record.work_type == WorkTimeType.TRAINING:
                dimensions['training_hours'] += duration_hours
            
            dimensions['pause_hours'] += pause_hours
            dimensions['total_hours'] += duration_hours
        
        return dimensions
    
    def detect_work_time_anomalies(self, user_id: str, date: datetime) -> List[WorkTimeAnomaly]:
        """检测工时异常"""
        anomalies = []
        
        # 获取当日工时记录
        daily_records = self._get_daily_records(user_id, date)
        if not daily_records:
            return anomalies
        
        # 计算当日总工时
        total_hours = sum(r.duration_minutes for r in daily_records) / 60.0
        
        # 检测工时过长
        if total_hours > self.anomaly_thresholds['excessive_daily_hours']:
            anomaly = WorkTimeAnomaly(
                id=f"excessive_{user_id}_{date.strftime('%Y%m%d')}",
                record_id=daily_records[0].id,
                user_id=user_id,
                anomaly_type=AnomalyType.EXCESSIVE_HOURS,
                severity="high",
                description=f"Daily work hours ({total_hours:.1f}h) exceed threshold ({self.anomaly_thresholds['excessive_daily_hours']}h)",
                detected_at=datetime.now()
            )
            anomalies.append(anomaly)
        
        # 检测工时不足
        if total_hours < self.anomaly_thresholds['insufficient_daily_hours']:
            anomaly = WorkTimeAnomaly(
                id=f"insufficient_{user_id}_{date.strftime('%Y%m%d')}",
                record_id=daily_records[0].id,
                user_id=user_id,
                anomaly_type=AnomalyType.INSUFFICIENT_HOURS,
                severity="medium",
                description=f"Daily work hours ({total_hours:.1f}h) below threshold ({self.anomaly_thresholds['insufficient_daily_hours']}h)",
                detected_at=datetime.now()
            )
            anomalies.append(anomaly)
        
        # 检测不规律模式
        pattern_anomaly = self._detect_irregular_pattern(user_id, daily_records)
        if pattern_anomaly:
            anomalies.append(pattern_anomaly)
        
        # 检测可疑活动
        suspicious_anomaly = self._detect_suspicious_activity(user_id, daily_records)
        if suspicious_anomaly:
            anomalies.append(suspicious_anomaly)
        
        # 保存异常记录
        for anomaly in anomalies:
            self.anomalies[anomaly.id] = anomaly
        
        return anomalies
    
    def auto_correct_anomalies(self, anomaly_ids: List[str]) -> Dict[str, bool]:
        """自动纠正异常"""
        correction_results = {}
        
        for anomaly_id in anomaly_ids:
            if anomaly_id not in self.anomalies:
                correction_results[anomaly_id] = False
                continue
            
            anomaly = self.anomalies[anomaly_id]
            corrected = False
            
            try:
                if anomaly.anomaly_type == AnomalyType.EXCESSIVE_HOURS:
                    corrected = self._correct_excessive_hours(anomaly)
                elif anomaly.anomaly_type == AnomalyType.MISSING_RECORDS:
                    corrected = self._correct_missing_records(anomaly)
                elif anomaly.anomaly_type == AnomalyType.IRREGULAR_PATTERN:
                    corrected = self._correct_irregular_pattern(anomaly)
                
                if corrected:
                    anomaly.resolved = True
                    anomaly.auto_corrected = True
                    anomaly.resolution_notes = "Auto-corrected by system"
                
                correction_results[anomaly_id] = corrected
                
            except Exception as e:
                logger.error(f"Failed to auto-correct anomaly {anomaly_id}: {str(e)}")
                correction_results[anomaly_id] = False
        
        return correction_results
    
    def generate_work_time_statistics(self, user_id: str, start_date: datetime, 
                                    end_date: datetime) -> WorkTimeStatistics:
        """生成工时统计报表"""
        # 获取时间段内的工时数据
        dimensions = self.calculate_multi_dimensional_hours(user_id, start_date, end_date)
        
        # 计算工作日数
        work_days = self._calculate_work_days(start_date, end_date)
        
        # 计算平均日工时
        avg_daily_hours = dimensions['effective_hours'] / work_days if work_days > 0 else 0
        
        # 计算生产力评分
        productivity_score = self._calculate_productivity_score(user_id, start_date, end_date)
        
        # 计算效率等级
        efficiency_rating = self._calculate_efficiency_rating(productivity_score)
        
        # 统计异常数量
        user_anomalies = [a for a in self.anomalies.values() 
                         if a.user_id == user_id and 
                         start_date <= a.detected_at <= end_date]
        
        # 获取任务完成数和质量分数
        tasks_completed = self._count_completed_tasks(user_id, start_date, end_date)
        quality_score = self._get_average_quality_score(user_id, start_date, end_date)
        
        return WorkTimeStatistics(
            user_id=user_id,
            period_start=start_date,
            period_end=end_date,
            total_effective_hours=dimensions['effective_hours'],
            total_pause_hours=dimensions['pause_hours'],
            total_overtime_hours=dimensions['overtime_hours'],
            average_daily_hours=avg_daily_hours,
            productivity_score=productivity_score,
            efficiency_rating=efficiency_rating,
            anomaly_count=len(user_anomalies),
            tasks_completed=tasks_completed,
            quality_score=quality_score
        )
    
    def get_work_time_report(self, user_id: str, start_date: datetime, 
                           end_date: datetime) -> Dict[str, Any]:
        """获取详细工时报表"""
        statistics = self.generate_work_time_statistics(user_id, start_date, end_date)
        dimensions = self.calculate_multi_dimensional_hours(user_id, start_date, end_date)
        
        # 获取异常列表
        user_anomalies = [a for a in self.anomalies.values() 
                         if a.user_id == user_id and 
                         start_date <= a.detected_at <= end_date]
        
        # 获取工时记录
        user_records = [r for r in self.records.values() 
                       if r.user_id == user_id and 
                       start_date <= r.start_time <= end_date]
        
        return {
            'user_id': user_id,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'statistics': {
                'total_effective_hours': statistics.total_effective_hours,
                'total_pause_hours': statistics.total_pause_hours,
                'total_overtime_hours': statistics.total_overtime_hours,
                'average_daily_hours': statistics.average_daily_hours,
                'productivity_score': statistics.productivity_score,
                'efficiency_rating': statistics.efficiency_rating,
                'tasks_completed': statistics.tasks_completed,
                'quality_score': statistics.quality_score
            },
            'dimensions': dimensions,
            'anomalies': [
                {
                    'type': a.anomaly_type.value,
                    'severity': a.severity,
                    'description': a.description,
                    'detected_at': a.detected_at.isoformat(),
                    'resolved': a.resolved
                }
                for a in user_anomalies
            ],
            'daily_breakdown': self._get_daily_breakdown(user_records),
            'recommendations': self._generate_recommendations(statistics, user_anomalies)
        }
    
    # 私有辅助方法
    
    def _calculate_duration_minutes(self, start_time: datetime, end_time: datetime) -> int:
        """计算时长（分钟）"""
        return int((end_time - start_time).total_seconds() / 60)
    
    def _get_client_ip(self) -> str:
        """获取客户端IP（模拟）"""
        return "192.168.1.100"
    
    def _get_user_agent(self) -> str:
        """获取用户代理（模拟）"""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def get_active_session(self, user_id: str) -> Optional[WorkTimeRecord]:
        """获取用户的活跃会话"""
        return self.active_sessions.get(user_id)
    
    def _detect_session_anomalies(self, record: WorkTimeRecord):
        """检测单个会话的异常"""
        # 检测过长的工作会话
        if record.duration_minutes > self.max_continuous_hours * 60:
            anomaly = WorkTimeAnomaly(
                id=f"long_session_{record.id}",
                record_id=record.id,
                user_id=record.user_id,
                anomaly_type=AnomalyType.EXCESSIVE_HOURS,
                severity="medium",
                description=f"Work session duration ({record.duration_minutes/60:.1f}h) exceeds maximum continuous hours ({self.max_continuous_hours}h)",
                detected_at=datetime.now()
            )
            self.anomalies[anomaly.id] = anomaly
    
    def _get_daily_records(self, user_id: str, date: datetime) -> List[WorkTimeRecord]:
        """获取指定日期的工时记录"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        return [r for r in self.records.values() 
                if r.user_id == user_id and 
                start_of_day <= r.start_time < end_of_day and
                r.status == WorkTimeStatus.COMPLETED]
    
    def _detect_irregular_pattern(self, user_id: str, daily_records: List[WorkTimeRecord]) -> Optional[WorkTimeAnomaly]:
        """检测不规律工作模式"""
        if len(daily_records) < 3:
            return None
        
        # 分析工作时间间隔
        intervals = []
        for i in range(1, len(daily_records)):
            interval = (daily_records[i].start_time - daily_records[i-1].end_time).total_seconds() / 60
            intervals.append(interval)
        
        # 如果间隔变化很大，认为是不规律模式
        if len(intervals) > 1:
            interval_std = statistics.stdev(intervals)
            if interval_std > 120:  # 标准差超过2小时
                return WorkTimeAnomaly(
                    id=f"irregular_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    record_id=daily_records[0].id,
                    user_id=user_id,
                    anomaly_type=AnomalyType.IRREGULAR_PATTERN,
                    severity="low",
                    description=f"Irregular work pattern detected, interval std: {interval_std:.1f} minutes",
                    detected_at=datetime.now()
                )
        
        return None
    
    def _detect_suspicious_activity(self, user_id: str, daily_records: List[WorkTimeRecord]) -> Optional[WorkTimeAnomaly]:
        """检测可疑活动"""
        # 检测是否有异常的暂停时间模式
        total_pause_time = sum(r.pause_duration_minutes for r in daily_records)
        total_work_time = sum(r.duration_minutes for r in daily_records)
        
        if total_work_time > 0:
            pause_ratio = total_pause_time / total_work_time
            if pause_ratio > self.anomaly_thresholds['suspicious_activity_threshold']:
                return WorkTimeAnomaly(
                    id=f"suspicious_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    record_id=daily_records[0].id,
                    user_id=user_id,
                    anomaly_type=AnomalyType.SUSPICIOUS_ACTIVITY,
                    severity="medium",
                    description=f"High pause-to-work ratio detected: {pause_ratio:.2f}",
                    detected_at=datetime.now()
                )
        
        return None
    
    def _correct_excessive_hours(self, anomaly: WorkTimeAnomaly) -> bool:
        """纠正过长工时"""
        # 简单的纠正策略：将超出部分标记为加班时间
        record = self.records.get(anomaly.record_id)
        if not record:
            return False
        
        if record.duration_minutes > self.max_daily_hours * 60:
            # 将超出的时间转为加班时间
            excess_minutes = record.duration_minutes - (self.max_daily_hours * 60)
            record.duration_minutes = self.max_daily_hours * 60
            
            # 创建加班记录
            overtime_record = WorkTimeRecord(
                id=f"{record.id}_overtime",
                user_id=record.user_id,
                task_id=record.task_id,
                project_id=record.project_id,
                start_time=record.end_time - timedelta(minutes=excess_minutes),
                end_time=record.end_time,
                work_type=WorkTimeType.OVERTIME,
                status=WorkTimeStatus.COMPLETED,
                duration_minutes=excess_minutes,
                description="Auto-generated overtime record"
            )
            
            self.records[overtime_record.id] = overtime_record
            return True
        
        return False
    
    def _correct_missing_records(self, anomaly: WorkTimeAnomaly) -> bool:
        """纠正缺失记录"""
        # 这里可以实现自动填补缺失记录的逻辑
        # 暂时返回False，表示需要人工处理
        return False
    
    def _correct_irregular_pattern(self, anomaly: WorkTimeAnomaly) -> bool:
        """纠正不规律模式"""
        # 这里可以实现模式规范化的逻辑
        # 暂时返回False，表示需要人工处理
        return False
    
    def _calculate_work_days(self, start_date: datetime, end_date: datetime) -> int:
        """计算工作日数"""
        current_date = start_date.date()
        end_date = end_date.date()
        work_days = 0
        
        while current_date <= end_date:
            # 排除周末（周六=5，周日=6）
            if current_date.weekday() < 5:
                work_days += 1
            current_date += timedelta(days=1)
        
        return work_days
    
    def _calculate_productivity_score(self, user_id: str, start_date: datetime, end_date: datetime) -> float:
        """计算生产力评分"""
        # 基于工时、任务完成数和质量的综合评分
        dimensions = self.calculate_multi_dimensional_hours(user_id, start_date, end_date)
        tasks_completed = self._count_completed_tasks(user_id, start_date, end_date)
        quality_score = self._get_average_quality_score(user_id, start_date, end_date)
        
        # 简单的评分算法
        if dimensions['effective_hours'] == 0:
            return 0.0
        
        efficiency = tasks_completed / dimensions['effective_hours'] if dimensions['effective_hours'] > 0 else 0
        productivity = (efficiency * 0.4 + quality_score * 0.6) * 100
        
        return min(100.0, max(0.0, productivity))
    
    def _calculate_efficiency_rating(self, productivity_score: float) -> str:
        """计算效率等级"""
        if productivity_score >= 90:
            return "Excellent"
        elif productivity_score >= 80:
            return "Good"
        elif productivity_score >= 70:
            return "Average"
        elif productivity_score >= 60:
            return "Below Average"
        else:
            return "Poor"
    
    def _count_completed_tasks(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        """统计完成的任务数"""
        # 根据工时记录统计不同任务ID的数量
        user_records = [r for r in self.records.values() 
                       if r.user_id == user_id and 
                       start_date <= r.start_time <= end_date and
                       r.status == WorkTimeStatus.COMPLETED]
        
        unique_tasks = set(r.task_id for r in user_records)
        return len(unique_tasks)
    
    def _get_average_quality_score(self, user_id: str, start_date: datetime, end_date: datetime) -> float:
        """获取平均质量分数"""
        # 这里应该从质量评估系统获取数据
        # 暂时返回模拟数据
        return 85.0
    
    def _get_daily_breakdown(self, records: List[WorkTimeRecord]) -> List[Dict[str, Any]]:
        """获取每日工时分解"""
        daily_data = defaultdict(lambda: {
            'date': '',
            'effective_hours': 0.0,
            'pause_hours': 0.0,
            'overtime_hours': 0.0,
            'sessions': 0
        })
        
        for record in records:
            date_key = record.start_time.date().isoformat()
            daily_data[date_key]['date'] = date_key
            daily_data[date_key]['sessions'] += 1
            
            duration_hours = record.duration_minutes / 60.0
            pause_hours = record.pause_duration_minutes / 60.0
            
            if record.work_type == WorkTimeType.EFFECTIVE:
                daily_data[date_key]['effective_hours'] += duration_hours
            elif record.work_type == WorkTimeType.OVERTIME:
                daily_data[date_key]['overtime_hours'] += duration_hours
            
            daily_data[date_key]['pause_hours'] += pause_hours
        
        return list(daily_data.values())
    
    def _generate_recommendations(self, statistics: WorkTimeStatistics, 
                                anomalies: List[WorkTimeAnomaly]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于工时统计的建议
        if statistics.average_daily_hours > 9:
            recommendations.append("建议合理安排工作时间，避免过度加班影响工作效率")
        elif statistics.average_daily_hours < 6:
            recommendations.append("建议提高工作时间投入，确保任务按时完成")
        
        # 基于生产力评分的建议
        if statistics.productivity_score < 70:
            recommendations.append("建议分析工作流程，寻找提高效率的方法")
        
        # 基于异常的建议
        if statistics.anomaly_count > 5:
            recommendations.append("检测到多个工时异常，建议规范工作时间记录")
        
        # 基于质量分数的建议
        if statistics.quality_score < 80:
            recommendations.append("建议加强质量控制，提高工作成果质量")
        
        return recommendations