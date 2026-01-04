"""
Unit tests for i18n API endpoints
Tests language settings and translation retrieval endpoints
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api.i18n import router
from i18n import set_language, get_current_language


class TestLanguageSettingsEndpoints:
    """Unit tests for language settings endpoints"""
    
    def setup_method(self):
        """Set up test client and reset language to default"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        # Reset to default language
        set_language('zh')
    
    def test_get_language_settings_success(self):
        """Test GET endpoint returns current settings"""
        # Validates: Requirements 8.1
        response = self.client.get("/api/settings/language")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "current_language" in data
        assert "supported_languages" in data
        assert "language_names" in data
        
        # Verify default language
        assert data["current_language"] == "zh"
        
        # Verify supported languages
        assert "zh" in data["supported_languages"]
        assert "en" in data["supported_languages"]
        
        # Verify language names
        assert "zh" in data["language_names"]
        assert "en" in data["language_names"]
    
    def test_post_language_setting_success_zh(self):
        """Test POST endpoint changes language to Chinese successfully"""
        # Validates: Requirements 8.2
        response = self.client.post("/api/settings/language?language=zh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "current_language" in data
        
        # Verify language was set in response
        assert data["current_language"] == "zh"
        
        # Note: Due to FastAPI TestClient context isolation,
        # we verify the response rather than global state
    
    def test_post_language_setting_success_en(self):
        """Test POST endpoint changes language to English successfully"""
        # Validates: Requirements 8.2
        response = self.client.post("/api/settings/language?language=en")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "current_language" in data
        
        # Verify language was set in response
        assert data["current_language"] == "en"
        
        # Note: Due to FastAPI TestClient context isolation,
        # we verify the response rather than global state
    
    def test_post_language_setting_invalid_language(self):
        """Test error handling for invalid language requests"""
        # Validates: Requirements 8.2
        response = self.client.post("/api/settings/language?language=invalid")
        
        assert response.status_code == 400
        data = response.json()
        
        # Verify error response
        assert "detail" in data
        
        # Note: Due to FastAPI TestClient context isolation,
        # we verify the error response rather than global state
    
    def test_post_language_setting_missing_parameter(self):
        """Test error handling for missing language parameter"""
        # Validates: Requirements 8.2
        response = self.client.post("/api/settings/language")
        
        assert response.status_code == 422  # FastAPI validation error
        
        # Note: Due to FastAPI TestClient context isolation,
        # we verify the error response rather than global state


class TestTranslationEndpoints:
    """Unit tests for translation retrieval endpoints"""
    
    def setup_method(self):
        """Set up test client and reset language to default"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        # Reset to default language
        set_language('zh')
    
    def test_get_translations_current_language(self):
        """Test translations endpoint returns complete translations for current language"""
        # Validates: Requirements 8.3
        response = self.client.get("/api/i18n/translations")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "language" in data
        assert "translations" in data
        
        # Verify current language
        assert data["language"] == "zh"
        
        # Verify translations exist
        assert isinstance(data["translations"], dict)
        assert len(data["translations"]) > 0
        
        # Verify some expected keys exist
        expected_keys = ["app_name", "login", "logout"]
        for key in expected_keys:
            assert key in data["translations"]
    
    def test_get_translations_specific_language_zh(self):
        """Test language-specific translation retrieval for Chinese"""
        # Validates: Requirements 8.3
        response = self.client.get("/api/i18n/translations?language=zh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["language"] == "zh"
        assert isinstance(data["translations"], dict)
        
        # Verify Chinese translations
        assert "app_name" in data["translations"]
        assert "SuperInsight" in data["translations"]["app_name"]
    
    def test_get_translations_specific_language_en(self):
        """Test language-specific translation retrieval for English"""
        # Validates: Requirements 8.3
        response = self.client.get("/api/i18n/translations?language=en")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["language"] == "en"
        assert isinstance(data["translations"], dict)
        
        # Verify English translations
        assert "app_name" in data["translations"]
        assert "SuperInsight" in data["translations"]["app_name"]
    
    def test_get_translations_invalid_language(self):
        """Test error handling for invalid language parameter"""
        # Validates: Requirements 8.3
        response = self.client.get("/api/i18n/translations?language=invalid")
        
        assert response.status_code == 400
        data = response.json()
        
        # Verify error response
        assert "detail" in data
    
    def test_get_supported_languages_endpoint(self):
        """Test supported languages endpoint"""
        # Validates: Requirements 8.4
        response = self.client.get("/api/i18n/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "supported_languages" in data
        assert "language_names" in data
        
        # Verify supported languages
        assert isinstance(data["supported_languages"], list)
        assert "zh" in data["supported_languages"]
        assert "en" in data["supported_languages"]
        
        # Verify language names
        assert isinstance(data["language_names"], dict)
        assert "zh" in data["language_names"]
        assert "en" in data["language_names"]


class TestAPIErrorHandling:
    """Unit tests for API error handling and HTTP status codes"""
    
    def setup_method(self):
        """Set up test client"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
    
    def test_http_status_codes_success(self):
        """Test appropriate HTTP status codes for successful requests"""
        # Test successful GET requests
        response = self.client.get("/api/settings/language")
        assert response.status_code == 200
        
        response = self.client.get("/api/i18n/translations")
        assert response.status_code == 200
        
        response = self.client.get("/api/i18n/languages")
        assert response.status_code == 200
        
        # Test successful POST request
        response = self.client.post("/api/settings/language?language=zh")
        assert response.status_code == 200
    
    def test_http_status_codes_bad_requests(self):
        """Test appropriate HTTP status codes for bad requests"""
        # Test invalid language parameter
        response = self.client.post("/api/settings/language?language=invalid")
        assert response.status_code == 400
        
        response = self.client.get("/api/i18n/translations?language=invalid")
        assert response.status_code == 400
        
        # Test missing required parameter
        response = self.client.post("/api/settings/language")
        assert response.status_code == 422  # FastAPI validation error
    
    def test_error_response_format(self):
        """Test error response format consistency"""
        response = self.client.post("/api/settings/language?language=invalid")
        
        assert response.status_code == 400
        data = response.json()
        
        # Verify error response has detail field with structured format
        assert "detail" in data
        assert isinstance(data["detail"], dict)
        
        # Check the structured error response format
        detail = data["detail"]
        assert "error" in detail
        assert "message" in detail
        assert "request_id" in detail
        assert "timestamp" in detail
        
        # Verify error details
        assert detail["error"] == "UNSUPPORTED_LANGUAGE"
        assert len(detail["message"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])