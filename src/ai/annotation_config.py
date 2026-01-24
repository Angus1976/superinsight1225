"""
AI Annotation Configuration Module

Provides centralized configuration for AI annotation features:
- Batch processing settings
- Model caching settings
- Rate limiting settings
- Quality thresholds
- WebSocket settings
- Engine settings
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from functools import lru_cache


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing."""
    batch_size: int = 100
    max_concurrency: int = 20
    timeout_seconds: int = 3600
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class ModelCacheConfig:
    """Configuration for model caching."""
    strategy: str = "lru"  # lru, lfu, ttl
    max_size_mb: int = 1024
    ttl_seconds: int = 3600
    redis_enabled: bool = True
    memory_fallback: bool = True


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 1000
    burst_size: int = 100
    per_user_limit: int = 100
    per_project_limit: int = 500


@dataclass
class QualityThresholdsConfig:
    """Configuration for quality thresholds."""
    confidence_threshold: float = 0.7
    review_threshold: float = 0.5
    auto_accept_threshold: float = 0.95
    accuracy_target: float = 0.9
    consistency_target: float = 0.85
    completeness_target: float = 0.9


@dataclass
class SuggestionConfig:
    """Configuration for real-time suggestions."""
    latency_target_ms: int = 100
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    max_suggestions_per_request: int = 10
    pattern_matching_enabled: bool = True


@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connections."""
    heartbeat_interval: int = 30
    max_connections_per_project: int = 100
    message_queue_size: int = 1000
    reconnect_delay_seconds: int = 3
    max_reconnect_attempts: int = 5


@dataclass
class EngineConfig:
    """Configuration for annotation engines."""
    health_check_interval: int = 30
    max_consecutive_failures: int = 3
    fallback_enabled: bool = True
    hot_reload_enabled: bool = True
    default_timeout_seconds: int = 30


@dataclass
class RedisConfig:
    """Configuration for Redis."""
    url: str = "redis://localhost:6379/0"
    max_connections: int = 50
    pubsub_channel_prefix: str = "annotation:"
    cache_key_prefix: str = "ai_annotation:"


@dataclass
class LabelStudioConfig:
    """Configuration for Label Studio integration."""
    url: str = "http://localhost:8080"
    api_key: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class ArgillaConfig:
    """Configuration for Argilla integration."""
    url: str = "http://localhost:6900"
    api_key: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class AIAnnotationConfig:
    """Main configuration class for AI annotation."""
    batch_processing: BatchProcessingConfig = field(default_factory=BatchProcessingConfig)
    model_cache: ModelCacheConfig = field(default_factory=ModelCacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    quality_thresholds: QualityThresholdsConfig = field(default_factory=QualityThresholdsConfig)
    suggestion: SuggestionConfig = field(default_factory=SuggestionConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    label_studio: LabelStudioConfig = field(default_factory=LabelStudioConfig)
    argilla: ArgillaConfig = field(default_factory=ArgillaConfig)
    
    @classmethod
    def from_env(cls) -> 'AIAnnotationConfig':
        """Create configuration from environment variables."""
        return cls(
            batch_processing=BatchProcessingConfig(
                batch_size=int(os.getenv('ANNOTATION_BATCH_SIZE', '100')),
                max_concurrency=int(os.getenv('ANNOTATION_MAX_CONCURRENCY', '20')),
                timeout_seconds=int(os.getenv('ANNOTATION_BATCH_TIMEOUT_SECONDS', '3600')),
            ),
            model_cache=ModelCacheConfig(
                strategy=os.getenv('MODEL_CACHE_STRATEGY', 'lru'),
                max_size_mb=int(os.getenv('MODEL_CACHE_MAX_SIZE_MB', '1024')),
                ttl_seconds=int(os.getenv('MODEL_CACHE_TTL_SECONDS', '3600')),
            ),
            rate_limit=RateLimitConfig(
                requests_per_minute=int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '1000')),
                burst_size=int(os.getenv('RATE_LIMIT_BURST_SIZE', '100')),
            ),
            quality_thresholds=QualityThresholdsConfig(
                confidence_threshold=float(os.getenv('ANNOTATION_CONFIDENCE_THRESHOLD', '0.7')),
                review_threshold=float(os.getenv('ANNOTATION_REVIEW_THRESHOLD', '0.5')),
                auto_accept_threshold=float(os.getenv('ANNOTATION_AUTO_ACCEPT_THRESHOLD', '0.95')),
            ),
            suggestion=SuggestionConfig(
                latency_target_ms=int(os.getenv('SUGGESTION_LATENCY_TARGET_MS', '100')),
                cache_enabled=os.getenv('SUGGESTION_CACHE_ENABLED', 'true').lower() == 'true',
                cache_ttl_seconds=int(os.getenv('SUGGESTION_CACHE_TTL_SECONDS', '300')),
            ),
            websocket=WebSocketConfig(
                heartbeat_interval=int(os.getenv('WEBSOCKET_HEARTBEAT_INTERVAL', '30')),
                max_connections_per_project=int(os.getenv('WEBSOCKET_MAX_CONNECTIONS_PER_PROJECT', '100')),
                message_queue_size=int(os.getenv('WEBSOCKET_MESSAGE_QUEUE_SIZE', '1000')),
            ),
            engine=EngineConfig(
                health_check_interval=int(os.getenv('ENGINE_HEALTH_CHECK_INTERVAL', '30')),
                max_consecutive_failures=int(os.getenv('ENGINE_MAX_CONSECUTIVE_FAILURES', '3')),
                fallback_enabled=os.getenv('ENGINE_FALLBACK_ENABLED', 'true').lower() == 'true',
            ),
            redis=RedisConfig(
                url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
                pubsub_channel_prefix=os.getenv('REDIS_PUBSUB_CHANNEL_PREFIX', 'annotation:'),
            ),
            label_studio=LabelStudioConfig(
                url=os.getenv('LABEL_STUDIO_URL', 'http://localhost:8080'),
                api_key=os.getenv('LABEL_STUDIO_API_KEY', ''),
            ),
            argilla=ArgillaConfig(
                url=os.getenv('ARGILLA_URL', 'http://localhost:6900'),
                api_key=os.getenv('ARGILLA_API_KEY', ''),
            ),
        )


@lru_cache(maxsize=1)
def get_annotation_config() -> AIAnnotationConfig:
    """Get cached annotation configuration."""
    return AIAnnotationConfig.from_env()


def reload_config() -> AIAnnotationConfig:
    """Reload configuration from environment."""
    get_annotation_config.cache_clear()
    return get_annotation_config()
