#!/usr/bin/env python3
"""
简化的 SuperInsight 测试应用
用于本地测试和演示
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import jwt
import json
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from i18n import get_manager, set_language, get_translation

# 初始化翻译管理器（默认中文）
i18n_manager = get_manager(default_language='zh')

# 创建 FastAPI 应用
app = FastAPI(
    title="SuperInsight 平台 - 测试版",
    description="企业级 AI 数据治理与标注平台",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 语言中间件
@app.middleware("http")
async def language_middleware(request, call_next):
    """
    处理语言设置的中间件
    从请求头或查询参数中获取语言设置
    """
    # 从请求头获取语言
    language = request.headers.get("Accept-Language", "zh")
    
    # 从查询参数获取语言（优先级更高）
    if "language" in request.query_params:
        language = request.query_params.get("language", "zh")
    
    # 验证语言是否支持
    if language not in i18n_manager.get_supported_languages():
        language = "zh"
    
    # 设置当前语言
    set_language(language)
    
    response = await call_next(request)
    response.headers["Content-Language"] = language
    return response

# 配置
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

# 数据模型
class User(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict

# 内存数据存储（用于演示）
users_db = {
    "admin_test": {
        "username": "admin_test",
        "email": "admin@test.com",
        "password": "admin123",
        "full_name": "系统管理员",
        "role": "ADMIN"
    },
    "expert_test": {
        "username": "expert_test",
        "email": "expert@test.com",
        "password": "expert123",
        "full_name": "业务专家",
        "role": "BUSINESS_EXPERT"
    },
    "annotator_test": {
        "username": "annotator_test",
        "email": "annotator@test.com",
        "password": "annotator123",
        "full_name": "数据标注员",
        "role": "ANNOTATOR"
    },
    "viewer_test": {
        "username": "viewer_test",
        "email": "viewer@test.com",
        "password": "viewer123",
        "full_name": "报表查看者",
        "role": "VIEWER"
    }
}

# 根端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "name": get_translation("app_name"),
        "version": "1.0.0",
        "description": get_translation("app_description"),
        "docs_url": "/docs",
        "health_url": "/health",
        "login_url": "/api/security/login",
        "language": i18n_manager.get_language()
    }

# 语言管理端点
@app.get("/api/settings/language")
async def get_language():
    """获取当前语言设置"""
    return {
        "current_language": i18n_manager.get_language(),
        "supported_languages": i18n_manager.get_supported_languages(),
        "language_names": {
            "zh": get_translation("chinese", "zh"),
            "en": get_translation("english", "en")
        }
    }

@app.post("/api/settings/language")
async def set_language_endpoint(language: str):
    """设置语言"""
    if language not in i18n_manager.get_supported_languages():
        raise HTTPException(
            status_code=400,
            detail=get_translation("bad_request")
        )
    
    set_language(language)
    return {
        "message": get_translation("language_changed"),
        "current_language": language
    }

@app.get("/api/i18n/translations")
async def get_translations(language: Optional[str] = None):
    """获取所有翻译"""
    if language and language not in i18n_manager.get_supported_languages():
        raise HTTPException(
            status_code=400,
            detail=get_translation("bad_request")
        )
    
    return {
        "language": language or i18n_manager.get_language(),
        "translations": i18n_manager.get_all(language)
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "overall_status": get_translation("healthy"),
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": get_translation("healthy"),
            "database": get_translation("healthy"),
            "cache": get_translation("healthy")
        }
    }

# 系统状态
@app.get("/system/status")
async def system_status():
    """系统状态端点"""
    return {
        "overall_status": get_translation("healthy"),
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": {"status": get_translation("healthy"), "uptime": "100%"},
            "database": {"status": get_translation("healthy"), "connections": 5},
            "cache": {"status": get_translation("healthy"), "memory_usage": "45%"}
        },
        "metrics": {
            "cpu_usage": "25%",
            "memory_usage": "60%",
            "disk_usage": "40%"
        }
    }

# 系统服务
@app.get("/system/services")
async def system_services():
    """获取所有服务状态"""
    return {
        "services": [
            {"name": "api", "status": get_translation("healthy"), "version": "1.0.0"},
            {"name": "database", "status": get_translation("healthy"), "version": "15.0"},
            {"name": "cache", "status": get_translation("healthy"), "version": "7.0"},
            {"name": "label_studio", "status": get_translation("healthy"), "version": "1.0.0"}
        ]
    }

# 系统指标
@app.get("/system/metrics")
async def system_metrics():
    """获取系统指标"""
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "requests_total": 1000,
            "requests_per_second": 10,
            "response_time_avg": 150,
            "response_time_max": 500,
            "error_rate": 0.01,
            "cpu_usage": 25,
            "memory_usage": 60,
            "disk_usage": 40
        }
    }

# API 信息
@app.get("/api/info")
async def api_info():
    """获取 API 信息"""
    return {
        "name": get_translation("app_name"),
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "system_status": "/system/status",
            "system_services": "/system/services",
            "system_metrics": "/system/metrics",
            "login": "/api/security/login",
            "users": "/api/security/users",
            "extraction": "/api/v1/extraction",
            "quality": "/api/v1/quality",
            "ai_annotation": "/api/ai",
            "billing": "/api/billing",
            "knowledge_graph": "/api/v1/knowledge-graph"
        },
        "features": [
            get_translation("extraction"),
            get_translation("quality"),
            get_translation("ai_annotation"),
            get_translation("billing"),
            get_translation("knowledge_graph"),
            "系统监控与健康检查"
        ]
    }

# 用户登录
@app.post("/api/security/login")
async def login(request: LoginRequest):
    """用户登录"""
    user = users_db.get(request.username)
    
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=401,
            detail=get_translation("invalid_credentials")
        )
    
    # 创建 JWT Token
    payload = {
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": get_translation("login_success"),
        "user": {
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

# 创建用户
@app.post("/api/security/users")
async def create_user(user: User):
    """创建新用户"""
    if user.username in users_db:
        raise HTTPException(
            status_code=409,
            detail=get_translation("user_exists")
        )
    
    users_db[user.username] = user.dict()
    
    return {
        "message": get_translation("user_created"),
        "user": {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

# 获取当前用户信息
@app.get("/api/security/users/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """获取当前登录用户信息"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=get_translation("unauthorized")
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # 解码 JWT Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        
        if not username or username not in users_db:
            raise HTTPException(
                status_code=401,
                detail=get_translation("unauthorized")
            )
        
        user = users_db[username]
        return {
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail=get_translation("token_expired")
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail=get_translation("invalid_token")
        )

# 获取用户列表
@app.get("/api/security/users")
async def get_users():
    """获取用户列表"""
    return {
        "users": [
            {
                "username": u["username"],
                "email": u["email"],
                "full_name": u["full_name"],
                "role": u["role"]
            }
            for u in users_db.values()
        ]
    }

# 数据提取端点
@app.post("/api/v1/extraction/extract")
async def extract_data(data: Dict):
    """提取数据"""
    return {
        "task_id": "task_123",
        "status": "processing",
        "message": get_translation("extraction_started"),
        "source_type": data.get("source_type"),
        "created_at": datetime.now().isoformat()
    }

# 质量评估端点
@app.post("/api/v1/quality/evaluate")
async def evaluate_quality(data: Dict):
    """评估数据质量"""
    return {
        "evaluation_id": "eval_123",
        "status": "completed",
        "metrics": {
            "completeness": 0.95,
            "accuracy": 0.92,
            "consistency": 0.88,
            "overall_score": 0.92
        },
        "timestamp": datetime.now().isoformat()
    }

# AI 预标注端点
@app.post("/api/ai/preannotate")
async def preannotate(data: Dict):
    """AI 预标注"""
    return {
        "preannotation_id": "pre_123",
        "status": "completed",
        "results": [
            {
                "text": "这是一条测试数据",
                "label": get_translation("label"),
                "confidence": 0.95
            }
        ],
        "timestamp": datetime.now().isoformat()
    }

# 计费查询端点
@app.get("/api/billing/usage")
async def get_billing_usage():
    """获取使用统计"""
    return {
        "period": "2025-01",
        "usage": {
            "extraction_tasks": 100,
            "annotations": 5000,
            "ai_predictions": 2000,
            "storage_gb": 50
        },
        "costs": {
            "extraction": 100.00,
            "annotation": 500.00,
            "ai": 200.00,
            "storage": 50.00,
            "total": 850.00
        },
        "currency": "CNY"
    }

# 知识图谱端点
@app.get("/api/v1/knowledge-graph/entities")
async def get_entities():
    """获取知识图谱实体"""
    return {
        "entities": [
            {"id": "entity_1", "name": "实体1", "type": get_translation("person")},
            {"id": "entity_2", "name": "实体2", "type": get_translation("organization")},
            {"id": "entity_3", "name": "实体3", "type": get_translation("location")}
        ]
    }

# 任务管理端点
@app.get("/api/v1/tasks")
async def get_tasks():
    """获取任务列表"""
    return {
        "tasks": [
            {
                "id": "task_1",
                "title": "数据标注任务1",
                "status": get_translation("pending"),
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "task_2",
                "title": "数据标注任务2",
                "status": get_translation("in_progress"),
                "created_at": datetime.now().isoformat()
            }
        ]
    }

# Dashboard / Business Metrics 端点
@app.get("/api/business-metrics/summary")
async def get_dashboard_summary():
    """获取Dashboard摘要数据"""
    return {
        "active_tasks": 12,
        "today_annotations": 156,
        "total_corpus": 25000,
        "total_billing": 8500,
        "active_users": 8,
        "completion_rate": 0.85,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/business-metrics/annotation-efficiency")
async def get_annotation_efficiency(hours: int = 24):
    """获取标注效率数据"""
    now = datetime.now()
    trends = []
    for i in range(hours):
        timestamp = now - timedelta(hours=hours-i-1)
        trends.append({
            "timestamp": int(timestamp.timestamp() * 1000),
            "datetime": timestamp.isoformat(),
            "annotations_per_hour": 20 + (i % 10) * 3,
            "avg_time_per_annotation": 120 - (i % 5) * 10
        })
    
    return {
        "current_rate": 25.5,
        "avg_rate": 22.3,
        "peak_rate": 35.2,
        "trends": trends,
        "period_hours": hours
    }

@app.get("/api/business-metrics/user-activity")
async def get_user_activity(hours: int = 24):
    """获取用户活动数据"""
    return {
        "active_users": 8,
        "total_sessions": 45,
        "avg_session_duration": 3600,
        "top_users": [
            {"username": "admin_test", "annotations": 120, "time_spent": 7200},
            {"username": "expert_test", "annotations": 95, "time_spent": 5400},
            {"username": "annotator_test", "annotations": 78, "time_spent": 4800}
        ],
        "period_hours": hours
    }

@app.get("/api/business-metrics/ai-models")
async def get_ai_models(model_name: Optional[str] = None, hours: int = 24):
    """获取AI模型指标"""
    return {
        "total_predictions": 2500,
        "avg_confidence": 0.87,
        "models": [
            {
                "name": "sentiment_classifier",
                "predictions": 1200,
                "avg_confidence": 0.89,
                "accuracy": 0.92
            },
            {
                "name": "ner_model",
                "predictions": 800,
                "avg_confidence": 0.85,
                "accuracy": 0.88
            }
        ],
        "period_hours": hours
    }

@app.get("/api/business-metrics/projects")
async def get_projects(project_id: Optional[str] = None, hours: int = 24):
    """获取项目指标"""
    return {
        "total_projects": 5,
        "active_projects": 3,
        "projects": [
            {
                "id": "proj_1",
                "name": "客户评论分类",
                "status": "active",
                "progress": 0.65,
                "annotations": 1500
            },
            {
                "id": "proj_2",
                "name": "命名实体识别",
                "status": "active",
                "progress": 0.42,
                "annotations": 890
            }
        ],
        "period_hours": hours
    }

# 任务统计端点
@app.get("/api/tasks/stats")
async def get_task_stats():
    """获取任务统计"""
    return {
        "total": 25,
        "pending": 8,
        "in_progress": 12,
        "completed": 4,
        "cancelled": 1,
        "overdue": 2
    }

# ============================================================================
# Label Studio 集成 API 端点
# ============================================================================

# Label Studio 项目和任务的内存存储
label_studio_projects = {}
label_studio_tasks = {}
label_studio_annotations = {}

# Label Studio 数据模型
class LabelStudioProject(BaseModel):
    title: str
    description: Optional[str] = None
    label_config: Optional[str] = None
    sampling: Optional[str] = "Sequential sampling"
    show_instruction: Optional[bool] = True
    show_skip_button: Optional[bool] = True
    enable_empty_annotation: Optional[bool] = True

class LabelStudioTask(BaseModel):
    data: Dict
    project: Optional[int] = None

class LabelStudioAnnotation(BaseModel):
    result: List[Dict]
    task: int
    completed_by: Optional[int] = None

# Label Studio 项目管理
@app.get("/api/label-studio/projects")
async def get_label_studio_projects(authorization: Optional[str] = Header(None)):
    """获取所有 Label Studio 项目"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "count": len(label_studio_projects),
        "results": list(label_studio_projects.values())
    }

@app.post("/api/label-studio/projects")
async def create_label_studio_project(
    project: LabelStudioProject,
    authorization: Optional[str] = Header(None)
):
    """创建新的 Label Studio 项目"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    project_id = len(label_studio_projects) + 1
    project_data = {
        "id": project_id,
        "title": project.title,
        "description": project.description or "",
        "label_config": project.label_config or get_default_label_config(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "sampling": project.sampling,
        "show_instruction": project.show_instruction,
        "show_skip_button": project.show_skip_button,
        "enable_empty_annotation": project.enable_empty_annotation,
        "task_number": 0,
        "total_annotations_number": 0,
        "total_predictions_number": 0,
        "num_tasks_with_annotations": 0,
        "useful_annotation_number": 0,
        "ground_truth_number": 0,
        "skipped_annotations_number": 0,
        "created_by": {
            "id": 1,
            "email": "admin@test.com",
            "first_name": "Admin",
            "last_name": "User"
        }
    }
    
    label_studio_projects[project_id] = project_data
    return project_data

@app.get("/api/label-studio/projects/{project_id}")
async def get_label_studio_project(
    project_id: int,
    authorization: Optional[str] = Header(None)
):
    """获取指定的 Label Studio 项目"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if project_id not in label_studio_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return label_studio_projects[project_id]

@app.patch("/api/label-studio/projects/{project_id}")
async def update_label_studio_project(
    project_id: int,
    project: Dict,
    authorization: Optional[str] = Header(None)
):
    """更新 Label Studio 项目"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if project_id not in label_studio_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    label_studio_projects[project_id].update(project)
    label_studio_projects[project_id]["updated_at"] = datetime.now().isoformat()
    
    return label_studio_projects[project_id]

@app.delete("/api/label-studio/projects/{project_id}")
async def delete_label_studio_project(
    project_id: int,
    authorization: Optional[str] = Header(None)
):
    """删除 Label Studio 项目"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if project_id not in label_studio_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    del label_studio_projects[project_id]
    return {"message": "Project deleted successfully"}

# Label Studio 任务管理
@app.get("/api/label-studio/projects/{project_id}/tasks")
async def get_label_studio_tasks(
    project_id: int,
    authorization: Optional[str] = Header(None)
):
    """获取项目的所有任务"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if project_id not in label_studio_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_tasks = [
        task for task in label_studio_tasks.values()
        if task.get("project") == project_id
    ]
    
    return {
        "count": len(project_tasks),
        "results": project_tasks
    }

@app.post("/api/label-studio/projects/{project_id}/tasks")
async def create_label_studio_task(
    project_id: int,
    task: LabelStudioTask,
    authorization: Optional[str] = Header(None)
):
    """创建新的标注任务"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if project_id not in label_studio_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task_id = len(label_studio_tasks) + 1
    task_data = {
        "id": task_id,
        "data": task.data,
        "project": project_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "is_labeled": False,
        "annotations": [],
        "predictions": [],
        "file_upload": None,
        "storage_filename": None
    }
    
    label_studio_tasks[task_id] = task_data
    
    # 更新项目的任务计数
    label_studio_projects[project_id]["task_number"] += 1
    
    return task_data

@app.get("/api/label-studio/tasks/{task_id}")
async def get_label_studio_task(
    task_id: int,
    authorization: Optional[str] = Header(None)
):
    """获取指定的标注任务"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if task_id not in label_studio_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return label_studio_tasks[task_id]

# Label Studio 标注管理
@app.get("/api/label-studio/projects/{project_id}/tasks/{task_id}/annotations")
async def get_task_annotations(
    project_id: int,
    task_id: int,
    authorization: Optional[str] = Header(None)
):
    """获取任务的所有标注"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    task_annotations = [
        ann for ann in label_studio_annotations.values()
        if ann.get("task") == task_id
    ]
    
    return {
        "count": len(task_annotations),
        "results": task_annotations
    }

@app.post("/api/label-studio/projects/{project_id}/tasks/{task_id}/annotations")
async def create_annotation(
    project_id: int,
    task_id: int,
    annotation: LabelStudioAnnotation,
    authorization: Optional[str] = Header(None)
):
    """创建新的标注"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if project_id not in label_studio_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if task_id not in label_studio_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 从 token 中获取用户信息
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
    except:
        username = "unknown"
    
    annotation_id = len(label_studio_annotations) + 1
    annotation_data = {
        "id": annotation_id,
        "result": annotation.result,
        "task": task_id,
        "project": project_id,
        "completed_by": annotation.completed_by or 1,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "lead_time": 0,
        "was_cancelled": False,
        "ground_truth": False,
        "created_username": username,
        "created_ago": "刚刚"
    }
    
    label_studio_annotations[annotation_id] = annotation_data
    
    # 更新任务状态
    if task_id in label_studio_tasks:
        label_studio_tasks[task_id]["is_labeled"] = True
        label_studio_tasks[task_id]["annotations"].append(annotation_data)
    
    # 更新项目统计
    if project_id in label_studio_projects:
        label_studio_projects[project_id]["total_annotations_number"] += 1
        label_studio_projects[project_id]["useful_annotation_number"] += 1
    
    return annotation_data

@app.patch("/api/label-studio/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: int,
    annotation: Dict,
    authorization: Optional[str] = Header(None)
):
    """更新标注"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if annotation_id not in label_studio_annotations:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    label_studio_annotations[annotation_id].update(annotation)
    label_studio_annotations[annotation_id]["updated_at"] = datetime.now().isoformat()
    
    return label_studio_annotations[annotation_id]

@app.delete("/api/label-studio/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: int,
    authorization: Optional[str] = Header(None)
):
    """删除标注"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if annotation_id not in label_studio_annotations:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    annotation = label_studio_annotations[annotation_id]
    task_id = annotation.get("task")
    project_id = annotation.get("project")
    
    del label_studio_annotations[annotation_id]
    
    # 更新项目统计
    if project_id and project_id in label_studio_projects:
        label_studio_projects[project_id]["total_annotations_number"] -= 1
        label_studio_projects[project_id]["useful_annotation_number"] -= 1
    
    return {"message": "Annotation deleted successfully"}

# 辅助函数：获取默认的标注配置
def get_default_label_config():
    """返回默认的 Label Studio 配置（文本分类）"""
    return """<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single">
    <Choice value="Positive"/>
    <Choice value="Negative"/>
    <Choice value="Neutral"/>
  </Choices>
</View>"""

# 初始化一些示例数据
def initialize_label_studio_data():
    """初始化示例 Label Studio 数据"""
    # 创建示例项目
    project_data = {
        "id": 1,
        "title": "客户评论情感分析",
        "description": "对客户评论进行情感分类标注",
        "label_config": get_default_label_config(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "sampling": "Sequential sampling",
        "show_instruction": True,
        "show_skip_button": True,
        "enable_empty_annotation": True,
        "task_number": 3,
        "total_annotations_number": 1,
        "total_predictions_number": 0,
        "num_tasks_with_annotations": 1,
        "useful_annotation_number": 1,
        "ground_truth_number": 0,
        "skipped_annotations_number": 0,
        "created_by": {
            "id": 1,
            "email": "admin@test.com",
            "first_name": "Admin",
            "last_name": "User"
        }
    }
    label_studio_projects[1] = project_data
    
    # 创建示例任务
    sample_texts = [
        "这个产品非常好用，我很满意！",
        "质量太差了，完全不值这个价格。",
        "还可以吧，没有特别惊艳也没有特别失望。"
    ]
    
    for i, text in enumerate(sample_texts, 1):
        task_data = {
            "id": i,
            "data": {"text": text},
            "project": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_labeled": i == 1,  # 第一个任务已标注
            "annotations": [],
            "predictions": [],
            "file_upload": None,
            "storage_filename": None
        }
        label_studio_tasks[i] = task_data
    
    # 为第一个任务创建示例标注
    annotation_data = {
        "id": 1,
        "result": [
            {
                "value": {"choices": ["Positive"]},
                "from_name": "sentiment",
                "to_name": "text",
                "type": "choices"
            }
        ],
        "task": 1,
        "project": 1,
        "completed_by": 1,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "lead_time": 15.5,
        "was_cancelled": False,
        "ground_truth": False,
        "created_username": "annotator_test",
        "created_ago": "2小时前"
    }
    label_studio_annotations[1] = annotation_data
    label_studio_tasks[1]["annotations"].append(annotation_data)

# 在应用启动时初始化数据
initialize_label_studio_data()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
