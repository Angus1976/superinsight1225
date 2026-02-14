"""
Unit tests for SkillManager.

Tests skill packaging, deployment, hot-reloading, and listing functionality.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.ai_integration.skill_manager import (
    SkillManager,
    SkillPackage,
    SkillPackageError,
    SkillDeploymentError,
    SkillNotFoundError
)
from src.models.ai_integration import AISkill, AIGateway


@pytest.fixture
def db_session():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def skill_manager(db_session, tmp_path):
    """Create SkillManager instance with temp directory."""
    return SkillManager(db_session, skills_base_path=str(tmp_path))


@pytest.fixture
def sample_gateway():
    """Create sample gateway."""
    return AIGateway(
        id="gateway-123",
        name="Test Gateway",
        gateway_type="openclaw",
        tenant_id="tenant-123",
        status="active",
        configuration={},
        api_key_hash="hash1",
        api_secret_hash="hash2"
    )


@pytest.fixture
def sample_skill():
    """Create sample skill."""
    return AISkill(
        id="skill-123",
        gateway_id="gateway-123",
        name="test-skill",
        version="1.0.0",
        code_path="/app/skills/test-skill/1.0.0",
        configuration={},
        dependencies=["axios@1.0.0"],
        status="deployed"
    )


class TestPackageSkill:
    """Tests for package_skill method."""
    
    def test_package_skill_success(self, skill_manager):
        """Test successful skill packaging."""
        skill_code = "module.exports = { run: () => {} };"
        dependencies = ["axios@1.0.0", "lodash@4.17.21"]
        config = {"timeout": 30}
        
        package = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code=skill_code,
            dependencies=dependencies,
            config=config
        )
        
        assert isinstance(package, SkillPackage)
        assert package.name == "test-skill"
        assert package.version == "1.0.0"
        assert package.dependencies == dependencies
        assert package.configuration == config
        
        skill_dir = Path(package.code_path)
        assert skill_dir.exists()
        assert (skill_dir / "index.js").exists()
        assert (skill_dir / "package.json").exists()
        assert (skill_dir / "config.json").exists()
    
    def test_package_skill_creates_package_json(self, skill_manager):
        """Test package.json creation with dependencies."""
        dependencies = ["axios@1.0.0", "lodash"]
        
        package = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code="code",
            dependencies=dependencies,
            config={}
        )
        
        package_json_path = Path(package.code_path) / "package.json"
        package_json = json.loads(package_json_path.read_text())
        
        assert package_json["name"] == "test-skill"
        assert package_json["version"] == "1.0.0"
        assert package_json["main"] == "index.js"
        assert package_json["dependencies"]["axios"] == "1.0.0"
        assert package_json["dependencies"]["lodash"] == "latest"
    
    def test_package_skill_empty_name(self, skill_manager):
        """Test packaging fails with empty name."""
        with pytest.raises(SkillPackageError, match="name cannot be empty"):
            skill_manager.package_skill(
                name="",
                version="1.0.0",
                skill_code="code",
                dependencies=[],
                config={}
            )
    
    def test_package_skill_empty_version(self, skill_manager):
        """Test packaging fails with empty version."""
        with pytest.raises(SkillPackageError, match="version cannot be empty"):
            skill_manager.package_skill(
                name="test-skill",
                version="",
                skill_code="code",
                dependencies=[],
                config={}
            )
    
    def test_package_skill_empty_code(self, skill_manager):
        """Test packaging fails with empty code."""
        with pytest.raises(SkillPackageError, match="code cannot be empty"):
            skill_manager.package_skill(
                name="test-skill",
                version="1.0.0",
                skill_code="",
                dependencies=[],
                config={}
            )


class TestDeploySkill:
    """Tests for deploy_skill method."""
    
    def test_deploy_skill_success(
        self,
        skill_manager,
        db_session,
        sample_gateway
    ):
        """Test successful skill deployment."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_gateway
        
        package = SkillPackage(
            name="test-skill",
            version="1.0.0",
            code_path="/app/skills/test-skill/1.0.0",
            dependencies=["axios@1.0.0"],
            configuration={"timeout": 30}
        )
        
        skill = skill_manager.deploy_skill("gateway-123", package)
        
        assert db_session.add.called
        assert db_session.commit.called
        assert db_session.refresh.called
    
    def test_deploy_skill_inactive_gateway(
        self,
        skill_manager,
        db_session,
        sample_gateway
    ):
        """Test deployment fails for inactive gateway."""
        sample_gateway.status = "inactive"
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_gateway
        
        package = SkillPackage(
            name="test-skill",
            version="1.0.0",
            code_path="/path",
            dependencies=[],
            configuration={}
        )
        
        with pytest.raises(SkillDeploymentError, match="not active"):
            skill_manager.deploy_skill("gateway-123", package)
    
    def test_deploy_skill_gateway_not_found(
        self,
        skill_manager,
        db_session
    ):
        """Test deployment fails when gateway not found."""
        db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        package = SkillPackage(
            name="test-skill",
            version="1.0.0",
            code_path="/path",
            dependencies=[],
            configuration={}
        )
        
        with pytest.raises(SkillDeploymentError, match="not found"):
            skill_manager.deploy_skill("gateway-123", package)
    
    def test_deploy_skill_database_error(
        self,
        skill_manager,
        db_session,
        sample_gateway
    ):
        """Test deployment handles database errors."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_gateway
        db_session.commit.side_effect = Exception("DB error")
        
        package = SkillPackage(
            name="test-skill",
            version="1.0.0",
            code_path="/path",
            dependencies=[],
            configuration={}
        )
        
        with pytest.raises(SkillDeploymentError, match="Failed to deploy"):
            skill_manager.deploy_skill("gateway-123", package)
        
        assert db_session.rollback.called


class TestHotReloadSkill:
    """Tests for hot_reload_skill method."""
    
    def test_hot_reload_success(
        self,
        skill_manager,
        db_session,
        sample_skill
    ):
        """Test successful hot reload."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_skill
        
        skill_manager.hot_reload_skill("gateway-123", "skill-123")
        
        assert db_session.commit.called
    
    def test_hot_reload_skill_not_found(
        self,
        skill_manager,
        db_session
    ):
        """Test hot reload fails when skill not found."""
        db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(SkillNotFoundError, match="not found"):
            skill_manager.hot_reload_skill("gateway-123", "skill-123")
    
    def test_hot_reload_wrong_gateway(
        self,
        skill_manager,
        db_session,
        sample_skill
    ):
        """Test hot reload fails for wrong gateway."""
        sample_skill.gateway_id = "other-gateway"
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_skill
        
        with pytest.raises(SkillNotFoundError, match="not found for gateway"):
            skill_manager.hot_reload_skill("gateway-123", "skill-123")
    
    def test_hot_reload_database_error(
        self,
        skill_manager,
        db_session,
        sample_skill
    ):
        """Test hot reload handles database errors."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_skill
        db_session.commit.side_effect = Exception("DB error")
        
        with pytest.raises(SkillDeploymentError, match="Failed to hot reload"):
            skill_manager.hot_reload_skill("gateway-123", "skill-123")
        
        assert db_session.rollback.called


class TestListSkills:
    """Tests for list_skills method."""
    
    def test_list_skills_success(
        self,
        skill_manager,
        db_session,
        sample_skill
    ):
        """Test listing skills for gateway."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_skill]
        db_session.execute.return_value = mock_result
        
        skills = skill_manager.list_skills("gateway-123")
        
        assert len(skills) == 1
        assert skills[0].id == "skill-123"
    
    def test_list_skills_empty(self, skill_manager, db_session):
        """Test listing skills returns empty list."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute.return_value = mock_result
        
        skills = skill_manager.list_skills("gateway-123")
        
        assert len(skills) == 0


class TestParseDependencies:
    """Tests for _parse_dependencies helper method."""
    
    def test_parse_dependencies_with_versions(self, skill_manager):
        """Test parsing dependencies with versions."""
        deps = ["axios@1.0.0", "lodash@4.17.21"]
        parsed = skill_manager._parse_dependencies(deps)
        
        assert parsed == {
            "axios": "1.0.0",
            "lodash": "4.17.21"
        }
    
    def test_parse_dependencies_without_versions(self, skill_manager):
        """Test parsing dependencies without versions."""
        deps = ["axios", "lodash"]
        parsed = skill_manager._parse_dependencies(deps)
        
        assert parsed == {
            "axios": "latest",
            "lodash": "latest"
        }
    
    def test_parse_dependencies_mixed(self, skill_manager):
        """Test parsing mixed dependencies."""
        deps = ["axios@1.0.0", "lodash"]
        parsed = skill_manager._parse_dependencies(deps)
        
        assert parsed == {
            "axios": "1.0.0",
            "lodash": "latest"
        }
    
    def test_parse_dependencies_empty(self, skill_manager):
        """Test parsing empty dependencies."""
        parsed = skill_manager._parse_dependencies([])
        assert parsed == {}
    
    def test_parse_dependencies_with_special_chars(self, skill_manager):
        """Test parsing dependencies with special characters."""
        deps = ["axios@^1.0.0", "lodash@~4.17.21"]
        parsed = skill_manager._parse_dependencies(deps)
        
        assert parsed == {
            "axios": "^1.0.0",
            "lodash": "~4.17.21"
        }


class TestSkillPackageFileCreation:
    """Tests for skill package file creation."""
    
    def test_package_creates_all_required_files(self, skill_manager):
        """Test that packaging creates all required files."""
        package = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code="module.exports = {};",
            dependencies=["axios@1.0.0"],
            config={"timeout": 30}
        )
        
        skill_dir = Path(package.code_path)
        assert (skill_dir / "index.js").exists()
        assert (skill_dir / "package.json").exists()
        assert (skill_dir / "config.json").exists()
    
    def test_package_code_content_matches(self, skill_manager):
        """Test that packaged code matches input."""
        code = "module.exports = { run: () => 'test' };"
        
        package = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code=code,
            dependencies=[],
            config={}
        )
        
        index_file = Path(package.code_path) / "index.js"
        assert index_file.read_text() == code
    
    def test_package_config_content_matches(self, skill_manager):
        """Test that packaged config matches input."""
        config = {"timeout": 60, "retries": 3}
        
        package = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code="code",
            dependencies=[],
            config=config
        )
        
        config_file = Path(package.code_path) / "config.json"
        loaded_config = json.loads(config_file.read_text())
        assert loaded_config == config


class TestSkillPackageVersioning:
    """Tests for skill versioning."""
    
    def test_package_different_versions_separate_directories(
        self,
        skill_manager
    ):
        """Test that different versions create separate directories."""
        package_v1 = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code="v1 code",
            dependencies=[],
            config={}
        )
        
        package_v2 = skill_manager.package_skill(
            name="test-skill",
            version="2.0.0",
            skill_code="v2 code",
            dependencies=[],
            config={}
        )
        
        assert package_v1.code_path != package_v2.code_path
        assert Path(package_v1.code_path).exists()
        assert Path(package_v2.code_path).exists()
    
    def test_package_same_version_overwrites(self, skill_manager):
        """Test that same version overwrites existing package."""
        package_v1 = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code="original code",
            dependencies=[],
            config={}
        )
        
        package_v2 = skill_manager.package_skill(
            name="test-skill",
            version="1.0.0",
            skill_code="updated code",
            dependencies=[],
            config={}
        )
        
        assert package_v1.code_path == package_v2.code_path
        index_file = Path(package_v2.code_path) / "index.js"
        assert index_file.read_text() == "updated code"


class TestDeploySkillEdgeCases:
    """Tests for deploy_skill edge cases."""
    
    def test_deploy_skill_updates_status(
        self,
        skill_manager,
        db_session,
        sample_gateway
    ):
        """Test that deployment updates skill status."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_gateway
        
        package = SkillPackage(
            name="test-skill",
            version="1.0.0",
            code_path="/path",
            dependencies=[],
            configuration={}
        )
        
        skill = skill_manager.deploy_skill("gateway-123", package)
        
        assert skill.status == "deployed"
        assert skill.deployed_at is not None
    
    def test_deploy_skill_with_complex_config(
        self,
        skill_manager,
        db_session,
        sample_gateway
    ):
        """Test deployment with complex configuration."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_gateway
        
        complex_config = {
            "timeout": 60,
            "retries": 3,
            "env": {"API_KEY": "test"},
            "permissions": ["read", "write"]
        }
        
        package = SkillPackage(
            name="test-skill",
            version="1.0.0",
            code_path="/path",
            dependencies=["axios@1.0.0"],
            configuration=complex_config
        )
        
        skill = skill_manager.deploy_skill("gateway-123", package)
        
        assert skill.configuration == complex_config
        assert skill.dependencies == ["axios@1.0.0"]


class TestHotReloadEdgeCases:
    """Tests for hot_reload_skill edge cases."""
    
    def test_hot_reload_updates_timestamp(
        self,
        skill_manager,
        db_session,
        sample_skill
    ):
        """Test that hot reload updates timestamp."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_skill
        original_time = sample_skill.updated_at
        
        skill_manager.hot_reload_skill("gateway-123", "skill-123")
        
        assert db_session.commit.called
    
    def test_hot_reload_preserves_skill_data(
        self,
        skill_manager,
        db_session,
        sample_skill
    ):
        """Test that hot reload preserves skill data."""
        db_session.execute.return_value.scalar_one_or_none.return_value = sample_skill
        original_name = sample_skill.name
        original_version = sample_skill.version
        
        skill_manager.hot_reload_skill("gateway-123", "skill-123")
        
        assert sample_skill.name == original_name
        assert sample_skill.version == original_version


class TestListSkillsFiltering:
    """Tests for list_skills filtering."""
    
    def test_list_skills_returns_only_gateway_skills(
        self,
        skill_manager,
        db_session
    ):
        """Test that list_skills filters by gateway."""
        skill1 = AISkill(
            id="skill-1",
            gateway_id="gateway-123",
            name="skill-1",
            version="1.0.0",
            code_path="/path1",
            configuration={},
            dependencies=[],
            status="deployed"
        )
        skill2 = AISkill(
            id="skill-2",
            gateway_id="other-gateway",
            name="skill-2",
            version="1.0.0",
            code_path="/path2",
            configuration={},
            dependencies=[],
            status="deployed"
        )
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [skill1]
        db_session.execute.return_value = mock_result
        
        skills = skill_manager.list_skills("gateway-123")
        
        assert len(skills) == 1
        assert skills[0].gateway_id == "gateway-123"
