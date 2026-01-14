"""
Hardware Fingerprint Generator for SuperInsight Platform.

Generates unique hardware fingerprints for license binding.
"""

import hashlib
import platform
import socket
import uuid
from typing import Optional, Dict, Any


class HardwareFingerprint:
    """
    Hardware Fingerprint Generator.
    
    Generates unique hardware identifiers for license binding.
    """
    
    def __init__(self):
        """Initialize Hardware Fingerprint generator."""
        self._cached_fingerprint: Optional[str] = None
    
    def _get_mac_address(self) -> str:
        """Get MAC address."""
        try:
            mac = uuid.getnode()
            return ':'.join(('%012x' % mac)[i:i+2] for i in range(0, 12, 2))
        except Exception:
            return "00:00:00:00:00:00"
    
    def _get_hostname(self) -> str:
        """Get hostname."""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
    
    def _get_platform_info(self) -> str:
        """Get platform information."""
        try:
            return f"{platform.system()}-{platform.machine()}-{platform.processor()}"
        except Exception:
            return "unknown-platform"
    
    def _get_cpu_info(self) -> str:
        """Get CPU information."""
        try:
            return platform.processor() or "unknown-cpu"
        except Exception:
            return "unknown-cpu"
    
    def get_hardware_components(self) -> Dict[str, str]:
        """
        Get individual hardware components.
        
        Returns:
            Dictionary of hardware component values
        """
        return {
            "mac_address": self._get_mac_address(),
            "hostname": self._get_hostname(),
            "platform": self._get_platform_info(),
            "cpu": self._get_cpu_info(),
        }
    
    def generate_fingerprint(self, use_cache: bool = True) -> str:
        """
        Generate hardware fingerprint.
        
        Args:
            use_cache: Whether to use cached fingerprint
            
        Returns:
            SHA-256 hash of hardware components
        """
        if use_cache and self._cached_fingerprint:
            return self._cached_fingerprint
        
        components = self.get_hardware_components()
        
        # Create deterministic string from components
        fingerprint_data = "|".join([
            components["mac_address"],
            components["hostname"],
            components["platform"],
            components["cpu"],
        ])
        
        # Generate SHA-256 hash
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        
        if use_cache:
            self._cached_fingerprint = fingerprint
        
        return fingerprint
    
    def verify_fingerprint(self, expected: str) -> bool:
        """
        Verify if current hardware matches expected fingerprint.
        
        Args:
            expected: Expected fingerprint to match
            
        Returns:
            True if fingerprints match
        """
        current = self.generate_fingerprint(use_cache=False)
        return current == expected
    
    def get_fingerprint_info(self) -> Dict[str, Any]:
        """
        Get fingerprint with component information.
        
        Returns:
            Dictionary with fingerprint and components
        """
        components = self.get_hardware_components()
        fingerprint = self.generate_fingerprint()
        
        return {
            "fingerprint": fingerprint,
            "components": components,
            "algorithm": "sha256",
        }
    
    def clear_cache(self):
        """Clear cached fingerprint."""
        self._cached_fingerprint = None


# Global instance for convenience
_fingerprint_generator = HardwareFingerprint()


def get_hardware_fingerprint() -> str:
    """Get hardware fingerprint using global instance."""
    return _fingerprint_generator.generate_fingerprint()


def verify_hardware_fingerprint(expected: str) -> bool:
    """Verify hardware fingerprint using global instance."""
    return _fingerprint_generator.verify_fingerprint(expected)
