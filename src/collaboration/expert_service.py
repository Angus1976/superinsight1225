"""
Expert Management Service (专家管理服务)

Provides CRUD operations and recommendation functionality for ontology domain experts.
Implements Task 3 from ontology-expert-collaboration specification.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class ExpertiseArea(str, Enum):
    """Expertise areas for ontology domain experts (本体领域专家专业领域)"""
    # Core domains
    FINANCE = "finance"  # 金融
    HEALTHCARE = "healthcare"  # 医疗
    MANUFACTURING = "manufacturing"  # 制造
    RETAIL = "retail"  # 零售
    LOGISTICS = "logistics"  # 物流
    ENERGY = "energy"  # 能源
    TELECOM = "telecom"  # 电信
    EDUCATION = "education"  # 教育
    GOVERNMENT = "government"  # 政府

    # Technical domains
    DATA_MODELING = "data_modeling"  # 数据建模
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱
    SEMANTIC_WEB = "semantic_web"  # 语义网
    NLP = "nlp"  # 自然语言处理
    MACHINE_LEARNING = "machine_learning"  # 机器学习

    # Compliance domains
    DATA_SECURITY = "data_security"  # 数据安全
    PRIVACY = "privacy"  # 隐私保护
    COMPLIANCE = "compliance"  # 合规

    # Regional domains
    CHINA_BUSINESS = "china_business"  # 中国业务
    INTERNATIONAL = "international"  # 国际业务


class CertificationType(str, Enum):
    """Certification types for experts (专家认证类型)"""
    ONTOLOGY_ENGINEER = "ontology_engineer"  # 本体工程师
    DATA_ARCHITECT = "data_architect"  # 数据架构师
    KNOWLEDGE_ENGINEER = "knowledge_engineer"  # 知识工程师
    DOMAIN_EXPERT = "domain_expert"  # 领域专家
    COMPLIANCE_OFFICER = "compliance_officer"  # 合规官
    SENIOR_REVIEWER = "senior_reviewer"  # 高级审核员


class ExpertStatus(str, Enum):
    """Expert status (专家状态)"""
    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 非活跃
    ON_LEAVE = "on_leave"  # 休假
    SUSPENDED = "suspended"  # 暂停


class AvailabilityLevel(str, Enum):
    """Expert availability level (专家可用性级别)"""
    HIGH = "high"  # 高
    MEDIUM = "medium"  # 中
    LOW = "low"  # 低
    UNAVAILABLE = "unavailable"  # 不可用


# Related expertise areas for fallback recommendations
RELATED_EXPERTISE: Dict[ExpertiseArea, List[ExpertiseArea]] = {
    ExpertiseArea.FINANCE: [ExpertiseArea.COMPLIANCE, ExpertiseArea.DATA_SECURITY],
    ExpertiseArea.HEALTHCARE: [ExpertiseArea.PRIVACY, ExpertiseArea.COMPLIANCE],
    ExpertiseArea.MANUFACTURING: [ExpertiseArea.LOGISTICS, ExpertiseArea.ENERGY],
    ExpertiseArea.DATA_MODELING: [ExpertiseArea.KNOWLEDGE_GRAPH, ExpertiseArea.SEMANTIC_WEB],
    ExpertiseArea.KNOWLEDGE_GRAPH: [ExpertiseArea.DATA_MODELING, ExpertiseArea.NLP],
    ExpertiseArea.DATA_SECURITY: [ExpertiseArea.PRIVACY, ExpertiseArea.COMPLIANCE],
    ExpertiseArea.PRIVACY: [ExpertiseArea.DATA_SECURITY, ExpertiseArea.COMPLIANCE],
    ExpertiseArea.COMPLIANCE: [ExpertiseArea.DATA_SECURITY, ExpertiseArea.PRIVACY],
    ExpertiseArea.CHINA_BUSINESS: [ExpertiseArea.COMPLIANCE, ExpertiseArea.FINANCE],
}


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class ExpertProfileCreate(BaseModel):
    """Create expert profile request (创建专家档案请求)"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    expertise_areas: List[ExpertiseArea] = Field(..., min_length=1)
    certifications: List[CertificationType] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["zh-CN"])
    department: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None

    @field_validator("expertise_areas")
    @classmethod
    def validate_expertise_areas(cls, v: List[ExpertiseArea]) -> List[ExpertiseArea]:
        """Validate that expertise areas are not empty and unique."""
        if not v:
            raise ValueError("At least one expertise area is required")
        if len(v) != len(set(v)):
            raise ValueError("Expertise areas must be unique")
        return v


class ExpertProfileUpdate(BaseModel):
    """Update expert profile request (更新专家档案请求)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    expertise_areas: Optional[List[ExpertiseArea]] = None
    certifications: Optional[List[CertificationType]] = None
    languages: Optional[List[str]] = None
    department: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[ExpertStatus] = None
    availability: Optional[AvailabilityLevel] = None


class ContributionMetrics(BaseModel):
    """Expert contribution metrics (专家贡献指标)"""
    total_contributions: int = 0
    accepted_contributions: int = 0
    rejected_contributions: int = 0
    pending_contributions: int = 0
    quality_score: float = 0.0  # 0.0 to 100.0
    recognition_score: float = 0.0  # 0.0 to 100.0
    peer_reviews_given: int = 0
    peer_reviews_received: int = 0
    average_review_rating: float = 0.0  # 0.0 to 5.0

    @property
    def acceptance_rate(self) -> float:
        """Calculate acceptance rate."""
        total = self.accepted_contributions + self.rejected_contributions
        if total == 0:
            return 0.0
        return self.accepted_contributions / total * 100


class ExpertProfile(BaseModel):
    """Expert profile (专家档案)"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    expertise_areas: List[ExpertiseArea]
    certifications: List[CertificationType] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["zh-CN"])
    department: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    status: ExpertStatus = ExpertStatus.ACTIVE
    availability: AvailabilityLevel = AvailabilityLevel.HIGH
    contribution_metrics: ContributionMetrics = Field(default_factory=ContributionMetrics)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpertRecommendation(BaseModel):
    """Expert recommendation result (专家推荐结果)"""
    expert_id: UUID
    expert_name: str
    expertise_match_score: float  # 0.0 to 1.0
    contribution_quality_score: float  # 0.0 to 1.0
    availability_score: float  # 0.0 to 1.0
    overall_score: float  # 0.0 to 1.0
    matching_expertise: List[ExpertiseArea]
    is_fallback: bool = False


class ExpertSearchFilter(BaseModel):
    """Expert search filter (专家搜索过滤器)"""
    expertise_areas: Optional[List[ExpertiseArea]] = None
    certifications: Optional[List[CertificationType]] = None
    languages: Optional[List[str]] = None
    status: Optional[ExpertStatus] = None
    availability: Optional[AvailabilityLevel] = None
    min_quality_score: Optional[float] = None
    department: Optional[str] = None


# =============================================================================
# Expert Service
# =============================================================================

class ExpertService:
    """
    Expert Management Service (专家管理服务)

    Provides CRUD operations for expert profiles and expert recommendation
    functionality for ontology collaboration workflows.

    Features:
    - Create, read, update, delete expert profiles
    - Expert recommendation algorithm with expertise matching
    - Fallback recommendations for related expertise areas
    - Caching for frequently requested recommendations
    - Thread-safe operations using asyncio.Lock
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        cache_ttl_seconds: int = 900,  # 15 minutes
    ):
        """
        Initialize ExpertService.

        Args:
            redis_client: Optional Redis client for caching
            cache_ttl_seconds: Cache TTL in seconds (default 15 minutes)
        """
        self._lock = asyncio.Lock()
        self._experts: Dict[UUID, ExpertProfile] = {}
        self._email_index: Dict[str, UUID] = {}
        self._redis = redis_client
        self._cache_ttl = cache_ttl_seconds

        # Recommendation cache (in-memory)
        self._recommendation_cache: Dict[str, Tuple[datetime, List[ExpertRecommendation]]] = {}

        logger.info("ExpertService initialized")

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create_expert(self, data: ExpertProfileCreate) -> ExpertProfile:
        """
        Create a new expert profile.

        Args:
            data: Expert profile creation data

        Returns:
            Created expert profile

        Raises:
            ValueError: If email already exists
        """
        async with self._lock:
            # Check email uniqueness
            if data.email.lower() in self._email_index:
                raise ValueError(f"Expert with email {data.email} already exists")

            # Create profile
            profile = ExpertProfile(
                name=data.name,
                email=data.email.lower(),
                expertise_areas=data.expertise_areas,
                certifications=data.certifications,
                languages=data.languages,
                department=data.department,
                title=data.title,
                bio=data.bio,
            )

            # Store
            self._experts[profile.id] = profile
            self._email_index[profile.email] = profile.id

            # Invalidate recommendation cache
            await self._invalidate_recommendation_cache()

            logger.info(f"Created expert profile: {profile.id} ({profile.name})")
            return profile

    async def get_expert(self, expert_id: UUID) -> Optional[ExpertProfile]:
        """
        Get expert profile by ID.

        Args:
            expert_id: Expert UUID

        Returns:
            Expert profile or None if not found
        """
        return self._experts.get(expert_id)

    async def get_expert_by_email(self, email: str) -> Optional[ExpertProfile]:
        """
        Get expert profile by email.

        Args:
            email: Expert email address

        Returns:
            Expert profile or None if not found
        """
        expert_id = self._email_index.get(email.lower())
        if expert_id:
            return self._experts.get(expert_id)
        return None

    async def update_expert(
        self,
        expert_id: UUID,
        data: ExpertProfileUpdate,
    ) -> Optional[ExpertProfile]:
        """
        Update expert profile.

        Args:
            expert_id: Expert UUID
            data: Update data

        Returns:
            Updated expert profile or None if not found
        """
        async with self._lock:
            profile = self._experts.get(expert_id)
            if not profile:
                return None

            # Update fields
            update_data = data.model_dump(exclude_unset=True)
            for field_name, value in update_data.items():
                if value is not None:
                    setattr(profile, field_name, value)

            profile.updated_at = datetime.utcnow()

            # Store updated profile
            self._experts[expert_id] = profile

            # Invalidate recommendation cache
            await self._invalidate_recommendation_cache()

            logger.info(f"Updated expert profile: {expert_id}")
            return profile

    async def delete_expert(self, expert_id: UUID) -> bool:
        """
        Delete expert profile.

        Args:
            expert_id: Expert UUID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            profile = self._experts.get(expert_id)
            if not profile:
                return False

            # Remove from indexes
            del self._experts[expert_id]
            if profile.email in self._email_index:
                del self._email_index[profile.email]

            # Invalidate recommendation cache
            await self._invalidate_recommendation_cache()

            logger.info(f"Deleted expert profile: {expert_id}")
            return True

    async def list_experts(
        self,
        filter_params: Optional[ExpertSearchFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ExpertProfile]:
        """
        List expert profiles with optional filtering.

        Args:
            filter_params: Optional search filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of expert profiles
        """
        experts = list(self._experts.values())

        # Apply filters
        if filter_params:
            experts = self._apply_filters(experts, filter_params)

        # Apply pagination
        return experts[skip:skip + limit]

    def _apply_filters(
        self,
        experts: List[ExpertProfile],
        filter_params: ExpertSearchFilter,
    ) -> List[ExpertProfile]:
        """Apply search filters to expert list."""
        filtered = experts

        if filter_params.expertise_areas:
            filter_set = set(filter_params.expertise_areas)
            filtered = [
                e for e in filtered
                if filter_set.intersection(set(e.expertise_areas))
            ]

        if filter_params.certifications:
            filter_set = set(filter_params.certifications)
            filtered = [
                e for e in filtered
                if filter_set.intersection(set(e.certifications))
            ]

        if filter_params.languages:
            filter_set = set(filter_params.languages)
            filtered = [
                e for e in filtered
                if filter_set.intersection(set(e.languages))
            ]

        if filter_params.status:
            filtered = [e for e in filtered if e.status == filter_params.status]

        if filter_params.availability:
            filtered = [e for e in filtered if e.availability == filter_params.availability]

        if filter_params.min_quality_score is not None:
            filtered = [
                e for e in filtered
                if e.contribution_metrics.quality_score >= filter_params.min_quality_score
            ]

        if filter_params.department:
            filtered = [
                e for e in filtered
                if e.department and filter_params.department.lower() in e.department.lower()
            ]

        return filtered

    # =========================================================================
    # Contribution Metrics
    # =========================================================================

    async def update_contribution_metrics(
        self,
        expert_id: UUID,
        contribution_type: str,
        accepted: bool = True,
        quality_score: Optional[float] = None,
    ) -> Optional[ContributionMetrics]:
        """
        Update expert contribution metrics.

        Args:
            expert_id: Expert UUID
            contribution_type: Type of contribution (e.g., 'entity', 'relation', 'review')
            accepted: Whether the contribution was accepted
            quality_score: Optional quality score for this contribution

        Returns:
            Updated contribution metrics or None if expert not found
        """
        async with self._lock:
            profile = self._experts.get(expert_id)
            if not profile:
                return None

            metrics = profile.contribution_metrics

            # Update counts
            metrics.total_contributions += 1
            if accepted:
                metrics.accepted_contributions += 1
            else:
                metrics.rejected_contributions += 1

            # Update quality score (moving average)
            if quality_score is not None:
                total = metrics.total_contributions
                if total == 1:
                    metrics.quality_score = quality_score
                else:
                    # Exponential moving average
                    alpha = 0.3
                    metrics.quality_score = (
                        alpha * quality_score + (1 - alpha) * metrics.quality_score
                    )

            # Update recognition score based on acceptance rate and quality
            acceptance_rate = metrics.acceptance_rate
            metrics.recognition_score = (
                0.4 * acceptance_rate + 0.6 * metrics.quality_score
            )

            profile.contribution_metrics = metrics
            profile.updated_at = datetime.utcnow()
            profile.last_active_at = datetime.utcnow()

            self._experts[expert_id] = profile

            # Invalidate recommendation cache
            await self._invalidate_recommendation_cache()

            logger.debug(f"Updated contribution metrics for expert: {expert_id}")
            return metrics

    async def get_contribution_metrics(
        self,
        expert_id: UUID,
    ) -> Optional[ContributionMetrics]:
        """
        Get expert contribution metrics.

        Args:
            expert_id: Expert UUID

        Returns:
            Contribution metrics or None if expert not found
        """
        profile = self._experts.get(expert_id)
        if profile:
            return profile.contribution_metrics
        return None

    # =========================================================================
    # Expert Recommendation
    # =========================================================================

    async def recommend_experts(
        self,
        required_expertise: List[ExpertiseArea],
        max_results: int = 5,
        include_fallback: bool = True,
        min_quality_score: float = 0.0,
    ) -> List[ExpertRecommendation]:
        """
        Recommend experts based on required expertise areas.

        Algorithm:
        1. Find experts matching required expertise
        2. Calculate expertise match score (intersection / required)
        3. Calculate contribution quality score
        4. Calculate availability score
        5. Compute overall score with weighted average
        6. Include fallback experts from related areas if needed

        Args:
            required_expertise: List of required expertise areas
            max_results: Maximum number of recommendations
            include_fallback: Whether to include fallback recommendations
            min_quality_score: Minimum quality score filter

        Returns:
            List of expert recommendations sorted by overall score
        """
        # Check cache
        cache_key = self._generate_cache_key(
            required_expertise, max_results, include_fallback, min_quality_score
        )
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        recommendations: List[ExpertRecommendation] = []
        required_set = set(required_expertise)

        # Find matching experts
        for profile in self._experts.values():
            if profile.status != ExpertStatus.ACTIVE:
                continue

            if min_quality_score > 0:
                if profile.contribution_metrics.quality_score < min_quality_score:
                    continue

            expert_areas = set(profile.expertise_areas)
            matching = expert_areas.intersection(required_set)

            if matching:
                # Calculate scores
                expertise_score = len(matching) / len(required_set)
                quality_score = profile.contribution_metrics.quality_score / 100.0
                availability_score = self._get_availability_score(profile.availability)

                # Weighted overall score
                overall_score = (
                    0.5 * expertise_score +
                    0.3 * quality_score +
                    0.2 * availability_score
                )

                recommendations.append(ExpertRecommendation(
                    expert_id=profile.id,
                    expert_name=profile.name,
                    expertise_match_score=expertise_score,
                    contribution_quality_score=quality_score,
                    availability_score=availability_score,
                    overall_score=overall_score,
                    matching_expertise=list(matching),
                    is_fallback=False,
                ))

        # Add fallback recommendations if needed
        if include_fallback and len(recommendations) < max_results:
            fallback_recommendations = await self._get_fallback_recommendations(
                required_expertise,
                max_results - len(recommendations),
                min_quality_score,
                {r.expert_id for r in recommendations},  # Exclude already recommended
            )
            recommendations.extend(fallback_recommendations)

        # Sort by overall score (descending)
        recommendations.sort(key=lambda x: x.overall_score, reverse=True)

        # Limit results
        result = recommendations[:max_results]

        # Cache result
        await self._save_to_cache(cache_key, result)

        return result

    async def _get_fallback_recommendations(
        self,
        required_expertise: List[ExpertiseArea],
        max_results: int,
        min_quality_score: float,
        exclude_ids: Set[UUID],
    ) -> List[ExpertRecommendation]:
        """Get fallback recommendations from related expertise areas."""
        fallback_recommendations: List[ExpertRecommendation] = []

        # Collect related expertise areas
        related_areas: Set[ExpertiseArea] = set()
        for area in required_expertise:
            if area in RELATED_EXPERTISE:
                related_areas.update(RELATED_EXPERTISE[area])

        # Remove required areas from related
        related_areas -= set(required_expertise)

        if not related_areas:
            return fallback_recommendations

        # Find experts with related expertise
        for profile in self._experts.values():
            if profile.id in exclude_ids:
                continue
            if profile.status != ExpertStatus.ACTIVE:
                continue
            if min_quality_score > 0:
                if profile.contribution_metrics.quality_score < min_quality_score:
                    continue

            expert_areas = set(profile.expertise_areas)
            matching = expert_areas.intersection(related_areas)

            if matching:
                # Calculate scores (lower expertise score for fallback)
                expertise_score = len(matching) / len(related_areas) * 0.7  # 30% penalty
                quality_score = profile.contribution_metrics.quality_score / 100.0
                availability_score = self._get_availability_score(profile.availability)

                # Weighted overall score
                overall_score = (
                    0.5 * expertise_score +
                    0.3 * quality_score +
                    0.2 * availability_score
                )

                fallback_recommendations.append(ExpertRecommendation(
                    expert_id=profile.id,
                    expert_name=profile.name,
                    expertise_match_score=expertise_score,
                    contribution_quality_score=quality_score,
                    availability_score=availability_score,
                    overall_score=overall_score,
                    matching_expertise=list(matching),
                    is_fallback=True,
                ))

        # Sort by overall score (descending)
        fallback_recommendations.sort(key=lambda x: x.overall_score, reverse=True)

        return fallback_recommendations[:max_results]

    def _get_availability_score(self, availability: AvailabilityLevel) -> float:
        """Convert availability level to score."""
        scores = {
            AvailabilityLevel.HIGH: 1.0,
            AvailabilityLevel.MEDIUM: 0.7,
            AvailabilityLevel.LOW: 0.3,
            AvailabilityLevel.UNAVAILABLE: 0.0,
        }
        return scores.get(availability, 0.5)

    # =========================================================================
    # Caching
    # =========================================================================

    def _generate_cache_key(
        self,
        expertise: List[ExpertiseArea],
        max_results: int,
        include_fallback: bool,
        min_quality_score: float,
    ) -> str:
        """Generate cache key for recommendations."""
        expertise_str = ",".join(sorted(e.value for e in expertise))
        key_data = f"{expertise_str}:{max_results}:{include_fallback}:{min_quality_score}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _get_from_cache(
        self,
        cache_key: str,
    ) -> Optional[List[ExpertRecommendation]]:
        """Get recommendations from cache."""
        # Check in-memory cache first
        if cache_key in self._recommendation_cache:
            timestamp, recommendations = self._recommendation_cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self._cache_ttl):
                logger.debug(f"Cache hit for recommendation key: {cache_key[:8]}...")
                return recommendations
            else:
                # Expired
                del self._recommendation_cache[cache_key]

        # Check Redis cache if available
        if self._redis:
            try:
                data = await self._redis.get(f"expert_rec:{cache_key}")
                if data:
                    # Deserialize (implement based on your serialization format)
                    logger.debug(f"Redis cache hit for recommendation key: {cache_key[:8]}...")
                    return None  # TODO: Deserialize
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")

        return None

    async def _save_to_cache(
        self,
        cache_key: str,
        recommendations: List[ExpertRecommendation],
    ) -> None:
        """Save recommendations to cache."""
        # Save to in-memory cache
        self._recommendation_cache[cache_key] = (datetime.utcnow(), recommendations)

        # Save to Redis if available
        if self._redis:
            try:
                # Serialize (implement based on your serialization format)
                # await self._redis.setex(
                #     f"expert_rec:{cache_key}",
                #     self._cache_ttl,
                #     serialized_data
                # )
                pass
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")

    async def _invalidate_recommendation_cache(self) -> None:
        """Invalidate all recommendation caches."""
        self._recommendation_cache.clear()

        if self._redis:
            try:
                # Delete all recommendation keys
                keys = await self._redis.keys("expert_rec:*")
                if keys:
                    await self._redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache invalidation error: {e}")

        logger.debug("Recommendation cache invalidated")

    # =========================================================================
    # Search and Filtering
    # =========================================================================

    async def search_experts(
        self,
        query: str,
        filter_params: Optional[ExpertSearchFilter] = None,
        limit: int = 20,
    ) -> List[ExpertProfile]:
        """
        Search experts by name, email, or bio.

        Args:
            query: Search query string
            filter_params: Optional additional filters
            limit: Maximum results

        Returns:
            List of matching expert profiles
        """
        query_lower = query.lower()
        results: List[ExpertProfile] = []

        for profile in self._experts.values():
            # Search in name, email, bio
            if (
                query_lower in profile.name.lower() or
                query_lower in profile.email.lower() or
                (profile.bio and query_lower in profile.bio.lower()) or
                (profile.department and query_lower in profile.department.lower())
            ):
                results.append(profile)

        # Apply additional filters
        if filter_params:
            results = self._apply_filters(results, filter_params)

        return results[:limit]

    async def get_experts_by_expertise(
        self,
        expertise_area: ExpertiseArea,
        active_only: bool = True,
    ) -> List[ExpertProfile]:
        """
        Get all experts with a specific expertise area.

        Args:
            expertise_area: Required expertise area
            active_only: Whether to include only active experts

        Returns:
            List of expert profiles
        """
        results: List[ExpertProfile] = []

        for profile in self._experts.values():
            if expertise_area in profile.expertise_areas:
                if active_only and profile.status != ExpertStatus.ACTIVE:
                    continue
                results.append(profile)

        return results

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_expert_statistics(self) -> Dict[str, Any]:
        """
        Get overall expert statistics.

        Returns:
            Dictionary with various statistics
        """
        total = len(self._experts)
        if total == 0:
            return {
                "total_experts": 0,
                "active_experts": 0,
                "expertise_distribution": {},
                "certification_distribution": {},
                "average_quality_score": 0.0,
            }

        active_count = sum(
            1 for e in self._experts.values()
            if e.status == ExpertStatus.ACTIVE
        )

        # Expertise distribution
        expertise_dist: Dict[str, int] = {}
        for profile in self._experts.values():
            for area in profile.expertise_areas:
                expertise_dist[area.value] = expertise_dist.get(area.value, 0) + 1

        # Certification distribution
        cert_dist: Dict[str, int] = {}
        for profile in self._experts.values():
            for cert in profile.certifications:
                cert_dist[cert.value] = cert_dist.get(cert.value, 0) + 1

        # Average quality score
        total_quality = sum(
            e.contribution_metrics.quality_score
            for e in self._experts.values()
        )
        avg_quality = total_quality / total

        return {
            "total_experts": total,
            "active_experts": active_count,
            "expertise_distribution": expertise_dist,
            "certification_distribution": cert_dist,
            "average_quality_score": avg_quality,
        }

    async def get_top_contributors(
        self,
        expertise_area: Optional[ExpertiseArea] = None,
        limit: int = 10,
    ) -> List[Tuple[ExpertProfile, ContributionMetrics]]:
        """
        Get top contributing experts.

        Args:
            expertise_area: Optional filter by expertise area
            limit: Maximum results

        Returns:
            List of (profile, metrics) tuples sorted by recognition score
        """
        experts = list(self._experts.values())

        if expertise_area:
            experts = [e for e in experts if expertise_area in e.expertise_areas]

        # Filter active only
        experts = [e for e in experts if e.status == ExpertStatus.ACTIVE]

        # Sort by recognition score
        experts.sort(
            key=lambda x: x.contribution_metrics.recognition_score,
            reverse=True,
        )

        return [(e, e.contribution_metrics) for e in experts[:limit]]
