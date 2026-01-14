"""
Configuration Validator for SuperInsight Platform.

Provides validation for various configuration types including:
- LLM configurations
- Database connections
- Sync strategies
- Third-party tools

Also provides connection testing and permission verification.
"""

import re
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime
from urllib.parse import urlparse

from src.admin.schemas import (
    ValidationResult,
    ValidationError,
    ConnectionTestResult,
    LLMConfigCreate,
    LLMConfigUpdate,
    DBConfigCreate,
    DBConfigUpdate,
    SyncStrategyCreate,
    SyncStrategyUpdate,
    DatabaseType,
    LLMType,
    SyncMode,
)

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Configuration validator for admin configurations.
    
    Validates configuration data for correctness and completeness,
    and provides connection testing capabilities.
    """
    
    # Database default ports
    DB_DEFAULT_PORTS = {
        DatabaseType.POSTGRESQL: 5432,
        DatabaseType.MYSQL: 3306,
        DatabaseType.SQLITE: None,
        DatabaseType.ORACLE: 1521,
        DatabaseType.SQLSERVER: 1433,
    }
    
    # LLM default endpoints
    LLM_DEFAULT_ENDPOINTS = {
        LLMType.LOCAL_OLLAMA: "http://localhost:11434",
        LLMType.OPENAI: "https://api.openai.com/v1",
        LLMType.QIANWEN: "https://dashscope.aliyuncs.com/api/v1",
        LLMType.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
        LLMType.HUNYUAN: "https://hunyuan.tencentcloudapi.com",
    }
    
    def __init__(self):
        """Initialize the config validator."""
        self._cron_pattern = re.compile(
            r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*\/([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) '
            r'(\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3])) '
            r'(\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*\/([1-9]|1[0-9]|2[0-9]|3[0-1])) '
            r'(\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2])) '
            r'(\*|([0-6])|\*\/([0-6]))$'
        )
    
    def validate_llm_config(
        self,
        config: Union[LLMConfigCreate, LLMConfigUpdate, Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate LLM configuration.
        
        Args:
            config: LLM configuration to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []
        
        # Convert to dict if needed
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump(exclude_unset=True)
        elif hasattr(config, 'dict'):
            config_dict = config.dict(exclude_unset=True)
        else:
            config_dict = config
        
        # Validate LLM type
        llm_type = config_dict.get('llm_type')
        if llm_type:
            if isinstance(llm_type, str):
                try:
                    llm_type = LLMType(llm_type)
                except ValueError:
                    errors.append(ValidationError(
                        field="llm_type",
                        message=f"Invalid LLM type: {llm_type}",
                        code="invalid_llm_type"
                    ))
        
        # Validate API endpoint
        api_endpoint = config_dict.get('api_endpoint')
        if api_endpoint:
            if not self._is_valid_url(api_endpoint):
                errors.append(ValidationError(
                    field="api_endpoint",
                    message=f"Invalid API endpoint URL: {api_endpoint}",
                    code="invalid_url"
                ))
        
        # Validate API key for cloud providers
        api_key = config_dict.get('api_key')
        if llm_type and llm_type != LLMType.LOCAL_OLLAMA:
            if not api_key:
                warnings.append(f"API key is recommended for {llm_type}")
        
        # Validate temperature
        temperature = config_dict.get('temperature')
        if temperature is not None:
            if not (0.0 <= temperature <= 2.0):
                errors.append(ValidationError(
                    field="temperature",
                    message="Temperature must be between 0.0 and 2.0",
                    code="invalid_range"
                ))
        
        # Validate max_tokens
        max_tokens = config_dict.get('max_tokens')
        if max_tokens is not None:
            if not (1 <= max_tokens <= 128000):
                errors.append(ValidationError(
                    field="max_tokens",
                    message="max_tokens must be between 1 and 128000",
                    code="invalid_range"
                ))
        
        # Validate timeout
        timeout = config_dict.get('timeout_seconds')
        if timeout is not None:
            if not (1 <= timeout <= 600):
                errors.append(ValidationError(
                    field="timeout_seconds",
                    message="timeout_seconds must be between 1 and 600",
                    code="invalid_range"
                ))
        
        # Validate model name
        model_name = config_dict.get('model_name')
        if model_name is not None and not model_name.strip():
            errors.append(ValidationError(
                field="model_name",
                message="Model name cannot be empty",
                code="required_field"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_db_config(
        self,
        config: Union[DBConfigCreate, DBConfigUpdate, Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate database connection configuration.
        
        Args:
            config: Database configuration to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []
        
        # Convert to dict if needed
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump(exclude_unset=True)
        elif hasattr(config, 'dict'):
            config_dict = config.dict(exclude_unset=True)
        else:
            config_dict = config
        
        # Validate database type
        db_type = config_dict.get('db_type')
        if db_type:
            if isinstance(db_type, str):
                try:
                    db_type = DatabaseType(db_type)
                except ValueError:
                    errors.append(ValidationError(
                        field="db_type",
                        message=f"Invalid database type: {db_type}",
                        code="invalid_db_type"
                    ))
        
        # Validate host
        host = config_dict.get('host')
        if host is not None:
            if not host.strip():
                errors.append(ValidationError(
                    field="host",
                    message="Host cannot be empty",
                    code="required_field"
                ))
            elif not self._is_valid_host(host):
                errors.append(ValidationError(
                    field="host",
                    message=f"Invalid host: {host}",
                    code="invalid_host"
                ))
        
        # Validate port
        port = config_dict.get('port')
        if port is not None:
            if not (1 <= port <= 65535):
                errors.append(ValidationError(
                    field="port",
                    message="Port must be between 1 and 65535",
                    code="invalid_range"
                ))
        
        # Validate database name
        database = config_dict.get('database')
        if database is not None and not database.strip():
            errors.append(ValidationError(
                field="database",
                message="Database name cannot be empty",
                code="required_field"
            ))
        
        # Validate username
        username = config_dict.get('username')
        if username is not None and not username.strip():
            errors.append(ValidationError(
                field="username",
                message="Username cannot be empty",
                code="required_field"
            ))
        
        # Warn about missing password
        password = config_dict.get('password')
        if password is None and db_type != DatabaseType.SQLITE:
            warnings.append("Password is recommended for database connections")
        
        # Warn about non-readonly connections
        is_readonly = config_dict.get('is_readonly', True)
        if not is_readonly:
            warnings.append("Non-readonly connections may pose security risks")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_sync_config(
        self,
        config: Union[SyncStrategyCreate, SyncStrategyUpdate, Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate sync strategy configuration.
        
        Args:
            config: Sync strategy configuration to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []
        
        # Convert to dict if needed
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump(exclude_unset=True)
        elif hasattr(config, 'dict'):
            config_dict = config.dict(exclude_unset=True)
        else:
            config_dict = config
        
        # Validate sync mode
        mode = config_dict.get('mode')
        if mode:
            if isinstance(mode, str):
                try:
                    mode = SyncMode(mode)
                except ValueError:
                    errors.append(ValidationError(
                        field="mode",
                        message=f"Invalid sync mode: {mode}",
                        code="invalid_sync_mode"
                    ))
        
        # Validate incremental field for incremental mode
        incremental_field = config_dict.get('incremental_field')
        if mode == SyncMode.INCREMENTAL:
            if not incremental_field:
                errors.append(ValidationError(
                    field="incremental_field",
                    message="Incremental field is required for incremental sync mode",
                    code="required_field"
                ))
        
        # Validate schedule (cron expression)
        schedule = config_dict.get('schedule')
        if schedule:
            if not self._is_valid_cron(schedule):
                errors.append(ValidationError(
                    field="schedule",
                    message=f"Invalid cron expression: {schedule}",
                    code="invalid_cron"
                ))
        
        # Validate batch size
        batch_size = config_dict.get('batch_size')
        if batch_size is not None:
            if not (1 <= batch_size <= 100000):
                errors.append(ValidationError(
                    field="batch_size",
                    message="Batch size must be between 1 and 100000",
                    code="invalid_range"
                ))
        
        # Validate filter conditions
        filter_conditions = config_dict.get('filter_conditions', [])
        for i, condition in enumerate(filter_conditions):
            if not isinstance(condition, dict):
                errors.append(ValidationError(
                    field=f"filter_conditions[{i}]",
                    message="Filter condition must be an object",
                    code="invalid_type"
                ))
                continue
            
            if 'field' not in condition:
                errors.append(ValidationError(
                    field=f"filter_conditions[{i}].field",
                    message="Filter condition must have a field",
                    code="required_field"
                ))
            
            if 'operator' not in condition:
                errors.append(ValidationError(
                    field=f"filter_conditions[{i}].operator",
                    message="Filter condition must have an operator",
                    code="required_field"
                ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def test_db_connection(
        self,
        config: Union[DBConfigCreate, Dict[str, Any]],
        password: Optional[str] = None
    ) -> ConnectionTestResult:
        """
        Test database connection.
        
        Args:
            config: Database configuration to test
            password: Decrypted password (if not in config)
            
        Returns:
            ConnectionTestResult with connection status
        """
        import time
        
        # Convert to dict if needed
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump()
        elif hasattr(config, 'dict'):
            config_dict = config.dict()
        else:
            config_dict = config.copy()
        
        # Use provided password or from config
        if password:
            config_dict['password'] = password
        
        db_type = config_dict.get('db_type')
        if isinstance(db_type, str):
            db_type = DatabaseType(db_type)
        
        start_time = time.time()
        
        try:
            if db_type == DatabaseType.POSTGRESQL:
                result = await self._test_postgresql_connection(config_dict)
            elif db_type == DatabaseType.MYSQL:
                result = await self._test_mysql_connection(config_dict)
            elif db_type == DatabaseType.SQLITE:
                result = await self._test_sqlite_connection(config_dict)
            elif db_type == DatabaseType.ORACLE:
                result = await self._test_oracle_connection(config_dict)
            elif db_type == DatabaseType.SQLSERVER:
                result = await self._test_sqlserver_connection(config_dict)
            else:
                return ConnectionTestResult(
                    success=False,
                    latency_ms=0,
                    error_message=f"Unsupported database type: {db_type}"
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if result[0]:
                return ConnectionTestResult(
                    success=True,
                    latency_ms=latency_ms,
                    details=result[1]
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    latency_ms=latency_ms,
                    error_message=result[1]
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Database connection test failed: {e}")
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=str(e)
            )
    
    async def verify_readonly_permission(
        self,
        config: Union[DBConfigCreate, Dict[str, Any]],
        password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Verify that the database connection has only read-only permissions.
        
        Args:
            config: Database configuration to verify
            password: Decrypted password (if not in config)
            
        Returns:
            Tuple of (is_readonly, message)
        """
        # Convert to dict if needed
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump()
        elif hasattr(config, 'dict'):
            config_dict = config.dict()
        else:
            config_dict = config.copy()
        
        if password:
            config_dict['password'] = password
        
        db_type = config_dict.get('db_type')
        if isinstance(db_type, str):
            db_type = DatabaseType(db_type)
        
        try:
            if db_type == DatabaseType.POSTGRESQL:
                return await self._verify_postgresql_readonly(config_dict)
            elif db_type == DatabaseType.MYSQL:
                return await self._verify_mysql_readonly(config_dict)
            elif db_type == DatabaseType.SQLITE:
                # SQLite doesn't have user permissions
                return (True, "SQLite connections are file-based")
            else:
                return (False, f"Read-only verification not implemented for {db_type}")
                
        except Exception as e:
            logger.error(f"Read-only verification failed: {e}")
            return (False, str(e))
    
    # ========== Private helper methods ==========
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if a string is a valid URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_valid_host(self, host: str) -> bool:
        """Check if a string is a valid hostname or IP address."""
        # Simple validation - hostname or IP
        hostname_pattern = re.compile(
            r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*'
            r'([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        )
        ip_pattern = re.compile(
            r'^(\d{1,3}\.){3}\d{1,3}$'
        )
        
        return bool(hostname_pattern.match(host) or ip_pattern.match(host) or host == 'localhost')
    
    def _is_valid_cron(self, cron: str) -> bool:
        """Check if a string is a valid cron expression."""
        # Simple cron validation (5 fields)
        parts = cron.strip().split()
        if len(parts) != 5:
            return False
        
        # Define valid ranges for each field
        # minute (0-59), hour (0-23), day of month (1-31), month (1-12), day of week (0-6)
        field_ranges = [
            (0, 59),   # minute
            (0, 23),   # hour
            (1, 31),   # day of month
            (1, 12),   # month
            (0, 6),    # day of week
        ]
        
        def validate_value(value: int, min_val: int, max_val: int) -> bool:
            """Check if value is within valid range."""
            return min_val <= value <= max_val
        
        def validate_field(field: str, min_val: int, max_val: int) -> bool:
            """Validate a single cron field."""
            if field == '*':
                return True
            
            if '/' in field:
                base, step = field.split('/', 1)
                try:
                    step_val = int(step)
                    if step_val < 1:
                        return False
                    if base == '*':
                        return True
                    base_val = int(base)
                    return validate_value(base_val, min_val, max_val)
                except ValueError:
                    return False
            
            if '-' in field:
                try:
                    start, end = field.split('-', 1)
                    start_val = int(start)
                    end_val = int(end)
                    return (validate_value(start_val, min_val, max_val) and 
                            validate_value(end_val, min_val, max_val))
                except ValueError:
                    return False
            
            if ',' in field:
                try:
                    for val in field.split(','):
                        if not validate_value(int(val), min_val, max_val):
                            return False
                    return True
                except ValueError:
                    return False
            
            try:
                return validate_value(int(field), min_val, max_val)
            except ValueError:
                return False
        
        # Validate each field
        try:
            for i, (part, (min_val, max_val)) in enumerate(zip(parts, field_ranges)):
                if not validate_field(part, min_val, max_val):
                    return False
            return True
        except (ValueError, IndexError):
            return False
    
    async def _test_postgresql_connection(self, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Test PostgreSQL connection."""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config.get('password', ''),
                timeout=10
            )
            
            # Get server version
            version = await conn.fetchval('SELECT version()')
            await conn.close()
            
            return (True, {"version": version})
            
        except ImportError:
            # Fallback to psycopg2
            try:
                import psycopg2
                
                conn = psycopg2.connect(
                    host=config['host'],
                    port=config['port'],
                    dbname=config['database'],
                    user=config['username'],
                    password=config.get('password', ''),
                    connect_timeout=10
                )
                
                cursor = conn.cursor()
                cursor.execute('SELECT version()')
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                return (True, {"version": version})
                
            except Exception as e:
                return (False, str(e))
        except Exception as e:
            return (False, str(e))
    
    async def _test_mysql_connection(self, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Test MySQL connection."""
        try:
            import aiomysql
            
            conn = await aiomysql.connect(
                host=config['host'],
                port=config['port'],
                db=config['database'],
                user=config['username'],
                password=config.get('password', ''),
                connect_timeout=10
            )
            
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT VERSION()')
                version = await cursor.fetchone()
            
            conn.close()
            
            return (True, {"version": version[0] if version else "unknown"})
            
        except ImportError:
            return (False, "aiomysql not installed")
        except Exception as e:
            return (False, str(e))
    
    async def _test_sqlite_connection(self, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Test SQLite connection."""
        try:
            import aiosqlite
            
            db_path = config.get('database', ':memory:')
            
            async with aiosqlite.connect(db_path) as conn:
                cursor = await conn.execute('SELECT sqlite_version()')
                version = await cursor.fetchone()
            
            return (True, {"version": version[0] if version else "unknown"})
            
        except ImportError:
            # Fallback to sqlite3
            try:
                import sqlite3
                
                db_path = config.get('database', ':memory:')
                conn = sqlite3.connect(db_path, timeout=10)
                cursor = conn.cursor()
                cursor.execute('SELECT sqlite_version()')
                version = cursor.fetchone()
                cursor.close()
                conn.close()
                
                return (True, {"version": version[0] if version else "unknown"})
                
            except Exception as e:
                return (False, str(e))
        except Exception as e:
            return (False, str(e))
    
    async def _test_oracle_connection(self, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Test Oracle connection."""
        try:
            import cx_Oracle
            
            dsn = cx_Oracle.makedsn(
                config['host'],
                config['port'],
                service_name=config['database']
            )
            
            conn = cx_Oracle.connect(
                user=config['username'],
                password=config.get('password', ''),
                dsn=dsn
            )
            
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM V$VERSION WHERE ROWNUM = 1')
            version = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return (True, {"version": version[0] if version else "unknown"})
            
        except ImportError:
            return (False, "cx_Oracle not installed")
        except Exception as e:
            return (False, str(e))
    
    async def _test_sqlserver_connection(self, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Test SQL Server connection."""
        try:
            import pyodbc
            
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={config['host']},{config['port']};"
                f"DATABASE={config['database']};"
                f"UID={config['username']};"
                f"PWD={config.get('password', '')}"
            )
            
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            cursor.execute('SELECT @@VERSION')
            version = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return (True, {"version": version[0] if version else "unknown"})
            
        except ImportError:
            return (False, "pyodbc not installed")
        except Exception as e:
            return (False, str(e))
    
    async def _verify_postgresql_readonly(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify PostgreSQL connection is read-only."""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config.get('password', ''),
                timeout=10
            )
            
            # Check if user has write permissions
            query = """
                SELECT has_database_privilege($1, $2, 'CREATE')
                    OR has_database_privilege($1, $2, 'CONNECT')
                    AND EXISTS (
                        SELECT 1 FROM information_schema.table_privileges
                        WHERE grantee = $1
                        AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
                    )
            """
            
            has_write = await conn.fetchval(
                query,
                config['username'],
                config['database']
            )
            
            await conn.close()
            
            if has_write:
                return (False, "User has write permissions")
            else:
                return (True, "User has read-only permissions")
                
        except Exception as e:
            return (False, f"Permission check failed: {e}")
    
    async def _verify_mysql_readonly(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify MySQL connection is read-only."""
        try:
            import aiomysql
            
            conn = await aiomysql.connect(
                host=config['host'],
                port=config['port'],
                db=config['database'],
                user=config['username'],
                password=config.get('password', ''),
                connect_timeout=10
            )
            
            async with conn.cursor() as cursor:
                # Check user privileges
                await cursor.execute(f"SHOW GRANTS FOR CURRENT_USER()")
                grants = await cursor.fetchall()
            
            conn.close()
            
            # Check for write privileges
            write_privs = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
            for grant in grants:
                grant_str = grant[0].upper()
                for priv in write_privs:
                    if priv in grant_str and 'ALL PRIVILEGES' not in grant_str:
                        return (False, f"User has {priv} permission")
                if 'ALL PRIVILEGES' in grant_str:
                    return (False, "User has ALL PRIVILEGES")
            
            return (True, "User has read-only permissions")
            
        except Exception as e:
            return (False, f"Permission check failed: {e}")


# Global validator instance
_config_validator: Optional[ConfigValidator] = None


def get_config_validator() -> ConfigValidator:
    """Get the global config validator instance."""
    global _config_validator
    if _config_validator is None:
        _config_validator = ConfigValidator()
    return _config_validator
