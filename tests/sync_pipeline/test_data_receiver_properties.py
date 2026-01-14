"""
Property-based tests for Data Receiver.

Tests Property 6: Webhook idempotent processing
Tests Property 7: Batch size limit
"""

import pytest
from hypothesis import given, strategies as st, settings
import json
import asyncio

from src.sync.pipeline.enums import DataFormat
from src.sync.pipeline.schemas import ReceiveResult
from src.sync.pipeline.idempotency_store import IdempotencyStore
from src.sync.pipeline.data_receiver import (
    DataReceiver,
    InvalidSignatureError,
    BatchSizeLimitExceededError,
)


# ============================================================================
# Test Helpers
# ============================================================================

def create_receiver():
    """Create a data receiver with fresh idempotency store."""
    store = IdempotencyStore()
    return DataReceiver(store, secret_key="test_secret")


def create_json_data(records: list) -> str:
    """Create JSON data string."""
    return json.dumps(records)


# ============================================================================
# Property 6: Webhook Idempotent Processing
# Validates: Requirements 3.6
# ============================================================================

@settings(max_examples=100)
@given(
    idempotency_key=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=50
    ),
    num_requests=st.integers(min_value=2, max_value=10)
)
def test_idempotent_processing(idempotency_key: str, num_requests: int):
    """
    Property 6: Webhook idempotent processing
    
    For any identical idempotency key, subsequent requests should be
    identified as duplicates and not create duplicate data.
    
    **Validates: Requirements 3.6**
    """
    async def run_test():
        receiver = create_receiver()
        
        # Create test data
        data = create_json_data([{"id": 1, "value": "test"}])
        signature = receiver.generate_signature(data)
        
        # First request should succeed
        result1 = await receiver.receive(
            data, DataFormat.JSON, signature, idempotency_key
        )
        assert result1.success
        assert not result1.duplicate
        assert result1.rows_received == 1
        
        # Subsequent requests should be marked as duplicates
        for i in range(num_requests - 1):
            result = await receiver.receive(
                data, DataFormat.JSON, signature, idempotency_key
            )
            assert result.success, f"Request {i+2} should succeed"
            assert result.duplicate, f"Request {i+2} should be marked as duplicate"
            assert result.rows_received == 0, f"Duplicate should have 0 rows"
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    key1=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=5,
        max_size=20
    ),
    key2=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=5,
        max_size=20
    )
)
def test_different_keys_not_duplicate(key1: str, key2: str):
    """
    Property 6 (inverse): Different keys are not duplicates
    
    Requests with different idempotency keys should not be
    treated as duplicates.
    
    **Validates: Requirements 3.6**
    """
    # Skip if keys happen to be the same
    if key1 == key2:
        return
    
    async def run_test():
        receiver = create_receiver()
        
        data = create_json_data([{"id": 1}])
        signature = receiver.generate_signature(data)
        
        # First request with key1
        result1 = await receiver.receive(
            data, DataFormat.JSON, signature, key1
        )
        assert result1.success
        assert not result1.duplicate
        
        # Request with key2 should not be duplicate
        result2 = await receiver.receive(
            data, DataFormat.JSON, signature, key2
        )
        assert result2.success
        assert not result2.duplicate, "Different key should not be duplicate"
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Property 7: Batch Size Limit
# Validates: Requirements 3.4
# ============================================================================

@settings(max_examples=100)
@given(
    batch_size=st.integers(min_value=10001, max_value=20000)
)
def test_batch_size_limit_exceeded(batch_size: int):
    """
    Property 7: Batch size limit
    
    For any batch with more than 10000 records, the system should
    reject the request with BatchSizeLimitExceededError.
    
    **Validates: Requirements 3.4**
    """
    async def run_test():
        receiver = create_receiver()
        
        # Create data exceeding limit
        records = [{"id": i} for i in range(batch_size)]
        data = create_json_data(records)
        signature = receiver.generate_signature(data)
        
        with pytest.raises(BatchSizeLimitExceededError):
            await receiver.receive(
                data, DataFormat.JSON, signature, "test_key"
            )
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    batch_size=st.integers(min_value=1, max_value=10000)
)
def test_batch_size_within_limit(batch_size: int):
    """
    Property 7 (inverse): Batches within limit are accepted
    
    For any batch with 10000 or fewer records, the request should
    be accepted.
    
    **Validates: Requirements 3.4**
    """
    async def run_test():
        receiver = create_receiver()
        
        # Create data within limit
        records = [{"id": i} for i in range(batch_size)]
        data = create_json_data(records)
        signature = receiver.generate_signature(data)
        
        result = await receiver.receive(
            data, DataFormat.JSON, signature, f"key_{batch_size}"
        )
        
        assert result.success
        assert result.rows_received == batch_size
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_batch_size_exactly_at_limit():
    """
    Property 7 (edge case): Exactly 10000 records is accepted
    
    **Validates: Requirements 3.4**
    """
    async def run_test():
        receiver = create_receiver()
        
        records = [{"id": i} for i in range(10000)]
        data = create_json_data(records)
        signature = receiver.generate_signature(data)
        
        result = await receiver.receive(
            data, DataFormat.JSON, signature, "exact_limit_key"
        )
        
        assert result.success
        assert result.rows_received == 10000
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Signature Verification Tests
# ============================================================================

@settings(max_examples=100)
@given(
    data_content=st.text(min_size=1, max_size=100)
)
def test_valid_signature_accepted(data_content: str):
    """
    Test that valid signatures are accepted.
    
    **Validates: Requirements 3.3**
    """
    async def run_test():
        receiver = create_receiver()
        
        data = create_json_data([{"content": data_content}])
        signature = receiver.generate_signature(data)
        
        result = await receiver.receive(
            data, DataFormat.JSON, signature, f"key_{hash(data_content)}"
        )
        
        assert result.success
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    wrong_signature=st.text(
        alphabet="abcdef0123456789",
        min_size=64,
        max_size=64
    )
)
def test_invalid_signature_rejected(wrong_signature: str):
    """
    Test that invalid signatures are rejected.
    
    **Validates: Requirements 3.3**
    """
    async def run_test():
        receiver = create_receiver()
        
        data = create_json_data([{"id": 1}])
        
        with pytest.raises(InvalidSignatureError):
            await receiver.receive(
                data, DataFormat.JSON, wrong_signature, "test_key"
            )
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Data Format Tests
# ============================================================================

def test_json_array_parsing():
    """Test parsing JSON array format."""
    receiver = create_receiver()
    
    data = '[{"id": 1}, {"id": 2}, {"id": 3}]'
    parsed = receiver.parse_data(data, DataFormat.JSON)
    
    assert len(parsed) == 3
    assert parsed[0]["id"] == 1


def test_json_object_with_data_key():
    """Test parsing JSON object with 'data' key."""
    receiver = create_receiver()
    
    data = '{"data": [{"id": 1}, {"id": 2}]}'
    parsed = receiver.parse_data(data, DataFormat.JSON)
    
    assert len(parsed) == 2


def test_csv_parsing():
    """Test parsing CSV format."""
    receiver = create_receiver()
    
    data = "id,name,value\n1,test1,100\n2,test2,200"
    parsed = receiver.parse_data(data, DataFormat.CSV)
    
    assert len(parsed) == 2
    assert parsed[0]["id"] == "1"
    assert parsed[0]["name"] == "test1"
