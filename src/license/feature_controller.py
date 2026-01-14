"""
Feature Controller for SuperInsight Platform.

Manages feature module access based on license type.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import LicenseModel, LicenseStatus, LicenseType
from src.schemas.license import (
    FeatureInfo, FeatureAccessResult, LicenseType as LicenseTypeSchema
)


class FeatureController:
    """
    Feature Controller.
    
    Manages feature module access based on license type and configuration.
    """
    
    # Feature definitions with descriptions
    FEATURE_DEFINITIONS = {
        "api_access": {
            "name": "API Access",
            "description": "REST API access for integrations",
            "category": "core",
        },
        "basic_annotation": {
            "name": "Basic Annotation",
            "description": "Basic annotation tools and workflows",
            "category": "core",
        },
        "export": {
            "name": "Data Export",
            "description": "Export annotations in various formats",
            "category": "core",
        },
        "ai_annotation": {
            "name": "AI Pre-annotation",
            "description": "AI-powered automatic annotation suggestions",
            "category": "ai",
        },
        "quality_assessment": {
            "name": "Quality Assessment",
            "description": "Ragas-based semantic quality assessment",
            "category": "quality",
        },
        "knowledge_graph": {
            "name": "Knowledge Graph",
            "description": "Neo4j-based knowledge graph features",
            "category": "advanced",
        },
        "advanced_analytics": {
            "name": "Advanced Analytics",
            "description": "Advanced reporting and analytics dashboards",
            "category": "advanced",
        },
        "multi_tenant": {
            "name": "Multi-Tenant",
            "description": "Multi-tenant workspace isolation",
            "category": "enterprise",
        },
        "custom_integrations": {
            "name": "Custom Integrations",
            "description": "Custom API integrations and webhooks",
            "category": "enterprise",
        },
        "sso": {
            "name": "Single Sign-On",
            "description": "SAML/OIDC single sign-on support",
            "category": "enterprise",
        },
        "audit_compliance": {
            "name": "Audit & Compliance",
            "description": "Advanced audit logging and compliance reports",
            "category": "enterprise",
        },
    }
    
    # Feature matrix by license type
    FEATURE_MATRIX = {
        LicenseType.TRIAL: [
            "api_access", "basic_annotation"
        ],
        LicenseType.BASIC: [
            "api_access", "basic_annotation", "export"
        ],
        LicenseType.PROFESSIONAL: [
            "api_access", "basic_annotation", "export",
            "ai_annotation", "quality_assessment"
        ],
        LicenseType.ENTERPRISE: [
            "api_access", "basic_annotation", "export",
            "ai_annotation", "quality_assessment",
            "knowledge_graph", "advanced_analytics",
            "multi_tenant", "custom_integrations",
            "sso", "audit_compliance"
        ],
    }
    
    # Upgrade path
    UPGRADE_PATH = {
        LicenseType.TRIAL: LicenseType.BASIC,
        LicenseType.BASIC: LicenseType.PROFESSIONAL,
        LicenseType.PROFESSIONAL: LicenseType.ENTERPRISE,
        LicenseType.ENTERPRISE: None,
    }
    
    def __init__(
        self,
        db: AsyncSession,
        trial_features: Optional[Dict[str, int]] = None
    ):
        """
        Initialize Feature Controller.
        
        Args:
            db: Database session
            trial_features: Optional dict of feature -> trial days
        """
        self.db = db
        self.trial_features = trial_features or {}
        self._license_cache: Optional[LicenseModel] = None
        self._feature_usage: Dict[str, int] = {}
    
    async def _get_current_license(self) -> Optional[LicenseModel]:
        """Get current active license."""
        if self._license_cache:
            return self._license_cache
        
        result = await self.db.execute(
            select(LicenseModel)
            .where(LicenseModel.status == LicenseStatus.ACTIVE)
            .order_by(LicenseModel.activated_at.desc())
            .limit(1)
        )
        license_model = result.scalar_one_or_none()
        
        if license_model:
            self._license_cache = license_model
        
        return license_model
    
    def get_features_for_type(
        self,
        license_type: LicenseType
    ) -> List[str]:
        """Get features available for a license type."""
        return self.FEATURE_MATRIX.get(license_type, [])
    
    def get_minimum_license_for_feature(
        self,
        feature: str
    ) -> Optional[LicenseType]:
        """Get minimum license type required for a feature."""
        for license_type in [
            LicenseType.TRIAL,
            LicenseType.BASIC,
            LicenseType.PROFESSIONAL,
            LicenseType.ENTERPRISE
        ]:
            if feature in self.FEATURE_MATRIX.get(license_type, []):
                return license_type
        return None
    
    async def check_feature_access(
        self,
        feature: str
    ) -> FeatureAccessResult:
        """
        Check if a feature is accessible.
        
        Args:
            feature: Feature identifier
            
        Returns:
            Feature access result
        """
        license = await self._get_current_license()
        
        if not license:
            return FeatureAccessResult(
                allowed=False,
                feature=feature,
                reason="No valid license found",
                requires_upgrade=True,
                upgrade_to=LicenseTypeSchema.BASIC
            )
        
        # Check if feature is in license
        if feature in license.features:
            # Track usage
            self._feature_usage[feature] = self._feature_usage.get(feature, 0) + 1
            return FeatureAccessResult(
                allowed=True,
                feature=feature
            )
        
        # Check if feature exists
        if feature not in self.FEATURE_DEFINITIONS:
            return FeatureAccessResult(
                allowed=False,
                feature=feature,
                reason=f"Unknown feature: {feature}"
            )
        
        # Feature not in license - suggest upgrade
        min_license = self.get_minimum_license_for_feature(feature)
        upgrade_to = self.UPGRADE_PATH.get(license.license_type)
        
        return FeatureAccessResult(
            allowed=False,
            feature=feature,
            reason=f"Feature '{feature}' requires {min_license.value if min_license else 'unknown'} license",
            requires_upgrade=True,
            upgrade_to=LicenseTypeSchema(upgrade_to.value) if upgrade_to else None
        )
    
    async def get_available_features(self) -> List[FeatureInfo]:
        """
        Get list of all features with availability status.
        
        Returns:
            List of feature information
        """
        license = await self._get_current_license()
        licensed_features = license.features if license else []
        
        features = []
        for feature_id, definition in self.FEATURE_DEFINITIONS.items():
            enabled = feature_id in licensed_features
            requires_upgrade = not enabled
            
            # Check trial availability
            trial_available = feature_id in self.trial_features
            trial_days = self.trial_features.get(feature_id, 0) if trial_available else None
            
            features.append(FeatureInfo(
                name=feature_id,
                enabled=enabled,
                description=definition.get("description"),
                requires_upgrade=requires_upgrade,
                trial_available=trial_available,
                trial_days_remaining=trial_days,
            ))
        
        return features
    
    async def get_enabled_features(self) -> List[str]:
        """Get list of enabled feature identifiers."""
        license = await self._get_current_license()
        return license.features if license else []
    
    async def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled."""
        result = await self.check_feature_access(feature)
        return result.allowed
    
    def get_feature_info(self, feature: str) -> Optional[Dict[str, Any]]:
        """Get feature definition information."""
        return self.FEATURE_DEFINITIONS.get(feature)
    
    def get_all_features(self) -> Dict[str, Dict[str, Any]]:
        """Get all feature definitions."""
        return self.FEATURE_DEFINITIONS.copy()
    
    def get_features_by_category(
        self,
        category: str
    ) -> List[str]:
        """Get features in a specific category."""
        return [
            feature_id
            for feature_id, definition in self.FEATURE_DEFINITIONS.items()
            if definition.get("category") == category
        ]
    
    def get_feature_usage_stats(self) -> Dict[str, int]:
        """Get feature usage statistics."""
        return self._feature_usage.copy()
    
    def reset_usage_stats(self):
        """Reset feature usage statistics."""
        self._feature_usage = {}
    
    def clear_cache(self):
        """Clear license cache."""
        self._license_cache = None
    
    async def get_upgrade_info(self) -> Optional[Dict[str, Any]]:
        """
        Get upgrade information for current license.
        
        Returns:
            Upgrade info or None if at highest tier
        """
        license = await self._get_current_license()
        
        if not license:
            return {
                "current_type": None,
                "upgrade_to": LicenseType.BASIC.value,
                "additional_features": self.FEATURE_MATRIX[LicenseType.BASIC],
            }
        
        upgrade_to = self.UPGRADE_PATH.get(license.license_type)
        
        if not upgrade_to:
            return None  # Already at highest tier
        
        current_features = set(license.features)
        upgrade_features = set(self.FEATURE_MATRIX.get(upgrade_to, []))
        additional = upgrade_features - current_features
        
        return {
            "current_type": license.license_type.value,
            "upgrade_to": upgrade_to.value,
            "additional_features": list(additional),
        }
