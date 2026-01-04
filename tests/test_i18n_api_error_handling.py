"""
i18n API 错误处理单元测试
测试 API 端点的错误处理、验证和响应格式化
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, HTTPException
from pydantic import ValidationError

from src.i18n.api_error_handler import (
    APIErrorDetail,
    APIErrorResponse,
    I18nAPIError,
    ValidationAPIError,
    LanguageNotSupportedAPIError,
    ResourceNotFoundAPIError,
    InternalServerAPIError,
    validate_language_parameter,
    validate_query_parameters,
    format_validation_error,
    create_error_response,
    handle_api_exception,
    safe_api_call,
    get_http_status_message,
    validate_http_status_code
)


class TestAPIErrorModels:
    """测试 API 错误模型"""
    
    def test_api_error_detail_creation(self):
        """测试 API 错误详情创建"""
        detail = APIErrorDetail(
            code="TEST_ERROR",
            message="Test error message",
            field="test_field",
            details={"key": "value"}
        )
        
        assert detail.code == "TEST_ERROR"
        assert detail.message == "Test error message"
        assert detail.field == "test_field"
        assert detail.details == {"key": "value"}
    
    def test_api_error_response_creation(self):
        """测试 API 错误响应创建"""
        details = [APIErrorDetail(code="TEST", message="Test")]
        response = APIErrorResponse(
            error="TEST_ERROR",
            message="Test error",
            details=details,
            request_id="test-123",
            timestamp="2023-01-01T00:00:00Z"
        )
        
        assert response.error == "TEST_ERROR"
        assert response.message == "Test error"
        assert len(response.details) == 1
        assert response.request_id == "test-123"
        assert response.timestamp == "2023-01-01T00:00:00Z"


class TestAPIExceptions:
    """测试 API 异常类"""
    
    def test_i18n_api_error(self):
        """测试基础 API 错误"""
        error = I18nAPIError(
            message="Test error",
            status_code=400,
            error_code="TEST_ERROR",
            details={"key": "value"}
        )
        
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}
    
    def test_validation_api_error(self):
        """测试验证 API 错误"""
        error = ValidationAPIError(
            message="Validation failed",
            field="test_field",
            details={"reason": "invalid"}
        )
        
        assert error.message == "Validation failed"
        assert error.status_code == 400
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field == "test_field"
        assert error.details == {"reason": "invalid"}
    
    def test_language_not_supported_api_error(self):
        """测试不支持语言 API 错误"""
        error = LanguageNotSupportedAPIError("fr", ["zh", "en"])
        
        assert error.status_code == 400
        assert error.error_code == "UNSUPPORTED_LANGUAGE"
        assert error.details["requested_language"] == "fr"
        assert error.details["supported_languages"] == ["zh", "en"]
    
    def test_resource_not_found_api_error(self):
        """测试资源未找到 API 错误"""
        error = ResourceNotFoundAPIError("translation", "missing_key")
        
        assert error.status_code == 404
        assert error.error_code == "RESOURCE_NOT_FOUND"
        assert error.details["resource_type"] == "translation"
        assert error.details["resource_id"] == "missing_key"
    
    def test_internal_server_api_error(self):
        """测试内部服务器 API 错误"""
        original_error = ValueError("Original error")
        error = InternalServerAPIError(original_error)
        
        assert error.status_code == 500
        assert error.error_code == "INTERNAL_SERVER_ERROR"
        assert error.details["original_error"] == "Original error"
        assert error.details["error_type"] == "ValueError"


class TestLanguageParameterValidation:
    """测试语言参数验证"""
    
    def test_validate_language_parameter_valid(self):
        """测试有效语言参数验证"""
        result = validate_language_parameter("zh", ["zh", "en"])
        assert result == "zh"
        
        result = validate_language_parameter("  EN  ", ["zh", "en"])
        assert result == "en"
    
    def test_validate_language_parameter_empty(self):
        """测试空语言参数"""
        with pytest.raises(ValidationAPIError) as exc_info:
            validate_language_parameter("", ["zh", "en"])
        
        assert exc_info.value.field == "language"
        # 错误消息可能被翻译，检查错误代码
        assert exc_info.value.error_code == "VALIDATION_ERROR"
    
    def test_validate_language_parameter_none(self):
        """测试 None 语言参数"""
        with pytest.raises(ValidationAPIError) as exc_info:
            validate_language_parameter(None, ["zh", "en"])
        
        assert exc_info.value.field == "language"
    
    def test_validate_language_parameter_wrong_type(self):
        """测试错误类型的语言参数"""
        with pytest.raises(ValidationAPIError) as exc_info:
            validate_language_parameter(123, ["zh", "en"])
        
        assert exc_info.value.field == "language"
        assert exc_info.value.error_code == "VALIDATION_ERROR"
    
    def test_validate_language_parameter_whitespace_only(self):
        """测试只有空白字符的语言参数"""
        with pytest.raises(ValidationAPIError) as exc_info:
            validate_language_parameter("   ", ["zh", "en"])
        
        assert exc_info.value.field == "language"
        assert exc_info.value.details["reason"] == "empty_after_strip"
    
    def test_validate_language_parameter_unsupported(self):
        """测试不支持的语言参数"""
        with pytest.raises(LanguageNotSupportedAPIError) as exc_info:
            validate_language_parameter("fr", ["zh", "en"])
        
        assert exc_info.value.details["requested_language"] == "fr"
        assert exc_info.value.details["supported_languages"] == ["zh", "en"]


class TestQueryParameterValidation:
    """测试查询参数验证"""
    
    def create_mock_request(self, query_params: dict):
        """创建模拟请求对象"""
        request = Mock(spec=Request)
        request.query_params = query_params
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com/api")
        return request
    
    def test_validate_query_parameters_valid(self):
        """测试有效查询参数验证"""
        request = self.create_mock_request({
            "required_param": "value1",
            "optional_param": "value2"
        })
        
        result = validate_query_parameters(
            request,
            required_params=["required_param"],
            optional_params=["optional_param"]
        )
        
        assert result["required_param"] == "value1"
        assert result["optional_param"] == "value2"
    
    def test_validate_query_parameters_missing_required(self):
        """测试缺失必需参数"""
        request = self.create_mock_request({"optional_param": "value"})
        
        with pytest.raises(ValidationAPIError) as exc_info:
            validate_query_parameters(
                request,
                required_params=["required_param"],
                optional_params=["optional_param"]
            )
        
        assert exc_info.value.field == "required_param"
        assert exc_info.value.error_code == "VALIDATION_ERROR"
    
    def test_validate_query_parameters_empty_required(self):
        """测试空的必需参数"""
        request = self.create_mock_request({"required_param": "   "})
        
        with pytest.raises(ValidationAPIError) as exc_info:
            validate_query_parameters(
                request,
                required_params=["required_param"]
            )
        
        assert exc_info.value.field == "required_param"
        assert exc_info.value.details["reason"] == "empty_value"
    
    def test_validate_query_parameters_unknown_params(self):
        """测试未知参数（应该记录警告但不抛出异常）"""
        request = self.create_mock_request({
            "required_param": "value",
            "unknown_param": "unknown_value"
        })
        
        with patch('src.i18n.api_error_handler.log_translation_error') as mock_log:
            result = validate_query_parameters(
                request,
                required_params=["required_param"]
            )
            
            assert result["required_param"] == "value"
            assert "unknown_param" not in result
            
            # 应该记录警告
            mock_log.assert_called_once()
            assert mock_log.call_args[0][0] == 'unknown_query_parameters'
    
    def test_validate_query_parameters_optional_empty(self):
        """测试可选参数为空"""
        request = self.create_mock_request({
            "required_param": "value",
            "optional_param": ""
        })
        
        result = validate_query_parameters(
            request,
            required_params=["required_param"],
            optional_params=["optional_param"]
        )
        
        assert result["required_param"] == "value"
        assert result["optional_param"] == ""


class TestErrorResponseCreation:
    """测试错误响应创建"""
    
    def test_create_error_response_i18n_api_error(self):
        """测试创建 i18n API 错误响应"""
        error = ValidationAPIError("Test validation error", "test_field", {"key": "value"})
        response = create_error_response(error, "test-123")
        
        assert response.error == "VALIDATION_ERROR"
        assert response.message == "Test validation error"
        assert response.request_id == "test-123"
        assert response.timestamp is not None
        assert response.details is not None
        assert len(response.details) == 1
        assert response.details[0].code == "VALIDATION_ERROR"
    
    def test_create_error_response_http_exception(self):
        """测试创建 HTTP 异常响应"""
        error = HTTPException(status_code=404, detail="Not found")
        response = create_error_response(error)
        
        assert response.error == "HTTP_ERROR"
        assert response.message == "Not found"
        assert len(response.details) == 1
        assert response.details[0].code == "HTTP_404"
    
    def test_create_error_response_validation_error(self):
        """测试创建验证错误响应"""
        # 创建一个模拟的 ValidationError
        from pydantic import BaseModel, validator
        
        class TestModel(BaseModel):
            name: str
            
            @validator('name')
            def name_must_not_be_empty(cls, v):
                if not v.strip():
                    raise ValueError('Name cannot be empty')
                return v
        
        try:
            TestModel(name="")
        except ValidationError as validation_error:
            response = create_error_response(validation_error)
            
            assert response.error == "VALIDATION_ERROR"
            assert len(response.details) > 0
            assert response.details[0].code == "VALIDATION_ERROR"
    
    def test_create_error_response_unknown_exception(self):
        """测试创建未知异常响应"""
        error = ValueError("Unknown error")
        
        with patch('src.i18n.api_error_handler.log_translation_error') as mock_log:
            response = create_error_response(error)
            
            assert response.error == "INTERNAL_SERVER_ERROR"
            assert len(response.details) == 1
            assert response.details[0].code == "UNEXPECTED_ERROR"
            
            # 应该记录错误
            mock_log.assert_called_once()
            assert mock_log.call_args[0][0] == 'unexpected_api_error'


class TestAPIExceptionHandling:
    """测试 API 异常处理"""
    
    def create_mock_request(self):
        """创建模拟请求对象"""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com/api")
        return request
    
    def test_handle_api_exception_i18n_error(self):
        """测试处理 i18n API 错误"""
        error = ValidationAPIError("Test error", "test_field")
        request = self.create_mock_request()
        
        with patch('src.i18n.api_error_handler.log_translation_error') as mock_log:
            result = handle_api_exception(error, request, "test-123")
            
            assert isinstance(result, HTTPException)
            assert result.status_code == 400
            assert isinstance(result.detail, dict)
            
            # 应该记录警告
            mock_log.assert_called_once()
    
    def test_handle_api_exception_http_exception(self):
        """测试处理 HTTP 异常"""
        error = HTTPException(status_code=404, detail="Not found")
        request = self.create_mock_request()
        
        result = handle_api_exception(error, request)
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 404
    
    def test_handle_api_exception_validation_error(self):
        """测试处理验证错误"""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
        
        try:
            TestModel(name=123)  # 类型错误
        except ValidationError as validation_error:
            result = handle_api_exception(validation_error)
            
            assert isinstance(result, HTTPException)
            assert result.status_code == 400
    
    def test_handle_api_exception_unknown_error(self):
        """测试处理未知错误"""
        error = ValueError("Unknown error")
        
        with patch('src.i18n.api_error_handler.log_translation_error') as mock_log:
            result = handle_api_exception(error)
            
            assert isinstance(result, HTTPException)
            assert result.status_code == 500
            
            # 应该记录错误（可能被调用多次）
            assert mock_log.call_count >= 1


class TestSafeAPICall:
    """测试安全 API 调用装饰器"""
    
    def test_safe_api_call_normal_execution(self):
        """测试正常执行"""
        @safe_api_call
        async def test_function(value):
            return {"result": value * 2}
        
        import asyncio
        result = asyncio.run(test_function(5))
        assert result == {"result": 10}
    
    def test_safe_api_call_i18n_error(self):
        """测试 i18n 错误处理"""
        @safe_api_call
        async def test_function():
            raise ValidationAPIError("Test error", "test_field")
        
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(test_function())
        
        assert exc_info.value.status_code == 400
    
    def test_safe_api_call_unexpected_error(self):
        """测试意外错误处理"""
        @safe_api_call
        async def test_function():
            raise ValueError("Unexpected error")
        
        import asyncio
        with patch('src.i18n.api_error_handler.log_translation_error') as mock_log:
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(test_function())
            
            assert exc_info.value.status_code == 500
            
            # 应该记录关键错误
            mock_log.assert_called()
            assert any(call[0][0] == 'unexpected_api_error' for call in mock_log.call_args_list)


class TestHTTPStatusCodeUtils:
    """测试 HTTP 状态码工具函数"""
    
    def test_get_http_status_message_known(self):
        """测试获取已知状态码消息"""
        assert get_http_status_message(200) == "OK"
        assert get_http_status_message(404) == "Not Found"
        assert get_http_status_message(500) == "Internal Server Error"
    
    def test_get_http_status_message_unknown(self):
        """测试获取未知状态码消息"""
        assert get_http_status_message(999) == "Unknown Status"
    
    def test_validate_http_status_code_valid(self):
        """测试验证有效状态码"""
        assert validate_http_status_code(200) is True
        assert validate_http_status_code(404) is True
        assert validate_http_status_code(500) is True
    
    def test_validate_http_status_code_invalid_range(self):
        """测试验证无效范围的状态码"""
        assert validate_http_status_code(99) is False
        assert validate_http_status_code(600) is False
    
    def test_validate_http_status_code_unknown_but_valid_range(self):
        """测试验证未知但在有效范围内的状态码"""
        assert validate_http_status_code(299) is False  # 不在常用列表中
        assert validate_http_status_code(418) is False  # I'm a teapot


class TestErrorHandlingIntegration:
    """测试错误处理集成"""
    
    def test_error_chain_validation_to_response(self):
        """测试从验证到响应的错误链"""
        # 模拟完整的错误处理流程
        try:
            validate_language_parameter("invalid", ["zh", "en"])
        except LanguageNotSupportedAPIError as error:
            response = create_error_response(error, "test-123")
            
            assert response.error == "UNSUPPORTED_LANGUAGE"
            assert response.request_id == "test-123"
            assert len(response.details) == 1
    
    def test_multiple_validation_errors(self):
        """测试多个验证错误"""
        from pydantic import BaseModel, validator
        
        class TestModel(BaseModel):
            name: str
            age: int
            
            @validator('name')
            def name_must_not_be_empty(cls, v):
                if not v.strip():
                    raise ValueError('Name cannot be empty')
                return v
            
            @validator('age')
            def age_must_be_positive(cls, v):
                if v < 0:
                    raise ValueError('Age must be positive')
                return v
        
        try:
            TestModel(name="", age=-1)
        except ValidationError as validation_error:
            details = format_validation_error(validation_error)
            
            assert len(details) >= 2  # 至少两个错误
            assert all(isinstance(detail, APIErrorDetail) for detail in details)


if __name__ == "__main__":
    pytest.main([__file__])