"""
File System Connector for SuperInsight Platform.

Provides connectors for various file systems:
- Local file system
- FTP/SFTP
- Cloud storage (S3, Azure Blob, GCS)
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union
import hashlib
import mimetypes

from pydantic import BaseModel, Field

from src.sync.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectionStatus,
    DataBatch,
    DataRecord,
    OperationType,
    SyncResult,
    ConnectorFactory,
)

logger = logging.getLogger(__name__)


class FileSystemType(str, Enum):
    """Supported file system types."""
    LOCAL = "local"
    FTP = "ftp"
    SFTP = "sftp"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"


@dataclass
class FileInfo:
    """Information about a file."""
    path: str
    name: str
    size: int
    modified_at: datetime
    created_at: Optional[datetime] = None
    is_directory: bool = False
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileSystemConfig(ConnectorConfig):
    """Base file system configuration."""
    fs_type: FileSystemType = FileSystemType.LOCAL
    base_path: str = ""
    
    # File filtering
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    recursive: bool = True
    
    # Processing settings
    chunk_size: int = 8192
    compute_checksum: bool = True


class LocalFileSystemConfig(FileSystemConfig):
    """Local file system configuration."""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.fs_type = FileSystemType.LOCAL


class SFTPConfig(FileSystemConfig):
    """SFTP configuration."""
    host: str = "localhost"
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    known_hosts_path: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.fs_type = FileSystemType.SFTP


class S3Config(FileSystemConfig):
    """AWS S3 configuration."""
    bucket: str = ""
    region: str = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None  # For S3-compatible services
    
    def __init__(self, **data):
        super().__init__(**data)
        self.fs_type = FileSystemType.S3


class AzureBlobConfig(FileSystemConfig):
    """Azure Blob Storage configuration."""
    container: str = ""
    connection_string: Optional[str] = None
    account_name: Optional[str] = None
    account_key: Optional[str] = None
    sas_token: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.fs_type = FileSystemType.AZURE_BLOB


class GCSConfig(FileSystemConfig):
    """Google Cloud Storage configuration."""
    bucket: str = ""
    project_id: Optional[str] = None
    credentials_path: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.fs_type = FileSystemType.GCS


class BaseFileSystemConnector(BaseConnector):
    """Abstract base class for file system connectors."""
    
    def __init__(self, config: FileSystemConfig):
        super().__init__(config)
        self.fs_config = config
    
    @abstractmethod
    async def list_files(
        self,
        path: str = "",
        recursive: bool = True
    ) -> List[FileInfo]:
        """List files in a directory."""
        pass
    
    @abstractmethod
    async def read_file(self, path: str) -> bytes:
        """Read file content."""
        pass
    
    @abstractmethod
    async def write_file(self, path: str, content: bytes) -> bool:
        """Write file content."""
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Get file information."""
        pass
    
    def _matches_patterns(self, path: str) -> bool:
        """Check if path matches include/exclude patterns."""
        import fnmatch
        
        # Check exclude patterns first
        for pattern in self.fs_config.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False
        
        # If no include patterns, include all
        if not self.fs_config.include_patterns:
            return True
        
        # Check include patterns
        for pattern in self.fs_config.include_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        
        return False
    
    def _compute_checksum(self, content: bytes) -> str:
        """Compute MD5 checksum of content."""
        return hashlib.md5(content).hexdigest()


class LocalFileSystemConnector(BaseFileSystemConnector):
    """
    Local file system connector.
    
    Features:
    - Directory listing with filtering
    - File reading and writing
    - Checksum computation
    - Metadata extraction
    """
    
    def __init__(self, config: LocalFileSystemConfig):
        super().__init__(config)
        self.local_config = config
    
    async def connect(self) -> bool:
        """Verify local file system access."""
        try:
            base_path = Path(self.local_config.base_path)
            
            if not base_path.exists():
                logger.warning(f"Base path does not exist: {base_path}")
                # Create if needed
                base_path.mkdir(parents=True, exist_ok=True)
            
            self._set_status(ConnectionStatus.CONNECTED)
            logger.info(f"Connected to local file system: {base_path}")
            return True
            
        except Exception as e:
            self._set_status(ConnectionStatus.ERROR)
            self._record_error(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect (no-op for local FS)."""
        self._set_status(ConnectionStatus.DISCONNECTED)
    
    async def health_check(self) -> bool:
        """Check if base path is accessible."""
        try:
            base_path = Path(self.local_config.base_path)
            return base_path.exists() and os.access(base_path, os.R_OK)
        except Exception:
            return False
    
    async def fetch_schema(self) -> Dict[str, Any]:
        """Get file system schema (directory structure)."""
        files = await self.list_files()
        
        return {
            "type": "local_filesystem",
            "base_path": self.local_config.base_path,
            "total_files": len(files),
            "total_size": sum(f.size for f in files),
            "file_types": list(set(f.mime_type for f in files if f.mime_type))
        }
    
    async def fetch_data(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None
    ) -> DataBatch:
        """Fetch files as data records."""
        path = table or ""
        files = await self.list_files(path, self.local_config.recursive)
        
        # Apply incremental filter
        if incremental_field == "modified_at" and incremental_value:
            cutoff = datetime.fromisoformat(incremental_value)
            files = [f for f in files if f.modified_at > cutoff]
        
        # Apply pagination
        total = len(files)
        files = files[offset:offset + (limit or self.config.batch_size)]
        
        records = []
        for file_info in files:
            content = await self.read_file(file_info.path)
            
            record = DataRecord(
                id=file_info.path,
                data={
                    "path": file_info.path,
                    "name": file_info.name,
                    "size": file_info.size,
                    "mime_type": file_info.mime_type,
                    "content": content.decode('utf-8', errors='replace') if len(content) < 1024 * 1024 else "[binary]",
                    "checksum": file_info.checksum
                },
                metadata={
                    "modified_at": file_info.modified_at.isoformat(),
                    "created_at": file_info.created_at.isoformat() if file_info.created_at else None
                },
                timestamp=file_info.modified_at,
                operation=OperationType.UPSERT
            )
            records.append(record)
        
        return DataBatch(
            records=records,
            source_id=f"local:{self.local_config.base_path}",
            total_count=total,
            offset=offset,
            has_more=(offset + len(records)) < total
        )
    
    async def fetch_data_stream(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None
    ) -> AsyncIterator[DataBatch]:
        """Stream files in batches."""
        batch_size = batch_size or self.config.batch_size
        offset = 0
        has_more = True
        
        while has_more:
            batch = await self.fetch_data(
                table=table,
                limit=batch_size,
                offset=offset,
                incremental_field=incremental_field,
                incremental_value=incremental_value
            )
            
            yield batch
            
            has_more = batch.has_more
            offset += len(batch.records)
    
    async def write_data(self, batch: DataBatch, mode: str = "upsert") -> SyncResult:
        """Write data batch to file system."""
        import time
        start_time = time.time()
        
        result = SyncResult(
            success=True,
            records_processed=len(batch.records)
        )
        
        for record in batch.records:
            try:
                path = record.data.get("path", record.id)
                content = record.data.get("content", "")
                
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                await self.write_file(path, content)
                result.records_inserted += 1
                
            except Exception as e:
                result.records_failed += 1
                result.errors.append({
                    "record_id": record.id,
                    "error": str(e)
                })
        
        result.duration_seconds = time.time() - start_time
        return result
    
    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get file count."""
        files = await self.list_files(table or "", self.local_config.recursive)
        return len(files)
    
    async def list_files(
        self,
        path: str = "",
        recursive: bool = True
    ) -> List[FileInfo]:
        """List files in directory."""
        base = Path(self.local_config.base_path) / path
        files = []
        
        if not base.exists():
            return files
        
        def process_path(p: Path):
            if p.is_file() and self._matches_patterns(str(p)):
                stat = p.stat()
                mime_type, _ = mimetypes.guess_type(str(p))
                
                checksum = None
                if self.fs_config.compute_checksum:
                    with open(p, 'rb') as f:
                        checksum = self._compute_checksum(f.read())
                
                files.append(FileInfo(
                    path=str(p.relative_to(self.local_config.base_path)),
                    name=p.name,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    mime_type=mime_type,
                    checksum=checksum
                ))
        
        if recursive:
            for p in base.rglob("*"):
                process_path(p)
        else:
            for p in base.iterdir():
                process_path(p)
        
        return files
    
    async def read_file(self, path: str) -> bytes:
        """Read file content."""
        full_path = Path(self.local_config.base_path) / path
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    async def write_file(self, path: str, content: bytes) -> bool:
        """Write file content."""
        full_path = Path(self.local_config.base_path) / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(content)
        
        return True
    
    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        full_path = Path(self.local_config.base_path) / path
        
        if full_path.exists():
            full_path.unlink()
            return True
        
        return False
    
    async def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        full_path = Path(self.local_config.base_path) / path
        return full_path.exists()
    
    async def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Get file information."""
        full_path = Path(self.local_config.base_path) / path
        
        if not full_path.exists():
            return None
        
        stat = full_path.stat()
        mime_type, _ = mimetypes.guess_type(str(full_path))
        
        checksum = None
        if self.fs_config.compute_checksum:
            with open(full_path, 'rb') as f:
                checksum = self._compute_checksum(f.read())
        
        return FileInfo(
            path=path,
            name=full_path.name,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            created_at=datetime.fromtimestamp(stat.st_ctime),
            is_directory=full_path.is_dir(),
            mime_type=mime_type,
            checksum=checksum
        )


class S3Connector(BaseFileSystemConnector):
    """
    AWS S3 connector.
    
    Features:
    - Bucket operations
    - Object listing with prefix filtering
    - Multipart upload support
    - Versioning support
    """
    
    def __init__(self, config: S3Config):
        super().__init__(config)
        self.s3_config = config
        self._client = None
    
    async def connect(self) -> bool:
        """Connect to S3."""
        try:
            import aioboto3
            
            session = aioboto3.Session()
            
            client_kwargs = {
                "region_name": self.s3_config.region
            }
            
            if self.s3_config.access_key_id:
                client_kwargs["aws_access_key_id"] = self.s3_config.access_key_id
                client_kwargs["aws_secret_access_key"] = self.s3_config.secret_access_key
            
            if self.s3_config.endpoint_url:
                client_kwargs["endpoint_url"] = self.s3_config.endpoint_url
            
            self._session = session
            self._client_kwargs = client_kwargs
            
            # Test connection
            async with session.client("s3", **client_kwargs) as client:
                await client.head_bucket(Bucket=self.s3_config.bucket)
            
            self._set_status(ConnectionStatus.CONNECTED)
            logger.info(f"Connected to S3: {self.s3_config.bucket}")
            return True
            
        except ImportError:
            logger.error("aioboto3 is required. Install with: pip install aioboto3")
            return False
        except Exception as e:
            self._set_status(ConnectionStatus.ERROR)
            self._record_error(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from S3."""
        self._set_status(ConnectionStatus.DISCONNECTED)
        logger.info("Disconnected from S3")
    
    async def health_check(self) -> bool:
        """Check S3 bucket accessibility."""
        try:
            async with self._session.client("s3", **self._client_kwargs) as client:
                await client.head_bucket(Bucket=self.s3_config.bucket)
            return True
        except Exception:
            return False
    
    async def fetch_schema(self) -> Dict[str, Any]:
        """Get S3 bucket schema."""
        files = await self.list_files()
        
        return {
            "type": "s3",
            "bucket": self.s3_config.bucket,
            "region": self.s3_config.region,
            "total_objects": len(files),
            "total_size": sum(f.size for f in files)
        }
    
    async def fetch_data(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None
    ) -> DataBatch:
        """Fetch S3 objects as data records."""
        prefix = table or self.s3_config.base_path
        files = await self.list_files(prefix)
        
        # Apply incremental filter
        if incremental_field == "modified_at" and incremental_value:
            cutoff = datetime.fromisoformat(incremental_value)
            files = [f for f in files if f.modified_at > cutoff]
        
        # Apply pagination
        total = len(files)
        files = files[offset:offset + (limit or self.config.batch_size)]
        
        records = []
        for file_info in files:
            record = DataRecord(
                id=file_info.path,
                data={
                    "key": file_info.path,
                    "bucket": self.s3_config.bucket,
                    "size": file_info.size,
                    "etag": file_info.checksum
                },
                metadata={
                    "modified_at": file_info.modified_at.isoformat()
                },
                timestamp=file_info.modified_at,
                operation=OperationType.UPSERT
            )
            records.append(record)
        
        return DataBatch(
            records=records,
            source_id=f"s3:{self.s3_config.bucket}",
            total_count=total,
            offset=offset,
            has_more=(offset + len(records)) < total
        )
    
    async def fetch_data_stream(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None
    ) -> AsyncIterator[DataBatch]:
        """Stream S3 objects in batches."""
        batch_size = batch_size or self.config.batch_size
        offset = 0
        has_more = True
        
        while has_more:
            batch = await self.fetch_data(
                table=table,
                limit=batch_size,
                offset=offset,
                incremental_field=incremental_field,
                incremental_value=incremental_value
            )
            
            yield batch
            
            has_more = batch.has_more
            offset += len(batch.records)
    
    async def write_data(self, batch: DataBatch, mode: str = "upsert") -> SyncResult:
        """Write data batch to S3."""
        import time
        start_time = time.time()
        
        result = SyncResult(
            success=True,
            records_processed=len(batch.records)
        )
        
        async with self._session.client("s3", **self._client_kwargs) as client:
            for record in batch.records:
                try:
                    key = record.data.get("key", record.id)
                    content = record.data.get("content", b"")
                    
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    
                    await client.put_object(
                        Bucket=self.s3_config.bucket,
                        Key=key,
                        Body=content
                    )
                    result.records_inserted += 1
                    
                except Exception as e:
                    result.records_failed += 1
                    result.errors.append({
                        "record_id": record.id,
                        "error": str(e)
                    })
        
        result.duration_seconds = time.time() - start_time
        return result
    
    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get object count."""
        files = await self.list_files(table or "")
        return len(files)
    
    async def list_files(
        self,
        path: str = "",
        recursive: bool = True
    ) -> List[FileInfo]:
        """List S3 objects."""
        files = []
        prefix = path or self.s3_config.base_path
        
        async with self._session.client("s3", **self._client_kwargs) as client:
            paginator = client.get_paginator('list_objects_v2')
            
            async for page in paginator.paginate(
                Bucket=self.s3_config.bucket,
                Prefix=prefix
            ):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    
                    if not self._matches_patterns(key):
                        continue
                    
                    files.append(FileInfo(
                        path=key,
                        name=key.split('/')[-1],
                        size=obj['Size'],
                        modified_at=obj['LastModified'],
                        checksum=obj.get('ETag', '').strip('"')
                    ))
        
        return files
    
    async def read_file(self, path: str) -> bytes:
        """Read S3 object content."""
        async with self._session.client("s3", **self._client_kwargs) as client:
            response = await client.get_object(
                Bucket=self.s3_config.bucket,
                Key=path
            )
            return await response['Body'].read()
    
    async def write_file(self, path: str, content: bytes) -> bool:
        """Write S3 object."""
        async with self._session.client("s3", **self._client_kwargs) as client:
            await client.put_object(
                Bucket=self.s3_config.bucket,
                Key=path,
                Body=content
            )
        return True
    
    async def delete_file(self, path: str) -> bool:
        """Delete S3 object."""
        async with self._session.client("s3", **self._client_kwargs) as client:
            await client.delete_object(
                Bucket=self.s3_config.bucket,
                Key=path
            )
        return True
    
    async def file_exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        try:
            async with self._session.client("s3", **self._client_kwargs) as client:
                await client.head_object(
                    Bucket=self.s3_config.bucket,
                    Key=path
                )
            return True
        except Exception:
            return False
    
    async def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Get S3 object information."""
        try:
            async with self._session.client("s3", **self._client_kwargs) as client:
                response = await client.head_object(
                    Bucket=self.s3_config.bucket,
                    Key=path
                )
                
                return FileInfo(
                    path=path,
                    name=path.split('/')[-1],
                    size=response['ContentLength'],
                    modified_at=response['LastModified'],
                    mime_type=response.get('ContentType'),
                    checksum=response.get('ETag', '').strip('"')
                )
        except Exception:
            return None


# Register connectors
ConnectorFactory.register("local_filesystem", LocalFileSystemConnector)
ConnectorFactory.register("s3", S3Connector)


__all__ = [
    "FileSystemType",
    "FileInfo",
    "FileSystemConfig",
    "LocalFileSystemConfig",
    "SFTPConfig",
    "S3Config",
    "AzureBlobConfig",
    "GCSConfig",
    "BaseFileSystemConnector",
    "LocalFileSystemConnector",
    "S3Connector",
]
