"""
Rate Limiter for AI Gateway Integration

Implements distributed rate limiting using Redis with sliding window algorithm.
Supports both per-minute rate limits and daily/monthly quotas.
"""
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis.asyncio as redis

from src.config.settings import settings


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after_seconds: Optional[int] = None


@dataclass
class QuotaResult:
    """Result of quota check."""
    allowed: bool
    used: int
    limit: int
    reset_at: datetime


class RateLimiter:
    """
    Distributed rate limiter using Redis sliding window algorithm.
    
    Features:
    - Sliding window rate limiting for accurate per-minute limits
    - Daily and monthly quota tracking
    - Automatic counter reset
    - Thread-safe distributed operations
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize rate limiter with Redis client."""
        self.redis = redis_client or redis.from_url(
            settings.redis.redis_url,
            decode_responses=True
        )
    
    async def check_rate_limit(
        self,
        gateway_id: str,
        limit_per_minute: int
    ) -> RateLimitResult:
        """
        Check if request is within rate limit using sliding window.
        
        Args:
            gateway_id: Gateway identifier
            limit_per_minute: Maximum requests per minute
            
        Returns:
            RateLimitResult with allowed status and metadata
        """
        now = time.time()
        window_start = now - 60
        key = f"rate_limit:{gateway_id}"
        
        # Remove old entries outside window
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        current_count = await self.redis.zcard(key)
        
        if current_count >= limit_per_minute:
            # Get oldest request timestamp
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            reset_time = oldest[0][1] + 60 if oldest else now + 60
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=datetime.fromtimestamp(reset_time),
                retry_after_seconds=int(reset_time - now)
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=limit_per_minute - current_count - 1,
            reset_at=datetime.fromtimestamp(window_start + 60)
        )
    
    async def check_quota(
        self,
        gateway_id: str,
        quota_limit: int,
        period: str = "day"
    ) -> QuotaResult:
        """
        Check if request is within quota limit.
        
        Args:
            gateway_id: Gateway identifier
            quota_limit: Maximum requests per period
            period: "day" or "month"
            
        Returns:
            QuotaResult with quota status
        """
        now = datetime.utcnow()
        
        if period == "day":
            period_key = now.strftime("%Y-%m-%d")
            reset_at = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:  # month
            period_key = now.strftime("%Y-%m")
            next_month = now.replace(day=1) + timedelta(days=32)
            reset_at = next_month.replace(day=1, hour=0, minute=0, second=0)
        
        key = f"quota:{gateway_id}:{period}:{period_key}"
        current_usage = await self.redis.get(key)
        used = int(current_usage) if current_usage else 0
        
        return QuotaResult(
            allowed=used < quota_limit,
            used=used,
            limit=quota_limit,
            reset_at=reset_at
        )
    
    async def record_request(
        self,
        gateway_id: str,
        limit_per_minute: int,
        quota_per_day: Optional[int] = None,
        quota_per_month: Optional[int] = None
    ) -> None:
        """
        Record a request for rate limiting and quota tracking.
        
        Args:
            gateway_id: Gateway identifier
            limit_per_minute: Rate limit for sliding window
            quota_per_day: Optional daily quota
            quota_per_month: Optional monthly quota
        """
        now = time.time()
        
        # Record for rate limiting (sliding window)
        rate_key = f"rate_limit:{gateway_id}"
        await self.redis.zadd(rate_key, {str(now): now})
        await self.redis.expire(rate_key, 60)
        
        # Record for daily quota
        if quota_per_day:
            day_key = f"quota:{gateway_id}:day:{datetime.utcnow().strftime('%Y-%m-%d')}"
            await self.redis.incr(day_key)
            await self.redis.expire(day_key, 86400)
        
        # Record for monthly quota
        if quota_per_month:
            month_key = f"quota:{gateway_id}:month:{datetime.utcnow().strftime('%Y-%m')}"
            await self.redis.incr(month_key)
            await self.redis.expire(month_key, 2678400)  # ~31 days
    
    async def reset_counters(self, gateway_id: str) -> None:
        """
        Reset all counters for a gateway.
        
        Args:
            gateway_id: Gateway identifier
        """
        # Delete rate limit key
        await self.redis.delete(f"rate_limit:{gateway_id}")
        
        # Delete quota keys
        now = datetime.utcnow()
        day_key = f"quota:{gateway_id}:day:{now.strftime('%Y-%m-%d')}"
        month_key = f"quota:{gateway_id}:month:{now.strftime('%Y-%m')}"
        
        await self.redis.delete(day_key)
        await self.redis.delete(month_key)
    
    async def get_usage_stats(
        self,
        gateway_id: str
    ) -> Tuple[int, int, int]:
        """
        Get current usage statistics.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            Tuple of (current_rate, daily_usage, monthly_usage)
        """
        now = datetime.utcnow()
        
        # Current rate (requests in last minute)
        rate_key = f"rate_limit:{gateway_id}"
        window_start = time.time() - 60
        await self.redis.zremrangebyscore(rate_key, 0, window_start)
        current_rate = await self.redis.zcard(rate_key)
        
        # Daily usage
        day_key = f"quota:{gateway_id}:day:{now.strftime('%Y-%m-%d')}"
        daily_usage = await self.redis.get(day_key)
        daily_usage = int(daily_usage) if daily_usage else 0
        
        # Monthly usage
        month_key = f"quota:{gateway_id}:month:{now.strftime('%Y-%m')}"
        monthly_usage = await self.redis.get(month_key)
        monthly_usage = int(monthly_usage) if monthly_usage else 0
        
        return (current_rate, daily_usage, monthly_usage)
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()
