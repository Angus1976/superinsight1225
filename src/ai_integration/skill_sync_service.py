"""
Skill Sync Service — syncs skills from OpenClaw Agent into the database
and executes skills via the Agent HTTP API.

Requirements: 3.1–3.7, 4.1, 4.3–4.6
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.ai_integration import AIAuditLog, AIGateway, AISkill

logger = logging.getLogger(__name__)

EXECUTE_TIMEOUT_SECONDS = 30
SYNC_TIMEOUT_SECONDS = 15


class SkillSyncService:
    """Synchronises skills from OpenClaw Agent and executes them."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def sync_from_agent(self, gateway: AIGateway) -> dict:
        """Fetch skills from Agent and upsert into ai_skills table.

        Returns dict with keys: added, updated, removed, skills.
        Raises HTTPException 400 (missing config) or 503 (agent unreachable).
        """
        agent_url = self._resolve_agent_url(gateway)
        agent_skills = await self._fetch_agent_skills(agent_url)
        result = self._upsert_skills(gateway, agent_skills)
        return result

    async def execute_skill(
        self,
        skill: AISkill,
        gateway: AIGateway,
        params: dict,
    ) -> dict:
        """Execute a deployed skill via the Agent.

        Returns dict with keys: success, result, error, execution_time_ms.
        Raises HTTPException 400 (not deployed), 503 (unreachable), 504 (timeout).
        """
        if skill.status != "deployed":
            raise HTTPException(
                status_code=400,
                detail="技能未部署，无法执行",
            )

        agent_url = self._resolve_agent_url(gateway)
        start = time.monotonic()
        success = False
        result_payload: dict[str, Any] = {}
        error_msg: Optional[str] = None

        try:
            result_payload = await self._call_agent_execute(
                agent_url, skill, params
            )
            success = True
        except HTTPException:
            raise
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._write_audit_log(
                gateway=gateway,
                skill=skill,
                success=success,
                error_message=error_msg,
                execution_time_ms=elapsed_ms,
                params=params,
            )

        return {
            "success": True,
            "result": result_payload,
            "error": None,
            "execution_time_ms": int((time.monotonic() - start) * 1000),
        }

    # ------------------------------------------------------------------
    # Agent URL resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_agent_url(gateway: AIGateway) -> str:
        """Extract agent_url from gateway configuration.

        Raises HTTPException 400 when no URL is configured.
        """
        config = gateway.configuration or {}

        # Direct agent_url takes priority
        agent_url = config.get("agent_url", "")
        if not agent_url:
            # Fallback to network_settings.base_url
            network = config.get("network_settings", {})
            agent_url = network.get("base_url", "")

        if not agent_url:
            raise HTTPException(
                status_code=400,
                detail="网关配置缺少 agent_url",
            )
        return agent_url.rstrip("/")

    # ------------------------------------------------------------------
    # Agent HTTP calls
    # ------------------------------------------------------------------

    async def _fetch_agent_skills(self, agent_url: str) -> list[dict]:
        """GET {agent_url}/api/skills — returns list of skill dicts."""
        url = f"{agent_url}/api/skills"
        try:
            async with httpx.AsyncClient(timeout=SYNC_TIMEOUT_SECONDS) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                # Agent may return {"skills": [...]} or a bare list
                if isinstance(data, list):
                    return data
                return data.get("skills", [])
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Agent 服务不可达")
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="Agent 服务响应超时")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Agent 返回错误: {exc.response.status_code}",
            )

    async def _call_agent_execute(
        self, agent_url: str, skill: AISkill, params: dict
    ) -> dict:
        """POST {agent_url}/api/skills/execute — returns result payload."""
        url = f"{agent_url}/api/skills/execute"
        payload = {
            "skill_id": skill.id,
            "skill_name": skill.name,
            "parameters": params,
        }
        try:
            async with httpx.AsyncClient(
                timeout=EXECUTE_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Agent 服务不可达")
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504, detail="技能执行超时（30s）"
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Agent 执行返回错误: {exc.response.status_code}",
            )

    # ------------------------------------------------------------------
    # Upsert logic
    # ------------------------------------------------------------------

    def _upsert_skills(
        self, gateway: AIGateway, agent_skills: list[dict]
    ) -> dict:
        """Reconcile DB skills with Agent skills.

        New → INSERT, existing → UPDATE, missing → mark removed.
        Returns dict with added, updated, removed counts and skill list.
        """
        existing = (
            self.db.query(AISkill)
            .filter(AISkill.gateway_id == gateway.id)
            .all()
        )
        existing_by_name: dict[str, AISkill] = {s.name: s for s in existing}
        agent_names: set[str] = set()

        added = 0
        updated = 0

        now = datetime.now(timezone.utc)

        for skill_data in agent_skills:
            name = skill_data.get("name", "")
            if not name:
                continue
            agent_names.add(name)

            if name in existing_by_name:
                self._update_skill(existing_by_name[name], skill_data, now)
                updated += 1
            else:
                self._insert_skill(gateway, skill_data, now)
                added += 1

        # Mark removed skills
        removed = 0
        for db_skill in existing:
            if db_skill.name not in agent_names and db_skill.status != "removed":
                db_skill.status = "removed"
                db_skill.updated_at = now
                removed += 1

        self.db.commit()

        # Reload all skills for the response
        all_skills = (
            self.db.query(AISkill)
            .filter(AISkill.gateway_id == gateway.id)
            .all()
        )

        from src.ai_integration.schemas import SkillDetailResponse

        skills_response = [
            SkillDetailResponse(
                id=s.id,
                name=s.name,
                version=s.version,
                status=s.status,
                description=(s.configuration or {}).get("description"),
                category=(s.configuration or {}).get("category"),
                gateway_id=gateway.id,
                gateway_name=gateway.name,
                deployed_at=s.deployed_at,
                created_at=s.created_at,
            )
            for s in all_skills
        ]

        return {
            "added": added,
            "updated": updated,
            "removed": removed,
            "skills": skills_response,
        }

    @staticmethod
    def _update_skill(
        skill: AISkill, data: dict, now: datetime
    ) -> None:
        """Update an existing skill from Agent data."""
        skill.version = data.get("version", skill.version)
        skill.status = "deployed"
        skill.deployed_at = now
        skill.updated_at = now
        if "configuration" in data:
            skill.configuration = data["configuration"]
        if "code_path" in data:
            skill.code_path = data["code_path"]

    def _insert_skill(
        self, gateway: AIGateway, data: dict, now: datetime
    ) -> None:
        """Insert a new skill from Agent data."""
        config = data.get("configuration", {})
        skill = AISkill(
            id=str(uuid4()),
            gateway_id=gateway.id,
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            code_path=data.get("code_path", ""),
            configuration=config,
            dependencies=data.get("dependencies", []),
            status="deployed",
            deployed_at=now,
        )
        self.db.add(skill)

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _write_audit_log(
        self,
        gateway: AIGateway,
        skill: AISkill,
        success: bool,
        error_message: Optional[str],
        execution_time_ms: int,
        params: dict,
    ) -> None:
        """Write an ai_audit_logs record for a skill execution."""
        log_id = str(uuid4())
        now = datetime.now(timezone.utc)

        metadata = {
            "skill_id": skill.id,
            "skill_name": skill.name,
            "parameters": params,
            "execution_time_ms": execution_time_ms,
        }

        signature = self._compute_signature(
            log_id=log_id,
            gateway_id=gateway.id,
            tenant_id=gateway.tenant_id,
            event_type="skill_execution",
            resource=f"skill:{skill.id}",
            action="execute",
            timestamp=now,
            metadata=metadata,
            success=success,
        )

        log_entry = AIAuditLog(
            id=log_id,
            gateway_id=gateway.id,
            tenant_id=gateway.tenant_id,
            event_type="skill_execution",
            resource=f"skill:{skill.id}",
            action="execute",
            event_metadata=metadata,
            success=success,
            error_message=error_message,
            timestamp=now,
            signature=signature,
        )
        self.db.add(log_entry)
        self.db.commit()

    @staticmethod
    def _compute_signature(**fields: Any) -> str:
        """SHA-256 hash of the audit event fields."""
        canonical = json.dumps(
            {k: (v.isoformat() if isinstance(v, datetime) else v)
             for k, v in sorted(fields.items())},
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()
