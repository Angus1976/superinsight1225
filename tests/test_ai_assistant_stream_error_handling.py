"""
Test error handling in AI Assistant stream endpoints.

Tests that BaseException errors are properly caught and converted to SSE error chunks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.api.ai_assistant import generate_stream, openclaw_stream, ChatRequest, ChatMessage


@pytest.mark.asyncio
async def test_generate_stream_handles_base_exception():
    """Test that generate_stream catches BaseException and yields error chunk."""
    # Arrange
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="test")],
        mode="direct"
    )
    
    # Create a mock switcher that raises a custom BaseException subclass
    class CustomError(BaseException):
        pass
    
    async def failing_stream(*args, **kwargs):
        raise CustomError("Test error")
        yield  # Make it a generator
    
    mock_switcher = MagicMock()
    mock_switcher.stream_generate = failing_stream
    
    # Act
    chunks = []
    async for chunk in generate_stream(request, mock_switcher):
        chunks.append(chunk)
    
    # Assert
    assert len(chunks) == 1
    assert '"error"' in chunks[0]
    assert '"done": true' in chunks[0]
    assert 'CustomError' in chunks[0] or 'Test error' in chunks[0]


@pytest.mark.asyncio
async def test_generate_stream_handles_standard_exception():
    """Test that generate_stream catches standard Exception and yields error chunk."""
    # Arrange
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="test")],
        mode="direct"
    )
    
    async def failing_stream(*args, **kwargs):
        raise ValueError("Connection failed")
        yield  # Make it a generator
    
    mock_switcher = MagicMock()
    mock_switcher.stream_generate = failing_stream
    
    # Act
    chunks = []
    async for chunk in generate_stream(request, mock_switcher):
        chunks.append(chunk)
    
    # Assert
    assert len(chunks) == 1
    assert '"error"' in chunks[0]
    assert '"done": true' in chunks[0]
    assert 'Connection failed' in chunks[0]


@pytest.mark.asyncio
async def test_openclaw_stream_handles_base_exception():
    """Test that openclaw_stream catches BaseException and yields error chunk."""
    # Arrange
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="test")],
        mode="openclaw",
        gateway_id="test-gateway"
    )
    
    # Create a mock service that raises a custom BaseException subclass
    class CustomError(BaseException):
        pass
    
    async def failing_stream(*args, **kwargs):
        raise CustomError("Gateway error")
        yield  # Make it a generator
    
    mock_service = MagicMock()
    mock_service.stream_chat = failing_stream
    
    mock_user = MagicMock()
    mock_user.tenant_id = "test-tenant"
    
    # Act
    chunks = []
    async for chunk in openclaw_stream(request, mock_service, mock_user):
        chunks.append(chunk)
    
    # Assert
    assert len(chunks) == 1
    assert '"error"' in chunks[0]
    assert '"done": true' in chunks[0]
    assert 'CustomError' in chunks[0] or 'Gateway error' in chunks[0]


@pytest.mark.asyncio
async def test_generate_stream_successful_flow():
    """Test that generate_stream works correctly with successful stream."""
    # Arrange
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="test")],
        mode="direct"
    )
    
    async def successful_stream(*args, **kwargs):
        yield "Hello"
        yield " world"
    
    mock_switcher = MagicMock()
    mock_switcher.stream_generate = successful_stream
    
    # Act
    chunks = []
    async for chunk in generate_stream(request, mock_switcher):
        chunks.append(chunk)
    
    # Assert
    assert len(chunks) == 3  # 2 content chunks + 1 done chunk
    assert '"content": "Hello"' in chunks[0]
    assert '"done": false' in chunks[0]
    assert '"content": " world"' in chunks[1]
    assert '"done": false' in chunks[1]
    assert '"done": true' in chunks[2]
