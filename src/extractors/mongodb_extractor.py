"""
MongoDB Data Extractor for SuperInsight Platform.

Provides secure extraction from MongoDB databases with support for:
- Collection discovery and schema inference
- Aggregation pipeline support
- Change streams for real-time data
- GridFS file extraction
"""

import logging
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime
from dataclasses import dataclass

from src.extractors.base import BaseExtractor, ExtractionResult
from src.models.document import Document

logger = logging.getLogger(__name__)


@dataclass
class MongoDBConfig:
    """MongoDB connection configuration."""
    host: str = "localhost"
    port: int = 27017
    database: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    auth_source: str = "admin"
    replica_set: Optional[str] = None
    
    # Connection settings
    connection_timeout: int = 30
    read_timeout: int = 60
    max_pool_size: int = 10
    
    # SSL settings
    use_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None
    
    def get_connection_uri(self) -> str:
        """Generate MongoDB connection URI."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        
        uri = f"mongodb://{auth}{self.host}:{self.port}/{self.database}"
        
        params = []
        if self.auth_source:
            params.append(f"authSource={self.auth_source}")
        if self.replica_set:
            params.append(f"replicaSet={self.replica_set}")
        if self.use_ssl:
            params.append("ssl=true")
        
        if params:
            uri += "?" + "&".join(params)
        
        return uri


class MongoDBExtractor(BaseExtractor):
    """
    MongoDB extractor with comprehensive extraction capabilities.
    
    Features:
    - Collection discovery and schema inference
    - Flexible query support with aggregation pipelines
    - Change stream support for real-time data
    - GridFS file extraction
    - Batch processing with cursor management
    """
    
    def __init__(self, config: MongoDBConfig):
        self.mongo_config = config
        self._client = None
        self._db = None
        
    async def connect(self) -> bool:
        """Connect to MongoDB."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            self._client = AsyncIOMotorClient(
                self.mongo_config.get_connection_uri(),
                serverSelectionTimeoutMS=self.mongo_config.connection_timeout * 1000,
                maxPoolSize=self.mongo_config.max_pool_size
            )
            
            self._db = self._client[self.mongo_config.database]
            
            # Test connection
            await self._client.admin.command('ping')
            
            logger.info(f"Connected to MongoDB: {self.mongo_config.host}:{self.mongo_config.port}")
            return True
            
        except ImportError:
            logger.error("motor is required for MongoDB. Install with: pip install motor")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
        logger.info("Disconnected from MongoDB")
    
    def test_connection(self) -> bool:
        """Test MongoDB connection synchronously."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.connect())
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def extract_data(self, query: Optional[str] = None, **kwargs) -> ExtractionResult:
        """Extract data synchronously."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.extract_data_async(query, **kwargs))
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return ExtractionResult(success=False, error=str(e))
    
    async def extract_data_async(
        self,
        query: Optional[str] = None,
        collection: Optional[str] = None,
        filter_query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: int = 0,
        sort: Optional[List[tuple]] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract data from MongoDB asynchronously.
        
        Args:
            query: JSON query string (alternative to filter_query)
            collection: Collection name
            filter_query: MongoDB filter query
            projection: Fields to include/exclude
            limit: Maximum documents
            skip: Documents to skip
            sort: Sort specification
            
        Returns:
            ExtractionResult with extracted documents
        """
        try:
            if not self._db:
                await self.connect()
            
            if not collection:
                return ExtractionResult(
                    success=False,
                    error="Collection name is required"
                )
            
            coll = self._db[collection]
            
            # Parse query string if provided
            if query:
                import json
                filter_query = json.loads(query)
            
            filter_query = filter_query or {}
            
            # Build cursor
            cursor = coll.find(filter_query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            # Extract documents
            documents = []
            async for doc in cursor:
                # Convert ObjectId to string
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                
                document = Document(
                    source_type="mongodb",
                    source_config={
                        "host": self.mongo_config.host,
                        "database": self.mongo_config.database,
                        "collection": collection
                    },
                    content=str(doc),
                    metadata={
                        "collection": collection,
                        "document_data": doc,
                        "extraction_time": datetime.now().isoformat()
                    }
                )
                documents.append(document)
            
            logger.info(f"Extracted {len(documents)} documents from {collection}")
            return ExtractionResult(success=True, documents=documents)
            
        except Exception as e:
            logger.error(f"MongoDB extraction failed: {e}")
            return ExtractionResult(success=False, error=str(e))
    
    async def extract_with_aggregation(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]],
        **kwargs
    ) -> ExtractionResult:
        """
        Extract data using aggregation pipeline.
        
        Args:
            collection: Collection name
            pipeline: Aggregation pipeline stages
            
        Returns:
            ExtractionResult with aggregated documents
        """
        try:
            if not self._db:
                await self.connect()
            
            coll = self._db[collection]
            cursor = coll.aggregate(pipeline)
            
            documents = []
            async for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                
                document = Document(
                    source_type="mongodb",
                    source_config={
                        "host": self.mongo_config.host,
                        "database": self.mongo_config.database,
                        "collection": collection,
                        "aggregation": True
                    },
                    content=str(doc),
                    metadata={
                        "collection": collection,
                        "document_data": doc,
                        "pipeline_stages": len(pipeline),
                        "extraction_time": datetime.now().isoformat()
                    }
                )
                documents.append(document)
            
            logger.info(f"Extracted {len(documents)} documents via aggregation from {collection}")
            return ExtractionResult(success=True, documents=documents)
            
        except Exception as e:
            logger.error(f"Aggregation extraction failed: {e}")
            return ExtractionResult(success=False, error=str(e))
    
    async def list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            if not self._db:
                await self.connect()
            
            collections = await self._db.list_collection_names()
            logger.info(f"Found {len(collections)} collections")
            return collections
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get statistics for a collection."""
        try:
            if not self._db:
                await self.connect()
            
            stats = await self._db.command("collStats", collection)
            
            return {
                "collection": collection,
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "avg_obj_size": stats.get("avgObjSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("nindexes", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    async def infer_schema(self, collection: str, sample_size: int = 100) -> Dict[str, Any]:
        """
        Infer schema from collection documents.
        
        Args:
            collection: Collection name
            sample_size: Number of documents to sample
            
        Returns:
            Inferred schema information
        """
        try:
            if not self._db:
                await self.connect()
            
            coll = self._db[collection]
            
            # Sample documents
            cursor = coll.aggregate([
                {"$sample": {"size": sample_size}}
            ])
            
            field_info = {}
            
            async for doc in cursor:
                self._analyze_document(doc, field_info, "")
            
            # Convert to schema format
            schema = {
                "collection": collection,
                "sample_size": sample_size,
                "fields": []
            }
            
            for path, info in field_info.items():
                schema["fields"].append({
                    "path": path,
                    "types": list(info["types"]),
                    "nullable": info["nullable"],
                    "count": info["count"]
                })
            
            return schema
            
        except Exception as e:
            logger.error(f"Schema inference failed: {e}")
            return {}
    
    def _analyze_document(
        self,
        doc: Dict[str, Any],
        field_info: Dict[str, Any],
        prefix: str
    ) -> None:
        """Recursively analyze document structure."""
        for key, value in doc.items():
            path = f"{prefix}.{key}" if prefix else key
            
            if path not in field_info:
                field_info[path] = {
                    "types": set(),
                    "nullable": False,
                    "count": 0
                }
            
            field_info[path]["count"] += 1
            
            if value is None:
                field_info[path]["nullable"] = True
            else:
                type_name = type(value).__name__
                field_info[path]["types"].add(type_name)
                
                # Recurse into nested documents
                if isinstance(value, dict):
                    self._analyze_document(value, field_info, path)
    
    async def watch_changes(
        self,
        collection: str,
        pipeline: Optional[List[Dict[str, Any]]] = None,
        full_document: str = "updateLookup"
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Watch for changes using change streams.
        
        Args:
            collection: Collection to watch
            pipeline: Optional aggregation pipeline for filtering
            full_document: Full document option
            
        Yields:
            Change events
        """
        try:
            if not self._db:
                await self.connect()
            
            coll = self._db[collection]
            
            async with coll.watch(
                pipeline=pipeline,
                full_document=full_document
            ) as stream:
                async for change in stream:
                    # Convert ObjectIds
                    if 'documentKey' in change and '_id' in change['documentKey']:
                        change['documentKey']['_id'] = str(change['documentKey']['_id'])
                    if 'fullDocument' in change and '_id' in change['fullDocument']:
                        change['fullDocument']['_id'] = str(change['fullDocument']['_id'])
                    
                    yield change
                    
        except Exception as e:
            logger.error(f"Change stream error: {e}")
            raise


__all__ = [
    "MongoDBExtractor",
    "MongoDBConfig",
]
