"""
Data Receiver for Data Sync Pipeline.

Provides Webhook endpoint for receiving pushed data with signature verification
and idempotent processing.
"""

import csv
import hashlib
import hmac
import io
import json
from typing import Any, Dict, List, Optional, Union
import logging

from src.sync.pipeline.enums import DataFormat
from src.sync.pipeline.schemas import ReceiveResult
from src.sync.pipeline.idempotency_store import IdempotencyStore

logger = logging.getLogger(__name__)


class InvalidSignatureError(Exception):
    """Raised when signature verification fails."""
    pass


class BatchSizeLimitExceededError(Exception):
    """Raised when batch size exceeds the limit."""
    pass


class DataParseError(Exception):
    """Raised when data parsing fails."""
    pass


class DataReceiver:
    """
    Data Receiver for Webhook-based data ingestion.
    
    Features:
    - Signature verification (HMAC-SHA256)
    - Idempotent processing
    - Batch size limits
    - JSON and CSV format support
    """
    
    # Maximum batch size (10000 records)
    MAX_BATCH_SIZE = 10000
    
    def __init__(
        self,
        idempotency_store: IdempotencyStore,
        secret_key: Optional[str] = None
    ):
        """
        Initialize the Data Receiver.
        
        Args:
            idempotency_store: Store for managing idempotency keys
            secret_key: Secret key for signature verification
        """
        self.idempotency_store = idempotency_store
        self.secret_key = secret_key or "default_secret_key"
    
    async def receive(
        self,
        data: Union[str, bytes],
        format: DataFormat,
        signature: str,
        idempotency_key: str
    ) -> ReceiveResult:
        """
        Receive and process incoming data.
        
        Args:
            data: Raw data (string or bytes)
            format: Data format (JSON or CSV)
            signature: HMAC signature for verification
            idempotency_key: Unique key for idempotent processing
            
        Returns:
            ReceiveResult with processing status
            
        Raises:
            InvalidSignatureError: If signature verification fails
            BatchSizeLimitExceededError: If batch size exceeds limit
        """
        # Verify signature
        if not self.verify_signature(data, signature):
            raise InvalidSignatureError("Invalid signature")
        
        # Check idempotency
        if await self.idempotency_store.exists(idempotency_key):
            logger.info(f"Duplicate request detected: {idempotency_key}")
            return ReceiveResult(
                success=True,
                duplicate=True,
                rows_received=0
            )
        
        # Parse data
        try:
            parsed = self.parse_data(data, format)
        except Exception as e:
            logger.error(f"Failed to parse data: {str(e)}")
            return ReceiveResult(
                success=False,
                duplicate=False,
                rows_received=0,
                error_message=f"Parse error: {str(e)}"
            )
        
        # Validate batch size
        if len(parsed) > self.MAX_BATCH_SIZE:
            raise BatchSizeLimitExceededError(
                f"Batch size {len(parsed)} exceeds limit of {self.MAX_BATCH_SIZE}"
            )
        
        # Save idempotency key
        await self.idempotency_store.save(idempotency_key)
        
        logger.info(f"Received {len(parsed)} records with key {idempotency_key}")
        
        return ReceiveResult(
            success=True,
            duplicate=False,
            rows_received=len(parsed)
        )
    
    def verify_signature(
        self,
        data: Union[str, bytes],
        signature: str
    ) -> bool:
        """
        Verify HMAC-SHA256 signature.
        
        Args:
            data: Data to verify
            signature: Expected signature
            
        Returns:
            True if signature is valid
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def generate_signature(self, data: Union[str, bytes]) -> str:
        """
        Generate HMAC-SHA256 signature for data.
        
        Args:
            data: Data to sign
            
        Returns:
            Signature string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return hmac.new(
            self.secret_key.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()
    
    def parse_data(
        self,
        data: Union[str, bytes],
        format: DataFormat
    ) -> List[Dict[str, Any]]:
        """
        Parse incoming data based on format.
        
        Args:
            data: Raw data
            format: Data format
            
        Returns:
            List of parsed records
            
        Raises:
            DataParseError: If parsing fails
        """
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        if format == DataFormat.JSON:
            return self._parse_json(data)
        elif format == DataFormat.CSV:
            return self._parse_csv(data)
        else:
            raise DataParseError(f"Unsupported format: {format}")
    
    def _parse_json(self, data: str) -> List[Dict[str, Any]]:
        """
        Parse JSON data.
        
        Args:
            data: JSON string
            
        Returns:
            List of records
        """
        try:
            parsed = json.loads(data)
            
            # Handle both array and single object
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # Check if it's a wrapper with 'data' key
                if 'data' in parsed and isinstance(parsed['data'], list):
                    return parsed['data']
                return [parsed]
            else:
                raise DataParseError("JSON must be an array or object")
                
        except json.JSONDecodeError as e:
            raise DataParseError(f"Invalid JSON: {str(e)}")
    
    def _parse_csv(self, data: str) -> List[Dict[str, Any]]:
        """
        Parse CSV data.
        
        Args:
            data: CSV string
            
        Returns:
            List of records
        """
        try:
            reader = csv.DictReader(io.StringIO(data))
            return list(reader)
        except Exception as e:
            raise DataParseError(f"Invalid CSV: {str(e)}")
    
    async def receive_with_callback(
        self,
        data: Union[str, bytes],
        format: DataFormat,
        signature: str,
        idempotency_key: str,
        callback
    ) -> ReceiveResult:
        """
        Receive data and process with a callback function.
        
        Args:
            data: Raw data
            format: Data format
            signature: HMAC signature
            idempotency_key: Idempotency key
            callback: Async callback function to process parsed data
            
        Returns:
            ReceiveResult with processing status
        """
        result = await self.receive(data, format, signature, idempotency_key)
        
        if result.success and not result.duplicate:
            # Parse and process with callback
            parsed = self.parse_data(data, format)
            await callback(parsed)
        
        return result
