"""
工时管理 API 接口

提供工时计算、验证和报表功能的 REST API 接口
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError
import logging

from ..quality_billing.work_time_manager import (
    WorkTimeManager, WorkTimeManagerConfig
)
from ..quality_billing.work_time_calculator import WorkTimeType
from ..quality_billing.work_time_verifier import AutoRecordingConfig
from ..quality_billing.work_time_reporter import (
    ReportConfig, ReportType, ReportFormat, AggregationLevel
)
from ..quality_billing.work_time_quality_analyzer import (
    EfficiencyLevel, QualityTrend, PredictionAccuracy
)

logger = logging.getLogger(__name__)

# 创建蓝图
work_time_bp = Blueprint('work_time', __name__, url_prefix='/api/work-time')

# 全局工时管理器实例
work_time_manager = WorkTimeManager()


# 请求验证模式
class StartSessionSchema(Schema):
    """开始工作会话请求模式"""
    user_id = fields.Str(required=True)
    task_id = fields.Str(required=True)
    project_id = fields.Str(required=True)
    work_type = fields.Str(missing='effective')
    description = fields.Str(missing='')
    auto_record = fields.Bool(missing=None)


class EndSessionSchema(Schema):
    """结束工作会话请求模式"""
    user_id = fields.Str(required=True)
    description = fields.Str(missing='')


class PauseResumeSessionSchema(Schema):
    """暂停/恢复工作会话请求模式"""
    user_id = fields.Str(required=True)
    reason = fields.Str(missing='')


class StatisticsQuerySchema(Schema):
    """工时统计查询请求模式"""
    user_id = fields.Str(required=True)
    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(required=True)


class ReportGenerationSchema(Schema):
    """报表生成请求模式"""
    report_type = fields.Str(required=True)
    format = fields.Str(missing='json')
    aggregation_level = fields.Str(missing='user')
    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(required=True)
    entity_ids = fields.List(fields.Str(), missing=None)
    include_charts = fields.Bool(missing=True)
    include_trends = fields.Bool(missing=True)
    include_comparisons = fields.Bool(missing=True)


class AutoRecordingConfigSchema(Schema):
    """自动记录配置请求模式"""
    user_id = fields.Str(required=True)
    enabled = fields.Bool(missing=True)
    recording_interval_minutes = fields.Int(missing=5)
    idle_threshold_minutes = fields.Int(missing=10)
    auto_pause_enabled = fields.Bool(missing=True)
    auto_resume_enabled = fields.Bool(missing=True)
    activity_tracking = fields.Bool(missing=True)


# 工作会话管理接口

@work_time_bp.route('/sessions/start', methods=['POST'])
def start_work_session():
    """开始工作会话"""
    try:
        schema = StartSessionSchema()
        data = schema.load(request.json)
        
        # 转换工时类型
        work_type = WorkTimeType(data['work_type'])
        
        result = work_time_manager.start_work_session(
            user_id=data['user_id'],
            task_id=data['task_id'],
            project_id=data['project_id'],
            work_type=work_type,
            description=data['description'],
            auto_record=data['auto_record']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Work session started successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to start work session'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error starting work session: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/sessions/end', methods=['POST'])
def end_work_session():
    """结束工作会话"""
    try:
        schema = EndSessionSchema()
        data = schema.load(request.json)
        
        result = work_time_manager.end_work_session(
            user_id=data['user_id'],
            description=data['description']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Work session ended successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to end work session'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error ending work session: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/sessions/pause', methods=['POST'])
def pause_work_session():
    """暂停工作会话"""
    try:
        schema = PauseResumeSessionSchema()
        data = schema.load(request.json)
        
        result = work_time_manager.pause_work_session(
            user_id=data['user_id'],
            reason=data['reason']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Work session paused successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to pause work session'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error pausing work session: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/sessions/resume', methods=['POST'])
def resume_work_session():
    """恢复工作会话"""
    try:
        schema = PauseResumeSessionSchema()
        data = schema.load(request.json)
        
        result = work_time_manager.resume_work_session(data['user_id'])
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Work session resumed successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to resume work session'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error resuming work session: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/sessions/status/<user_id>', methods=['GET'])
def get_session_status(user_id: str):
    """获取工作会话状态"""
    try:
        result = work_time_manager.get_session_status(user_id)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Session status retrieved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# 工时统计和分析接口

@work_time_bp.route('/statistics', methods=['POST'])
def get_work_time_statistics():
    """获取工时统计"""
    try:
        schema = StatisticsQuerySchema()
        data = schema.load(request.json)
        
        result = work_time_manager.get_work_time_statistics(
            user_id=data['user_id'],
            start_date=data['start_date'],
            end_date=data['end_date']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['statistics'],
                'message': 'Statistics retrieved successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to retrieve statistics'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/reports/detailed', methods=['POST'])
def get_detailed_report():
    """获取详细工时报表"""
    try:
        schema = StatisticsQuerySchema()
        data = schema.load(request.json)
        
        result = work_time_manager.get_detailed_report(
            user_id=data['user_id'],
            start_date=data['start_date'],
            end_date=data['end_date']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['report'],
                'message': 'Detailed report retrieved successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to retrieve detailed report'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error getting detailed report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/reports/custom', methods=['POST'])
def generate_custom_report():
    """生成自定义报表"""
    try:
        schema = ReportGenerationSchema()
        data = schema.load(request.json)
        
        # 创建报表配置
        config = ReportConfig(
            report_type=ReportType(data['report_type']),
            format=ReportFormat(data['format']),
            aggregation_level=AggregationLevel(data['aggregation_level']),
            include_charts=data['include_charts'],
            include_trends=data['include_trends'],
            include_comparisons=data['include_comparisons']
        )
        
        result = work_time_manager.generate_custom_report(
            config=config,
            start_date=data['start_date'],
            end_date=data['end_date'],
            entity_ids=data['entity_ids']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['report'],
                'message': 'Custom report generated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to generate custom report'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error generating custom report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/reports/export', methods=['POST'])
def export_report():
    """导出报表"""
    try:
        data = request.json
        report = data.get('report')
        format_type = data.get('format', 'json')
        filename = data.get('filename')
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report data is required'
            }), 400
        
        result = work_time_manager.export_report(
            report=report,
            format=ReportFormat(format_type),
            filename=filename
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'format': result['format'],
                    'size_bytes': result['size_bytes']
                },
                'message': 'Report exported successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to export report'
            }), 400
            
    except Exception as e:
        logger.error(f"Error exporting report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# 异常检测和处理接口

@work_time_bp.route('/anomalies/detect', methods=['POST'])
def detect_anomalies():
    """检测工时异常"""
    try:
        data = request.json
        user_id = data.get('user_id')
        date_str = data.get('date')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        date = datetime.fromisoformat(date_str) if date_str else None
        
        result = work_time_manager.detect_anomalies(user_id, date)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['anomalies'],
                'message': 'Anomalies detected successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to detect anomalies'
            }), 400
            
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/anomalies/correct', methods=['POST'])
def auto_correct_anomalies():
    """自动纠正异常"""
    try:
        data = request.json
        anomaly_ids = data.get('anomaly_ids', [])
        
        if not anomaly_ids:
            return jsonify({
                'success': False,
                'error': 'anomaly_ids is required'
            }), 400
        
        result = work_time_manager.auto_correct_anomalies(anomaly_ids)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Anomalies corrected successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to correct anomalies'
            }), 400
            
    except Exception as e:
        logger.error(f"Error correcting anomalies: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# 数据完整性检查接口

@work_time_bp.route('/integrity/check', methods=['POST'])
def check_data_integrity():
    """检查数据完整性"""
    try:
        data = request.json
        user_ids = data.get('user_ids')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
        
        result = work_time_manager.check_data_integrity(
            user_ids=user_ids,
            start_date=start_date,
            end_date=end_date
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['integrity_result'],
                'message': 'Data integrity checked successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to check data integrity'
            }), 400
            
    except Exception as e:
        logger.error(f"Error checking data integrity: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# 配置管理接口

@work_time_bp.route('/config/auto-recording', methods=['POST'])
def configure_auto_recording():
    """配置自动记录"""
    try:
        schema = AutoRecordingConfigSchema()
        data = schema.load(request.json)
        
        config = AutoRecordingConfig(
            user_id=data['user_id'],
            enabled=data['enabled'],
            recording_interval_minutes=data['recording_interval_minutes'],
            idle_threshold_minutes=data['idle_threshold_minutes'],
            auto_pause_enabled=data['auto_pause_enabled'],
            auto_resume_enabled=data['auto_resume_enabled'],
            activity_tracking=data['activity_tracking']
        )
        
        result = work_time_manager.configure_auto_recording(data['user_id'], config)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to configure auto recording'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error configuring auto recording: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/config/auto-recording/<user_id>', methods=['GET'])
def get_user_config(user_id: str):
    """获取用户配置"""
    try:
        result = work_time_manager.get_user_config(user_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['config'],
                'message': 'User config retrieved successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to retrieve user config'
            }), 400
            
    except Exception as e:
        logger.error(f"Error getting user config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


class PredictionSchema(Schema):
    """工时质量预测请求模式"""
    user_id = fields.Str(required=True)
    task_type = fields.Str(required=True)
    task_complexity = fields.Float(required=True, validate=lambda x: 0 <= x <= 1)
    historical_window_days = fields.Int(missing=90)


class BenchmarkConfigSchema(Schema):
    """基准配置请求模式"""
    task_type = fields.Str(required=True)
    project_type = fields.Str(required=True)
    skill_level = fields.Str(required=True)
    sample_data = fields.List(fields.Dict(), required=True)


class EfficiencyPlanningSchema(Schema):
    """效率规划请求模式"""
    team_ids = fields.List(fields.Str(), required=True)
    project_id = fields.Str(required=True)
    planning_horizon_weeks = fields.Int(missing=4)


# 工时质量关联分析接口

@work_time_bp.route('/quality/correlation', methods=['POST'])
def analyze_quality_correlation():
    """分析工时与质量分数的关联性"""
    try:
        schema = StatisticsQuerySchema()
        data = schema.load(request.json)
        
        result = work_time_manager.analyze_work_time_quality_correlation(
            user_id=data['user_id'],
            start_date=data['start_date'],
            end_date=data['end_date']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Quality correlation analysis completed successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to analyze quality correlation'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error analyzing quality correlation: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/efficiency/assessment', methods=['POST'])
def assess_efficiency():
    """评估效率并提供优化建议"""
    try:
        data = request.json
        user_id = data.get('user_id')
        task_type = data.get('task_type')
        project_id = data.get('project_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        result = work_time_manager.assess_efficiency_and_optimization(
            user_id=user_id,
            task_type=task_type,
            project_id=project_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Efficiency assessment completed successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to assess efficiency'
            }), 400
            
    except Exception as e:
        logger.error(f"Error assessing efficiency: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/benchmarks/configure', methods=['POST'])
def configure_benchmarks():
    """配置工时基准和标准"""
    try:
        schema = BenchmarkConfigSchema()
        data = schema.load(request.json)
        
        result = work_time_manager.configure_work_time_benchmarks(
            task_type=data['task_type'],
            project_type=data['project_type'],
            skill_level=data['skill_level'],
            sample_data=data['sample_data']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Benchmarks configured successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to configure benchmarks'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error configuring benchmarks: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/prediction/work-time-quality', methods=['POST'])
def predict_work_time_quality():
    """预测工时和质量"""
    try:
        schema = PredictionSchema()
        data = schema.load(request.json)
        
        result = work_time_manager.predict_work_time_and_quality(
            user_id=data['user_id'],
            task_type=data['task_type'],
            task_complexity=data['task_complexity'],
            historical_window_days=data['historical_window_days']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Work time and quality prediction completed successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to predict work time and quality'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error predicting work time and quality: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/planning/efficiency-report', methods=['POST'])
def generate_efficiency_planning():
    """生成效率规划报告"""
    try:
        schema = EfficiencyPlanningSchema()
        data = schema.load(request.json)
        
        result = work_time_manager.generate_efficiency_planning_report(
            team_ids=data['team_ids'],
            project_id=data['project_id'],
            planning_horizon_weeks=data['planning_horizon_weeks']
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Efficiency planning report generated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to generate efficiency planning report'
            }), 400
            
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error generating efficiency planning report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# 系统状态和管理接口

@work_time_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        status = work_time_manager.get_system_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'message': 'System status retrieved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/system/cleanup', methods=['POST'])
def cleanup_old_data():
    """清理旧数据"""
    try:
        data = request.json
        days_to_keep = data.get('days_to_keep', 90)
        
        result = work_time_manager.cleanup_old_data(days_to_keep)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Old data cleaned up successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to cleanup old data'
            }), 400
            
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@work_time_bp.route('/batch/process', methods=['POST'])
def batch_process_records():
    """批量处理记录"""
    try:
        data = request.json
        operation = data.get('operation')
        record_ids = data.get('record_ids', [])
        parameters = data.get('parameters', {})
        
        if not operation or not record_ids:
            return jsonify({
                'success': False,
                'error': 'operation and record_ids are required'
            }), 400
        
        result = work_time_manager.batch_process_records(
            operation=operation,
            record_ids=record_ids,
            parameters=parameters
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Batch processing completed successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'Failed to process records'
            }), 400
            
    except Exception as e:
        logger.error(f"Error batch processing records: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# 错误处理

@work_time_bp.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist'
    }), 404


@work_time_bp.errorhandler(405)
def method_not_allowed(error):
    """405 错误处理"""
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'message': 'The HTTP method is not allowed for this endpoint'
    }), 405


@work_time_bp.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500