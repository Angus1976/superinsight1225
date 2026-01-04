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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
