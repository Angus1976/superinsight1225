"""
工时统计报表和分析模块

实现工时数据的统计分析、报表生成和可视化功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
from collections import defaultdict
import statistics
import pandas as pd
from io import BytesIO

from .work_time_calculator import WorkTimeRecord, WorkTimeStatistics, WorkTimeType, WorkTimeStatus

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """报表类型枚举"""
    DAILY = "daily"  # 日报
    WEEKLY = "weekly"  # 周报
    MONTHLY = "monthly"  # 月报
    QUARTERLY = "quarterly"  # 季报
    YEARLY = "yearly"  # 年报
    CUSTOM = "custom"  # 自定义


class ReportFormat(str, Enum):
    """报表格式枚举"""
    JSON = "json"
    EXCEL = "excel"
    PDF = "pdf"
    CSV = "csv"
    HTML = "html"


class AggregationLevel(str, Enum):
    """聚合级别枚举"""
    USER = "user"  # 用户级别
    TEAM = "team"  # 团队级别
    PROJECT = "project"  # 项目级别
    DEPARTMENT = "department"  # 部门级别
    ORGANIZATION = "organization"  # 组织级别


@dataclass
class ReportConfig:
    """报表配置"""
    report_type: ReportType
    format: ReportFormat
    aggregation_level: AggregationLevel
    include_charts: bool = True
    include_trends: bool = True
    include_comparisons: bool = True
    include_recommendations: bool = True
    filters: Dict[str, Any] = field(default_factory=dict)
    custom_metrics: List[str] = field(default_factory=list)


@dataclass
class WorkTimeMetrics:
    """工时指标"""
    total_hours: float
    effective_hours: float
    overtime_hours: float
    pause_hours: float
    productivity_score: float
    efficiency_ratio: float
    quality_score: float
    task_completion_rate: float
    average_session_duration: float
    peak_productivity_hours: List[int]


@dataclass
class TrendAnalysis:
    """趋势分析"""
    metric_name: str
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-1
    change_percentage: float
    seasonal_patterns: Dict[str, float]
    anomaly_periods: List[Dict[str, Any]]
    forecast_values: List[float]


class WorkTimeReporter:
    """工时报表生成器"""
    
    def __init__(self):
        self.report_cache: Dict[str, Dict[str, Any]] = {}
        self.baseline_metrics: Dict[str, WorkTimeMetrics] = {}
        
    def generate_report(self, config: ReportConfig, start_date: datetime, 
                       end_date: datetime, entity_ids: List[str] = None) -> Dict[str, Any]:
        """生成工时报表"""
        # 生成缓存键
        cache_key = self._generate_cache_key(config, start_date, end_date, entity_ids)
        
        # 检查缓存
        if cache_key in self.report_cache:
            cached_report = self.report_cache[cache_key]
            if self._is_cache_valid(cached_report):
                return cached_report
        
        # 获取数据
        raw_data = self._fetch_work_time_data(start_date, end_date, entity_ids, config.filters)
        
        # 生成报表
        report = {
            'metadata': {
                'report_type': config.report_type.value,
                'aggregation_level': config.aggregation_level.value,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'generated_at': datetime.now().isoformat(),
                'entity_count': len(entity_ids) if entity_ids else 0,
                'record_count': len(raw_data)
            },
            'summary': self._generate_summary_metrics(raw_data, config),
            'detailed_metrics': self._generate_detailed_metrics(raw_data, config),
            'trends': self._generate_trend_analysis(raw_data, config) if config.include_trends else None,
            'comparisons': self._generate_comparisons(raw_data, config) if config.include_comparisons else None,
            'charts': self._generate_chart_data(raw_data, config) if config.include_charts else None,
            'recommendations': self._generate_recommendations(raw_data, config) if config.include_recommendations else None
        }
        
        # 缓存报表
        self.report_cache[cache_key] = report
        
        return report
    
    def _fetch_work_time_data(self, start_date: datetime, end_date: datetime, 
                             entity_ids: List[str], filters: Dict[str, Any]) -> List[WorkTimeRecord]:
        """获取工时数据（模拟）"""
        # 这里应该从数据库获取实际数据
        # 暂时返回模拟数据
        records = []
        
        if not entity_ids:
            entity_ids = ["user1", "user2", "user3"]
        
        current_date = start_date
        while current_date <= end_date:
            for user_id in entity_ids:
                # 生成模拟工时记录
                if current_date.weekday() < 5:  # 工作日
                    start_time = current_date.replace(hour=9, minute=0)
                    end_time = start_time + timedelta(hours=8)
                    
                    record = WorkTimeRecord(
                        id=f"{user_id}_{current_date.strftime('%Y%m%d')}",
                        user_id=user_id,
                        task_id=f"task_{current_date.day}",
                        project_id="project1",
                        start_time=start_time,
                        end_time=end_time,
                        work_type=WorkTimeType.EFFECTIVE,
                        status=WorkTimeStatus.COMPLETED,
                        duration_minutes=480,  # 8小时
                        pause_duration_minutes=60,  # 1小时休息
                        description="Daily work session"
                    )
                    records.append(record)
            
            current_date += timedelta(days=1)
        
        return records
    
    def _generate_summary_metrics(self, records: List[WorkTimeRecord], config: ReportConfig) -> Dict[str, Any]:
        """生成汇总指标"""
        if not records:
            return {}
        
        total_duration = sum(r.duration_minutes for r in records)
        total_pause = sum(r.pause_duration_minutes for r in records)
        effective_duration = total_duration - total_pause
        
        # 按用户分组统计
        user_stats = defaultdict(lambda: {'duration': 0, 'pause': 0, 'sessions': 0})
        for record in records:
            user_stats[record.user_id]['duration'] += record.duration_minutes
            user_stats[record.user_id]['pause'] += record.pause_duration_minutes
            user_stats[record.user_id]['sessions'] += 1
        
        # 按项目分组统计
        project_stats = defaultdict(lambda: {'duration': 0, 'users': set()})
        for record in records:
            project_stats[record.project_id]['duration'] += record.duration_minutes
            project_stats[record.project_id]['users'].add(record.user_id)
        
        return {
            'total_hours': total_duration / 60.0,
            'effective_hours': effective_duration / 60.0,
            'pause_hours': total_pause / 60.0,
            'average_daily_hours': (total_duration / 60.0) / len(set(r.start_time.date() for r in records)),
            'total_sessions': len(records),
            'unique_users': len(user_stats),
            'unique_projects': len(project_stats),
            'efficiency_ratio': effective_duration / total_duration if total_duration > 0 else 0,
            'user_statistics': {
                user_id: {
                    'total_hours': stats['duration'] / 60.0,
                    'pause_hours': stats['pause'] / 60.0,
                    'sessions': stats['sessions'],
                    'avg_session_hours': (stats['duration'] / 60.0) / stats['sessions'] if stats['sessions'] > 0 else 0
                }
                for user_id, stats in user_stats.items()
            },
            'project_statistics': {
                project_id: {
                    'total_hours': stats['duration'] / 60.0,
                    'user_count': len(stats['users']),
                    'avg_hours_per_user': (stats['duration'] / 60.0) / len(stats['users']) if stats['users'] else 0
                }
                for project_id, stats in project_stats.items()
            }
        }
    
    def _generate_detailed_metrics(self, records: List[WorkTimeRecord], config: ReportConfig) -> Dict[str, Any]:
        """生成详细指标"""
        if not records:
            return {}
        
        # 按时间维度分析
        hourly_distribution = defaultdict(int)
        daily_totals = defaultdict(int)
        weekly_totals = defaultdict(int)
        
        for record in records:
            # 小时分布
            hourly_distribution[record.start_time.hour] += record.duration_minutes
            
            # 日总计
            date_key = record.start_time.date().isoformat()
            daily_totals[date_key] += record.duration_minutes
            
            # 周总计
            week_key = record.start_time.strftime('%Y-W%U')
            weekly_totals[week_key] += record.duration_minutes
        
        # 计算工作模式
        work_patterns = self._analyze_work_patterns(records)
        
        # 计算生产力指标
        productivity_metrics = self._calculate_productivity_metrics(records)
        
        return {
            'time_distribution': {
                'hourly': {str(hour): minutes / 60.0 for hour, minutes in hourly_distribution.items()},
                'daily': {date: minutes / 60.0 for date, minutes in daily_totals.items()},
                'weekly': {week: minutes / 60.0 for week, minutes in weekly_totals.items()}
            },
            'work_patterns': work_patterns,
            'productivity_metrics': productivity_metrics,
            'quality_metrics': self._calculate_quality_metrics(records),
            'efficiency_metrics': self._calculate_efficiency_metrics(records)
        }
    
    def _analyze_work_patterns(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """分析工作模式"""
        if not records:
            return {}
        
        # 分析开始时间模式
        start_hours = [r.start_time.hour for r in records]
        avg_start_hour = statistics.mean(start_hours)
        start_hour_std = statistics.stdev(start_hours) if len(start_hours) > 1 else 0
        
        # 分析工作时长模式
        durations = [r.duration_minutes for r in records]
        avg_duration = statistics.mean(durations)
        duration_std = statistics.stdev(durations) if len(durations) > 1 else 0
        
        # 分析工作日模式
        weekday_hours = defaultdict(int)
        for record in records:
            weekday_hours[record.start_time.weekday()] += record.duration_minutes
        
        # 识别高峰工作时间
        hourly_activity = defaultdict(int)
        for record in records:
            for hour in range(record.start_time.hour, 
                            (record.end_time or record.start_time).hour + 1):
                hourly_activity[hour] += 1
        
        peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'average_start_hour': avg_start_hour,
            'start_time_consistency': max(0, 1 - start_hour_std / 12),  # 标准化一致性分数
            'average_session_duration_hours': avg_duration / 60.0,
            'duration_consistency': max(0, 1 - duration_std / avg_duration) if avg_duration > 0 else 0,
            'weekday_distribution': {
                str(day): hours / 60.0 for day, hours in weekday_hours.items()
            },
            'peak_activity_hours': [hour for hour, _ in peak_hours],
            'work_regularity_score': self._calculate_regularity_score(records)
        }
    
    def _calculate_productivity_metrics(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """计算生产力指标"""
        if not records:
            return {}
        
        total_hours = sum(r.duration_minutes for r in records) / 60.0
        total_pause_hours = sum(r.pause_duration_minutes for r in records) / 60.0
        
        # 计算任务完成率（模拟）
        completed_tasks = len(set(r.task_id for r in records))
        task_completion_rate = completed_tasks / len(records) if records else 0
        
        # 计算效率比率
        efficiency_ratio = (total_hours - total_pause_hours) / total_hours if total_hours > 0 else 0
        
        # 计算平均会话生产力
        avg_session_productivity = total_hours / len(records) if records else 0
        
        return {
            'total_productive_hours': total_hours - total_pause_hours,
            'productivity_rate': efficiency_ratio,
            'task_completion_rate': task_completion_rate,
            'average_session_productivity': avg_session_productivity,
            'focus_time_ratio': efficiency_ratio,
            'multitasking_index': self._calculate_multitasking_index(records)
        }
    
    def _calculate_quality_metrics(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """计算质量指标"""
        # 这里应该集成质量评估系统的数据
        # 暂时返回模拟数据
        return {
            'average_quality_score': 85.0,
            'quality_trend': 'improving',
            'quality_consistency': 0.8,
            'defect_rate': 0.05,
            'rework_rate': 0.03
        }
    
    def _calculate_efficiency_metrics(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """计算效率指标"""
        if not records:
            return {}
        
        # 计算时间利用率
        total_scheduled_time = len(records) * 8 * 60  # 假设每天8小时
        total_actual_time = sum(r.duration_minutes for r in records)
        time_utilization = total_actual_time / total_scheduled_time if total_scheduled_time > 0 else 0
        
        # 计算平均处理时间
        avg_processing_time = statistics.mean([r.duration_minutes for r in records])
        
        return {
            'time_utilization_rate': time_utilization,
            'average_processing_time_hours': avg_processing_time / 60.0,
            'throughput_rate': len(records) / (total_actual_time / 60.0) if total_actual_time > 0 else 0,
            'efficiency_score': min(100, time_utilization * 100)
        }
    
    def _calculate_regularity_score(self, records: List[WorkTimeRecord]) -> float:
        """计算工作规律性评分"""
        if len(records) < 2:
            return 1.0
        
        # 分析开始时间的规律性
        start_hours = [r.start_time.hour for r in records]
        start_regularity = 1.0 - (statistics.stdev(start_hours) / 12) if len(start_hours) > 1 else 1.0
        
        # 分析工作时长的规律性
        durations = [r.duration_minutes for r in records]
        avg_duration = statistics.mean(durations)
        duration_regularity = 1.0 - (statistics.stdev(durations) / avg_duration) if avg_duration > 0 else 1.0
        
        return (start_regularity + duration_regularity) / 2
    
    def _calculate_multitasking_index(self, records: List[WorkTimeRecord]) -> float:
        """计算多任务处理指数"""
        if not records:
            return 0.0
        
        # 统计同一时间段内的任务数量
        task_switches = 0
        prev_task = None
        
        for record in sorted(records, key=lambda r: r.start_time):
            if prev_task and prev_task != record.task_id:
                task_switches += 1
            prev_task = record.task_id
        
        return task_switches / len(records) if records else 0.0
    
    def _generate_trend_analysis(self, records: List[WorkTimeRecord], config: ReportConfig) -> Dict[str, Any]:
        """生成趋势分析"""
        if len(records) < 7:  # 需要至少一周的数据
            return {'insufficient_data': True}
        
        # 按日期分组
        daily_metrics = defaultdict(lambda: {'hours': 0, 'sessions': 0, 'quality': 0})
        
        for record in records:
            date_key = record.start_time.date().isoformat()
            daily_metrics[date_key]['hours'] += record.duration_minutes / 60.0
            daily_metrics[date_key]['sessions'] += 1
        
        # 计算趋势
        dates = sorted(daily_metrics.keys())
        hours_series = [daily_metrics[date]['hours'] for date in dates]
        
        # 简单的线性趋势计算
        if len(hours_series) > 1:
            x_values = list(range(len(hours_series)))
            slope = statistics.correlation(x_values, hours_series) if len(hours_series) > 2 else 0
            
            trend_direction = 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable'
            trend_strength = abs(slope)
        else:
            trend_direction = 'stable'
            trend_strength = 0
        
        return {
            'hours_trend': {
                'direction': trend_direction,
                'strength': trend_strength,
                'daily_values': hours_series
            },
            'productivity_trend': self._analyze_productivity_trend(records),
            'quality_trend': self._analyze_quality_trend(records)
        }
    
    def _analyze_productivity_trend(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """分析生产力趋势"""
        # 简化的生产力趋势分析
        return {
            'direction': 'stable',
            'strength': 0.5,
            'change_percentage': 0.0
        }
    
    def _analyze_quality_trend(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """分析质量趋势"""
        # 简化的质量趋势分析
        return {
            'direction': 'improving',
            'strength': 0.3,
            'change_percentage': 5.0
        }
    
    def _generate_comparisons(self, records: List[WorkTimeRecord], config: ReportConfig) -> Dict[str, Any]:
        """生成对比分析"""
        # 与历史同期对比
        historical_comparison = self._compare_with_historical_data(records)
        
        # 用户间对比
        user_comparison = self._compare_users(records)
        
        # 项目间对比
        project_comparison = self._compare_projects(records)
        
        return {
            'historical': historical_comparison,
            'users': user_comparison,
            'projects': project_comparison
        }
    
    def _compare_with_historical_data(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """与历史数据对比"""
        # 这里应该获取历史同期数据进行对比
        # 暂时返回模拟对比结果
        return {
            'current_period_hours': sum(r.duration_minutes for r in records) / 60.0,
            'previous_period_hours': 800.0,  # 模拟历史数据
            'change_percentage': 5.0,
            'trend': 'improving'
        }
    
    def _compare_users(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """用户间对比"""
        user_stats = defaultdict(lambda: {'hours': 0, 'sessions': 0})
        
        for record in records:
            user_stats[record.user_id]['hours'] += record.duration_minutes / 60.0
            user_stats[record.user_id]['sessions'] += 1
        
        # 排序用户
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['hours'], reverse=True)
        
        return {
            'top_performers': sorted_users[:3],
            'average_hours': statistics.mean([stats['hours'] for stats in user_stats.values()]),
            'performance_distribution': dict(user_stats)
        }
    
    def _compare_projects(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """项目间对比"""
        project_stats = defaultdict(lambda: {'hours': 0, 'users': set()})
        
        for record in records:
            project_stats[record.project_id]['hours'] += record.duration_minutes / 60.0
            project_stats[record.project_id]['users'].add(record.user_id)
        
        return {
            'project_hours': {pid: stats['hours'] for pid, stats in project_stats.items()},
            'project_user_counts': {pid: len(stats['users']) for pid, stats in project_stats.items()}
        }
    
    def _generate_chart_data(self, records: List[WorkTimeRecord], config: ReportConfig) -> Dict[str, Any]:
        """生成图表数据"""
        return {
            'time_series': self._generate_time_series_data(records),
            'distribution': self._generate_distribution_data(records),
            'comparison': self._generate_comparison_chart_data(records),
            'heatmap': self._generate_heatmap_data(records)
        }
    
    def _generate_time_series_data(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """生成时间序列数据"""
        daily_hours = defaultdict(float)
        
        for record in records:
            date_key = record.start_time.date().isoformat()
            daily_hours[date_key] += record.duration_minutes / 60.0
        
        return {
            'labels': sorted(daily_hours.keys()),
            'values': [daily_hours[date] for date in sorted(daily_hours.keys())],
            'type': 'line'
        }
    
    def _generate_distribution_data(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """生成分布数据"""
        hourly_distribution = defaultdict(int)
        
        for record in records:
            hourly_distribution[record.start_time.hour] += 1
        
        return {
            'labels': [f"{hour:02d}:00" for hour in range(24)],
            'values': [hourly_distribution[hour] for hour in range(24)],
            'type': 'bar'
        }
    
    def _generate_comparison_chart_data(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """生成对比图表数据"""
        user_hours = defaultdict(float)
        
        for record in records:
            user_hours[record.user_id] += record.duration_minutes / 60.0
        
        return {
            'labels': list(user_hours.keys()),
            'values': list(user_hours.values()),
            'type': 'bar'
        }
    
    def _generate_heatmap_data(self, records: List[WorkTimeRecord]) -> Dict[str, Any]:
        """生成热力图数据"""
        # 按小时和星期几统计活动
        heatmap_data = defaultdict(lambda: defaultdict(int))
        
        for record in records:
            weekday = record.start_time.weekday()
            hour = record.start_time.hour
            heatmap_data[weekday][hour] += record.duration_minutes
        
        return {
            'data': dict(heatmap_data),
            'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            'hours': list(range(24))
        }
    
    def _generate_recommendations(self, records: List[WorkTimeRecord], config: ReportConfig) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if not records:
            return ["无足够数据生成建议"]
        
        # 分析工时模式
        total_hours = sum(r.duration_minutes for r in records) / 60.0
        avg_daily_hours = total_hours / len(set(r.start_time.date() for r in records))
        
        if avg_daily_hours > 10:
            recommendations.append("平均日工时较高，建议合理安排工作时间，避免过度疲劳")
        elif avg_daily_hours < 6:
            recommendations.append("平均日工时较低，建议提高工作时间投入")
        
        # 分析工作规律性
        start_hours = [r.start_time.hour for r in records]
        if len(start_hours) > 1:
            start_hour_std = statistics.stdev(start_hours)
            if start_hour_std > 2:
                recommendations.append("工作开始时间不够规律，建议建立固定的工作时间表")
        
        # 分析暂停时间
        total_pause = sum(r.pause_duration_minutes for r in records) / 60.0
        pause_ratio = total_pause / total_hours if total_hours > 0 else 0
        
        if pause_ratio > 0.3:
            recommendations.append("暂停时间占比较高，建议分析原因并优化工作流程")
        elif pause_ratio < 0.1:
            recommendations.append("暂停时间较少，建议适当安排休息时间，保持工作效率")
        
        return recommendations
    
    def _generate_cache_key(self, config: ReportConfig, start_date: datetime, 
                           end_date: datetime, entity_ids: List[str]) -> str:
        """生成缓存键"""
        key_parts = [
            config.report_type.value,
            config.aggregation_level.value,
            start_date.isoformat(),
            end_date.isoformat(),
            str(sorted(entity_ids)) if entity_ids else "all"
        ]
        return "_".join(key_parts)
    
    def _is_cache_valid(self, cached_report: Dict[str, Any], max_age_minutes: int = 30) -> bool:
        """检查缓存是否有效"""
        if 'metadata' not in cached_report:
            return False
        
        generated_at = datetime.fromisoformat(cached_report['metadata']['generated_at'])
        age_minutes = (datetime.now() - generated_at).total_seconds() / 60
        
        return age_minutes < max_age_minutes
    
    def export_report(self, report: Dict[str, Any], format: ReportFormat, 
                     filename: str = None) -> bytes:
        """导出报表"""
        if format == ReportFormat.JSON:
            return json.dumps(report, indent=2, ensure_ascii=False).encode('utf-8')
        
        elif format == ReportFormat.CSV:
            return self._export_to_csv(report)
        
        elif format == ReportFormat.EXCEL:
            return self._export_to_excel(report)
        
        elif format == ReportFormat.HTML:
            return self._export_to_html(report)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_to_csv(self, report: Dict[str, Any]) -> bytes:
        """导出为CSV"""
        # 简化的CSV导出
        csv_data = "Metric,Value\n"
        
        if 'summary' in report:
            for key, value in report['summary'].items():
                if isinstance(value, (int, float)):
                    csv_data += f"{key},{value}\n"
        
        return csv_data.encode('utf-8')
    
    def _export_to_excel(self, report: Dict[str, Any]) -> bytes:
        """导出为Excel"""
        # 这里需要使用pandas和openpyxl
        # 简化实现
        buffer = BytesIO()
        
        # 创建DataFrame
        summary_data = []
        if 'summary' in report:
            for key, value in report['summary'].items():
                if isinstance(value, (int, float)):
                    summary_data.append({'Metric': key, 'Value': value})
        
        if summary_data:
            df = pd.DataFrame(summary_data)
            df.to_excel(buffer, index=False, sheet_name='Summary')
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _export_to_html(self, report: Dict[str, Any]) -> bytes:
        """导出为HTML"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Work Time Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Work Time Report</h1>
            <h2>Summary</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
        """
        
        if 'summary' in report:
            for key, value in report['summary'].items():
                if isinstance(value, (int, float)):
                    html_content += f"<tr><td class='metric'>{key}</td><td>{value:.2f}</td></tr>"
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        return html_content.encode('utf-8')