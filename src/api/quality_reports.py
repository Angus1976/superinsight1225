"""
Quality Reports API - 质量报告 API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from pydantic import BaseModel, Field

from src.quality.quality_reporter import (
    QualityReporter,
    ProjectQualityReport,
    AnnotatorRankingReport,
    QualityTrendReport,
    ReportSchedule,
    TrendPoint,
    AnnotatorRanking
)


router = APIRouter(prefix="/api/v1/quality-reports", tags=["Quality Reports"])


# 全局实例
_reporter: Optional[QualityReporter] = None


def get_reporter() -> QualityReporter:
    global _reporter
    if _reporter is None:
        _reporter = QualityReporter()
    return _reporter


# Request/Response Models
class ProjectReportRequest(BaseModel):
    """项目报告请求"""
    project_id: str
    start_date: datetime
    end_date: datetime


class ProjectReportResponse(BaseModel):
    """项目报告响应"""
    id: str
    project_id: str
    period_start: datetime
    period_end: datetime
    total_annotations: int
    average_scores: Dict[str, float]
    quality_trend: List[Dict[str, Any]]
    issue_distribution: Dict[str, int]
    passed_count: int
    failed_count: int
    generated_at: datetime


class RankingRequest(BaseModel):
    """排名请求"""
    project_id: str
    period: str = "month"  # day, week, month


class AnnotatorRankingResponse(BaseModel):
    """标注员排名响应"""
    annotator_id: str
    annotator_name: str
    rank: int
    total_annotations: int
    average_score: float
    accuracy: float
    pass_rate: float


class RankingReportResponse(BaseModel):
    """排名报告响应"""
    id: str
    project_id: str
    period: str
    rankings: List[AnnotatorRankingResponse]
    generated_at: datetime


class TrendRequest(BaseModel):
    """趋势请求"""
    project_id: str
    granularity: str = "day"  # day, week, month


class TrendPointResponse(BaseModel):
    """趋势数据点响应"""
    date: datetime
    score: float
    count: int


class TrendReportResponse(BaseModel):
    """趋势报告响应"""
    id: str
    project_id: str
    granularity: str
    trend_data: List[TrendPointResponse]
    summary: Dict[str, Any]
    generated_at: datetime


class ExportRequest(BaseModel):
    """导出请求"""
    report_type: str  # project, ranking, trend
    project_id: str
    format: str = "pdf"  # pdf, excel, html, json
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = None
    granularity: Optional[str] = None


class ScheduleReportRequest(BaseModel):
    """定时报告请求"""
    project_id: str
    report_type: str
    name: str
    schedule: str  # cron 表达式
    recipients: List[str]
    export_format: str = "pdf"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ScheduleResponse(BaseModel):
    """调度响应"""
    id: str
    project_id: str
    report_type: str
    name: str
    schedule: str
    recipients: List[str]
    export_format: str
    enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime


# API Endpoints
@router.post("/project", response_model=ProjectReportResponse)
async def generate_project_report(
    request: ProjectReportRequest,
    reporter: QualityReporter = Depends(get_reporter)
) -> ProjectReportResponse:
    """
    生成项目质量汇总报告
    
    - **project_id**: 项目ID
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    report = await reporter.generate_project_report(
        project_id=request.project_id,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return ProjectReportResponse(
        id=report.id,
        project_id=report.project_id,
        period_start=report.period_start,
        period_end=report.period_end,
        total_annotations=report.total_annotations,
        average_scores=report.average_scores,
        quality_trend=[
            {
                "date": t.date.isoformat(),
                "score": t.score,
                "count": t.count
            }
            for t in report.quality_trend
        ],
        issue_distribution=report.issue_distribution,
        passed_count=report.passed_count,
        failed_count=report.failed_count,
        generated_at=report.generated_at
    )


@router.post("/annotator-ranking", response_model=RankingReportResponse)
async def generate_annotator_ranking(
    request: RankingRequest,
    reporter: QualityReporter = Depends(get_reporter)
) -> RankingReportResponse:
    """
    生成标注员质量排名报告
    
    - **project_id**: 项目ID
    - **period**: 时间周期 (day/week/month)
    """
    report = await reporter.generate_annotator_ranking(
        project_id=request.project_id,
        period=request.period
    )
    
    return RankingReportResponse(
        id=report.id,
        project_id=report.project_id,
        period=report.period,
        rankings=[
            AnnotatorRankingResponse(
                annotator_id=r.annotator_id,
                annotator_name=r.annotator_name,
                rank=r.rank,
                total_annotations=r.total_annotations,
                average_score=r.average_score,
                accuracy=r.accuracy,
                pass_rate=r.pass_rate
            )
            for r in report.rankings
        ],
        generated_at=report.generated_at
    )


@router.post("/trend", response_model=TrendReportResponse)
async def generate_trend_report(
    request: TrendRequest,
    reporter: QualityReporter = Depends(get_reporter)
) -> TrendReportResponse:
    """
    生成质量趋势分析报告
    
    - **project_id**: 项目ID
    - **granularity**: 粒度 (day/week/month)
    """
    report = await reporter.generate_trend_report(
        project_id=request.project_id,
        granularity=request.granularity
    )
    
    return TrendReportResponse(
        id=report.id,
        project_id=report.project_id,
        granularity=report.granularity,
        trend_data=[
            TrendPointResponse(
                date=t.date,
                score=t.score,
                count=t.count
            )
            for t in report.trend_data
        ],
        summary=report.summary,
        generated_at=report.generated_at
    )


@router.post("/export")
async def export_report(
    request: ExportRequest,
    reporter: QualityReporter = Depends(get_reporter)
) -> Response:
    """
    导出报告
    
    - **report_type**: 报告类型 (project/ranking/trend)
    - **project_id**: 项目ID
    - **format**: 导出格式 (pdf/excel/html/json)
    """
    # 生成报告
    if request.report_type == "project":
        if not request.start_date or not request.end_date:
            raise HTTPException(status_code=400, detail="start_date and end_date are required for project report")
        report = await reporter.generate_project_report(
            project_id=request.project_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
    elif request.report_type == "ranking":
        report = await reporter.generate_annotator_ranking(
            project_id=request.project_id,
            period=request.period or "month"
        )
    elif request.report_type == "trend":
        report = await reporter.generate_trend_report(
            project_id=request.project_id,
            granularity=request.granularity or "day"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {request.report_type}")
    
    # 导出
    content = await reporter.export_report(report, request.format)
    
    # 设置响应头
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
        "json": "application/json"
    }
    
    extensions = {
        "pdf": "pdf",
        "excel": "xlsx",
        "html": "html",
        "json": "json"
    }
    
    content_type = content_types.get(request.format, "application/octet-stream")
    extension = extensions.get(request.format, "bin")
    filename = f"quality_report_{request.project_id}_{datetime.utcnow().strftime('%Y%m%d')}.{extension}"
    
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule_report(
    request: ScheduleReportRequest,
    reporter: QualityReporter = Depends(get_reporter)
) -> ScheduleResponse:
    """
    创建定时报告
    
    - **project_id**: 项目ID
    - **report_type**: 报告类型
    - **name**: 报告名称
    - **schedule**: Cron 表达式
    - **recipients**: 接收人列表
    - **export_format**: 导出格式
    """
    schedule = await reporter.schedule_report(
        project_id=request.project_id,
        report_type=request.report_type,
        name=request.name,
        schedule=request.schedule,
        recipients=request.recipients,
        export_format=request.export_format,
        parameters=request.parameters
    )
    
    return ScheduleResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        report_type=schedule.report_type,
        name=schedule.name,
        schedule=schedule.schedule,
        recipients=schedule.recipients,
        export_format=schedule.export_format,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at
    )


@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    project_id: str = Query(..., description="项目ID"),
    reporter: QualityReporter = Depends(get_reporter)
) -> List[ScheduleResponse]:
    """
    获取项目的定时报告列表
    
    - **project_id**: 项目ID
    """
    schedules = await reporter.get_schedules(project_id)
    
    return [
        ScheduleResponse(
            id=s.id,
            project_id=s.project_id,
            report_type=s.report_type,
            name=s.name,
            schedule=s.schedule,
            recipients=s.recipients,
            export_format=s.export_format,
            enabled=s.enabled,
            last_run_at=s.last_run_at,
            next_run_at=s.next_run_at,
            created_at=s.created_at
        )
        for s in schedules
    ]
