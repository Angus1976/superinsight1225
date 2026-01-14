"""
REST API Adapter for Third-Party Text-to-SQL Tools.

Provides a base adapter for HTTP/REST-based Text-to-SQL services.
"""

import logging
import aiohttp
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..schemas import (
    SQLGenerationResult,
    PluginInfo,
    PluginConfig,
    ConnectionType,
)
from ..schema_analyzer import DatabaseSchema
from ..plugin_interface import BasePlugin, PluginCallError

logger = logging.getLogger(__name__)


class RESTAPIPlugin(BasePlugin):
    """
    REST API adapter for third-party Text-to-SQL tools.
    
    Supports HTTP/HTTPS endpoints with JSON request/response format.
    """
    
    def __init__(self, config: PluginConfig):
        """
        Initialize REST API plugin.
        
        Args:
            config: Plugin configuration with endpoint and credentials
        """
        super().__init__(config)
        self.endpoint = config.endpoint
        self.api_key = config.api_key
        self.timeout = config.timeout
        self.extra_config = config.extra_config
        
        # HTTP client settings
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = self._build_headers()
    
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if self.api_key:
            # Support different auth header formats
            auth_header = self.extra_config.get("auth_header", "Authorization")
            auth_prefix = self.extra_config.get("auth_prefix", "Bearer")
            headers[auth_header] = f"{auth_prefix} {self.api_key}"
        
        # Add custom headers
        custom_headers = self.extra_config.get("headers", {})
        headers.update(custom_headers)
        
        return headers
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name=self.config.name,
            version=self.extra_config.get("version", "1.0.0"),
            description=self.extra_config.get(
                "description",
                f"REST API plugin for {self.config.name}"
            ),
            connection_type=ConnectionType.REST_API,
            supported_db_types=self.extra_config.get("supported_db_types", []),
            config_schema={
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "api_key": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["endpoint"],
            },
            is_healthy=self._is_healthy,
            last_health_check=self._last_health_check,
        )
    
    def to_native_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None
    ) -> Dict[str, Any]:
        """
        Convert query to REST API request format.
        
        Args:
            query: Natural language query
            schema: Database schema
            
        Returns:
            Request body dictionary
        """
        # Default format - can be customized via extra_config
        request_format = self.extra_config.get("request_format", "default")
        
        if request_format == "openai":
            return self._to_openai_format(query, schema)
        elif request_format == "vanna":
            return self._to_vanna_format(query, schema)
        else:
            return self._to_default_format(query, schema)
    
    def _to_default_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema]
    ) -> Dict[str, Any]:
        """Default request format."""
        request = {
            "query": query,
            "natural_language": query,
        }
        
        if schema:
            request["schema"] = {
                "tables": schema.tables,
                "db_type": schema.db_type,
            }
        
        return request
    
    def _to_openai_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema]
    ) -> Dict[str, Any]:
        """OpenAI-compatible request format."""
        schema_context = ""
        if schema:
            schema_context = f"\n\nDatabase Schema:\n{schema.to_llm_context()}"
        
        return {
            "model": self.extra_config.get("model", "gpt-4"),
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a SQL expert. Generate SQL queries based on natural language.{schema_context}"
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.1,
        }
    
    def _to_vanna_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema]
    ) -> Dict[str, Any]:
        """Vanna.ai-compatible request format."""
        return {
            "question": query,
            "db_type": schema.db_type if schema else "postgresql",
        }
    
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the REST API endpoint.
        
        Args:
            request: Request body
            
        Returns:
            Response body
            
        Raises:
            PluginCallError: If call fails
        """
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Determine HTTP method
                method = self.extra_config.get("method", "POST").upper()
                
                # Build URL
                url = self.endpoint
                endpoint_path = self.extra_config.get("endpoint_path", "")
                if endpoint_path:
                    url = f"{url.rstrip('/')}/{endpoint_path.lstrip('/')}"
                
                # Make request
                async with session.request(
                    method,
                    url,
                    json=request,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        raise PluginCallError(
                            self.config.name,
                            f"HTTP {response.status}: {error_text}"
                        )
                    
                    result = await response.json()
                    result["_response_time_ms"] = response_time
                    
                    return result
                    
        except aiohttp.ClientError as e:
            raise PluginCallError(self.config.name, f"HTTP error: {e}")
        except Exception as e:
            raise PluginCallError(self.config.name, str(e))
    
    def from_native_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """
        Convert REST API response to unified format.
        
        Args:
            response: Response body
            
        Returns:
            SQLGenerationResult
        """
        response_format = self.extra_config.get("response_format", "default")
        
        if response_format == "openai":
            return self._from_openai_format(response)
        elif response_format == "vanna":
            return self._from_vanna_format(response)
        else:
            return self._from_default_format(response)
    
    def _from_default_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """Parse default response format."""
        return SQLGenerationResult(
            sql=response.get("sql", response.get("query", "")),
            method_used=f"third_party:{self.config.name}",
            confidence=response.get("confidence", 0.8),
            execution_time_ms=response.get("_response_time_ms", 0.0),
            explanation=response.get("explanation"),
            metadata={
                "plugin": self.config.name,
                "raw_response": response,
            },
        )
    
    def _from_openai_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """Parse OpenAI-compatible response format."""
        content = ""
        if "choices" in response and response["choices"]:
            content = response["choices"][0].get("message", {}).get("content", "")
        
        # Extract SQL from content
        sql = self._extract_sql_from_text(content)
        
        return SQLGenerationResult(
            sql=sql,
            method_used=f"third_party:{self.config.name}",
            confidence=0.85,
            execution_time_ms=response.get("_response_time_ms", 0.0),
            explanation=content,
            metadata={
                "plugin": self.config.name,
                "model": response.get("model"),
                "usage": response.get("usage"),
            },
        )
    
    def _from_vanna_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        """Parse Vanna.ai response format."""
        return SQLGenerationResult(
            sql=response.get("sql", ""),
            method_used=f"third_party:{self.config.name}",
            confidence=response.get("confidence", 0.8),
            execution_time_ms=response.get("_response_time_ms", 0.0),
            explanation=response.get("explanation"),
            metadata={
                "plugin": self.config.name,
                "training_data_used": response.get("training_data_used"),
            },
        )
    
    def _extract_sql_from_text(self, text: str) -> str:
        """Extract SQL from text that may contain markdown code blocks."""
        import re
        
        # Try to find SQL in code blocks
        sql_pattern = r"```(?:sql)?\s*([\s\S]*?)```"
        matches = re.findall(sql_pattern, text, re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, return the whole text
        return text.strip()
    
    async def health_check(self) -> bool:
        """
        Check if the REST API is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        self._last_health_check = datetime.utcnow()
        
        try:
            # Try health endpoint if configured
            health_path = self.extra_config.get("health_path", "/health")
            url = f"{self.endpoint.rstrip('/')}{health_path}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    self._is_healthy = response.status < 400
                    return self._is_healthy
                    
        except Exception as e:
            logger.warning(f"Health check failed for {self.config.name}: {e}")
            self._is_healthy = False
            return False
