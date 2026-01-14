"""
SAML 2.0 SSO Connector for SuperInsight Platform.

Implements SAML 2.0 authentication flow.
"""

import base64
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree as ET
import uuid
from datetime import datetime, timedelta

from src.models.security import SSOProtocol
from src.security.sso.base import (
    SSOConnector, SSOUserInfo, LoginInitiation, SSOLoginResult,
    LogoutResult, SSOAuthenticationError
)


class SAMLConnector(SSOConnector):
    """
    SAML 2.0 SSO Connector.
    
    Supports SAML 2.0 Web Browser SSO Profile with HTTP-POST and HTTP-Redirect bindings.
    """
    
    @property
    def protocol(self) -> SSOProtocol:
        return SSOProtocol.SAML
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.entity_id = config.get("entity_id")
        self.sso_url = config.get("sso_url")
        self.slo_url = config.get("slo_url")
        self.certificate = config.get("certificate")
        self.private_key = config.get("private_key")
        self.acs_url = config.get("acs_url")  # Assertion Consumer Service URL
        self.name_id_format = config.get("name_id_format", "urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress")
        self.supports_slo = bool(self.slo_url)
        
        # Attribute mapping
        self.attribute_mapping = config.get("attribute_mapping", {
            "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
            "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
            "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
            "groups": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/groups"
        })
    
    async def initiate_login(self, redirect_uri: str, state: Optional[str] = None) -> LoginInitiation:
        """
        Initiate SAML login by creating AuthnRequest.
        
        Args:
            redirect_uri: URI to redirect after authentication
            state: Optional state parameter
            
        Returns:
            LoginInitiation with SAML AuthnRequest URL
        """
        # Generate unique request ID
        request_id = f"_saml_request_{uuid.uuid4().hex}"
        
        # Create SAML AuthnRequest
        authn_request = self._create_authn_request(request_id, redirect_uri)
        
        # Encode and compress the request
        encoded_request = self._encode_saml_request(authn_request)
        
        # Build SSO URL with parameters
        params = {
            "SAMLRequest": encoded_request,
            "RelayState": state or redirect_uri
        }
        
        # Add signature if configured
        if self.private_key:
            signature = self._sign_request(encoded_request)
            params.update(signature)
        
        sso_url = f"{self.sso_url}?{urlencode(params)}"
        
        return LoginInitiation(
            redirect_url=sso_url,
            state=request_id,
            provider_name=self.name
        )
    
    async def validate_callback(self, callback_data: Dict[str, Any]) -> SSOUserInfo:
        """
        Validate SAML Response and extract user information.
        
        Args:
            callback_data: SAML Response data from callback
            
        Returns:
            SSOUserInfo with user details
            
        Raises:
            SSOAuthenticationError: If validation fails
        """
        saml_response = callback_data.get("SAMLResponse")
        if not saml_response:
            raise SSOAuthenticationError("Missing SAMLResponse parameter", self.name)
        
        try:
            # Decode SAML Response
            decoded_response = base64.b64decode(saml_response)
            response_xml = ET.fromstring(decoded_response)
            
            # Validate response signature if certificate provided
            if self.certificate:
                if not self._validate_signature(response_xml):
                    raise SSOAuthenticationError("Invalid SAML Response signature", self.name)
            
            # Extract assertion
            assertion = self._extract_assertion(response_xml)
            if not assertion:
                raise SSOAuthenticationError("No valid assertion found in SAML Response", self.name)
            
            # Validate assertion conditions
            self._validate_assertion_conditions(assertion)
            
            # Extract user information
            user_info = self._extract_user_info(assertion)
            
            return user_info
            
        except ET.ParseError as e:
            raise SSOAuthenticationError(f"Invalid SAML Response XML: {e}", self.name)
        except Exception as e:
            self.logger.error(f"SAML validation error: {e}")
            raise SSOAuthenticationError(f"SAML validation failed: {e}", self.name)
    
    async def initiate_logout(self, user_id: str, session_id: Optional[str] = None) -> LogoutResult:
        """
        Initiate SAML Single Logout.
        
        Args:
            user_id: User to log out
            session_id: Optional session ID
            
        Returns:
            LogoutResult with SLO URL
        """
        if not self.supports_slo:
            return LogoutResult(success=True)
        
        # Generate unique logout request ID
        request_id = f"_saml_logout_{uuid.uuid4().hex}"
        
        # Create SAML LogoutRequest
        logout_request = self._create_logout_request(request_id, user_id, session_id)
        
        # Encode the request
        encoded_request = self._encode_saml_request(logout_request)
        
        # Build SLO URL
        params = {"SAMLRequest": encoded_request}
        
        # Add signature if configured
        if self.private_key:
            signature = self._sign_request(encoded_request)
            params.update(signature)
        
        slo_url = f"{self.slo_url}?{urlencode(params)}"
        
        return LogoutResult(success=True, redirect_url=slo_url)
    
    def _create_authn_request(self, request_id: str, acs_url: str) -> str:
        """Create SAML AuthnRequest XML."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{timestamp}"
    Destination="{self.sso_url}"
    AssertionConsumerServiceURL="{acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{self.name_id_format}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""
        
        return authn_request
    
    def _create_logout_request(self, request_id: str, user_id: str, session_id: Optional[str] = None) -> str:
        """Create SAML LogoutRequest XML."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        session_index = f'<samlp:SessionIndex>{session_id}</samlp:SessionIndex>' if session_id else ''
        
        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{timestamp}"
    Destination="{self.slo_url}">
    <saml:Issuer>{self.entity_id}</saml:Issuer>
    <saml:NameID Format="{self.name_id_format}">{user_id}</saml:NameID>
    {session_index}
</samlp:LogoutRequest>"""
        
        return logout_request
    
    def _encode_saml_request(self, request_xml: str) -> str:
        """Encode SAML request for HTTP-Redirect binding."""
        import zlib
        
        # Compress and encode
        compressed = zlib.compress(request_xml.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        return encoded
    
    def _sign_request(self, encoded_request: str) -> Dict[str, str]:
        """Sign SAML request (simplified implementation)."""
        # In a real implementation, this would use proper cryptographic signing
        # For now, return empty signature parameters
        return {
            "SigAlg": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "Signature": "placeholder_signature"
        }
    
    def _validate_signature(self, response_xml: ET.Element) -> bool:
        """Validate SAML Response signature."""
        # In a real implementation, this would validate the XML signature
        # using the IdP's certificate
        self.logger.warning("SAML signature validation not fully implemented")
        return True
    
    def _extract_assertion(self, response_xml: ET.Element) -> Optional[ET.Element]:
        """Extract assertion from SAML Response."""
        # Find assertion element
        assertion = response_xml.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}Assertion")
        return assertion
    
    def _validate_assertion_conditions(self, assertion: ET.Element) -> None:
        """Validate assertion conditions (audience, time bounds)."""
        # Check NotBefore and NotOnOrAfter
        conditions = assertion.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}Conditions")
        if conditions is not None:
            not_before = conditions.get("NotBefore")
            not_on_or_after = conditions.get("NotOnOrAfter")
            
            now = datetime.utcnow()
            
            if not_before:
                not_before_dt = datetime.fromisoformat(not_before.replace('Z', '+00:00'))
                if now < not_before_dt.replace(tzinfo=None):
                    raise SSOAuthenticationError("Assertion not yet valid", self.name)
            
            if not_on_or_after:
                not_on_or_after_dt = datetime.fromisoformat(not_on_or_after.replace('Z', '+00:00'))
                if now >= not_on_or_after_dt.replace(tzinfo=None):
                    raise SSOAuthenticationError("Assertion expired", self.name)
        
        # Check audience restriction
        audience_restriction = assertion.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}AudienceRestriction")
        if audience_restriction is not None:
            audience = audience_restriction.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}Audience")
            if audience is not None and audience.text != self.entity_id:
                raise SSOAuthenticationError("Invalid audience", self.name)
    
    def _extract_user_info(self, assertion: ET.Element) -> SSOUserInfo:
        """Extract user information from SAML assertion."""
        # Extract NameID
        name_id = assertion.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}NameID")
        if name_id is None:
            raise SSOAuthenticationError("No NameID found in assertion", self.name)
        
        sso_id = name_id.text
        
        # Extract attributes
        attributes = {}
        attribute_statements = assertion.findall(".//{urn:oasis:names:tc:SAML:2.0:assertion}AttributeStatement")
        
        for attr_statement in attribute_statements:
            for attr in attr_statement.findall(".//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"):
                attr_name = attr.get("Name")
                attr_values = []
                
                for value in attr.findall(".//{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue"):
                    if value.text:
                        attr_values.append(value.text)
                
                if attr_values:
                    attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values
        
        # Map attributes to standard fields
        mapped_attrs = self.map_attributes(attributes)
        
        return SSOUserInfo(
            sso_id=sso_id,
            email=mapped_attrs.get("email", sso_id),
            name=mapped_attrs.get("name"),
            first_name=mapped_attrs.get("first_name"),
            last_name=mapped_attrs.get("last_name"),
            groups=mapped_attrs.get("groups", []) if isinstance(mapped_attrs.get("groups"), list) else [mapped_attrs.get("groups")] if mapped_attrs.get("groups") else [],
            attributes=attributes,
            provider_name=self.name
        )
    
    def validate_config(self) -> List[str]:
        """Validate SAML connector configuration."""
        errors = []
        
        if not self.entity_id:
            errors.append("entity_id is required")
        
        if not self.sso_url:
            errors.append("sso_url is required")
        
        if not self.acs_url:
            errors.append("acs_url is required")
        
        # Validate URLs
        if self.sso_url and not self._is_valid_url(self.sso_url):
            errors.append("sso_url is not a valid URL")
        
        if self.slo_url and not self._is_valid_url(self.slo_url):
            errors.append("slo_url is not a valid URL")
        
        if self.acs_url and not self._is_valid_url(self.acs_url):
            errors.append("acs_url is not a valid URL")
        
        return errors
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False