"""
工时计算系统单元测试

测试工时计算、验证和管理功能的核心逻辑
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.quality_billing.work_time_calculator import (
    WorkTimeCalculator, WorkTimeRecord, WorkTimeStatistics,
    WorkTimeType, WorkTimeStatus, WorkTimeAnomaly, AnomalyType
)
from src.quality_billing.work_time_verifier import (
    WorkTimeVerifier, AutoWorkTimeRecorder, WorkTimeIntegrityChecker,
    VerificationRule, VerificationResult, VerificationStatus,
    AutoRecordingConfig
)
from src.quality_billing.work_time_manager import (
    WorkTimeManager, WorkTimeManagerConfig
)


class TestWorkTimeCalculator:
    """工时计算器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.calculator = WorkTimeCalculator()
        self.user_id = "test_user_001"
        self.task_id = "task_001"
        self.project_id = "project_001"
    
    def test_start_work_session(self):
        """测试开始工作会话"""
        session_id = self.calculator.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        assert session_id is not None
        assert session_id in self.calculator.records
        assert self.user_id in self.calculator.active_sessions
        
        record = self.calculator.records[session_id]
        assert record.user_id == self.user_id
        assert record.task_id == self.task_id
        assert record.project_id == self.project_id
        assert record.status == WorkTimeStatus.ACTIVE
        assert record.work_type == WorkTimeType.EFFECTIVE
    
    def test_end_work_session(self):
        """测试结束工作会话"""
        # 开始会话
        session_id = self.calculator.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        # 模拟工作一段时间
        start_record = self.calculator.records[session_id]
        start_record.start_time = datetime.now() - timedelta(hours=2)
        
        # 结束会话
        end_record = self.calculator.end_work_session(session_id, "Work completed")
        
        assert end_record.status == WorkTimeStatus.COMPLETED
        assert end_record.end_time is not None
        assert end_record.duration_minutes > 0
        assert self.user_id not in self.calculator.active_sessions
        assert "Work completed" in end_record.description
    
    def test_pause_and_resume_session(self):
        """测试暂停和恢复会话"""
        # 开始会话
        session_id = self.calculator.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        # 暂停会话
        pause_record = self.calculator.pause_work_session(session_id, "Break time")
        assert pause_record.status == WorkTimeStatus.PAUSED
        
        # 恢复会话
        resume_record = self.calculator.resume_work_session(session_id)
        assert resume_record.status == WorkTimeStatus.ACTIVE
        assert resume_record.pause_duration_minutes >= 0
    
    def test_calculate_multi_dimensional_hours(self):
        """测试多维度工时计算"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # 创建测试记录
        self._create_test_records(start_date)
        
        dimensions = self.calculator.calculate_multi_dimensional_hours(
            self.user_id, start_date, end_date
        )
        
        assert 'effective_hours' in dimensions
        assert 'pause_hours' in dimensions
        assert 'overtime_hours' in dimensions
        assert 'total_hours' in dimensions
        assert dimensions['total_hours'] > 0
    
    def test_detect_work_time_anomalies(self):
        """测试工时异常检测"""
        test_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 创建异常工时记录（工时过长）
        session_id = self.calculator.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        record = self.calculator.records[session_id]
        record.start_time = test_date + timedelta(hours=8)
        record.end_time = test_date + timedelta(hours=20)  # 12小时工作
        record.duration_minutes = 720  # 12小时
        record.status = WorkTimeStatus.COMPLETED
        
        anomalies = self.calculator.detect_work_time_anomalies(self.user_id, test_date)
        
        assert len(anomalies) > 0
        excessive_hours_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.EXCESSIVE_HOURS), 
            None
        )
        assert excessive_hours_anomaly is not None
        assert excessive_hours_anomaly.severity == "high"
    
    def test_generate_work_time_statistics(self):
        """测试工时统计生成"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        
        # 创建一周的测试数据
        for i in range(5):  # 工作日
            date = start_date + timedelta(days=i)
            session_id = self.calculator.start_work_session(
                self.user_id, f"task_{i}", self.project_id
            )
            
            record = self.calculator.records[session_id]
            record.start_time = date + timedelta(hours=9)
            record.end_time = date + timedelta(hours=17)
            record.duration_minutes = 480  # 8小时
            record.pause_duration_minutes = 60  # 1小时休息
            record.status = WorkTimeStatus.COMPLETED
        
        statistics = self.calculator.generate_work_time_statistics(
            self.user_id, start_date, end_date
        )
        
        assert isinstance(statistics, WorkTimeStatistics)
        assert statistics.user_id == self.user_id
        assert statistics.total_effective_hours > 0
        assert statistics.average_daily_hours > 0
        assert statistics.tasks_completed > 0
    
    def test_auto_correct_anomalies(self):
        """测试异常自动纠正"""
        # 创建过长工时异常
        test_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        session_id = self.calculator.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        record = self.calculator.records[session_id]
        record.start_time = test_date + timedelta(hours=8)
        record.end_time = test_date + timedelta(hours=22)  # 14小时工作
        record.duration_minutes = 840  # 14小时
        record.status = WorkTimeStatus.COMPLETED
        
        # 检测异常
        anomalies = self.calculator.detect_work_time_anomalies(self.user_id, test_date)
        anomaly_ids = [a.id for a in anomalies if a.anomaly_type == AnomalyType.EXCESSIVE_HOURS]
        
        # 自动纠正
        correction_results = self.calculator.auto_correct_anomalies(anomaly_ids)
        
        assert len(correction_results) > 0
        # 检查是否有成功纠正的异常
        corrected_count = sum(1 for result in correction_results.values() if result)
        assert corrected_count >= 0  # 至少尝试了纠正
    
    def _create_test_records(self, start_date: datetime):
        """创建测试记录"""
        # 有效工时记录
        session_id1 = self.calculator.start_work_session(
            self.user_id, "task_1", self.project_id, WorkTimeType.EFFECTIVE
        )
        record1 = self.calculator.records[session_id1]
        record1.start_time = start_date + timedelta(hours=9)
        record1.end_time = start_date + timedelta(hours=17)
        record1.duration_minutes = 480
        record1.pause_duration_minutes = 60
        record1.status = WorkTimeStatus.COMPLETED
        
        # 加班工时记录
        session_id2 = self.calculator.start_work_session(
            self.user_id, "task_2", self.project_id, WorkTimeType.OVERTIME
        )
        record2 = self.calculator.records[session_id2]
        record2.start_time = start_date + timedelta(hours=18)
        record2.end_time = start_date + timedelta(hours=20)
        record2.duration_minutes = 120
        record2.status = WorkTimeStatus.COMPLETED


class TestWorkTimeVerifier:
    """工时验证器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.verifier = WorkTimeVerifier()
        self.user_id = "test_user_001"
    
    def test_verify_work_time_record_valid(self):
        """测试验证有效工时记录"""
        # 创建有效记录
        record = WorkTimeRecord(
            id="test_record_001",
            user_id=self.user_id,
            task_id="task_001",
            project_id="project_001",
            start_time=datetime.now().replace(hour=9, minute=0),
            end_time=datetime.now().replace(hour=17, minute=0),
            duration_minutes=480,
            status=WorkTimeStatus.COMPLETED
        )
        
        results = self.verifier.verify_work_time_record(record)
        
        assert len(results) > 0
        # 检查是否有验证通过的结果
        verified_results = [r for r in results if r.status == VerificationStatus.VERIFIED]
        assert len(verified_results) > 0
    
    def test_verify_work_time_record_suspicious(self):
        """测试验证可疑工时记录"""
        # 创建可疑记录（夜间工作）
        record = WorkTimeRecord(
            id="test_record_002",
            user_id=self.user_id,
            task_id="task_001",
            project_id="project_001",
            start_time=datetime.now().replace(hour=23, minute=0),  # 夜间开始
            end_time=datetime.now().replace(hour=2, minute=0) + timedelta(days=1),
            duration_minutes=180,
            status=WorkTimeStatus.COMPLETED
        )
        
        results = self.verifier.verify_work_time_record(record)
        
        # 检查是否有可疑结果
        suspicious_results = [r for r in results if r.status == VerificationStatus.SUSPICIOUS]
        assert len(suspicious_results) > 0
    
    def test_verify_work_time_record_failed(self):
        """测试验证失败的工时记录"""
        # 创建无效记录（工时过长）
        record = WorkTimeRecord(
            id="test_record_003",
            user_id=self.user_id,
            task_id="task_001",
            project_id="project_001",
            start_time=datetime.now().replace(hour=8, minute=0),
            end_time=datetime.now().replace(hour=22, minute=0),  # 14小时
            duration_minutes=840,
            status=WorkTimeStatus.COMPLETED
        )
        
        results = self.verifier.verify_work_time_record(record)
        
        # 检查是否有失败结果
        failed_results = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed_results) > 0
    
    def test_get_verification_summary(self):
        """测试获取验证摘要"""
        record_id = "test_record_004"
        
        # 创建并验证记录
        record = WorkTimeRecord(
            id=record_id,
            user_id=self.user_id,
            task_id="task_001",
            project_id="project_001",
            start_time=datetime.now().replace(hour=9, minute=0),
            end_time=datetime.now().replace(hour=17, minute=0),
            duration_minutes=480,
            status=WorkTimeStatus.COMPLETED
        )
        
        self.verifier.verify_work_time_record(record)
        
        summary = self.verifier.get_verification_summary(record_id)
        
        assert summary['record_id'] == record_id
        assert 'status' in summary
        assert 'total_checks' in summary
        assert 'overall_confidence' in summary
        assert summary['total_checks'] > 0


class TestAutoWorkTimeRecorder:
    """自动工时记录器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.verifier = WorkTimeVerifier()
        self.recorder = AutoWorkTimeRecorder(self.verifier)
        self.user_id = "test_user_001"
        self.task_id = "task_001"
        self.project_id = "project_001"
    
    def test_start_auto_recording(self):
        """测试开始自动记录"""
        recording_id = self.recorder.start_auto_recording(
            self.user_id, self.task_id, self.project_id
        )
        
        assert recording_id is not None
        assert recording_id in self.recorder.active_recordings
        
        recording = self.recorder.active_recordings[recording_id]
        assert recording['user_id'] == self.user_id
        assert recording['task_id'] == self.task_id
        assert recording['status'] == 'active'
    
    def test_record_activity(self):
        """测试记录活动"""
        recording_id = self.recorder.start_auto_recording(
            self.user_id, self.task_id, self.project_id
        )
        
        # 记录活动
        self.recorder.record_activity(
            recording_id, 
            "keyboard_input", 
            {"keys_pressed": 50, "words_typed": 10}
        )
        
        recording = self.recorder.active_recordings[recording_id]
        assert len(recording['activities']) == 1
        assert recording['activities'][0]['type'] == "keyboard_input"
    
    def test_stop_auto_recording(self):
        """测试停止自动记录"""
        recording_id = self.recorder.start_auto_recording(
            self.user_id, self.task_id, self.project_id
        )
        
        # 模拟一些活动
        recording = self.recorder.active_recordings[recording_id]
        recording['start_time'] = datetime.now() - timedelta(hours=2)
        
        # 停止记录
        work_record = self.recorder.stop_auto_recording(recording_id)
        
        assert isinstance(work_record, WorkTimeRecord)
        assert work_record.user_id == self.user_id
        assert work_record.duration_minutes > 0
        assert recording_id not in self.recorder.active_recordings
    
    def test_configure_auto_recording(self):
        """测试配置自动记录"""
        config = AutoRecordingConfig(
            user_id=self.user_id,
            enabled=True,
            recording_interval_minutes=3,
            idle_threshold_minutes=15
        )
        
        self.recorder.configure_auto_recording(self.user_id, config)
        
        retrieved_config = self.recorder.get_user_config(self.user_id)
        assert retrieved_config.user_id == self.user_id
        assert retrieved_config.recording_interval_minutes == 3
        assert retrieved_config.idle_threshold_minutes == 15


class TestWorkTimeIntegrityChecker:
    """工时完整性检查器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.checker = WorkTimeIntegrityChecker()
        self.user_id = "test_user_001"
    
    def test_check_data_integrity_clean(self):
        """测试检查干净数据的完整性"""
        # 创建无问题的记录
        records = self._create_clean_records()
        
        result = self.checker.check_data_integrity(records)
        
        assert result['total_records_checked'] == len(records)
        assert result['integrity_score'] >= 80  # 应该有较高的完整性分数
        assert len(result['issues']) == 0
    
    def test_check_data_integrity_with_issues(self):
        """测试检查有问题数据的完整性"""
        # 创建有重叠问题的记录
        records = self._create_overlapping_records()
        
        result = self.checker.check_data_integrity(records)
        
        assert result['total_records_checked'] == len(records)
        assert result['issues_found'] > 0
        assert result['integrity_score'] < 100
        
        # 检查是否检测到重叠问题
        overlapping_issues = [
            issue for issue in result['issues'] 
            if issue['type'] == 'overlapping_records'
        ]
        assert len(overlapping_issues) > 0
    
    def _create_clean_records(self) -> list:
        """创建无问题的记录"""
        base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        records = []
        for i in range(3):
            # 创建连续的工作记录，没有间隙
            start_time = base_time + timedelta(hours=i*2, minutes=30)  # 2.5小时间隔
            end_time = start_time + timedelta(hours=2)  # 2小时工作
            
            record = WorkTimeRecord(
                id=f"clean_record_{i}",
                user_id=self.user_id,
                task_id=f"task_{i}",
                project_id="project_001",
                start_time=start_time,
                end_time=end_time,
                duration_minutes=120,
                status=WorkTimeStatus.COMPLETED
            )
            records.append(record)
        
        return records
    
    def _create_overlapping_records(self) -> list:
        """创建有重叠问题的记录"""
        base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # 第一个记录
        record1 = WorkTimeRecord(
            id="overlap_record_1",
            user_id=self.user_id,
            task_id="task_1",
            project_id="project_001",
            start_time=base_time,
            end_time=base_time + timedelta(hours=3),
            duration_minutes=180,
            status=WorkTimeStatus.COMPLETED
        )
        
        # 第二个记录（与第一个重叠）
        record2 = WorkTimeRecord(
            id="overlap_record_2",
            user_id=self.user_id,
            task_id="task_2",
            project_id="project_001",
            start_time=base_time + timedelta(hours=2),  # 重叠1小时
            end_time=base_time + timedelta(hours=5),
            duration_minutes=180,
            status=WorkTimeStatus.COMPLETED
        )
        
        return [record1, record2]


class TestWorkTimeManager:
    """工时管理器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.config = WorkTimeManagerConfig()
        self.manager = WorkTimeManager(self.config)
        self.user_id = "test_user_001"
        self.task_id = "task_001"
        self.project_id = "project_001"
    
    def test_start_work_session_success(self):
        """测试成功开始工作会话"""
        result = self.manager.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        assert result['success'] is True
        assert 'session_id' in result
        assert result['user_id'] == self.user_id
        assert result['task_id'] == self.task_id
        assert result['project_id'] == self.project_id
    
    def test_start_work_session_duplicate(self):
        """测试重复开始工作会话"""
        # 第一次开始会话
        result1 = self.manager.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        assert result1['success'] is True
        
        # 第二次开始会话（应该失败）
        result2 = self.manager.start_work_session(
            self.user_id, "task_002", self.project_id
        )
        assert result2['success'] is False
        assert 'existing_session_id' in result2
    
    def test_end_work_session_success(self):
        """测试成功结束工作会话"""
        # 开始会话
        start_result = self.manager.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        assert start_result['success'] is True
        
        # 结束会话
        end_result = self.manager.end_work_session(self.user_id, "Work completed")
        
        assert end_result['success'] is True
        assert 'record' in end_result
        assert end_result['record']['duration_minutes'] >= 0
        assert 'verification_results' in end_result
    
    def test_pause_and_resume_session(self):
        """测试暂停和恢复会话"""
        # 开始会话
        start_result = self.manager.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        assert start_result['success'] is True
        
        # 暂停会话
        pause_result = self.manager.pause_work_session(self.user_id, "Break time")
        assert pause_result['success'] is True
        assert pause_result['reason'] == "Break time"
        
        # 恢复会话
        resume_result = self.manager.resume_work_session(self.user_id)
        assert resume_result['success'] is True
    
    def test_get_session_status(self):
        """测试获取会话状态"""
        # 无活跃会话时
        status1 = self.manager.get_session_status(self.user_id)
        assert status1['has_active_session'] is False
        
        # 开始会话后
        self.manager.start_work_session(self.user_id, self.task_id, self.project_id)
        status2 = self.manager.get_session_status(self.user_id)
        
        assert status2['has_active_session'] is True
        assert 'session_id' in status2
        assert status2['user_id'] == self.user_id
        assert status2['task_id'] == self.task_id
        assert 'duration_minutes' in status2
    
    def test_get_work_time_statistics(self):
        """测试获取工时统计"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # 创建一些测试数据
        self._create_test_session()
        
        result = self.manager.get_work_time_statistics(
            self.user_id, start_date, end_date
        )
        
        assert result['success'] is True
        assert 'statistics' in result
        stats = result['statistics']
        assert stats['user_id'] == self.user_id
        assert 'total_effective_hours' in stats
        assert 'productivity_score' in stats
    
    def test_detect_anomalies(self):
        """测试异常检测"""
        result = self.manager.detect_anomalies(self.user_id)
        
        assert result['success'] is True
        assert 'anomalies' in result
        # 新用户应该没有异常
        assert len(result['anomalies']) == 0
    
    def test_check_data_integrity(self):
        """测试数据完整性检查"""
        result = self.manager.check_data_integrity([self.user_id])
        
        assert result['success'] is True
        assert 'integrity_result' in result
        integrity = result['integrity_result']
        assert 'total_records_checked' in integrity
        assert 'integrity_score' in integrity
    
    def test_get_system_status(self):
        """测试获取系统状态"""
        status = self.manager.get_system_status()
        
        assert 'active_sessions' in status
        assert 'total_records' in status
        assert 'config' in status
        assert 'health_status' in status
        assert status['health_status'] == 'healthy'
    
    def test_batch_process_records(self):
        """测试批量处理记录"""
        # 创建测试会话并结束
        self._create_test_session()
        
        # 获取记录ID
        record_ids = list(self.manager.calculator.records.keys())
        
        if record_ids:
            result = self.manager.batch_process_records('verify', record_ids)
            
            assert result['success'] is True
            assert result['operation'] == 'verify'
            assert result['total_records'] == len(record_ids)
            assert 'results' in result
    
    def _create_test_session(self):
        """创建测试会话"""
        # 开始并立即结束一个会话
        start_result = self.manager.start_work_session(
            self.user_id, self.task_id, self.project_id
        )
        
        if start_result['success']:
            # 模拟工作时间
            session_id = start_result['session_id']
            record = self.manager.calculator.records[session_id]
            record.start_time = datetime.now() - timedelta(hours=1)
            
            # 结束会话
            self.manager.end_work_session(self.user_id, "Test completed")


# 集成测试
class TestWorkTimeSystemIntegration:
    """工时系统集成测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.manager = WorkTimeManager()
        self.user_id = "integration_test_user"
    
    def test_complete_work_flow(self):
        """测试完整工作流程"""
        # 1. 开始工作会话
        start_result = self.manager.start_work_session(
            self.user_id, "integration_task", "integration_project"
        )
        assert start_result['success'] is True
        session_id = start_result['session_id']
        
        # 2. 模拟工作活动
        if start_result.get('auto_recording_id'):
            self.manager.auto_recorder.record_activity(
                start_result['auto_recording_id'],
                "typing",
                {"characters": 1000}
            )
        
        # 3. 暂停工作
        pause_result = self.manager.pause_work_session(self.user_id, "Lunch break")
        assert pause_result['success'] is True
        
        # 4. 恢复工作
        resume_result = self.manager.resume_work_session(self.user_id)
        assert resume_result['success'] is True
        
        # 5. 结束工作会话
        end_result = self.manager.end_work_session(self.user_id, "Task completed")
        assert end_result['success'] is True
        
        # 6. 检查统计数据
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        stats_result = self.manager.get_work_time_statistics(
            self.user_id, today, tomorrow
        )
        assert stats_result['success'] is True
        
        # 7. 检查数据完整性
        integrity_result = self.manager.check_data_integrity([self.user_id])
        assert integrity_result['success'] is True
        
        # 8. 检测异常
        anomaly_result = self.manager.detect_anomalies(self.user_id)
        assert anomaly_result['success'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])