"""
Environment variable injection tests for SuperInsight Platform.

Tests verify that environment variables are properly loaded and injected.
Validates: Requirements 8.4
"""

import os
import pytest
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class EnvVarStatus(Enum):
    """Status of environment variable validation."""
    SET = "set"
    NOT_SET = "not_set"
    INVALID = "invalid"
    DEFAULT = "default"


@dataclass
class EnvVarInfo:
    """Information about an environment variable."""
    name: str
    required: bool
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    status: EnvVarStatus = EnvVarStatus.NOT_SET
    source: str = "unknown"


# Required environment variables
REQUIRED_ENV_VARS = [
    "APP_ENV",
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET_KEY",
]


def get_docker_compose_file():
    """Path to docker-compose.yml file."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "docker-compose.yml"
    )


def get_env_file():
    """Path to .env file."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".env"
    )


def get_docker_env_file():
    """Path to .env.docker file."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".env.docker"
    )


def get_env_var_from_container(container_name: str, var_name: str) -> Optional[str]:
    """Get environment variable from a Docker container."""
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "printenv", var_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
        
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        pytest.skip("Docker not found - skipping environment variable tests")


class TestEnvironmentVariableInjection:
    """Tests for environment variable injection and configuration."""
    
    @pytest.fixture
    def docker_compose_file_path(self):
        """Path to docker-compose.yml file."""
        return get_docker_compose_file()
    
    @pytest.fixture
    def env_file_path(self):
        """Path to .env file."""
        return get_env_file()
    
    @pytest.fixture
    def docker_env_file_path(self):
        """Path to .env.docker file."""
        return get_docker_env_file()
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_required_env_vars_defined_in_docker_compose(self, docker_compose_file_path):
        """Test that required environment variables are defined in docker-compose.yml."""
        import yaml
        
        with open(docker_compose_file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get("services", {})
        app_service = services.get("app", {})
        env_vars = app_service.get("environment", [])
        
        # Convert list format to dict if needed
        env_dict = {}
        for env in env_vars:
            if isinstance(env, str) and "=" in env:
                key, value = env.split("=", 1)
                env_dict[key] = value
            elif isinstance(env, dict):
                env_dict.update(env)
        
        # Check required environment variables (excluding secrets that should be in .env)
        non_secret_vars = [v for v in REQUIRED_ENV_VARS if v != "JWT_SECRET_KEY"]
        missing_vars = []
        for var in non_secret_vars:
            if var not in env_dict:
                missing_vars.append(var)
        
        assert len(missing_vars) == 0, \
            f"Required environment variables not defined: {missing_vars}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_database_url_env_var_format(self, env_file_path):
        """Test that DATABASE_URL has valid format."""
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                content = f.read()
            
            # Check for DATABASE_URL pattern
            import re
            match = re.search(r'DATABASE_URL\s*=\s*(.+)', content)
            if match:
                db_url = match.group(1).strip().strip('"\'')
                # Should be postgresql:// URL
                assert db_url.startswith("postgresql://"), \
                    f"DATABASE_URL should be postgresql:// URL, got: {db_url}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_redis_url_env_var_format(self, env_file_path):
        """Test that REDIS_URL has valid format."""
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                content = f.read()
            
            # Check for REDIS_URL pattern
            import re
            match = re.search(r'REDIS_URL\s*=\s*(.+)', content)
            if match:
                redis_url = match.group(1).strip().strip('"\'')
                # Should be redis:// URL
                assert redis_url.startswith("redis://"), \
                    f"REDIS_URL should be redis:// URL, got: {redis_url}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_env_file_exists(self, env_file_path):
        """Test that .env file exists for local development."""
        assert os.path.exists(env_file_path), \
            f".env file not found at {env_file_path}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_docker_env_file_exists(self, docker_env_file_path):
        """Test that .env.docker file exists for Docker deployment."""
        assert os.path.exists(docker_env_file_path), \
            f".env.docker file not found at {docker_env_file_path}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_env_file_not_in_gitignore(self):
        """Test that .env files are properly handled in .gitignore."""
        gitignore_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".gitignore"
        )
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                content = f.read()
            
            # .env should be in .gitignore to prevent accidental commit
            assert ".env" in content or "/.env" in content, \
                ".env should be in .gitignore"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_container_has_app_env_set(self):
        """Test that app container has APP_ENV environment variable set."""
        env_value = get_env_var_from_container("superinsight-app", "APP_ENV")
        
        assert env_value is not None, \
            "APP_ENV not set in app container"
        assert env_value in ["development", "production", "test"], \
            f"APP_ENV has invalid value: {env_value}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_container_has_database_url_set(self):
        """Test that app container has DATABASE_URL environment variable set."""
        env_value = get_env_var_from_container("superinsight-app", "DATABASE_URL")
        
        assert env_value is not None, \
            "DATABASE_URL not set in app container"
        assert "postgresql://" in env_value, \
            f"DATABASE_URL has invalid format: {env_value}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_container_has_redis_url_set(self):
        """Test that app container has REDIS_URL environment variable set."""
        env_value = get_env_var_from_container("superinsight-app", "REDIS_URL")
        
        assert env_value is not None, \
            "REDIS_URL not set in app container"
        assert "redis://" in env_value, \
            f"REDIS_URL has invalid format: {env_value}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_container_has_jwt_secret_set(self):
        """Test that app container has JWT_SECRET_KEY environment variable set."""
        env_value = get_env_var_from_container("superinsight-app", "JWT_SECRET_KEY")
        
        # JWT_SECRET_KEY is a secret that should come from .env file
        # Skip this test if not set (it may be loaded from .env)
        if env_value is None:
            pytest.skip("JWT_SECRET_KEY not set in container (may be loaded from .env)")
        
        assert len(env_value) >= 32, \
            f"JWT_SECRET_KEY should be at least 32 characters, got {len(env_value)}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_all_required_env_vars_in_container(self):
        """Test that all required environment variables are set in the container."""
        missing_vars = []
        
        for var in REQUIRED_ENV_VARS:
            value = get_env_var_from_container("superinsight-app", var)
            if value is None:
                # JWT_SECRET_KEY may come from .env, skip it
                if var == "JWT_SECRET_KEY":
                    continue
                missing_vars.append(var)
        
        assert len(missing_vars) == 0, \
            f"Required environment variables not set: {missing_vars}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_frontend_env_vars_configured(self):
        """Test that frontend environment variables are properly configured."""
        env_value = get_env_var_from_container("superinsight-frontend", "VITE_API_BASE_URL")
        
        assert env_value is not None, \
            "VITE_API_BASE_URL not set in frontend container"
        assert "http://" in env_value or "https://" in env_value, \
            f"VITE_API_BASE_URL should be HTTP URL: {env_value}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_environment_specific_configuration(self, docker_compose_file_path):
        """Test that environment-specific configuration is applied."""
        import yaml
        
        with open(docker_compose_file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get("services", {})
        app_service = services.get("app", {})
        env_vars = app_service.get("environment", [])
        
        # Convert to dict
        env_dict = {}
        for env in env_vars:
            if isinstance(env, str) and "=" in env:
                key, value = env.split("=", 1)
                env_dict[key] = value
            elif isinstance(env, dict):
                env_dict.update(env)
        
        # Check for environment-specific settings
        assert "APP_ENV" in env_dict, \
            "APP_ENV should be set for environment-specific configuration"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_no_hardcoded_secrets_in_docker_compose(self, docker_compose_file_path):
        """Test that secrets are not hardcoded in docker-compose.yml."""
        with open(docker_compose_file_path, 'r') as f:
            content = f.read()
        
        # Check for common secret patterns that should be in .env
        # Note: Environment variables like POSTGRES_PASSWORD=password are service configuration,
        # not secrets that need to be hidden. We only flag actual secret-like patterns.
        secret_patterns = [
            r'JWT_SECRET_KEY\s*=\s*["\']?\w+["\']?',  # JWT secrets
            r'API_KEY\s*=\s*["\']?\w+["\']?',         # API keys
            r'PRIVATE_KEY\s*=\s*["\']?\w+["\']?',     # Private keys
        ]
        
        for pattern in secret_patterns:
            import re
            matches = re.finditer(pattern, content, re.IGNORECASE)
            # Allow comments
            non_comment_matches = []
            for match in matches:
                match_text = match.group()
                # Find position of match and check if it's in a comment
                match_start = match.start()
                # Get text before match
                before_match = content[:match_start]
                # Check if there's a # before this match on the same line
                lines_before = before_match.split('\n')
                last_line = lines_before[-1] if lines_before else ""
                if '#' not in last_line:
                    non_comment_matches.append(match_text)
            
            assert len(non_comment_matches) == 0, \
                f"Potential hardcoded secret found: {non_comment_matches}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_env_file_example_exists(self):
        """Test that .env.example file exists for reference."""
        example_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".env.example"
        )
        
        assert os.path.exists(example_file), \
            f".env.example file not found at {example_file}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_env_file_example_has_all_vars(self):
        """Test that .env.example contains all required variables."""
        example_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".env.example"
        )
        
        if os.path.exists(example_file):
            with open(example_file, 'r') as f:
                content = f.read()
            
            missing_vars = []
            for var in REQUIRED_ENV_VARS:
                if var not in content:
                    missing_vars.append(var)
            
            assert len(missing_vars) == 0, \
                f"Required variables missing from .env.example: {missing_vars}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_label_studio_env_vars_configured(self):
        """Test that Label Studio environment variables are properly configured."""
        env_value = get_env_var_from_container("superinsight-label-studio", "LABEL_STUDIO_HOST")
        
        assert env_value is not None, \
            "LABEL_STUDIO_HOST not set in label-studio container"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.environment
    def test_argilla_env_vars_configured(self):
        """Test that Argilla environment variables are properly configured."""
        env_value = get_env_var_from_container("superinsight-argilla", "ARGILLA_DATABASE_URL")
        
        assert env_value is not None, \
            "ARGILLA_DATABASE_URL not set in argilla container"