"""
Unit tests for the backend internationalization (i18n) message system.

Tests cover:
- get_message returns correct Chinese messages for all keys
- get_message returns correct English messages for all keys
- Default language fallback (when unsupported language requested)
- Message interpolation with kwargs (e.g., count, state)
- State name translations (temp_stored, in_sample_library, annotation_pending)
- parse_accept_language correctly parses Accept-Language headers
- Edge cases: missing keys, empty strings, None values
"""

import pytest
from src.services.transfer_messages import get_message, parse_accept_language, MESSAGES


# ============================================================================
# get_message: Chinese messages for all keys
# ============================================================================

class TestGetMessageChinese:
    """Verify get_message returns correct Chinese messages for every key."""

    def test_success_zh(self):
        msg = get_message("success", "zh", count=10, state="临时存储")
        assert msg == "成功转存 10 条记录到临时存储"

    def test_approval_required_zh(self):
        assert get_message("approval_required", "zh") == "转存请求已提交,等待审批"

    def test_permission_denied_zh(self):
        assert get_message("permission_denied", "zh") == "您没有权限执行此操作"

    def test_security_violation_zh(self):
        assert get_message("security_violation", "zh") == "检测到安全违规行为"

    def test_invalid_source_zh(self):
        assert get_message("invalid_source", "zh") == "源数据不存在或未完成"

    def test_invalid_status_zh(self):
        assert get_message("invalid_status", "zh") == "无效的审批状态"

    def test_internal_error_zh(self):
        assert get_message("internal_error", "zh") == "内部服务器错误"

    def test_approval_approved_zh(self):
        assert get_message("approval_approved", "zh") == "审批请求已批准"

    def test_approval_rejected_zh(self):
        assert get_message("approval_rejected", "zh") == "审批请求已拒绝"

    def test_approval_not_found_zh(self):
        msg = get_message("approval_not_found", "zh", approval_id="abc-123")
        assert msg == "审批请求 abc-123 不存在"

    def test_approval_expired_zh(self):
        assert get_message("approval_expired", "zh") == "审批请求已过期"


# ============================================================================
# get_message: English messages for all keys
# ============================================================================

class TestGetMessageEnglish:
    """Verify get_message returns correct English messages for every key."""

    def test_success_en(self):
        msg = get_message("success", "en", count=5, state="sample library")
        assert msg == "Successfully transferred 5 records to sample library"

    def test_approval_required_en(self):
        assert get_message("approval_required", "en") == "Transfer request submitted for approval"

    def test_permission_denied_en(self):
        assert get_message("permission_denied", "en") == "You don't have permission for this operation"

    def test_security_violation_en(self):
        assert get_message("security_violation", "en") == "Security violation detected"

    def test_invalid_source_en(self):
        assert get_message("invalid_source", "en") == "Source data not found or incomplete"

    def test_invalid_status_en(self):
        assert get_message("invalid_status", "en") == "Invalid approval status"

    def test_internal_error_en(self):
        assert get_message("internal_error", "en") == "Internal server error"

    def test_approval_approved_en(self):
        assert get_message("approval_approved", "en") == "Approval request approved successfully"

    def test_approval_rejected_en(self):
        assert get_message("approval_rejected", "en") == "Approval request rejected successfully"

    def test_approval_not_found_en(self):
        msg = get_message("approval_not_found", "en", approval_id="xyz-789")
        assert msg == "Approval request xyz-789 not found"

    def test_approval_expired_en(self):
        assert get_message("approval_expired", "en") == "Approval request has expired"


# ============================================================================
# Default language fallback
# ============================================================================

class TestDefaultLanguageFallback:
    """When no language or unsupported language is given, fall back to Chinese."""

    def test_default_language_is_zh(self):
        """Omitting lang should default to Chinese."""
        assert get_message("permission_denied") == "您没有权限执行此操作"

    def test_unsupported_language_falls_back_to_zh(self):
        assert get_message("permission_denied", "fr") == "您没有权限执行此操作"

    def test_unsupported_language_ja(self):
        assert get_message("internal_error", "ja") == "内部服务器错误"

    def test_unsupported_language_de(self):
        assert get_message("approval_required", "de") == "转存请求已提交,等待审批"


# ============================================================================
# Message interpolation with kwargs
# ============================================================================

class TestMessageInterpolation:
    """Verify kwargs are correctly interpolated into message templates."""

    def test_success_interpolation_zh(self):
        msg = get_message("success", "zh", count=100, state="样本库")
        assert "100" in msg
        assert "样本库" in msg

    def test_success_interpolation_en(self):
        msg = get_message("success", "en", count=0, state="temporary storage")
        assert "0" in msg
        assert "temporary storage" in msg

    def test_approval_not_found_interpolation(self):
        msg = get_message("approval_not_found", "en", approval_id="test-id-42")
        assert "test-id-42" in msg

    def test_no_kwargs_on_static_message(self):
        """Static messages should work fine without kwargs."""
        msg = get_message("permission_denied", "en")
        assert msg == "You don't have permission for this operation"

    def test_extra_kwargs_ignored_by_format(self):
        """Extra kwargs that aren't in the template should not cause errors
        if the template doesn't reference them (Python str.format ignores extras
        when using named placeholders)."""
        # 'approval_required' has no placeholders
        msg = get_message("approval_required", "zh", extra="ignored")
        assert msg == "转存请求已提交,等待审批"


# ============================================================================
# State name translations
# ============================================================================

class TestStateNameTranslations:
    """Verify state name translations via nested key access."""

    def test_temp_stored_zh(self):
        assert get_message("states.temp_stored", "zh") == "临时存储"

    def test_in_sample_library_zh(self):
        assert get_message("states.in_sample_library", "zh") == "样本库"

    def test_annotation_pending_zh(self):
        assert get_message("states.annotation_pending", "zh") == "待标注"

    def test_temp_stored_en(self):
        assert get_message("states.temp_stored", "en") == "temporary storage"

    def test_in_sample_library_en(self):
        assert get_message("states.in_sample_library", "en") == "sample library"

    def test_annotation_pending_en(self):
        assert get_message("states.annotation_pending", "en") == "pending annotation"

    def test_all_zh_states_present(self):
        """All three state keys should exist in the zh messages."""
        zh_states = MESSAGES["zh"]["states"]
        assert set(zh_states.keys()) == {"temp_stored", "in_sample_library", "annotation_pending"}

    def test_all_en_states_present(self):
        """All three state keys should exist in the en messages."""
        en_states = MESSAGES["en"]["states"]
        assert set(en_states.keys()) == {"temp_stored", "in_sample_library", "annotation_pending"}


# ============================================================================
# parse_accept_language
# ============================================================================

class TestParseAcceptLanguage:
    """Verify parse_accept_language correctly parses Accept-Language headers."""

    def test_none_returns_zh(self):
        assert parse_accept_language(None) == "zh"

    def test_empty_string_returns_zh(self):
        assert parse_accept_language("") == "zh"

    def test_en_us(self):
        assert parse_accept_language("en-US") == "en"

    def test_en_gb(self):
        assert parse_accept_language("en-GB") == "en"

    def test_en_plain(self):
        assert parse_accept_language("en") == "en"

    def test_zh_cn(self):
        assert parse_accept_language("zh-CN") == "zh"

    def test_zh_tw(self):
        assert parse_accept_language("zh-TW") == "zh"

    def test_case_insensitive_upper(self):
        assert parse_accept_language("EN-US") == "en"

    def test_case_insensitive_mixed(self):
        assert parse_accept_language("En-us") == "en"

    def test_french_defaults_to_zh(self):
        assert parse_accept_language("fr-FR") == "zh"

    def test_japanese_defaults_to_zh(self):
        assert parse_accept_language("ja-JP") == "zh"

    def test_german_defaults_to_zh(self):
        assert parse_accept_language("de-DE") == "zh"


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:
    """Edge cases: missing keys, empty strings, None-like values."""

    def test_missing_key_returns_key_itself(self):
        assert get_message("nonexistent_key", "zh") == "nonexistent_key"

    def test_missing_key_en_returns_key(self):
        assert get_message("totally_unknown", "en") == "totally_unknown"

    def test_missing_nested_key_returns_key(self):
        """A nested key where the second part doesn't exist."""
        result = get_message("states.nonexistent", "zh")
        assert result == "states.nonexistent"

    def test_empty_string_key(self):
        """Empty string key should return the empty string (not found → returns key)."""
        result = get_message("", "zh")
        assert result == ""

    def test_message_keys_consistent_across_languages(self):
        """Both zh and en should have the same top-level keys."""
        zh_keys = {k for k, v in MESSAGES["zh"].items() if isinstance(v, str)}
        en_keys = {k for k, v in MESSAGES["en"].items() if isinstance(v, str)}
        assert zh_keys == en_keys, f"Key mismatch: zh-only={zh_keys - en_keys}, en-only={en_keys - zh_keys}"

    def test_state_keys_consistent_across_languages(self):
        """Both zh and en should have the same state keys."""
        zh_state_keys = set(MESSAGES["zh"]["states"].keys())
        en_state_keys = set(MESSAGES["en"]["states"].keys())
        assert zh_state_keys == en_state_keys
