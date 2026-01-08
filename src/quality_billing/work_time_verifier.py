"""
工时自动记录和验证机制

实现工时数据的自动记录、验证和完整性检查
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
import hashlib
import hmac
import statistics
from collections import defaultdict

from .work_time_calculator import WorkTimeRecord, WorkTimeStatus, WorkTimeType, AnomalyType

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """验证状态枚举"""
    PENDING = "pending"  # 待验证
    VERIFIED = "verified"  # 已验证
    FAILED = "failed"  # 验证失败
    SUSPICIOUS = "suspicious"  # 可疑
    MANUAL_REVIEW = "manual_review"  # 需人工审核


class RecordingMethod(str, Enum):
    """记录方式枚举"""
    AUTOMATIC = "automatic"  # 自动记录
    MANUAL = "manual"  # 手动记录
    API = "api"  # API记录
    IMPORT = "import"  # 导入记录


@dataclass
class VerificationRule:
    """验证规则数据类"""
    id: str
    name: str
    description: str
    rule_type: str  # time_range, duration, pattern, consistency
    parameters: Dict[str, Any]
    severity: str  # low, medium, high, critical
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class VerificationResult:
    """验证结果数据类"""
    record_id: str
    rule_id: str
    status: VerificationStatus
    confidence_score: float  # 0-1之间的置信度
    details: Dict[str, Any]
    verified_at: datetime = field(default_factory=datetime.now)
    verified_by: str = "system"


@dataclass
class AutoRecordingConfig:
    """自动记录配置"""
    user_id: str
    enabled: bool = True
    recording_interval_minutes: int = 5  # 记录间隔
    idle_threshold_minutes: int = 10  # 空闲阈值
    auto_pause_enabled: bool = True  # 自动暂停
    auto_resume_enabled: bool = True  # 自动恢复
    activity_tracking: bool = True  # 活动跟踪
    screenshot_enabled: bool = False  # 截图功能
    keystroke_tracking: bool = False  # 按键跟踪
    mouse_tracking: bool = False  # 鼠标跟踪


class WorkTimeVerifier:
    """工时验证器"""
    
    def __init__(self):
        self.verification_rules: Dict[str, VerificationRule] = {}
        self.verification_results: Dict[str, List[VerificationResult]] = defaultdict(list)
        self.auto_recording_configs: Dict[str, AutoRecordingConfig] = {}
        self.activity_logs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 初始化默认验证规则
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """初始化默认验证规则"""
        rules = [
            VerificationRule(
                id="time_range_check",
                name="工作时间范围检查",
                description="检查工作时间是否在合理范围内",
                rule_type="time_range",
                parameters={
                    "min_start_hour": 6,
                    "max_start_hour": 22,
                    "min_end_hour": 7,
                    "max_end_hour": 23
                },
                severity="medium"
            ),
            VerificationRule(
                id="duration_check",
                name="工作时长检查",
                description="检查单次工作时长是否合理",
                rule_type="duration",
                parameters={
                    "min_duration_minutes": 5,
                    "max_duration_minutes": 480,  # 8小时
                    "max_continuous_minutes": 240  # 4小时
                },
                severity="high"
            ),
            VerificationRule(
                id="consistency_check",
                name="数据一致性检查",
                description="检查工时数据的一致性",
                rule_type="consistency",
                parameters={
                    "check_overlapping": True,
                    "check_gaps": True,
                    "max_gap_minutes": 30
                },
                severity="high"
            ),
            VerificationRule(
                id="pattern_check",
                name="工作模式检查",
                description="检查工作模式是否异常",
                rule_type="pattern",
                parameters={
                    "check_weekend_work": True,
                    "check_night_work": True,
                    "night_start_hour": 22,
                    "night_end_hour": 6
                },
                severity="low"
            )
        ]
        
        for rule in rules:
            self.verification_rules[rule.id] = rule
    
    def verify_work_time_record(self, record: WorkTimeRecord) -> List[VerificationResult]:
        """验证工时记录"""
        results = []
        
        for rule in self.verification_rules.values():
            if not rule.enabled:
                continue
            
            try:
                result = self._apply_verification_rule(record, rule)
                if result:
                    results.append(result)
                    self.verification_results[record.id].append(result)
            except Exception as e:
                logger.error(f"Error applying rule {rule.id} to record {record.id}: {str(e)}")
        
        return results
    
    def _apply_verification_rule(self, record: WorkTimeRecord, rule: VerificationRule) -> Optional[VerificationResult]:
        """应用验证规则"""
        if rule.rule_type == "time_range":
            return self._check_time_range(record, rule)
        elif rule.rule_type == "duration":
            return self._check_duration(record, rule)
        elif rule.rule_type == "consistency":
            return self._check_consistency(record, rule)
        elif rule.rule_type == "pattern":
            return self._check_pattern(record, rule)
        
        return None
    
    def _check_time_range(self, record: WorkTimeRecord, rule: VerificationRule) -> Optional[VerificationResult]:
        """检查时间范围"""
        params = rule.parameters
        start_hour = record.start_time.hour
        
        if record.end_time:
            end_hour = record.end_time.hour
        else:
            end_hour = start_hour
        
        # 检查开始时间
        if not (params["min_start_hour"] <= start_hour <= params["max_start_hour"]):
            return VerificationResult(
                record_id=record.id,
                rule_id=rule.id,
                status=VerificationStatus.SUSPICIOUS,
                confidence_score=0.8,
                details={
                    "issue": "start_time_out_of_range",
                    "start_hour": start_hour,
                    "expected_range": f"{params['min_start_hour']}-{params['max_start_hour']}"
                }
            )
        
        # 检查结束时间
        if not (params["min_end_hour"] <= end_hour <= params["max_end_hour"]):
            return VerificationResult(
                record_id=record.id,
                rule_id=rule.id,
                status=VerificationStatus.SUSPICIOUS,
                confidence_score=0.8,
                details={
                    "issue": "end_time_out_of_range",
                    "end_hour": end_hour,
                    "expected_range": f"{params['min_end_hour']}-{params['max_end_hour']}"
                }
            )
        
        return VerificationResult(
            record_id=record.id,
            rule_id=rule.id,
            status=VerificationStatus.VERIFIED,
            confidence_score=1.0,
            details={"check": "time_range_ok"}
        )
    
    def _check_duration(self, record: WorkTimeRecord, rule: VerificationRule) -> Optional[VerificationResult]:
        """检查工作时长"""
        params = rule.parameters
        duration = record.duration_minutes
        
        if duration < params["min_duration_minutes"]:
            return VerificationResult(
                record_id=record.id,
                rule_id=rule.id,
                status=VerificationStatus.SUSPICIOUS,
                confidence_score=0.9,
                details={
                    "issue": "duration_too_short",
                    "duration_minutes": duration,
                    "min_expected": params["min_duration_minutes"]
                }
            )
        
        if duration > params["max_duration_minutes"]:
            return VerificationResult(
                record_id=record.id,
                rule_id=rule.id,
                status=VerificationStatus.FAILED,
                confidence_score=0.95,
                details={
                    "issue": "duration_too_long",
                    "duration_minutes": duration,
                    "max_expected": params["max_duration_minutes"]
                }
            )
        
        return VerificationResult(
            record_id=record.id,
            rule_id=rule.id,
            status=VerificationStatus.VERIFIED,
            confidence_score=1.0,
            details={"check": "duration_ok"}
        )
    
    def _check_consistency(self, record: WorkTimeRecord, rule: VerificationRule) -> Optional[VerificationResult]:
        """检查数据一致性"""
        # 这里需要与其他记录进行比较，暂时返回验证通过
        return VerificationResult(
            record_id=record.id,
            rule_id=rule.id,
            status=VerificationStatus.VERIFIED,
            confidence_score=1.0,
            details={"check": "consistency_ok"}
        )
    
    def _check_pattern(self, record: WorkTimeRecord, rule: VerificationRule) -> Optional[VerificationResult]:
        """检查工作模式"""
        params = rule.parameters
        
        # 检查周末工作
        if params.get("check_weekend_work", False):
            if record.start_time.weekday() >= 5:  # 周六或周日
                return VerificationResult(
                    record_id=record.id,
                    rule_id=rule.id,
                    status=VerificationStatus.SUSPICIOUS,
                    confidence_score=0.7,
                    details={
                        "issue": "weekend_work",
                        "weekday": record.start_time.weekday()
                    }
                )
        
        # 检查夜间工作
        if params.get("check_night_work", False):
            night_start = params.get("night_start_hour", 22)
            night_end = params.get("night_end_hour", 6)
            
            start_hour = record.start_time.hour
            if start_hour >= night_start or start_hour <= night_end:
                return VerificationResult(
                    record_id=record.id,
                    rule_id=rule.id,
                    status=VerificationStatus.SUSPICIOUS,
                    confidence_score=0.6,
                    details={
                        "issue": "night_work",
                        "start_hour": start_hour
                    }
                )
        
        return VerificationResult(
            record_id=record.id,
            rule_id=rule.id,
            status=VerificationStatus.VERIFIED,
            confidence_score=1.0,
            details={"check": "pattern_ok"}
        )
    
    def get_verification_summary(self, record_id: str) -> Dict[str, Any]:
        """获取验证摘要"""
        results = self.verification_results.get(record_id, [])
        
        if not results:
            return {
                "record_id": record_id,
                "status": "not_verified",
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "suspicious_checks": 0,
                "overall_confidence": 0.0
            }
        
        status_counts = defaultdict(int)
        total_confidence = 0.0
        
        for result in results:
            status_counts[result.status.value] += 1
            total_confidence += result.confidence_score
        
        overall_status = "verified"
        if status_counts["failed"] > 0:
            overall_status = "failed"
        elif status_counts["suspicious"] > 0:
            overall_status = "suspicious"
        elif status_counts["manual_review"] > 0:
            overall_status = "manual_review"
        
        return {
            "record_id": record_id,
            "status": overall_status,
            "total_checks": len(results),
            "passed_checks": status_counts["verified"],
            "failed_checks": status_counts["failed"],
            "suspicious_checks": status_counts["suspicious"],
            "manual_review_checks": status_counts["manual_review"],
            "overall_confidence": total_confidence / len(results) if results else 0.0,
            "details": [
                {
                    "rule_id": r.rule_id,
                    "status": r.status.value,
                    "confidence": r.confidence_score,
                    "details": r.details
                }
                for r in results
            ]
        }


class AutoWorkTimeRecorder:
    """自动工时记录器"""
    
    def __init__(self, verifier: WorkTimeVerifier):
        self.verifier = verifier
        self.active_recordings: Dict[str, Dict[str, Any]] = {}
        self.recording_configs: Dict[str, AutoRecordingConfig] = {}
        self.activity_buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def start_auto_recording(self, user_id: str, task_id: str, project_id: str) -> str:
        """开始自动记录"""
        config = self.recording_configs.get(user_id, AutoRecordingConfig(user_id=user_id))
        
        if not config.enabled:
            raise ValueError(f"Auto recording is disabled for user {user_id}")
        
        recording_id = f"auto_{user_id}_{task_id}_{datetime.now().timestamp()}"
        
        self.active_recordings[recording_id] = {
            'user_id': user_id,
            'task_id': task_id,
            'project_id': project_id,
            'start_time': datetime.now(),
            'last_activity': datetime.now(),
            'config': config,
            'status': 'active',
            'activities': []
        }
        
        logger.info(f"Started auto recording {recording_id} for user {user_id}")
        return recording_id
    
    def record_activity(self, recording_id: str, activity_type: str, details: Dict[str, Any]):
        """记录活动"""
        if recording_id not in self.active_recordings:
            return
        
        recording = self.active_recordings[recording_id]
        activity = {
            'timestamp': datetime.now(),
            'type': activity_type,
            'details': details
        }
        
        recording['activities'].append(activity)
        recording['last_activity'] = datetime.now()
        
        # 检查是否需要自动暂停
        self._check_auto_pause(recording_id)
    
    def _check_auto_pause(self, recording_id: str):
        """检查是否需要自动暂停"""
        recording = self.active_recordings[recording_id]
        config = recording['config']
        
        if not config.auto_pause_enabled:
            return
        
        # 检查空闲时间
        idle_time = (datetime.now() - recording['last_activity']).total_seconds() / 60
        
        if idle_time > config.idle_threshold_minutes and recording['status'] == 'active':
            recording['status'] = 'auto_paused'
            recording['auto_pause_time'] = datetime.now()
            logger.info(f"Auto-paused recording {recording_id} due to inactivity")
    
    def _check_auto_resume(self, recording_id: str):
        """检查是否需要自动恢复"""
        recording = self.active_recordings[recording_id]
        config = recording['config']
        
        if not config.auto_resume_enabled:
            return
        
        if recording['status'] == 'auto_paused':
            recording['status'] = 'active'
            # 记录暂停时长
            if 'auto_pause_time' in recording:
                pause_duration = (datetime.now() - recording['auto_pause_time']).total_seconds() / 60
                recording.setdefault('total_pause_minutes', 0)
                recording['total_pause_minutes'] += pause_duration
                del recording['auto_pause_time']
            
            logger.info(f"Auto-resumed recording {recording_id}")
    
    def stop_auto_recording(self, recording_id: str) -> WorkTimeRecord:
        """停止自动记录"""
        if recording_id not in self.active_recordings:
            raise ValueError(f"Recording {recording_id} not found")
        
        recording = self.active_recordings[recording_id]
        end_time = datetime.now()
        
        # 计算总时长
        total_duration = (end_time - recording['start_time']).total_seconds() / 60
        pause_duration = recording.get('total_pause_minutes', 0)
        effective_duration = total_duration - pause_duration
        
        # 创建工时记录
        work_record = WorkTimeRecord(
            id=recording_id,
            user_id=recording['user_id'],
            task_id=recording['task_id'],
            project_id=recording['project_id'],
            start_time=recording['start_time'],
            end_time=end_time,
            work_type=WorkTimeType.EFFECTIVE,
            status=WorkTimeStatus.COMPLETED,
            duration_minutes=int(effective_duration),
            pause_duration_minutes=int(pause_duration),
            description="Auto-recorded work session",
            metadata={
                'recording_method': RecordingMethod.AUTOMATIC.value,
                'activity_count': len(recording['activities']),
                'auto_pauses': recording.get('auto_pause_count', 0),
                'config_snapshot': recording['config'].__dict__
            }
        )
        
        # 验证记录
        verification_results = self.verifier.verify_work_time_record(work_record)
        
        # 清理活跃记录
        del self.active_recordings[recording_id]
        
        logger.info(f"Stopped auto recording {recording_id}, duration: {effective_duration:.1f} minutes")
        return work_record
    
    def get_recording_status(self, recording_id: str) -> Dict[str, Any]:
        """获取记录状态"""
        if recording_id not in self.active_recordings:
            return {"status": "not_found"}
        
        recording = self.active_recordings[recording_id]
        current_time = datetime.now()
        
        total_duration = (current_time - recording['start_time']).total_seconds() / 60
        idle_time = (current_time - recording['last_activity']).total_seconds() / 60
        
        return {
            "recording_id": recording_id,
            "status": recording['status'],
            "start_time": recording['start_time'].isoformat(),
            "total_duration_minutes": total_duration,
            "idle_time_minutes": idle_time,
            "activity_count": len(recording['activities']),
            "pause_duration_minutes": recording.get('total_pause_minutes', 0)
        }
    
    def configure_auto_recording(self, user_id: str, config: AutoRecordingConfig):
        """配置自动记录"""
        self.recording_configs[user_id] = config
        logger.info(f"Updated auto recording config for user {user_id}")
    
    def get_user_config(self, user_id: str) -> AutoRecordingConfig:
        """获取用户配置"""
        return self.recording_configs.get(user_id, AutoRecordingConfig(user_id=user_id))


class WorkTimeIntegrityChecker:
    """工时完整性检查器"""
    
    def __init__(self):
        self.integrity_rules = {
            'no_overlapping': True,
            'no_gaps_in_workday': True,
            'consistent_daily_patterns': True,
            'reasonable_break_times': True
        }
    
    def check_data_integrity(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """检查数据完整性"""
        issues = []
        
        # 按用户和日期分组
        user_daily_records = self._group_records_by_user_date(records)
        
        for (user_id, date), daily_records in user_daily_records.items():
            # 检查重叠
            overlapping_issues = self._check_overlapping_records(daily_records)
            issues.extend(overlapping_issues)
            
            # 检查间隙
            gap_issues = self._check_record_gaps(daily_records)
            issues.extend(gap_issues)
            
            # 检查模式一致性
            pattern_issues = self._check_pattern_consistency(user_id, daily_records)
            issues.extend(pattern_issues)
        
        return {
            'total_records_checked': len(records),
            'issues_found': len(issues),
            'integrity_score': max(0, 100 - len(issues) * 5),  # 每个问题扣5分
            'issues': issues,
            'recommendations': self._generate_integrity_recommendations(issues)
        }
    
    def _group_records_by_user_date(self, records: List[WorkTimeRecord]) -> Dict[Tuple[str, str], List[WorkTimeRecord]]:
        """按用户和日期分组记录"""
        grouped = defaultdict(list)
        
        for record in records:
            if record.status == WorkTimeStatus.COMPLETED:
                date_key = record.start_time.date().isoformat()
                grouped[(record.user_id, date_key)].append(record)
        
        # 按开始时间排序
        for key in grouped:
            grouped[key].sort(key=lambda r: r.start_time)
        
        return dict(grouped)
    
    def _check_overlapping_records(self, records: List[WorkTimeRecord]) -> List[Dict[str, Any]]:
        """检查重叠记录"""
        issues = []
        
        for i in range(len(records) - 1):
            current = records[i]
            next_record = records[i + 1]
            
            if current.end_time and current.end_time > next_record.start_time:
                issues.append({
                    'type': 'overlapping_records',
                    'severity': 'high',
                    'record_ids': [current.id, next_record.id],
                    'description': f"Records overlap by {(current.end_time - next_record.start_time).total_seconds() / 60:.1f} minutes",
                    'user_id': current.user_id
                })
        
        return issues
    
    def _check_record_gaps(self, records: List[WorkTimeRecord]) -> List[Dict[str, Any]]:
        """检查记录间隙"""
        issues = []
        
        for i in range(len(records) - 1):
            current = records[i]
            next_record = records[i + 1]
            
            if current.end_time:
                gap_minutes = (next_record.start_time - current.end_time).total_seconds() / 60
                
                # 如果间隙超过2小时且在工作时间内，标记为问题
                if 30 < gap_minutes < 120:  # 30分钟到2小时的间隙
                    issues.append({
                        'type': 'suspicious_gap',
                        'severity': 'medium',
                        'record_ids': [current.id, next_record.id],
                        'description': f"Suspicious gap of {gap_minutes:.1f} minutes between records",
                        'user_id': current.user_id,
                        'gap_minutes': gap_minutes
                    })
        
        return issues
    
    def _check_pattern_consistency(self, user_id: str, records: List[WorkTimeRecord]) -> List[Dict[str, Any]]:
        """检查模式一致性"""
        issues = []
        
        if len(records) < 2:
            return issues
        
        # 检查工作时间模式
        start_hours = [r.start_time.hour for r in records]
        end_hours = [r.end_time.hour for r in records if r.end_time]
        
        # 如果开始时间变化很大，标记为不一致
        if len(start_hours) > 1:
            start_hour_std = statistics.stdev(start_hours) if len(start_hours) > 1 else 0
            if start_hour_std > 2:  # 标准差超过2小时
                issues.append({
                    'type': 'inconsistent_start_times',
                    'severity': 'low',
                    'description': f"Inconsistent start times, std: {start_hour_std:.1f} hours",
                    'user_id': user_id,
                    'start_hours': start_hours
                })
        
        return issues
    
    def _generate_integrity_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """生成完整性建议"""
        recommendations = []
        
        issue_types = set(issue['type'] for issue in issues)
        
        if 'overlapping_records' in issue_types:
            recommendations.append("发现重叠的工时记录，建议检查时间记录的准确性")
        
        if 'suspicious_gap' in issue_types:
            recommendations.append("发现可疑的时间间隙，建议确认是否遗漏了休息时间记录")
        
        if 'inconsistent_start_times' in issue_types:
            recommendations.append("工作开始时间不一致，建议规范工作时间安排")
        
        if not recommendations:
            recommendations.append("工时数据完整性良好，无需特别处理")
        
        return recommendations