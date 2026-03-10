"""
Backend i18n message file for data transfer operations.

Provides internationalized messages for data lifecycle transfer operations
in both Chinese (zh) and English (en).
"""

from typing import Optional


# I18n message mapping
MESSAGES = {
    "zh": {
        "success": "成功转存 {count} 条记录到{state}",
        "approval_required": "转存请求已提交,等待审批",
        "permission_denied": "您没有权限执行此操作",
        "security_violation": "检测到安全违规行为",
        "invalid_source": "源数据不存在或未完成",
        "invalid_status": "无效的审批状态",
        "internal_error": "内部服务器错误",
        "approval_approved": "审批请求已批准",
        "approval_rejected": "审批请求已拒绝",
        "approval_not_found": "审批请求 {approval_id} 不存在",
        "approval_expired": "审批请求已过期",
        "states": {
            "temp_stored": "临时存储",
            "in_sample_library": "样本库",
            "annotation_pending": "待标注"
        }
    },
    "en": {
        "success": "Successfully transferred {count} records to {state}",
        "approval_required": "Transfer request submitted for approval",
        "permission_denied": "You don't have permission for this operation",
        "security_violation": "Security violation detected",
        "invalid_source": "Source data not found or incomplete",
        "invalid_status": "Invalid approval status",
        "internal_error": "Internal server error",
        "approval_approved": "Approval request approved successfully",
        "approval_rejected": "Approval request rejected successfully",
        "approval_not_found": "Approval request {approval_id} not found",
        "approval_expired": "Approval request has expired",
        "states": {
            "temp_stored": "temporary storage",
            "in_sample_library": "sample library",
            "annotation_pending": "pending annotation"
        }
    }
}


def get_message(key: str, lang: str = "zh", **kwargs) -> str:
    """
    Get internationalized message.
    
    Args:
        key: Message key (e.g., "success", "approval_required")
        lang: Language code ("zh" or "en")
        **kwargs: Format parameters for the message
        
    Returns:
        Formatted message string
        
    Examples:
        >>> get_message("success", "zh", count=10, state="临时存储")
        '成功转存 10 条记录到临时存储'
        
        >>> get_message("states.temp_stored", "en")
        'temporary storage'
    """
    messages = MESSAGES.get(lang, MESSAGES["zh"])
    
    # Handle nested keys like "states.temp_stored"
    if "." in key:
        parts = key.split(".")
        template = messages
        for part in parts:
            template = template.get(part, key)
    else:
        template = messages.get(key, key)
    
    if isinstance(template, str) and kwargs:
        return template.format(**kwargs)
    return template


def parse_accept_language(accept_language: Optional[str]) -> str:
    """
    Parse Accept-Language header to determine language.
    
    Supports simple language detection from Accept-Language header.
    Defaults to Chinese (zh) if header is not provided or cannot be parsed.
    
    Args:
        accept_language: Accept-Language header value (e.g., "en-US", "zh-CN")
        
    Returns:
        Language code ("zh" or "en")
        
    Examples:
        >>> parse_accept_language("en-US")
        'en'
        
        >>> parse_accept_language("zh-CN")
        'zh'
        
        >>> parse_accept_language(None)
        'zh'
    """
    if not accept_language:
        return "zh"
    
    # Simple parsing: check if starts with "en"
    if accept_language.lower().startswith("en"):
        return "en"
    
    return "zh"
