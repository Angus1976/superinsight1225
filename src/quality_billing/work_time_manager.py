"""
工时管理主模块

整合工时计算、验证、记录和报表功能的统一接口
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .work_time_calculator import (
    WorkTimeCalculator, WorkTimeRecord, WorkTimeStatistics, 
    WorkTimeType, WorkTimeStatus, WorkTimeAnomaly, AnomalyType
)
from .work_time_verifier import (
    WorkTimeVerifier, AutoWorkTimeRecorder, WorkTimeIntegrityChecker,
    VerificationResult, VerificationStatus, AutoRecordingConfig
)
from .work_time_reporter import (
    WorkTimeReporter, ReportConfig, ReportType, ReportFormat, 
    AggregationLevel, WorkTimeMetrics
)
from .work_time_quality_analyzer import (
    WorkTimeQualityAnalyzer, EfficiencyBenchmark, WorkTimePrediction,
    EfficiencyOptimization, EfficiencyLevel
)

logger = logging.getLogger(__name__)


class WorkTimeManagerConfig:
    """工时管理器配置"""
    
    def __init__(self):
        # 计算器配置
        self.max_daily_hours = 12
        self.min_daily_hours = 4
        self.max_continuous_hours = 4
        
        # 验证器配置
        self.enable_auto_verification = True
        self.verification_interval_minutes = 30
        
        # 记录器配置
        self.enable_auto_recording = True
        self.recording_interval_minutes = 5
        self.idle_threshold_minutes = 10
        
        # 报表配置
        self.enable_report_caching = True
        self.cache_expiry_minutes = 30
        
        # 异常处理配置
        self.enable_auto_correction = True
        self.anomaly_detection_interval_minutes = 60
        
        # 通知配置
        self.enable_notifications = True
        self.notification_channels = ['email', 'system']


class WorkTimeManager:
    """工时管理器主类"""
    
    def __init__(self, config: WorkTimeManagerConfig = None):
        self.config = config or WorkTimeManagerConfig()
        
        # 初始化核心组件
        self.calculator = WorkTimeCalculator()
        self.verifier = WorkTimeVerifier()
        self.auto_recorder = AutoWorkTimeRecorder(self.verifier)
        self.integrity_checker = WorkTimeIntegrityChecker()
        self.reporter = WorkTimeReporter()
        self.quality_analyzer = WorkTimeQualityAnalyzer()  # 新增质量分析器
        
        # 状态管理
        self.active_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.scheduled_tasks: Dict[str, Any] = {}
        
        # 线程池用于异步任务
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 应用配置
        self._apply_config()
        
        logger.info("WorkTimeManager initialized successfully")
    
    def _apply_config(self):
        """应用配置到各组件"""
        # 配置计算器
        self.calculator.max_daily_hours = self.config.max_daily_hours
        self.calculator.min_daily_hours = self.config.min_daily_hours
        self.calculator.max_continuous_hours = self.config.max_continuous_hours
        
        logger.info("Configuration applied to all components")
    
    # 工时会话管理
    
    def start_work_session(self, user_id: str, task_id: str, project_id: str,
                          work_type: WorkTimeType = WorkTimeType.EFFECTIVE,
                          description: str = "", auto_record: bool = None) -> Dict[str, Any]:
        """开始工作会话"""
        try:
            # 检查是否已有活跃会话
            if user_id in self.active_sessions:
                existing_session = self.active_sessions[user_id]
                logger.warning(f"User {user_id} already has active session {existing_session}")
                return {
                    'success': False,
                    'error': 'User already has an active session',
                    'existing_session_id': existing_session
                }
            
            # 启动计算器会话
            session_id = self.calculator.start_work_session(
                user_id, task_id, project_id, work_type, description
            )
            
            # 启动自动记录（如果启用）
            auto_recording_id = None
            if auto_record is None:
                auto_record = self.config.enable_auto_recording
            
            if auto_record:
                try:
                    auto_recording_id = self.auto_recorder.start_auto_recording(
                        user_id, task_id, project_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to start auto recording for {user_id}: {str(e)}")
            
            # 记录活跃会话
            self.active_sessions[user_id] = session_id
            
            # 调度验证任务
            if self.config.enable_auto_verification:
                self._schedule_verification_task(session_id)
            
            return {
                'success': True,
                'session_id': session_id,
                'auto_recording_id': auto_recording_id,
                'start_time': datetime.now().isoformat(),
                'user_id': user_id,
                'task_id': task_id,
                'project_id': project_id
            }
            
        except Exception as e:
            logger.error(f"Failed to start work session for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def end_work_session(self, user_id: str, description: str = "") -> Dict[str, Any]:
        """结束工作会话"""
        try:
            if user_id not in self.active_sessions:
                return {
                    'success': False,
                    'error': 'No active session found for user'
                }
            
            session_id = self.active_sessions[user_id]
            
            # 结束计算器会话
            record = self.calculator.end_work_session(session_id, description)
            
            # 停止自动记录
            auto_record = None
            try:
                auto_record = self.auto_recorder.stop_auto_recording(session_id)
            except Exception as e:
                logger.warning(f"Failed to stop auto recording for {session_id}: {str(e)}")
            
            # 验证工时记录
            verification_results = []
            if self.config.enable_auto_verification:
                verification_results = self.verifier.verify_work_time_record(record)
            
            # 检测异常
            anomalies = self.calculator.detect_work_time_anomalies(
                user_id, record.start_time
            )
            
            # 清理活跃会话
            del self.active_sessions[user_id]
            
            # 取消调度任务
            self._cancel_scheduled_tasks(session_id)
            
            return {
                'success': True,
                'session_id': session_id,
                'record': {
                    'id': record.id,
                    'duration_minutes': record.duration_minutes,
                    'pause_duration_minutes': record.pause_duration_minutes,
                    'start_time': record.start_time.isoformat(),
                    'end_time': record.end_time.isoformat() if record.end_time else None,
                    'work_type': record.work_type.value,
                    'status': record.status.value
                },
                'verification_results': [
                    {
                        'rule_id': vr.rule_id,
                        'status': vr.status.value,
                        'confidence_score': vr.confidence_score
                    }
                    for vr in verification_results
                ],
                'anomalies': [
                    {
                        'type': a.anomaly_type.value,
                        'severity': a.severity,
                        'description': a.description
                    }
                    for a in anomalies
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to end work session for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def pause_work_session(self, user_id: str, reason: str = "") -> Dict[str, Any]:
        """暂停工作会话"""
        try:
            if user_id not in self.active_sessions:
                return {
                    'success': False,
                    'error': 'No active session found for user'
                }
            
            session_id = self.active_sessions[user_id]
            record = self.calculator.pause_work_session(session_id, reason)
            
            return {
                'success': True,
                'session_id': session_id,
                'status': record.status.value,
                'pause_time': datetime.now().isoformat(),
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Failed to pause work session for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def resume_work_session(self, user_id: str) -> Dict[str, Any]:
        """恢复工作会话"""
        try:
            if user_id not in self.active_sessions:
                return {
                    'success': False,
                    'error': 'No active session found for user'
                }
            
            session_id = self.active_sessions[user_id]
            record = self.calculator.resume_work_session(session_id)
            
            return {
                'success': True,
                'session_id': session_id,
                'status': record.status.value,
                'resume_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to resume work session for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_session_status(self, user_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        if user_id not in self.active_sessions:
            return {
                'has_active_session': False
            }
        
        session_id = self.active_sessions[user_id]
        
        # 获取计算器中的记录
        record = self.calculator.records.get(session_id)
        if not record:
            return {
                'has_active_session': False,
                'error': 'Session record not found'
            }
        
        # 获取自动记录状态
        auto_recording_status = self.auto_recorder.get_recording_status(session_id)
        
        current_time = datetime.now()
        duration_minutes = (current_time - record.start_time).total_seconds() / 60
        
        return {
            'has_active_session': True,
            'session_id': session_id,
            'user_id': record.user_id,
            'status': record.status.value,
            'start_time': record.start_time.isoformat(),
            'duration_minutes': duration_minutes,
            'pause_duration_minutes': record.pause_duration_minutes,
            'work_type': record.work_type.value,
            'task_id': record.task_id,
            'project_id': record.project_id,
            'auto_recording': auto_recording_status
        }
    
    # 工时统计和分析
    
    def get_work_time_statistics(self, user_id: str, start_date: datetime, 
                                end_date: datetime) -> Dict[str, Any]:
        """获取工时统计"""
        try:
            statistics = self.calculator.generate_work_time_statistics(
                user_id, start_date, end_date
            )
            
            return {
                'success': True,
                'statistics': {
                    'user_id': statistics.user_id,
                    'period': {
                        'start': statistics.period_start.isoformat(),
                        'end': statistics.period_end.isoformat()
                    },
                    'total_effective_hours': statistics.total_effective_hours,
                    'total_pause_hours': statistics.total_pause_hours,
                    'total_overtime_hours': statistics.total_overtime_hours,
                    'average_daily_hours': statistics.average_daily_hours,
                    'productivity_score': statistics.productivity_score,
                    'efficiency_rating': statistics.efficiency_rating,
                    'anomaly_count': statistics.anomaly_count,
                    'tasks_completed': statistics.tasks_completed,
                    'quality_score': statistics.quality_score
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get work time statistics for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_detailed_report(self, user_id: str, start_date: datetime, 
                           end_date: datetime) -> Dict[str, Any]:
        """获取详细工时报表"""
        try:
            report = self.calculator.get_work_time_report(user_id, start_date, end_date)
            
            return {
                'success': True,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Failed to get detailed report for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_custom_report(self, config: ReportConfig, start_date: datetime,
                              end_date: datetime, entity_ids: List[str] = None) -> Dict[str, Any]:
        """生成自定义报表"""
        try:
            report = self.reporter.generate_report(config, start_date, end_date, entity_ids)
            
            return {
                'success': True,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Failed to generate custom report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_report(self, report: Dict[str, Any], format: ReportFormat, 
                     filename: str = None) -> Dict[str, Any]:
        """导出报表"""
        try:
            exported_data = self.reporter.export_report(report, format, filename)
            
            return {
                'success': True,
                'data': exported_data,
                'format': format.value,
                'size_bytes': len(exported_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to export report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 异常检测和处理
    
    def detect_anomalies(self, user_id: str, date: datetime = None) -> Dict[str, Any]:
        """检测工时异常"""
        try:
            if date is None:
                date = datetime.now()
            
            anomalies = self.calculator.detect_work_time_anomalies(user_id, date)
            
            return {
                'success': True,
                'anomalies': [
                    {
                        'id': a.id,
                        'type': a.anomaly_type.value,
                        'severity': a.severity,
                        'description': a.description,
                        'detected_at': a.detected_at.isoformat(),
                        'resolved': a.resolved
                    }
                    for a in anomalies
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def auto_correct_anomalies(self, anomaly_ids: List[str]) -> Dict[str, Any]:
        """自动纠正异常"""
        try:
            if not self.config.enable_auto_correction:
                return {
                    'success': False,
                    'error': 'Auto correction is disabled'
                }
            
            correction_results = self.calculator.auto_correct_anomalies(anomaly_ids)
            
            return {
                'success': True,
                'correction_results': correction_results,
                'corrected_count': sum(1 for result in correction_results.values() if result),
                'failed_count': sum(1 for result in correction_results.values() if not result)
            }
            
        except Exception as e:
            logger.error(f"Failed to auto correct anomalies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 数据完整性检查
    
    def check_data_integrity(self, user_ids: List[str] = None, 
                           start_date: datetime = None, 
                           end_date: datetime = None) -> Dict[str, Any]:
        """检查数据完整性"""
        try:
            # 获取要检查的记录
            records = []
            for record in self.calculator.records.values():
                if record.status == WorkTimeStatus.COMPLETED:
                    # 用户过滤
                    if user_ids and record.user_id not in user_ids:
                        continue
                    
                    # 时间过滤
                    if start_date and record.start_time < start_date:
                        continue
                    if end_date and record.start_time > end_date:
                        continue
                    
                    records.append(record)
            
            integrity_result = self.integrity_checker.check_data_integrity(records)
            
            return {
                'success': True,
                'integrity_result': integrity_result
            }
            
        except Exception as e:
            logger.error(f"Failed to check data integrity: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 配置管理
    
    def configure_auto_recording(self, user_id: str, config: AutoRecordingConfig) -> Dict[str, Any]:
        """配置自动记录"""
        try:
            self.auto_recorder.configure_auto_recording(user_id, config)
            
            return {
                'success': True,
                'message': f'Auto recording configured for user {user_id}'
            }
            
        except Exception as e:
            logger.error(f"Failed to configure auto recording for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """获取用户配置"""
        try:
            config = self.auto_recorder.get_user_config(user_id)
            
            return {
                'success': True,
                'config': {
                    'user_id': config.user_id,
                    'enabled': config.enabled,
                    'recording_interval_minutes': config.recording_interval_minutes,
                    'idle_threshold_minutes': config.idle_threshold_minutes,
                    'auto_pause_enabled': config.auto_pause_enabled,
                    'auto_resume_enabled': config.auto_resume_enabled,
                    'activity_tracking': config.activity_tracking
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user config for {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 私有辅助方法
    
    def _schedule_verification_task(self, session_id: str):
        """调度验证任务"""
        # 这里可以实现定期验证任务的调度
        # 暂时只记录日志
        logger.info(f"Scheduled verification task for session {session_id}")
    
    def _cancel_scheduled_tasks(self, session_id: str):
        """取消调度任务"""
        # 取消与会话相关的所有调度任务
        if session_id in self.scheduled_tasks:
            del self.scheduled_tasks[session_id]
        logger.info(f"Cancelled scheduled tasks for session {session_id}")
    
    # 工时质量关联分析接口
    
    def analyze_work_time_quality_correlation(self, user_id: str, 
                                            start_date: datetime, 
                                            end_date: datetime) -> Dict[str, Any]:
        """分析工时与质量分数的关联性"""
        try:
            result = self.quality_analyzer.analyze_work_time_quality_correlation(
                user_id, start_date, end_date
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze work time quality correlation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def assess_efficiency_and_optimization(self, user_id: str, 
                                         task_type: str = None,
                                         project_id: str = None) -> Dict[str, Any]:
        """评估效率并提供优化建议"""
        try:
            result = self.quality_analyzer.assess_efficiency_and_optimization(
                user_id, task_type, project_id
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to assess efficiency: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def configure_work_time_benchmarks(self, task_type: str, 
                                     project_type: str,
                                     skill_level: str,
                                     sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """配置工时基准和标准"""
        try:
            result = self.quality_analyzer.configure_work_time_benchmarks(
                task_type, project_type, skill_level, sample_data
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to configure benchmarks: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict_work_time_and_quality(self, user_id: str, 
                                    task_type: str,
                                    task_complexity: float,
                                    historical_window_days: int = 90) -> Dict[str, Any]:
        """预测工时和质量"""
        try:
            result = self.quality_analyzer.predict_work_time_and_quality(
                user_id, task_type, task_complexity, historical_window_days
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to predict work time and quality: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_efficiency_planning_report(self, team_ids: List[str],
                                          project_id: str,
                                          planning_horizon_weeks: int = 4) -> Dict[str, Any]:
        """生成效率规划报告"""
        try:
            result = self.quality_analyzer.generate_efficiency_planning_report(
                team_ids, project_id, planning_horizon_weeks
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate efficiency planning report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    # 批量操作
    
    def batch_process_records(self, operation: str, record_ids: List[str], 
                             parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """批量处理记录"""
        try:
            results = {}
            
            for record_id in record_ids:
                try:
                    if operation == 'verify':
                        record = self.calculator.records.get(record_id)
                        if record:
                            verification_results = self.verifier.verify_work_time_record(record)
                            results[record_id] = {
                                'success': True,
                                'verification_count': len(verification_results)
                            }
                        else:
                            results[record_id] = {
                                'success': False,
                                'error': 'Record not found'
                            }
                    
                    elif operation == 'recalculate':
                        # 重新计算工时记录
                        record = self.calculator.records.get(record_id)
                        if record and record.start_time and record.end_time:
                            new_duration = self.calculator._calculate_duration_minutes(
                                record.start_time, record.end_time
                            )
                            record.duration_minutes = new_duration
                            results[record_id] = {
                                'success': True,
                                'new_duration_minutes': new_duration
                            }
                        else:
                            results[record_id] = {
                                'success': False,
                                'error': 'Invalid record for recalculation'
                            }
                    
                    else:
                        results[record_id] = {
                            'success': False,
                            'error': f'Unknown operation: {operation}'
                        }
                
                except Exception as e:
                    results[record_id] = {
                        'success': False,
                        'error': str(e)
                    }
            
            success_count = sum(1 for result in results.values() if result.get('success'))
            
            return {
                'success': True,
                'operation': operation,
                'total_records': len(record_ids),
                'success_count': success_count,
                'failure_count': len(record_ids) - success_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to batch process records: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 系统状态和健康检查
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'active_sessions': len(self.active_sessions),
            'total_records': len(self.calculator.records),
            'total_anomalies': len(self.calculator.anomalies),
            'verification_rules': len(self.verifier.verification_rules),
            'config': {
                'auto_verification_enabled': self.config.enable_auto_verification,
                'auto_recording_enabled': self.config.enable_auto_recording,
                'auto_correction_enabled': self.config.enable_auto_correction,
                'notifications_enabled': self.config.enable_notifications
            },
            'health_status': 'healthy'  # 可以添加更复杂的健康检查逻辑
        }
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # 清理旧记录
            old_records = [
                record_id for record_id, record in self.calculator.records.items()
                if record.created_at < cutoff_date
            ]
            
            for record_id in old_records:
                del self.calculator.records[record_id]
            
            # 清理旧异常
            old_anomalies = [
                anomaly_id for anomaly_id, anomaly in self.calculator.anomalies.items()
                if anomaly.detected_at < cutoff_date
            ]
            
            for anomaly_id in old_anomalies:
                del self.calculator.anomalies[anomaly_id]
            
            return {
                'success': True,
                'cleaned_records': len(old_records),
                'cleaned_anomalies': len(old_anomalies),
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }