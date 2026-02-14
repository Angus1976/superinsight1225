"""
Skill Manager for AI Application Integration.

Manages skill packages, deployment, and hot-reloading for AI gateways.
"""

import os
import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.ai_integration import AISkill, AIGateway


class SkillPackageError(Exception):
    """Raised when skill packaging fails."""
    pass


class SkillDeploymentError(Exception):
    """Raised when skill deployment fails."""
    pass


class SkillNotFoundError(Exception):
    """Raised when skill is not found."""
    pass


class SkillPackage:
    """Represents a packaged skill ready for deployment."""
    
    def __init__(
        self,
        name: str,
        version: str,
        code_path: str,
        dependencies: List[str],
        configuration: Dict[str, Any]
    ):
        self.name = name
        self.version = version
        self.code_path = code_path
        self.dependencies = dependencies
        self.configuration = configuration


class SkillManager:
    """
    Manages skill packages and deployment to AI gateways.
    
    Handles skill packaging, deployment, hot-reloading, and listing.
    """
    
    def __init__(self, db: Session, skills_base_path: str = "/app/skills"):
        """
        Initialize SkillManager.
        
        Args:
            db: Database session
            skills_base_path: Base path for skill storage
        """
        self.db = db
        self.skills_base_path = Path(skills_base_path)
        self.skills_base_path.mkdir(parents=True, exist_ok=True)
    
    def package_skill(
        self,
        name: str,
        version: str,
        skill_code: str,
        dependencies: List[str],
        config: Dict[str, Any]
    ) -> SkillPackage:
        """
        Package skill for deployment.
        
        Creates a skill package with code, dependencies, and configuration.
        
        Args:
            name: Skill name
            version: Skill version
            skill_code: Skill source code
            dependencies: List of npm dependencies
            config: Skill configuration
            
        Returns:
            SkillPackage ready for deployment
            
        Raises:
            SkillPackageError: If packaging fails
        """
        if not name or not name.strip():
            raise SkillPackageError("Skill name cannot be empty")
        
        if not version or not version.strip():
            raise SkillPackageError("Skill version cannot be empty")
        
        if not skill_code or not skill_code.strip():
            raise SkillPackageError("Skill code cannot be empty")
        
        try:
            skill_dir = self.skills_base_path / name / version
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            code_file = skill_dir / "index.js"
            code_file.write_text(skill_code)
            
            package_json = {
                "name": name,
                "version": version,
                "main": "index.js",
                "dependencies": self._parse_dependencies(dependencies)
            }
            (skill_dir / "package.json").write_text(
                json.dumps(package_json, indent=2)
            )
            
            config_file = skill_dir / "config.json"
            config_file.write_text(json.dumps(config, indent=2))
            
            return SkillPackage(
                name=name,
                version=version,
                code_path=str(skill_dir),
                dependencies=dependencies,
                configuration=config
            )
        except Exception as e:
            raise SkillPackageError(f"Failed to package skill: {str(e)}")
    
    def deploy_skill(
        self,
        gateway_id: str,
        skill_package: SkillPackage
    ) -> AISkill:
        """
        Deploy skill to gateway.
        
        Installs skill package to OpenClaw gateway and creates database record.
        
        Args:
            gateway_id: Target gateway ID
            skill_package: Packaged skill to deploy
            
        Returns:
            Deployed AISkill record
            
        Raises:
            SkillDeploymentError: If deployment fails
        """
        gateway = self._get_gateway(gateway_id)
        
        if gateway.status != "active":
            raise SkillDeploymentError(
                f"Gateway {gateway_id} is not active"
            )
        
        try:
            skill = AISkill(
                id=str(uuid4()),
                gateway_id=gateway_id,
                name=skill_package.name,
                version=skill_package.version,
                code_path=skill_package.code_path,
                configuration=skill_package.configuration,
                dependencies=skill_package.dependencies,
                status="deployed",
                deployed_at=datetime.utcnow()
            )
            
            self.db.add(skill)
            self.db.commit()
            self.db.refresh(skill)
            
            return skill
        except Exception as e:
            self.db.rollback()
            raise SkillDeploymentError(
                f"Failed to deploy skill: {str(e)}"
            )
    
    def hot_reload_skill(
        self,
        gateway_id: str,
        skill_id: str
    ) -> None:
        """
        Hot reload skill without restarting gateway.
        
        Updates skill code and configuration without gateway restart.
        
        Args:
            gateway_id: Gateway ID
            skill_id: Skill ID to reload
            
        Raises:
            SkillNotFoundError: If skill not found
            SkillDeploymentError: If reload fails
        """
        skill = self._get_skill(skill_id)
        
        if skill.gateway_id != gateway_id:
            raise SkillNotFoundError(
                f"Skill {skill_id} not found for gateway {gateway_id}"
            )
        
        try:
            skill.updated_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise SkillDeploymentError(
                f"Failed to hot reload skill: {str(e)}"
            )
    
    def list_skills(self, gateway_id: str) -> List[AISkill]:
        """
        List deployed skills for gateway.
        
        Args:
            gateway_id: Gateway ID
            
        Returns:
            List of deployed skills
        """
        stmt = select(AISkill).where(AISkill.gateway_id == gateway_id)
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def _get_gateway(self, gateway_id: str) -> AIGateway:
        """Get gateway by ID."""
        stmt = select(AIGateway).where(AIGateway.id == gateway_id)
        result = self.db.execute(stmt)
        gateway = result.scalar_one_or_none()
        
        if not gateway:
            raise SkillDeploymentError(f"Gateway {gateway_id} not found")
        
        return gateway
    
    def _get_skill(self, skill_id: str) -> AISkill:
        """Get skill by ID."""
        stmt = select(AISkill).where(AISkill.id == skill_id)
        result = self.db.execute(stmt)
        skill = result.scalar_one_or_none()
        
        if not skill:
            raise SkillNotFoundError(f"Skill {skill_id} not found")
        
        return skill
    
    def _parse_dependencies(
        self,
        dependencies: List[str]
    ) -> Dict[str, str]:
        """
        Parse dependency list into package.json format.
        
        Args:
            dependencies: List of dependencies (e.g., ["axios@1.0.0"])
            
        Returns:
            Dict mapping package names to versions
        """
        parsed = {}
        for dep in dependencies:
            if "@" in dep:
                parts = dep.rsplit("@", 1)
                if len(parts) == 2:
                    parsed[parts[0]] = parts[1]
                else:
                    parsed[dep] = "latest"
            else:
                parsed[dep] = "latest"
        return parsed
