"""
ClawHub Seed Skills — 首批数据分析/处理/查询相关技能。

从 ClawHub 官方认可的安全技能中精选，聚焦数据治理场景。
可通过 seed_clawhub_skills() 写入 ai_skills 表。
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from src.models.ai_integration import AISkill, AIGateway

logger = logging.getLogger(__name__)

# ClawHub 首批官方数据技能定义
CLAWHUB_DATA_SKILLS = [
    {
        "name": "data-query",
        "version": "1.0.0",
        "configuration": {
            "description": "结构化数据查询技能，支持 SQL 风格的数据检索与过滤",
            "category": "data-query",
            "source": "clawhub-official",
            "tags": ["query", "sql", "filter", "search"],
        },
    },
    {
        "name": "data-summary",
        "version": "1.0.0",
        "configuration": {
            "description": "数据摘要与统计分析技能，生成数据集的关键指标和分布概览",
            "category": "data-analysis",
            "source": "clawhub-official",
            "tags": ["summary", "statistics", "overview"],
        },
    },
    {
        "name": "data-quality-check",
        "version": "1.0.0",
        "configuration": {
            "description": "数据质量检测技能，识别缺失值、异常值、重复记录等问题",
            "category": "data-quality",
            "source": "clawhub-official",
            "tags": ["quality", "validation", "anomaly", "missing"],
        },
    },
    {
        "name": "data-transform",
        "version": "1.0.0",
        "configuration": {
            "description": "数据转换与清洗技能，支持格式转换、字段映射、数据标准化",
            "category": "data-processing",
            "source": "clawhub-official",
            "tags": ["transform", "clean", "normalize", "mapping"],
        },
    },
    {
        "name": "data-export",
        "version": "1.0.0",
        "configuration": {
            "description": "数据导出技能，支持 CSV/JSON/Excel 等格式的数据导出",
            "category": "data-export",
            "source": "clawhub-official",
            "tags": ["export", "csv", "json", "excel"],
        },
    },
    {
        "name": "data-comparison",
        "version": "1.0.0",
        "configuration": {
            "description": "多数据源对比分析技能，支持字段级差异检测与变更追踪",
            "category": "data-analysis",
            "source": "clawhub-official",
            "tags": ["compare", "diff", "change-tracking"],
        },
    },
    {
        "name": "data-annotation-assist",
        "version": "1.0.0",
        "configuration": {
            "description": "AI 辅助标注技能，基于已有标注数据自动推荐标签和分类",
            "category": "data-annotation",
            "source": "clawhub-official",
            "tags": ["annotation", "labeling", "classification", "auto-tag"],
        },
    },
    {
        "name": "data-lineage",
        "version": "1.0.0",
        "configuration": {
            "description": "数据血缘追踪技能，分析数据来源、流转路径和依赖关系",
            "category": "data-governance",
            "source": "clawhub-official",
            "tags": ["lineage", "provenance", "dependency", "tracing"],
        },
    },
]


def seed_clawhub_skills(db: Session, gateway_id: str) -> dict:
    """Seed ClawHub official data skills into ai_skills table.

    Idempotent: skips skills that already exist (by name + gateway_id).
    Returns dict with added/skipped counts and skill list.
    """
    gateway = db.query(AIGateway).filter(AIGateway.id == gateway_id).first()
    if not gateway:
        logger.error("Gateway %s not found, cannot seed skills", gateway_id)
        return {"added": 0, "skipped": 0, "error": "Gateway not found"}

    existing_names = {
        s.name
        for s in db.query(AISkill.name)
        .filter(AISkill.gateway_id == gateway_id)
        .all()
    }

    now = datetime.now(timezone.utc)
    added = 0
    skipped = 0

    for skill_def in CLAWHUB_DATA_SKILLS:
        if skill_def["name"] in existing_names:
            skipped += 1
            continue

        skill = AISkill(
            id=str(uuid4()),
            gateway_id=gateway_id,
            name=skill_def["name"],
            version=skill_def["version"],
            code_path=f"/app/skills/clawhub/{skill_def['name']}",
            configuration=skill_def["configuration"],
            dependencies=[],
            status="deployed",
            deployed_at=now,
            created_at=now,
        )
        db.add(skill)
        added += 1

    if added:
        db.commit()
        logger.info(
            "Seeded %d ClawHub skills for gateway %s (skipped %d)",
            added, gateway_id, skipped,
        )

    return {"added": added, "skipped": skipped}
