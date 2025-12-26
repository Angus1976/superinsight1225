"""
Graph Database Connection Manager for Knowledge Graph.

Provides Neo4j connection management, CRUD operations, and query execution.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from uuid import UUID

from .models import (
    Entity,
    Relation,
    EntityType,
    RelationType,
    GraphStatistics,
    GraphQueryResult,
)

logger = logging.getLogger(__name__)

# Neo4j driver - will be imported when available
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
    from neo4j.exceptions import Neo4jError, ServiceUnavailable
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncDriver = None
    AsyncSession = None
    logger.warning("Neo4j driver not installed. Install with: pip install neo4j")


class GraphDatabase:
    """
    Neo4j Graph Database connection manager.

    Provides async connection pooling, CRUD operations for entities and relations,
    and graph query execution.
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        connection_timeout: int = 30,
        max_transaction_retry_time: int = 30,
        encrypted: bool = False,
    ):
        """
        Initialize GraphDatabase.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            database: Database name
            max_connection_pool_size: Maximum connection pool size
            connection_timeout: Connection timeout in seconds
            max_transaction_retry_time: Max transaction retry time in seconds
            encrypted: Whether to use encryption
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.max_connection_pool_size = max_connection_pool_size
        self.connection_timeout = connection_timeout
        self.max_transaction_retry_time = max_transaction_retry_time
        self.encrypted = encrypted

        self._driver: Optional[AsyncDriver] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database connection."""
        if not NEO4J_AVAILABLE:
            logger.error("Neo4j driver not available")
            return

        if self._initialized:
            return

        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=self.max_connection_pool_size,
                connection_timeout=self.connection_timeout,
                max_transaction_retry_time=self.max_transaction_retry_time,
                encrypted=self.encrypted,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            self._initialized = True
            logger.info(f"Connected to Neo4j at {self.uri}")

            # Create indexes
            await self._create_indexes()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self) -> None:
        """Close the database connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._initialized = False
            logger.info("Closed Neo4j connection")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if not self._driver:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._driver.session(database=self.database)
        try:
            yield session
        finally:
            await session.close()

    async def _create_indexes(self) -> None:
        """Create indexes for better query performance."""
        async with self.session() as session:
            # Entity indexes
            await session.run(
                "CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id)"
            )
            await session.run(
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)"
            )
            await session.run(
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)"
            )
            await session.run(
                "CREATE INDEX entity_tenant IF NOT EXISTS FOR (e:Entity) ON (e.tenant_id)"
            )

            # Full-text search index
            try:
                await session.run(
                    """
                    CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
                    FOR (e:Entity)
                    ON EACH [e.name, e.description]
                    """
                )
            except Exception as e:
                logger.warning(f"Could not create fulltext index: {e}")

            logger.info("Created Neo4j indexes")

    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        if not self._driver:
            return {"status": "disconnected", "error": "Driver not initialized"}

        try:
            async with self.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                if record and record["health"] == 1:
                    return {"status": "healthy", "uri": self.uri}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

        return {"status": "unknown"}

    # ==================== Entity Operations ====================

    async def create_entity(self, entity: Entity) -> Entity:
        """
        Create an entity in the graph.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        query = """
        CREATE (e:Entity $props)
        RETURN e
        """

        async with self.session() as session:
            props = entity.to_neo4j_properties()
            result = await session.run(query, props=props)
            record = await result.single()

            if record:
                logger.info(f"Created entity: {entity.id} ({entity.name})")
                return entity

        raise RuntimeError(f"Failed to create entity: {entity.id}")

    async def get_entity(self, entity_id: UUID, tenant_id: Optional[str] = None) -> Optional[Entity]:
        """
        Get an entity by ID.

        Args:
            entity_id: Entity ID
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Entity if found, None otherwise
        """
        query = """
        MATCH (e:Entity {id: $id})
        WHERE e.is_active = true
        """
        if tenant_id:
            query += " AND e.tenant_id = $tenant_id"
        query += " RETURN e"

        params = {"id": str(entity_id)}
        if tenant_id:
            params["tenant_id"] = tenant_id

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if record:
                return self._record_to_entity(record["e"])

        return None

    async def update_entity(self, entity_id: UUID, updates: Dict[str, Any]) -> Optional[Entity]:
        """
        Update an entity.

        Args:
            entity_id: Entity ID
            updates: Fields to update

        Returns:
            Updated entity if found, None otherwise
        """
        # Build SET clause
        set_clauses = []
        params = {"id": str(entity_id)}

        for key, value in updates.items():
            if key not in ('id', 'created_at', 'created_by'):
                param_name = f"param_{key}"
                set_clauses.append(f"e.{key} = ${param_name}")
                params[param_name] = value

        set_clauses.append("e.updated_at = $updated_at")
        set_clauses.append("e.version = e.version + 1")
        params["updated_at"] = datetime.now().isoformat()

        query = f"""
        MATCH (e:Entity {{id: $id}})
        SET {', '.join(set_clauses)}
        RETURN e
        """

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if record:
                logger.info(f"Updated entity: {entity_id}")
                return self._record_to_entity(record["e"])

        return None

    async def delete_entity(self, entity_id: UUID, hard_delete: bool = False) -> bool:
        """
        Delete an entity.

        Args:
            entity_id: Entity ID
            hard_delete: If True, permanently delete; otherwise soft delete

        Returns:
            True if deleted, False otherwise
        """
        if hard_delete:
            query = """
            MATCH (e:Entity {id: $id})
            DETACH DELETE e
            RETURN count(e) as deleted
            """
        else:
            query = """
            MATCH (e:Entity {id: $id})
            SET e.is_active = false, e.updated_at = $updated_at
            RETURN count(e) as deleted
            """

        params = {"id": str(entity_id), "updated_at": datetime.now().isoformat()}

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if record and record["deleted"] > 0:
                logger.info(f"Deleted entity: {entity_id} (hard={hard_delete})")
                return True

        return False

    async def search_entities(
        self,
        query_text: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Entity]:
        """
        Search entities.

        Args:
            query_text: Text to search in name/description
            entity_type: Filter by entity type
            tenant_id: Filter by tenant
            limit: Maximum results
            offset: Results offset

        Returns:
            List of matching entities
        """
        conditions = ["e.is_active = true"]
        params = {"limit": limit, "offset": offset}

        if query_text:
            conditions.append("(e.name CONTAINS $query OR e.description CONTAINS $query)")
            params["query"] = query_text

        if entity_type:
            conditions.append("e.entity_type = $entity_type")
            params["entity_type"] = entity_type.value

        if tenant_id:
            conditions.append("e.tenant_id = $tenant_id")
            params["tenant_id"] = tenant_id

        where_clause = " AND ".join(conditions)
        query = f"""
        MATCH (e:Entity)
        WHERE {where_clause}
        RETURN e
        ORDER BY e.updated_at DESC
        SKIP $offset
        LIMIT $limit
        """

        entities = []
        async with self.session() as session:
            result = await session.run(query, **params)
            async for record in result:
                entity = self._record_to_entity(record["e"])
                if entity:
                    entities.append(entity)

        return entities

    # ==================== Relation Operations ====================

    async def create_relation(self, relation: Relation) -> Relation:
        """
        Create a relation between entities.

        Args:
            relation: Relation to create

        Returns:
            Created relation
        """
        query = """
        MATCH (source:Entity {id: $source_id})
        MATCH (target:Entity {id: $target_id})
        CREATE (source)-[r:RELATES_TO $props]->(target)
        RETURN r
        """

        props = relation.to_neo4j_properties()
        params = {
            "source_id": str(relation.source_id),
            "target_id": str(relation.target_id),
            "props": props,
        }

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if record:
                logger.info(f"Created relation: {relation.id} ({relation.relation_type.value})")
                return relation

        raise RuntimeError(f"Failed to create relation: {relation.id}")

    async def get_relation(self, relation_id: UUID) -> Optional[Relation]:
        """Get a relation by ID."""
        query = """
        MATCH ()-[r:RELATES_TO {id: $id}]->()
        WHERE r.is_active = true
        RETURN r, startNode(r) as source, endNode(r) as target
        """

        async with self.session() as session:
            result = await session.run(query, id=str(relation_id))
            record = await result.single()

            if record:
                return self._record_to_relation(record["r"], record["source"], record["target"])

        return None

    async def get_entity_relations(
        self,
        entity_id: UUID,
        direction: str = "both",
        relation_types: Optional[List[RelationType]] = None,
        limit: int = 100,
    ) -> List[Relation]:
        """
        Get relations for an entity.

        Args:
            entity_id: Entity ID
            direction: "outgoing", "incoming", or "both"
            relation_types: Filter by relation types
            limit: Maximum results

        Returns:
            List of relations
        """
        conditions = ["r.is_active = true"]
        params = {"entity_id": str(entity_id), "limit": limit}

        if relation_types:
            conditions.append("r.relation_type IN $relation_types")
            params["relation_types"] = [rt.value for rt in relation_types]

        where_clause = " AND ".join(conditions)

        if direction == "outgoing":
            query = f"""
            MATCH (e:Entity {{id: $entity_id}})-[r:RELATES_TO]->(target:Entity)
            WHERE {where_clause}
            RETURN r, e as source, target
            LIMIT $limit
            """
        elif direction == "incoming":
            query = f"""
            MATCH (source:Entity)-[r:RELATES_TO]->(e:Entity {{id: $entity_id}})
            WHERE {where_clause}
            RETURN r, source, e as target
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (e:Entity {{id: $entity_id}})-[r:RELATES_TO]-(other:Entity)
            WHERE {where_clause}
            RETURN r, startNode(r) as source, endNode(r) as target
            LIMIT $limit
            """

        relations = []
        async with self.session() as session:
            result = await session.run(query, **params)
            async for record in result:
                relation = self._record_to_relation(record["r"], record["source"], record["target"])
                if relation:
                    relations.append(relation)

        return relations

    async def delete_relation(self, relation_id: UUID, hard_delete: bool = False) -> bool:
        """Delete a relation."""
        if hard_delete:
            query = """
            MATCH ()-[r:RELATES_TO {id: $id}]->()
            DELETE r
            RETURN count(r) as deleted
            """
        else:
            query = """
            MATCH ()-[r:RELATES_TO {id: $id}]->()
            SET r.is_active = false, r.updated_at = $updated_at
            RETURN count(r) as deleted
            """

        params = {"id": str(relation_id), "updated_at": datetime.now().isoformat()}

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if record and record["deleted"] > 0:
                logger.info(f"Deleted relation: {relation_id}")
                return True

        return False

    # ==================== Graph Queries ====================

    async def get_neighbors(
        self,
        entity_id: UUID,
        depth: int = 1,
        limit: int = 100,
    ) -> GraphQueryResult:
        """
        Get neighboring entities up to a certain depth.

        Args:
            entity_id: Starting entity ID
            depth: Maximum traversal depth
            limit: Maximum results

        Returns:
            Query result with entities and relations
        """
        query = """
        MATCH path = (start:Entity {id: $entity_id})-[r:RELATES_TO*1..$depth]-(neighbor:Entity)
        WHERE start.is_active = true AND neighbor.is_active = true
        WITH start, neighbor, r, path
        LIMIT $limit
        RETURN DISTINCT neighbor, collect(r) as relations
        """

        params = {"entity_id": str(entity_id), "depth": depth, "limit": limit}

        entities = []
        relations = []
        start_time = datetime.now()

        async with self.session() as session:
            result = await session.run(query, **params)
            async for record in result:
                entity = self._record_to_entity(record["neighbor"])
                if entity:
                    entities.append(entity)

                for rel_data in record["relations"]:
                    # Relations in path are returned as list
                    pass  # TODO: Parse path relations

        query_time = (datetime.now() - start_time).total_seconds() * 1000

        return GraphQueryResult(
            entities=entities,
            relations=relations,
            total_count=len(entities),
            query=f"neighbors of {entity_id} depth={depth}",
            query_time_ms=query_time,
        )

    async def find_path(
        self,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 5,
    ) -> GraphQueryResult:
        """
        Find shortest path between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum path length

        Returns:
            Query result with path
        """
        query = """
        MATCH path = shortestPath(
            (source:Entity {id: $source_id})-[r:RELATES_TO*1..$max_depth]-(target:Entity {id: $target_id})
        )
        WHERE source.is_active = true AND target.is_active = true
        RETURN path
        """

        params = {
            "source_id": str(source_id),
            "target_id": str(target_id),
            "max_depth": max_depth,
        }

        paths = []
        start_time = datetime.now()

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if record:
                path = record["path"]
                path_data = []
                for node in path.nodes:
                    path_data.append({"type": "node", "id": node.get("id"), "name": node.get("name")})
                for rel in path.relationships:
                    path_data.append({"type": "relation", "id": rel.get("id"), "relation_type": rel.get("relation_type")})
                paths.append(path_data)

        query_time = (datetime.now() - start_time).total_seconds() * 1000

        return GraphQueryResult(
            paths=paths,
            total_count=len(paths),
            query=f"path from {source_id} to {target_id}",
            query_time_ms=query_time,
        )

    async def execute_cypher(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if params is None:
            params = {}

        results = []
        async with self.session() as session:
            result = await session.run(cypher, **params)
            async for record in result:
                results.append(dict(record))

        return results

    # ==================== Statistics ====================

    async def get_statistics(self, tenant_id: Optional[str] = None) -> GraphStatistics:
        """Get graph statistics."""
        conditions = ["e.is_active = true"]
        if tenant_id:
            conditions.append("e.tenant_id = $tenant_id")

        where_clause = " AND ".join(conditions)
        params = {}
        if tenant_id:
            params["tenant_id"] = tenant_id

        # Count entities
        entity_query = f"""
        MATCH (e:Entity) WHERE {where_clause}
        RETURN e.entity_type as type, count(e) as count
        """

        # Count relations
        relation_query = f"""
        MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
        WHERE e1.is_active = true AND e2.is_active = true AND r.is_active = true
        RETURN r.relation_type as type, count(r) as count
        """

        entities_by_type = {}
        relations_by_type = {}
        total_entities = 0
        total_relations = 0

        async with self.session() as session:
            # Entity stats
            result = await session.run(entity_query, **params)
            async for record in result:
                entity_type = record["type"]
                count = record["count"]
                entities_by_type[entity_type] = count
                total_entities += count

            # Relation stats
            result = await session.run(relation_query, **params)
            async for record in result:
                relation_type = record["type"]
                count = record["count"]
                relations_by_type[relation_type] = count
                total_relations += count

        # Calculate density
        density = 0.0
        if total_entities > 1:
            max_edges = total_entities * (total_entities - 1)
            density = total_relations / max_edges if max_edges > 0 else 0.0

        # Calculate average degree
        avg_degree = (2 * total_relations) / total_entities if total_entities > 0 else 0.0

        return GraphStatistics(
            total_entities=total_entities,
            total_relations=total_relations,
            entities_by_type=entities_by_type,
            relations_by_type=relations_by_type,
            avg_degree=avg_degree,
            density=density,
        )

    # ==================== Helper Methods ====================

    def _record_to_entity(self, node_data: Dict[str, Any]) -> Optional[Entity]:
        """Convert Neo4j node to Entity."""
        if not node_data:
            return None

        try:
            # Extract properties
            props = {}
            for key, value in node_data.items():
                if key.startswith("prop_"):
                    props[key[5:]] = value

            # Parse aliases
            aliases = node_data.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]

            return Entity(
                id=UUID(node_data["id"]),
                entity_type=EntityType(node_data["entity_type"]),
                name=node_data["name"],
                properties=props,
                aliases=aliases,
                description=node_data.get("description"),
                source=node_data.get("source"),
                source_id=node_data.get("source_id"),
                confidence=node_data.get("confidence", 1.0),
                verified=node_data.get("verified", False),
                tenant_id=node_data.get("tenant_id"),
                created_at=datetime.fromisoformat(node_data["created_at"]) if node_data.get("created_at") else datetime.now(),
                updated_at=datetime.fromisoformat(node_data["updated_at"]) if node_data.get("updated_at") else datetime.now(),
                version=node_data.get("version", 1),
                is_active=node_data.get("is_active", True),
            )
        except Exception as e:
            logger.error(f"Failed to parse entity: {e}")
            return None

    def _record_to_relation(self, rel_data: Dict[str, Any], source_data: Dict[str, Any], target_data: Dict[str, Any]) -> Optional[Relation]:
        """Convert Neo4j relationship to Relation."""
        if not rel_data:
            return None

        try:
            props = {}
            for key, value in rel_data.items():
                if key.startswith("prop_"):
                    props[key[5:]] = value

            return Relation(
                id=UUID(rel_data["id"]),
                source_id=UUID(source_data["id"]),
                target_id=UUID(target_data["id"]),
                relation_type=RelationType(rel_data["relation_type"]),
                properties=props,
                weight=rel_data.get("weight", 1.0),
                confidence=rel_data.get("confidence", 1.0),
                verified=rel_data.get("verified", False),
                evidence=rel_data.get("evidence"),
                source=rel_data.get("source"),
                tenant_id=rel_data.get("tenant_id"),
                created_at=datetime.fromisoformat(rel_data["created_at"]) if rel_data.get("created_at") else datetime.now(),
                updated_at=datetime.fromisoformat(rel_data["updated_at"]) if rel_data.get("updated_at") else datetime.now(),
                version=rel_data.get("version", 1),
                is_active=rel_data.get("is_active", True),
            )
        except Exception as e:
            logger.error(f"Failed to parse relation: {e}")
            return None


# Global instance
_graph_database: Optional[GraphDatabase] = None


def get_graph_database() -> GraphDatabase:
    """Get or create global GraphDatabase instance."""
    global _graph_database

    if _graph_database is None:
        from src.config.settings import settings

        _graph_database = GraphDatabase(
            uri=settings.neo4j.neo4j_uri,
            user=settings.neo4j.neo4j_user,
            password=settings.neo4j.neo4j_password,
            database=settings.neo4j.neo4j_database,
            max_connection_pool_size=settings.neo4j.neo4j_max_connection_pool_size,
            connection_timeout=settings.neo4j.neo4j_connection_timeout,
            max_transaction_retry_time=settings.neo4j.neo4j_max_transaction_retry_time,
            encrypted=settings.neo4j.neo4j_encrypted,
        )

    return _graph_database


async def init_graph_database() -> GraphDatabase:
    """Initialize and return the graph database."""
    db = get_graph_database()
    await db.initialize()
    return db
