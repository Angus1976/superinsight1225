"""
Gateway Manager for AI Application Integration.

This module provides the GatewayManager class for managing AI gateway lifecycle,
including registration, configuration updates, and deactivation with credential
revocation.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.ai_integration import AIGateway
from src.ai_integration.auth import generate_credentials, APICredentials
from src.database.connection import get_db


class GatewayRegistrationError(Exception):
    """Raised when gateway registration fails."""
    pass


class GatewayNotFoundError(Exception):
    """Raised when gateway is not found."""
    pass


class ConfigurationValidationError(Exception):
    """Raised when gateway configuration is invalid."""
    pass


class GatewayManager:
    """
    Manages AI gateway lifecycle, registration, and configuration.
    
    Provides methods for:
    - Gateway registration with credential generation
    - Configuration updates with versioning
    - Gateway deactivation with credential revocation
    """
    
    def __init__(self, db: Session):
        """
        Initialize GatewayManager.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def register_gateway(
        self,
        name: str,
        gateway_type: str,
        tenant_id: str,
        configuration: Dict[str, Any],
        rate_limit_per_minute: int = 60,
        quota_per_day: int = 10000
    ) -> tuple[AIGateway, APICredentials]:
        """
        Register a new AI gateway with validation and credential generation.
        
        Validates required configuration parameters, generates unique API credentials,
        and stores the gateway in the database.
        
        Args:
            name: Gateway name (must be unique within tenant)
            gateway_type: Type of gateway (e.g., 'openclaw', 'custom')
            tenant_id: Tenant ID for multi-tenant isolation
            configuration: Gateway configuration dictionary
            rate_limit_per_minute: Rate limit (default: 60)
            quota_per_day: Daily quota (default: 10000)
            
        Returns:
            Tuple of (AIGateway, APICredentials)
            
        Raises:
            GatewayRegistrationError: If registration fails
            ConfigurationValidationError: If configuration is invalid
            
        Validates: Requirements 2.1, 2.2, 2.3
        """
        # Validate inputs
        if not name or not name.strip():
            raise ConfigurationValidationError("Gateway name cannot be empty")
        
        if not gateway_type or not gateway_type.strip():
            raise ConfigurationValidationError("Gateway type cannot be empty")
        
        if not tenant_id or not tenant_id.strip():
            raise ConfigurationValidationError("Tenant ID cannot be empty")
        
        if not isinstance(configuration, dict):
            raise ConfigurationValidationError("Configuration must be a dictionary")
        
        # Validate configuration has required fields
        self._validate_configuration(configuration, gateway_type)
        
        # Check for duplicate gateway name within tenant
        existing = self.db.query(AIGateway).filter(
            AIGateway.name == name,
            AIGateway.tenant_id == tenant_id
        ).first()
        
        if existing:
            raise GatewayRegistrationError(
                f"Gateway with name '{name}' already exists for tenant '{tenant_id}'"
            )
        
        # Generate unique API credentials
        credentials = generate_credentials()
        
        # Create gateway record
        gateway = AIGateway(
            name=name.strip(),
            gateway_type=gateway_type.strip(),
            tenant_id=tenant_id.strip(),
            configuration=configuration,
            api_key_hash=credentials.api_key_hash,
            api_secret_hash=credentials.api_secret_hash,
            rate_limit_per_minute=rate_limit_per_minute,
            quota_per_day=quota_per_day,
            status="inactive"
        )
        
        try:
            self.db.add(gateway)
            self.db.commit()
            self.db.refresh(gateway)
        except IntegrityError as e:
            self.db.rollback()
            raise GatewayRegistrationError(f"Failed to register gateway: {str(e)}")
        
        return gateway, credentials
    
    def update_configuration(
        self,
        gateway_id: str,
        configuration: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> AIGateway:
        """
        Update gateway configuration with versioning.
        
        Validates the new configuration and stores it with version tracking.
        The configuration history is maintained in the configuration JSONB field
        with a 'versions' array.
        
        Args:
            gateway_id: Gateway ID to update
            configuration: New configuration dictionary
            updated_by: User/system identifier who made the update
            
        Returns:
            Updated AIGateway object
            
        Raises:
            GatewayNotFoundError: If gateway not found
            ConfigurationValidationError: If configuration is invalid
            
        Validates: Requirements 2.4
        """
        # Fetch gateway
        gateway = self.db.query(AIGateway).filter(
            AIGateway.id == gateway_id
        ).first()
        
        if not gateway:
            raise GatewayNotFoundError(f"Gateway with ID '{gateway_id}' not found")
        
        # Validate new configuration
        if not isinstance(configuration, dict):
            raise ConfigurationValidationError("Configuration must be a dictionary")
        
        self._validate_configuration(configuration, gateway.gateway_type)
        
        # Store current configuration in version history
        current_config = gateway.configuration.copy()
        
        # Initialize versions array if not exists
        if 'versions' not in current_config:
            current_config['versions'] = []
        
        # Add current config to version history
        version_entry = {
            'version': len(current_config.get('versions', [])) + 1,
            'configuration': {k: v for k, v in current_config.items() if k != 'versions'},
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'updated_by': updated_by or 'system'
        }
        
        # Create new configuration with version history
        new_config = configuration.copy()
        new_config['versions'] = current_config.get('versions', []) + [version_entry]
        
        # Update gateway
        gateway.configuration = new_config
        gateway.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
            self.db.refresh(gateway)
        except IntegrityError as e:
            self.db.rollback()
            raise GatewayRegistrationError(f"Failed to update configuration: {str(e)}")
        
        return gateway
    
    def deactivate_gateway(self, gateway_id: str) -> None:
        """
        Deactivate gateway and revoke its API credentials.
        
        Sets gateway status to 'inactive', disables all associated skills,
        and invalidates credentials by setting them to empty hashes.
        This ensures subsequent authentication attempts will fail.
        
        Args:
            gateway_id: Gateway ID to deactivate
            
        Raises:
            GatewayNotFoundError: If gateway not found
            
        Validates: Requirements 2.5
        """
        # Fetch gateway
        gateway = self.db.query(AIGateway).filter(
            AIGateway.id == gateway_id
        ).first()
        
        if not gateway:
            raise GatewayNotFoundError(f"Gateway with ID '{gateway_id}' not found")
        
        # Deactivate gateway
        gateway.status = "inactive"
        
        # Revoke credentials by setting to invalid hashes
        # This ensures authentication will fail without deleting the record
        gateway.api_key_hash = "REVOKED"
        gateway.api_secret_hash = "REVOKED"
        
        # Disable all associated skills
        for skill in gateway.skills:
            skill.status = "disabled"
        
        gateway.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise GatewayRegistrationError(f"Failed to deactivate gateway: {str(e)}")
    
    def _validate_configuration(
        self,
        configuration: Dict[str, Any],
        gateway_type: str
    ) -> None:
        """
        Validate gateway configuration based on gateway type.
        
        Args:
            configuration: Configuration dictionary to validate
            gateway_type: Type of gateway
            
        Raises:
            ConfigurationValidationError: If configuration is invalid
        """
        # Common required fields for all gateway types
        if 'channels' not in configuration:
            raise ConfigurationValidationError("Configuration must include 'channels'")
        
        if not isinstance(configuration['channels'], list):
            raise ConfigurationValidationError("'channels' must be a list")
        
        # Validate each channel
        for channel in configuration['channels']:
            if not isinstance(channel, dict):
                raise ConfigurationValidationError("Each channel must be a dictionary")
            
            if 'channel_type' not in channel:
                raise ConfigurationValidationError("Each channel must have 'channel_type'")
            
            if 'enabled' not in channel:
                raise ConfigurationValidationError("Each channel must have 'enabled' field")
        
        # Gateway-type specific validation
        if gateway_type == 'openclaw':
            self._validate_openclaw_configuration(configuration)
    
    def _validate_openclaw_configuration(
        self,
        configuration: Dict[str, Any]
    ) -> None:
        """
        Validate OpenClaw-specific configuration.
        
        Args:
            configuration: Configuration dictionary to validate
            
        Raises:
            ConfigurationValidationError: If configuration is invalid
        """
        # OpenClaw requires network_settings
        if 'network_settings' not in configuration:
            raise ConfigurationValidationError(
                "OpenClaw configuration must include 'network_settings'"
            )
        
        network_settings = configuration['network_settings']
        if not isinstance(network_settings, dict):
            raise ConfigurationValidationError("'network_settings' must be a dictionary")
