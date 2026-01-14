"""
Quality Reporter - 质量报告器
生成质量分析报告
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4
import json

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    """趋势数据点"""
    date: datetime
    score: float
    dimension: Optional[str] = None
    count: int = 0


class AnnotatorRanking(BaseModel):
    """标注员排名"""
    annotator_id: str
    annotator_name: str
    rank: int = 0
    total_annotations: int = 0
    average_score: float = 0.0
    accuracy: float = 0.0
    pass_rate: float = 0.0


class ProjectQualityReport(BaseModel):
    """项目质量汇总报告"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    period_start: datetime
    period_end: datetime
    total_annotations: int = 0
    average_scores: Dict[str, float] = Field(default_factory=dict)
    quality_trend: List[TrendPoint] = Field(default_factory=list)
    issue_distribution: Dict[str, int] = Field(default_factory=dict)
    passed_count: int = 0
    failed_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AnnotatorRankingReport(BaseModel):
    """标注员质量排名报告"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    period: str
    rankings: List[AnnotatorRanking] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class QualityTrendReport(BaseModel):
    """质量趋势分析报告"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    granularity: str  # day, week, month
    trend_data: List[TrendPoint] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSchedule(BaseModel):
    """报告调度配置"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    report_type: str
    name: str
    schedule: str  # cron 表达式
    parameters: Dict[str, Any] = Field(default_factory=dict)
    recipients: List[str] = Field(default_factory=list)
    export_format: str = "pdf"
    enabled: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnnotatorStats(BaseModel):
    """标注员统计"""
    total: int = 0
    average_score: float = 0.0
    accuracy: float = 0.0
    pass_rate: float = 0.0


class QualityReporter:
    """质量报告器"""
    
    def __init__(self, quality_scorer: Optional[Any] = None):
        """
        初始化质量报告器
        
        Args:
            quality_scorer: 质量评分器 (可选)
        """
        self.quality_scorer = quality_scorer
        
        # 内存存储 (用于测试)
        self._annotations: Dict[str, Dict[str, Any]] = {}
        self._scores: Dict[str, Dict[str, Any]] = {}
        self._check_results: Dict[str, Dict[str, Any]] = {}
        self._annotators: Dict[str, Dict[str, Any]] = {}
        self._schedules: Dict[str, ReportSchedule] = {}
    
    def add_annotation(
        self,
        annotation_id: str,
        project_id: str,
        annotator_id: str,
        data: Dict[str, Any],
        created_at: Optional[datetime] = None
    ) -> None:
        """添加标注数据 (用于测试)"""
        self._annotations[annotation_id] = {
            "id": annotation_id,
            "project_id": project_id,
            "annotator_id": annotator_id,
            "data": data,
            "created_at": created_at or datetime.utcnow()
        }
    
    def add_score(
        self,
        annotation_id: str,
        project_id: str,
        annotator_id: str,
        score: float,
        dimension_scores: Dict[str, float],
        passed: bool = True,
        scored_at: Optional[datetime] = None
    ) -> None:
        """添加评分数据 (用于测试)"""
        score_id = str(uuid4())
        self._scores[score_id] = {
            "id": score_id,
            "annotation_id": annotation_id,
            "project_id": project_id,
            "annotator_id": annotator_id,
            "total_score": score,
            "dimension_scores": dimension_scores,
            "passed": passed,
            "scored_at": scored_at or datetime.utcnow()
        }
    
    def add_annotator(self, annotator_id: str, name: str) -> None:
        """添加标注员 (用于测试)"""
        self._annotators[annotator_id] = {
            "id": annotator_id,
            "name": name
        }
    
    async def get_annotations_in_range(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """获取时间范围内的标注"""
        return [
            ann for ann in self._annotations.values()
            if ann["project_id"] == project_id
            and start_date <= ann["created_at"] <= end_date
        ]
    
    async def get_scores_in_range(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """获取时间范围内的评分"""
        return [
            score for score in self._scores.values()
            if score["project_id"] == project_id
            and start_date <= score["scored_at"] <= end_date
        ]
    
    async def generate_project_report(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> ProjectQualityReport:
        """
        生成项目质量汇总报告
        
        Args:
            project_id: 项目ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            项目质量报告
        """
        # 获取时间范围内的所有标注
        annotations = await self.get_annotations_in_range(project_id, start_date, end_date)
        scores = await self.get_scores_in_range(project_id, start_date, end_date)
        
        # 计算各维度平均分
        average_scores = await self._calculate_average_scores(scores)
        
        # 计算质量趋势
        trend = await self._calculate_quality_trend(project_id, start_date, end_date)
        
        # 统计问题分布
        issue_distribution = await self._get_issue_distribution(project_id, start_date, end_date)
        
        # 统计通过/失败数量
        passed_count = sum(1 for s in scores if s.get("passed", True))
        failed_count = len(scores) - passed_count
        
        return ProjectQualityReport(
            project_id=project_id,
            period_start=start_date,
            period_end=end_date,
            total_annotations=len(annotations),
            average_scores=average_scores,
            quality_trend=trend,
            issue_distribution=issue_distribution,
            passed_count=passed_count,
            failed_count=failed_count
        )
    
    async def _calculate_average_scores(
        self,
        scores: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """计算各维度平均分"""
        if not scores:
            return {}
        
        dimension_totals: Dict[str, List[float]] = {}
        
        for score in scores:
            dimension_scores = score.get("dimension_scores", {})
            for dim, val in dimension_scores.items():
                if dim not in dimension_totals:
                    dimension_totals[dim] = []
                dimension_totals[dim].append(val)
        
        return {
            dim: sum(vals) / len(vals)
            for dim, vals in dimension_totals.items()
            if vals
        }
    
    async def _calculate_quality_trend(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[TrendPoint]:
        """计算质量趋势"""
        scores = await self.get_scores_in_range(project_id, start_date, end_date)
        
        if not scores:
            return []
        
        # 按日期分组
        daily_scores: Dict[str, List[float]] = {}
        for score in scores:
            date_key = score["scored_at"].strftime("%Y-%m-%d")
            if date_key not in daily_scores:
                daily_scores[date_key] = []
            daily_scores[date_key].append(score["total_score"])
        
        # 生成趋势数据
        trend = []
        for date_str, day_scores in sorted(daily_scores.items()):
            avg_score = sum(day_scores) / len(day_scores)
            trend.append(TrendPoint(
                date=datetime.strptime(date_str, "%Y-%m-%d"),
                score=avg_score,
                count=len(day_scores)
            ))
        
        return trend
    
    async def _get_issue_distribution(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """获取问题分布"""
        # 从检查结果中统计问题类型
        distribution: Dict[str, int] = {}
        
        for result in self._check_results.values():
            if result.get("project_id") != project_id:
                continue
            
            checked_at = result.get("checked_at", datetime.utcnow())
            if not (start_date <= checked_at <= end_date):
                continue
            
            for issue in result.get("issues", []):
                issue_type = issue.get("rule_name", "unknown")
                distribution[issue_type] = distribution.get(issue_type, 0) + 1
        
        return distribution
    
    async def generate_annotator_ranking(
        self,
        project_id: str,
        period: str = "month"
    ) -> AnnotatorRankingReport:
        """
        生成标注员质量排名报告
        
        Args:
            project_id: 项目ID
            period: 时间周期 (day, week, month)
            
        Returns:
            标注员排名报告
        """
        # 计算时间范围
        end_date = datetime.utcnow()
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(weeks=1)
        else:  # month
            start_date = end_date - timedelta(days=30)
        
        # 获取项目标注员
        annotator_ids = set()
        for score in self._scores.values():
            if score["project_id"] == project_id:
                if score.get("annotator_id"):
                    annotator_ids.add(score["annotator_id"])
        
        rankings: List[AnnotatorRanking] = []
        
        for annotator_id in annotator_ids:
            stats = await self._calculate_annotator_stats(annotator_id, project_id, start_date, end_date)
            annotator = self._annotators.get(annotator_id, {})
            
            rankings.append(AnnotatorRanking(
                annotator_id=annotator_id,
                annotator_name=annotator.get("name", f"Annotator {annotator_id[:8]}"),
                total_annotations=stats.total,
                average_score=stats.average_score,
                accuracy=stats.accuracy,
                pass_rate=stats.pass_rate
            ))
        
        # 按平均分排序
        rankings.sort(key=lambda x: x.average_score, reverse=True)
        
        # 添加排名
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1
        
        return AnnotatorRankingReport(
            project_id=project_id,
            period=period,
            rankings=rankings
        )
    
    async def _calculate_annotator_stats(
        self,
        annotator_id: str,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> AnnotatorStats:
        """计算标注员统计"""
        scores = [
            s for s in self._scores.values()
            if s["project_id"] == project_id
            and s.get("annotator_id") == annotator_id
            and start_date <= s["scored_at"] <= end_date
        ]
        
        if not scores:
            return AnnotatorStats()
        
        total = len(scores)
        avg_score = sum(s["total_score"] for s in scores) / total
        
        # 计算准确率 (假设 accuracy 在 dimension_scores 中)
        accuracy_scores = [
            s["dimension_scores"].get("accuracy", s["total_score"])
            for s in scores
        ]
        accuracy = sum(accuracy_scores) / len(accuracy_scores)
        
        # 计算通过率
        passed = sum(1 for s in scores if s.get("passed", True))
        pass_rate = passed / total
        
        return AnnotatorStats(
            total=total,
            average_score=avg_score,
            accuracy=accuracy,
            pass_rate=pass_rate
        )
    
    async def generate_trend_report(
        self,
        project_id: str,
        granularity: str = "day"
    ) -> QualityTrendReport:
        """
        生成质量趋势分析报告
        
        Args:
            project_id: 项目ID
            granularity: 粒度 (day, week, month)
            
        Returns:
            趋势报告
        """
        # 计算时间范围
        end_date = datetime.utcnow()
        if granularity == "day":
            start_date = end_date - timedelta(days=30)
        elif granularity == "week":
            start_date = end_date - timedelta(weeks=12)
        else:  # month
            start_date = end_date - timedelta(days=365)
        
        trend = await self._calculate_quality_trend(project_id, start_date, end_date)
        
        # 计算摘要
        if trend:
            scores = [t.score for t in trend]
            summary = {
                "min_score": min(scores),
                "max_score": max(scores),
                "avg_score": sum(scores) / len(scores),
                "total_points": len(trend),
                "trend_direction": "up" if len(scores) > 1 and scores[-1] > scores[0] else "down"
            }
        else:
            summary = {}
        
        return QualityTrendReport(
            project_id=project_id,
            granularity=granularity,
            trend_data=trend,
            summary=summary
        )
    
    async def export_report(
        self,
        report: Union[ProjectQualityReport, AnnotatorRankingReport, QualityTrendReport],
        format: str = "json"
    ) -> bytes:
        """
        导出报告
        
        Args:
            report: 报告对象
            format: 导出格式 (json, pdf, excel, html)
            
        Returns:
            报告内容 (字节)
        """
        if format == "json":
            return self._export_to_json(report)
        elif format == "pdf":
            return await self._export_to_pdf(report)
        elif format == "excel":
            return await self._export_to_excel(report)
        elif format == "html":
            return await self._export_to_html(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_to_json(
        self,
        report: Union[ProjectQualityReport, AnnotatorRankingReport, QualityTrendReport]
    ) -> bytes:
        """导出为 JSON"""
        return report.json().encode("utf-8")
    
    async def _export_to_pdf(
        self,
        report: Union[ProjectQualityReport, AnnotatorRankingReport, QualityTrendReport]
    ) -> bytes:
        """导出为 PDF"""
        # 简化实现：返回 JSON 格式
        # 实际实现中应使用 reportlab 或 weasyprint 等库
        content = f"PDF Report\n\n{report.json(indent=2)}"
        return content.encode("utf-8")
    
    async def _export_to_excel(
        self,
        report: Union[ProjectQualityReport, AnnotatorRankingReport, QualityTrendReport]
    ) -> bytes:
        """导出为 Excel"""
        # 简化实现：返回 CSV 格式
        # 实际实现中应使用 openpyxl 或 xlsxwriter 等库
        if isinstance(report, AnnotatorRankingReport):
            lines = ["rank,annotator_id,annotator_name,total_annotations,average_score,accuracy,pass_rate"]
            for r in report.rankings:
                lines.append(f"{r.rank},{r.annotator_id},{r.annotator_name},{r.total_annotations},{r.average_score},{r.accuracy},{r.pass_rate}")
            return "\n".join(lines).encode("utf-8")
        else:
            return report.json().encode("utf-8")
    
    async def _export_to_html(
        self,
        report: Union[ProjectQualityReport, AnnotatorRankingReport, QualityTrendReport]
    ) -> bytes:
        """导出为 HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Quality Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Quality Report</h1>
            <pre>{report.json(indent=2)}</pre>
        </body>
        </html>
        """
        return html.encode("utf-8")
    
    async def schedule_report(
        self,
        project_id: str,
        report_type: str,
        name: str,
        schedule: str,
        recipients: List[str],
        export_format: str = "pdf",
        parameters: Optional[Dict[str, Any]] = None
    ) -> ReportSchedule:
        """
        创建定时报告
        
        Args:
            project_id: 项目ID
            report_type: 报告类型
            name: 报告名称
            schedule: Cron 表达式
            recipients: 接收人列表
            export_format: 导出格式
            parameters: 报告参数
            
        Returns:
            报告调度配置
        """
        report_schedule = ReportSchedule(
            project_id=project_id,
            report_type=report_type,
            name=name,
            schedule=schedule,
            recipients=recipients,
            export_format=export_format,
            parameters=parameters or {}
        )
        
        self._schedules[report_schedule.id] = report_schedule
        
        return report_schedule
    
    async def get_schedules(self, project_id: str) -> List[ReportSchedule]:
        """获取项目的报告调度列表"""
        return [
            s for s in self._schedules.values()
            if s.project_id == project_id
        ]


# 独立函数 (用于属性测试)
def generate_report(annotations: List[Dict[str, Any]]) -> ProjectQualityReport:
    """
    生成报告 (同步版本，用于属性测试)
    
    Args:
        annotations: 标注数据列表，每项包含 score 和 passed
        
    Returns:
        项目质量报告
    """
    if not annotations:
        return ProjectQualityReport(
            project_id="test",
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow(),
            total_annotations=0,
            average_scores={},
            passed_count=0,
            failed_count=0
        )
    
    total = len(annotations)
    passed_count = sum(1 for a in annotations if a.get("passed", True))
    failed_count = total - passed_count
    
    scores = [a.get("score", 0) for a in annotations]
    average_score = sum(scores) / len(scores) if scores else 0
    
    return ProjectQualityReport(
        project_id="test",
        period_start=datetime.utcnow() - timedelta(days=30),
        period_end=datetime.utcnow(),
        total_annotations=total,
        average_scores={"overall": average_score},
        passed_count=passed_count,
        failed_count=failed_count
    )
