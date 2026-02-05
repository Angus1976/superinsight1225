"""
Label Studio Exception Classes

This module contains all exception classes for the Label Studio integration.
Separated from integration.py to avoid circular imports.

Validates: Requirements 1.3, 1.5, 5.5 - Error handling with clear error messages
"""

from typing import Optional


class LabelStudioIntegrationError(Exception):
    """Custom exception for Label Studio integration errors"""
    pass


class LabelStudioAuthenticationError(LabelStudioIntegrationError):
    """
    Exception for Label Studio authentication failures.
    
    This exception is raised when authentication with Label Studio fails,
    such as invalid API token, expired credentials, or unauthorized access.
    
    Authentication errors should NOT be retried as they require user intervention
    (e.g., re-login, token refresh).
    
    Error messages are designed to be:
    - Clear and actionable (tell user what to do)
    - Include status code for debugging
    - Include server reason if available
    - NOT include sensitive data (passwords, tokens)
    
    Validates: Requirements 1.3, 1.5, 5.5 - Handle authentication failures with clear error messages (no retry)
    """
    
    # Predefined actionable error messages for common scenarios
    ERROR_MESSAGES = {
        401: {
            "invalid_credentials": (
                "Authentication failed: Invalid username or password. "
                "Please check your LABEL_STUDIO_USERNAME and LABEL_STUDIO_PASSWORD settings."
            ),
            "token_expired": (
                "Authentication failed: Access token has expired. "
                "The system will attempt to refresh the token automatically."
            ),
            "refresh_token_expired": (
                "Authentication failed: Refresh token has expired. "
                "The system will attempt to re-authenticate with username/password."
            ),
            "invalid_token": (
                "Authentication failed: Invalid or malformed token. "
                "Please check your LABEL_STUDIO_API_TOKEN setting or re-authenticate."
            ),
            "default": (
                "Authentication failed: Unauthorized access. "
                "Please verify your Label Studio credentials are correct."
            ),
        },
        403: {
            "insufficient_permissions": (
                "Authentication failed: Access forbidden. "
                "The user account may not have sufficient permissions. "
                "Please contact your Label Studio administrator."
            ),
            "account_disabled": (
                "Authentication failed: Account access denied. "
                "Your account may be disabled or restricted. "
                "Please contact your Label Studio administrator."
            ),
            "default": (
                "Authentication failed: Access forbidden (HTTP 403). "
                "Please verify your account has the required permissions."
            ),
        },
        500: {
            "default": (
                "Authentication failed: Label Studio server error. "
                "Please try again later or contact your administrator if the problem persists."
            ),
        },
        502: {
            "default": (
                "Authentication failed: Label Studio service unavailable (Bad Gateway). "
                "Please check if Label Studio is running and try again."
            ),
        },
        503: {
            "default": (
                "Authentication failed: Label Studio service temporarily unavailable. "
                "Please try again in a few moments."
            ),
        },
    }
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 401,
        error_type: Optional[str] = None,
        server_reason: Optional[str] = None
    ):
        """
        Initialize authentication error with clear, actionable message.
        
        Args:
            message: The error message (will be enhanced with context)
            status_code: HTTP status code from the server
            error_type: Type of error (e.g., 'invalid_credentials', 'token_expired')
            server_reason: Reason provided by the server (if available and safe to include)
        """
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.server_reason = server_reason
        self.message = message
    
    @classmethod
    def create(
        cls,
        status_code: int,
        error_type: Optional[str] = None,
        server_reason: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> 'LabelStudioAuthenticationError':
        """
        Factory method to create authentication error with appropriate message.
        
        This method selects the most appropriate error message based on the
        status code and error type, ensuring users receive clear, actionable
        guidance.
        
        Args:
            status_code: HTTP status code from the server
            error_type: Type of error (e.g., 'invalid_credentials', 'token_expired')
            server_reason: Reason provided by the server (sanitized, no sensitive data)
            custom_message: Optional custom message to override defaults
            
        Returns:
            LabelStudioAuthenticationError with appropriate message
            
        Example:
            >>> error = LabelStudioAuthenticationError.create(
            ...     status_code=401,
            ...     error_type='invalid_credentials'
            ... )
            >>> print(error)
            Authentication failed (HTTP 401): Invalid username or password...
        """
        if custom_message:
            message = custom_message
        else:
            # Get messages for this status code
            status_messages = cls.ERROR_MESSAGES.get(status_code, {})
            
            # Try to get specific error type message, fall back to default
            if error_type and error_type in status_messages:
                message = status_messages[error_type]
            elif 'default' in status_messages:
                message = status_messages['default']
            else:
                # Generic fallback
                message = (
                    f"Authentication failed with HTTP {status_code}. "
                    "Please check your Label Studio configuration and credentials."
                )
        
        # Append server reason if provided (and safe)
        if server_reason:
            message = f"{message} Server response: {server_reason}"
        
        return cls(
            message=message,
            status_code=status_code,
            error_type=error_type,
            server_reason=server_reason
        )
    
    def __str__(self) -> str:
        """Return formatted error message with status code."""
        return f"Authentication failed (HTTP {self.status_code}): {self.message}"
    
    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"LabelStudioAuthenticationError("
            f"status_code={self.status_code}, "
            f"error_type={self.error_type!r}, "
            f"message={self.message!r})"
        )


class LabelStudioProjectNotFoundError(LabelStudioIntegrationError):
    """
    Exception for Label Studio project not found errors.
    
    This exception is raised when a requested project does not exist in Label Studio.
    Project not found errors should NOT be retried as the project needs to be created.
    
    Validates: Requirements 1.5 - Handle project not found with appropriate error messages
    """
    
    def __init__(self, project_id: str, message: Optional[str] = None):
        self.project_id = project_id
        self.message = message or (
            f"Project '{project_id}' not found in Label Studio. "
            "Please verify the project ID exists or create a new project."
        )
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return self.message
    
    def __repr__(self) -> str:
        return f"LabelStudioProjectNotFoundError(project_id={self.project_id!r})"


class LabelStudioNetworkError(LabelStudioIntegrationError):
    """
    Exception for Label Studio network errors.
    
    This exception wraps network-related errors (timeouts, connection errors)
    for better error handling and logging.
    
    Network errors ARE retryable with exponential backoff.
    
    Error messages include:
    - Clear description of the network issue
    - Actionable guidance for resolution
    - Original error details for debugging
    
    Validates: Requirements 1.5, 5.2 - Handle network errors with retry
    """
    
    # Predefined actionable error messages for common network scenarios
    NETWORK_ERROR_MESSAGES = {
        "timeout": (
            "Connection to Label Studio timed out. "
            "Please check if Label Studio is running and accessible. "
            "You may need to increase the timeout or check network connectivity."
        ),
        "connection_refused": (
            "Connection to Label Studio was refused. "
            "Please verify that Label Studio is running at the configured URL "
            "and that the port is correct."
        ),
        "dns_error": (
            "Could not resolve Label Studio hostname. "
            "Please check the LABEL_STUDIO_URL setting and verify DNS configuration."
        ),
        "ssl_error": (
            "SSL/TLS error connecting to Label Studio. "
            "Please verify the SSL certificate is valid or check HTTPS configuration."
        ),
        "default": (
            "Network error communicating with Label Studio. "
            "Please check your network connection and Label Studio availability."
        ),
    }
    
    def __init__(
        self, 
        message: str, 
        original_error: Optional[Exception] = None,
        error_type: Optional[str] = None
    ):
        """
        Initialize network error with clear, actionable message.
        
        Args:
            message: The error message
            original_error: The underlying exception that caused this error
            error_type: Type of network error (e.g., 'timeout', 'connection_refused')
        """
        super().__init__(message)
        self.original_error = original_error
        self.error_type = error_type
        self.message = message
    
    @classmethod
    def create(
        cls,
        error_type: str,
        original_error: Optional[Exception] = None,
        url: Optional[str] = None
    ) -> 'LabelStudioNetworkError':
        """
        Factory method to create network error with appropriate message.
        
        Args:
            error_type: Type of network error
            original_error: The underlying exception
            url: The URL that was being accessed (for context)
            
        Returns:
            LabelStudioNetworkError with appropriate message
        """
        message = cls.NETWORK_ERROR_MESSAGES.get(
            error_type, 
            cls.NETWORK_ERROR_MESSAGES['default']
        )
        
        if url:
            message = f"{message} URL: {url}"
        
        return cls(
            message=message,
            original_error=original_error,
            error_type=error_type
        )
    
    def __str__(self) -> str:
        if self.original_error:
            return (
                f"Network error: {self.message} "
                f"(caused by: {type(self.original_error).__name__}: {self.original_error})"
            )
        return f"Network error: {self.message}"
    
    def __repr__(self) -> str:
        return (
            f"LabelStudioNetworkError("
            f"error_type={self.error_type!r}, "
            f"original_error={type(self.original_error).__name__ if self.original_error else None})"
        )


class LabelStudioTokenExpiredError(LabelStudioIntegrationError):
    """
    Exception for Label Studio token expiration errors.
    
    This exception is raised when an API call returns 401 with a token
    expiration message. It triggers automatic token refresh and retry
    of the original API call.
    
    Token expiration errors ARE retryable after token refresh.
    
    Validates: Requirements 5.3, 8.1 - Detect token expiration and trigger refresh
    """
    
    # Predefined messages for token expiration scenarios
    TOKEN_MESSAGES = {
        "access": (
            "Access token has expired. "
            "The system will automatically refresh the token and retry the request."
        ),
        "refresh": (
            "Refresh token has expired. "
            "The system will re-authenticate using username/password credentials."
        ),
    }
    
    def __init__(self, message: Optional[str] = None, token_type: str = "access"):
        """
        Initialize token expiration error.
        
        Args:
            message: Custom error message (optional)
            token_type: Type of token that expired ('access' or 'refresh')
        """
        self.token_type = token_type
        self.message = message or self.TOKEN_MESSAGES.get(
            token_type, 
            f"{token_type.capitalize()} token has expired."
        )
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return f"Token expired ({self.token_type}): {self.message}"
    
    def __repr__(self) -> str:
        return f"LabelStudioTokenExpiredError(token_type={self.token_type!r})"


class LabelStudioConfigurationError(LabelStudioIntegrationError):
    """
    Exception for Label Studio configuration errors.
    
    This exception is raised when Label Studio configuration is invalid
    or missing required settings.
    
    Configuration errors should NOT be retried as they require user intervention.
    
    Validates: Requirements 6.4 - Handle configuration errors with clear messages
    """
    
    # Predefined messages for common configuration issues
    CONFIG_ERROR_MESSAGES = {
        "missing_url": (
            "Label Studio URL is not configured. "
            "Please set the LABEL_STUDIO_URL environment variable."
        ),
        "missing_auth": (
            "No authentication method configured for Label Studio. "
            "Please set either LABEL_STUDIO_USERNAME/LABEL_STUDIO_PASSWORD "
            "for JWT authentication, or LABEL_STUDIO_API_TOKEN for token authentication."
        ),
        "invalid_url": (
            "Invalid Label Studio URL format. "
            "Please ensure LABEL_STUDIO_URL is a valid HTTP/HTTPS URL."
        ),
        "missing_credentials": (
            "Label Studio credentials are incomplete. "
            "Both LABEL_STUDIO_USERNAME and LABEL_STUDIO_PASSWORD must be set for JWT authentication."
        ),
    }
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        """
        Initialize configuration error.
        
        Args:
            message: The error message
            config_key: The configuration key that is invalid/missing
        """
        super().__init__(message)
        self.message = message
        self.config_key = config_key
    
    @classmethod
    def create(cls, error_type: str) -> 'LabelStudioConfigurationError':
        """
        Factory method to create configuration error with appropriate message.
        
        Args:
            error_type: Type of configuration error
            
        Returns:
            LabelStudioConfigurationError with appropriate message
        """
        message = cls.CONFIG_ERROR_MESSAGES.get(
            error_type,
            f"Label Studio configuration error: {error_type}"
        )
        return cls(message=message, config_key=error_type)
    
    def __str__(self) -> str:
        return f"Configuration error: {self.message}"
    
    def __repr__(self) -> str:
        return f"LabelStudioConfigurationError(config_key={self.config_key!r})"
