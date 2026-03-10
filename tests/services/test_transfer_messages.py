"""
Tests for transfer_messages i18n module.
"""

import pytest
from src.services.transfer_messages import get_message, parse_accept_language


class TestGetMessage:
    """Test get_message function."""
    
    def test_simple_message_zh(self):
        """Test simple message retrieval in Chinese."""
        msg = get_message("approval_required", "zh")
        assert msg == "转存请求已提交,等待审批"
    
    def test_simple_message_en(self):
        """Test simple message retrieval in English."""
        msg = get_message("approval_required", "en")
        assert msg == "Transfer request submitted for approval"
    
    def test_message_with_params_zh(self):
        """Test message with parameters in Chinese."""
        msg = get_message("success", "zh", count=10, state="临时存储")
        assert msg == "成功转存 10 条记录到临时存储"
    
    def test_message_with_params_en(self):
        """Test message with parameters in English."""
        msg = get_message("success", "en", count=5, state="sample library")
        assert msg == "Successfully transferred 5 records to sample library"
    
    def test_nested_key_zh(self):
        """Test nested key retrieval in Chinese."""
        msg = get_message("states.temp_stored", "zh")
        assert msg == "临时存储"
    
    def test_nested_key_en(self):
        """Test nested key retrieval in English."""
        msg = get_message("states.in_sample_library", "en")
        assert msg == "sample library"
    
    def test_missing_key_returns_key(self):
        """Test that missing key returns the key itself."""
        msg = get_message("nonexistent_key", "zh")
        assert msg == "nonexistent_key"
    
    def test_default_language_is_zh(self):
        """Test that default language is Chinese."""
        msg = get_message("approval_required")
        assert msg == "转存请求已提交,等待审批"
    
    def test_invalid_language_defaults_to_zh(self):
        """Test that invalid language code defaults to Chinese."""
        msg = get_message("approval_required", "fr")
        assert msg == "转存请求已提交,等待审批"


class TestParseAcceptLanguage:
    """Test parse_accept_language function."""
    
    def test_none_returns_zh(self):
        """Test that None returns Chinese."""
        lang = parse_accept_language(None)
        assert lang == "zh"
    
    def test_empty_string_returns_zh(self):
        """Test that empty string returns Chinese."""
        lang = parse_accept_language("")
        assert lang == "zh"
    
    def test_en_us_returns_en(self):
        """Test that en-US returns English."""
        lang = parse_accept_language("en-US")
        assert lang == "en"
    
    def test_en_gb_returns_en(self):
        """Test that en-GB returns English."""
        lang = parse_accept_language("en-GB")
        assert lang == "en"
    
    def test_zh_cn_returns_zh(self):
        """Test that zh-CN returns Chinese."""
        lang = parse_accept_language("zh-CN")
        assert lang == "zh"
    
    def test_zh_tw_returns_zh(self):
        """Test that zh-TW returns Chinese."""
        lang = parse_accept_language("zh-TW")
        assert lang == "zh"
    
    def test_case_insensitive(self):
        """Test that parsing is case insensitive."""
        lang = parse_accept_language("EN-US")
        assert lang == "en"
    
    def test_other_language_returns_zh(self):
        """Test that other languages default to Chinese."""
        lang = parse_accept_language("fr-FR")
        assert lang == "zh"
