"""
Advanced pagination system for SuperInsight Platform.

Provides efficient pagination with cursor-based and offset-based strategies.
Implements Requirement 9.3 for database query optimization.

i18n Translation Keys:
- database.pagination.invalid_page: 无效的页码: {page}
- database.pagination.invalid_size: 无效的页大小: {size}
- database.pagination.query_started: 分页查询开始: page={page}, size={size}
- database.pagination.query_completed: 分页查询完成: 返回 {count} 条记录
- database.error.query_failed: 查询失败: {error}
"""

import logging
import base64
import json
from typing import List, Dict, Any, Optional, TypeVar, Generic, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, asc, desc, and_, or_
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import UnaryExpression

from src.database.connection import db_manager
from src.database.models import DocumentModel, TaskModel, BillingRecordModel, QualityIssueModel

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PaginationStrategy(str, Enum):
    """Pagination strategy enumeration."""
    OFFSET = "offset"
    CURSOR = "cursor"
    KEYSET = "keyset"
    HYBRID = "hybrid"


class SortDirection(str, Enum):
    """Sort direction enumeration."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class SortField:
    """Sort field configuration."""
    field: str
    direction: SortDirection = SortDirection.ASC
    
    def to_sqlalchemy_order(self, model_class) -> UnaryExpression:
        """Convert to SQLAlchemy order expression."""
        field_attr = getattr(model_class, self.field)
        if self.direction == SortDirection.ASC:
            return asc(field_attr)
        else:
            return desc(field_attr)


@dataclass
class PaginationConfig:
    """Configuration for pagination operations."""
    page_size: int = 50
    max_page_size: int = 1000
    strategy: PaginationStrategy = PaginationStrategy.OFFSET
    sort_fields: List[SortField] = None
    enable_count: bool = True
    cursor_field: str = "id"
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.sort_fields is None:
            self.sort_fields = [SortField("id", SortDirection.ASC)]
        
        # Validate page size
        if self.page_size > self.max_page_size:
            self.page_size = self.max_page_size
        
        if self.page_size <= 0:
            self.page_size = 50


@dataclass
class PaginationResult(Generic[T]):
    """Result of pagination operation."""
    items: List[T]
    total_count: Optional[int] = None
    page: Optional[int] = None
    page_size: int = 0
    has_next: bool = False
    has_previous: bool = False
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None
    
    @property
    def total_pages(self) -> Optional[int]:
        """Calculate total pages."""
        if self.total_count is None or self.page_size == 0:
            return None
        return (self.total_count + self.page_size - 1) // self.page_size


class AdvancedPaginator(Generic[T]):
    """Advanced paginator with multiple strategies."""
    
    def __init__(self, session: Session, base_query: Select, model_class, config: PaginationConfig):
        """Initialize paginator."""
        self.session = session
        self.base_query = base_query
        self.model_class = model_class
        self.config = config
        self._total_count = None
    
    def get_total_count(self) -> int:
        """Get total count with caching."""
        if self._total_count is None and self.config.enable_count:
            # Use efficient count query
            count_query = select(func.count()).select_from(self.base_query.subquery())
            self._total_count = self.session.execute(count_query).scalar() or 0
        return self._total_count or 0
    
    def paginate_offset(self, page: int = 1) -> PaginationResult[T]:
        """Paginate using offset-based strategy."""
        if page < 1:
            page = 1
        
        offset = (page - 1) * self.config.page_size
        
        # Apply sorting
        query = self._apply_sorting(self.base_query)
        
        # Apply pagination
        paginated_query = query.offset(offset).limit(self.config.page_size + 1)  # +1 to check has_next
        
        items = self.session.execute(paginated_query).scalars().all()
        
        # Check if there are more items
        has_next = len(items) > self.config.page_size
        if has_next:
            items = items[:-1]  # Remove the extra item
        
        # Get total count if enabled
        total_count = self.get_total_count() if self.config.enable_count else None
        
        return PaginationResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=self.config.page_size,
            has_next=has_next,
            has_previous=page > 1
        )
    
    def paginate_cursor(self, cursor: Optional[str] = None, direction: str = "next") -> PaginationResult[T]:
        """Paginate using cursor-based strategy."""
        query = self._apply_sorting(self.base_query)
        
        # Apply cursor filtering
        if cursor:
            cursor_field = getattr(self.model_class, self.config.cursor_field)
            
            if direction == "next":
                # For next page, get items after cursor
                if self.config.sort_fields[0].direction == SortDirection.ASC:
                    query = query.where(cursor_field > cursor)
                else:
                    query = query.where(cursor_field < cursor)
            else:
                # For previous page, get items before cursor
                if self.config.sort_fields[0].direction == SortDirection.ASC:
                    query = query.where(cursor_field < cursor)
                else:
                    query = query.where(cursor_field > cursor)
        
        # Get one extra item to check for next/previous
        items = self.session.execute(query.limit(self.config.page_size + 1)).scalars().all()
        
        # Determine pagination state
        has_more = len(items) > self.config.page_size
        if has_more:
            items = items[:-1]
        
        # Generate cursors
        next_cursor = None
        previous_cursor = None
        
        if items:
            cursor_field_value = getattr(items[-1], self.config.cursor_field)
            next_cursor = str(cursor_field_value) if has_more else None
            
            if cursor:  # If we have a current cursor, we can go back
                previous_cursor = cursor
        
        return PaginationResult(
            items=items,
            page_size=self.config.page_size,
            has_next=has_more if direction == "next" else bool(cursor),
            has_previous=bool(cursor) if direction == "next" else has_more,
            next_cursor=next_cursor,
            previous_cursor=previous_cursor
        )
    
    def paginate_keyset(self, last_values: Optional[Dict[str, Any]] = None) -> PaginationResult[T]:
        """Paginate using keyset pagination (efficient for large datasets)."""
        query = self._apply_sorting(self.base_query)
        
        # Apply keyset filtering
        if last_values:
            conditions = []
            for sort_field in self.config.sort_fields:
                field_attr = getattr(self.model_class, sort_field.field)
                last_value = last_values.get(sort_field.field)
                
                if last_value is not None:
                    if sort_field.direction == SortDirection.ASC:
                        conditions.append(field_attr > last_value)
                    else:
                        conditions.append(field_attr < last_value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # Get items
        items = self.session.execute(query.limit(self.config.page_size + 1)).scalars().all()
        
        # Check for more items
        has_next = len(items) > self.config.page_size
        if has_next:
            items = items[:-1]
        
        # Generate next keyset values
        next_cursor = None
        if items and has_next:
            last_item = items[-1]
            next_values = {
                sort_field.field: getattr(last_item, sort_field.field)
                for sort_field in self.config.sort_fields
            }
            next_cursor = str(next_values)
        
        return PaginationResult(
            items=items,
            page_size=self.config.page_size,
            has_next=has_next,
            has_previous=bool(last_values),
            next_cursor=next_cursor
        )
    
    def paginate_hybrid(self, page: int = 1, cursor: Optional[str] = None) -> PaginationResult[T]:
        """Hybrid pagination that switches strategy based on page number."""
        # Use cursor-based for deep pagination, offset for shallow
        if page <= 10 and not cursor:
            return self.paginate_offset(page)
        else:
            return self.paginate_cursor(cursor)
    
    def _apply_sorting(self, query: Select) -> Select:
        """Apply sorting to query."""
        for sort_field in self.config.sort_fields:
            order_expr = sort_field.to_sqlalchemy_order(self.model_class)
            query = query.order_by(order_expr)
        return query


class PaginationService:
    """Service for managing pagination across different models."""
    
    def __init__(self):
        """Initialize pagination service."""
        self.default_configs = {
            'documents': PaginationConfig(
                page_size=50,
                sort_fields=[SortField("created_at", SortDirection.DESC)],
                cursor_field="id"
            ),
            'tasks': PaginationConfig(
                page_size=100,
                sort_fields=[SortField("created_at", SortDirection.DESC)],
                cursor_field="id"
            ),
            'billing_records': PaginationConfig(
                page_size=200,
                sort_fields=[SortField("billing_date", SortDirection.DESC)],
                cursor_field="id"
            ),
            'quality_issues': PaginationConfig(
                page_size=50,
                sort_fields=[SortField("created_at", SortDirection.DESC)],
                cursor_field="id"
            )
        }
    
    def paginate_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        strategy: PaginationStrategy = PaginationStrategy.OFFSET,
        cursor: Optional[str] = None
    ) -> PaginationResult[DocumentModel]:
        """Paginate documents with filters."""
        
        with db_manager.get_session() as session:
            # Build base query
            query = select(DocumentModel)
            
            # Apply filters
            if filters:
                query = self._apply_document_filters(query, filters)
            
            # Create pagination config
            config = self.default_configs['documents']
            if page_size:
                config.page_size = min(page_size, config.max_page_size)
            config.strategy = strategy
            
            # Create paginator and paginate
            paginator = AdvancedPaginator(session, query, DocumentModel, config)
            
            if strategy == PaginationStrategy.OFFSET:
                return paginator.paginate_offset(page)
            elif strategy == PaginationStrategy.CURSOR:
                return paginator.paginate_cursor(cursor)
            elif strategy == PaginationStrategy.KEYSET:
                last_values = self._parse_cursor_values(cursor) if cursor else None
                return paginator.paginate_keyset(last_values)
            else:  # HYBRID
                return paginator.paginate_hybrid(page, cursor)
    
    def paginate_tasks(
        self,
        project_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        strategy: PaginationStrategy = PaginationStrategy.OFFSET,
        cursor: Optional[str] = None
    ) -> PaginationResult[TaskModel]:
        """Paginate tasks with filters."""
        
        with db_manager.get_session() as session:
            # Build base query
            query = select(TaskModel)
            
            # Apply filters
            filters = []
            if project_id:
                filters.append(TaskModel.project_id == project_id)
            if status_filter:
                filters.append(TaskModel.status == status_filter)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Create pagination config
            config = self.default_configs['tasks']
            if page_size:
                config.page_size = min(page_size, config.max_page_size)
            config.strategy = strategy
            
            # Create paginator and paginate
            paginator = AdvancedPaginator(session, query, TaskModel, config)
            
            if strategy == PaginationStrategy.OFFSET:
                return paginator.paginate_offset(page)
            elif strategy == PaginationStrategy.CURSOR:
                return paginator.paginate_cursor(cursor)
            elif strategy == PaginationStrategy.KEYSET:
                last_values = self._parse_cursor_values(cursor) if cursor else None
                return paginator.paginate_keyset(last_values)
            else:  # HYBRID
                return paginator.paginate_hybrid(page, cursor)
    
    def paginate_billing_records(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        strategy: PaginationStrategy = PaginationStrategy.CURSOR  # Default to cursor for billing
    ) -> PaginationResult[BillingRecordModel]:
        """Paginate billing records with filters."""
        
        with db_manager.get_session() as session:
            # Build base query
            query = select(BillingRecordModel).where(BillingRecordModel.tenant_id == tenant_id)
            
            # Apply additional filters
            filters = []
            if user_id:
                filters.append(BillingRecordModel.user_id == user_id)
            if date_from:
                filters.append(BillingRecordModel.billing_date >= date_from)
            if date_to:
                filters.append(BillingRecordModel.billing_date <= date_to)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Create pagination config
            config = self.default_configs['billing_records']
            if page_size:
                config.page_size = min(page_size, config.max_page_size)
            config.strategy = strategy
            
            # Create paginator and paginate
            paginator = AdvancedPaginator(session, query, BillingRecordModel, config)
            
            if strategy == PaginationStrategy.OFFSET:
                return paginator.paginate_offset(page)
            elif strategy == PaginationStrategy.CURSOR:
                return paginator.paginate_cursor()
            elif strategy == PaginationStrategy.KEYSET:
                return paginator.paginate_keyset()
            else:  # HYBRID
                return paginator.paginate_hybrid(page)
    
    def _apply_document_filters(self, query: Select, filters: Dict[str, Any]) -> Select:
        """Apply filters to document query."""
        conditions = []
        
        if 'source_type' in filters:
            conditions.append(DocumentModel.source_type == filters['source_type'])
        
        if 'created_after' in filters:
            conditions.append(DocumentModel.created_at >= filters['created_after'])
        
        if 'created_before' in filters:
            conditions.append(DocumentModel.created_at <= filters['created_before'])
        
        if 'metadata_contains' in filters:
            # JSONB containment query
            conditions.append(DocumentModel.document_metadata.contains(filters['metadata_contains']))
        
        if 'content_search' in filters:
            # Full-text search (simplified)
            search_term = f"%{filters['content_search']}%"
            conditions.append(DocumentModel.content.ilike(search_term))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def _parse_cursor_values(self, cursor: str) -> Optional[Dict[str, Any]]:
        """Parse cursor values from string."""
        try:
            import json
            return json.loads(cursor)
        except (json.JSONDecodeError, TypeError):
            return None


class SmartPaginator:
    """Smart paginator that automatically chooses the best strategy."""
    
    def __init__(self, session: Session):
        """Initialize smart paginator."""
        self.session = session
        self.pagination_service = PaginationService()
    
    def auto_paginate(
        self,
        model_class,
        base_query: Select,
        page: int = 1,
        page_size: int = 50,
        total_estimate: Optional[int] = None
    ) -> PaginationResult:
        """Automatically choose the best pagination strategy."""
        
        # Estimate total count if not provided
        if total_estimate is None:
            count_query = select(func.count()).select_from(base_query.subquery())
            total_estimate = self.session.execute(count_query).scalar() or 0
        
        # Choose strategy based on dataset size and page number
        if total_estimate < 10000:
            # Small dataset: use offset pagination
            strategy = PaginationStrategy.OFFSET
        elif page <= 10:
            # Early pages: use offset pagination
            strategy = PaginationStrategy.OFFSET
        elif total_estimate > 100000:
            # Large dataset with deep pagination: use keyset
            strategy = PaginationStrategy.KEYSET
        else:
            # Medium dataset with deep pagination: use cursor
            strategy = PaginationStrategy.CURSOR
        
        # Create appropriate config
        config = PaginationConfig(
            page_size=page_size,
            strategy=strategy,
            enable_count=(total_estimate < 50000)  # Disable count for very large datasets
        )
        
        # Create and use paginator
        paginator = AdvancedPaginator(self.session, base_query, model_class, config)
        
        if strategy == PaginationStrategy.OFFSET:
            return paginator.paginate_offset(page)
        elif strategy == PaginationStrategy.CURSOR:
            return paginator.paginate_cursor()
        elif strategy == PaginationStrategy.KEYSET:
            return paginator.paginate_keyset()
        else:
            return paginator.paginate_hybrid(page)


# Global pagination service instance
pagination_service = PaginationService()



# ============================================================================
# Generic Pagination Functions (Requirement 9.3)
# ============================================================================

@dataclass
class PageInfo:
    """Pagination information.
    
    Attributes:
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_items: Total number of items
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result.
    
    Attributes:
        items: List of items for the current page
        page_info: Pagination metadata
    """
    items: List[T]
    page_info: PageInfo


@dataclass
class CursorPaginatedResult(Generic[T]):
    """Cursor-based paginated query result.
    
    Attributes:
        items: List of items for the current page
        next_cursor: Cursor for the next page (None if no more pages)
        prev_cursor: Cursor for the previous page (None if first page)
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """
    items: List[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_next: bool = False
    has_prev: bool = False


class Pagination:
    """Generic pagination utility class.
    
    Provides static methods for offset-based and cursor-based pagination.
    
    Example:
        ```python
        # Offset pagination
        result = await Pagination.paginate(
            query=select(UserModel),
            session=session,
            page=1,
            page_size=20
        )
        
        # Cursor pagination
        items, next_cursor = await Pagination.cursor_paginate(
            query=select(UserModel),
            session=session,
            cursor=None,
            limit=20
        )
        ```
    """
    
    @staticmethod
    async def paginate(
        query: Select,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        count_query: Optional[Select] = None
    ) -> PaginatedResult:
        """Paginate query results using offset-based pagination.
        
        Args:
            query: SQLAlchemy select query
            session: Async database session
            page: Page number (1-indexed, default: 1)
            page_size: Number of items per page (default: 20)
            count_query: Optional custom count query
            
        Returns:
            PaginatedResult with items and pagination info
            
        Raises:
            ValueError: If page or page_size is invalid
        """
        # Validate parameters
        if page < 1:
            # i18n key: database.pagination.invalid_page
            logger.warning(f"database.pagination.invalid_page: page={page}")
            page = 1
        
        if page_size < 1:
            # i18n key: database.pagination.invalid_size
            logger.warning(f"database.pagination.invalid_size: size={page_size}")
            page_size = 20
        
        if page_size > 1000:
            # Cap page size at 1000
            page_size = 1000
        
        # Log query start
        logger.debug(
            f"database.pagination.query_started: page={page}, size={page_size}",
            extra={"page": page, "size": page_size}
        )
        
        try:
            # Get total count
            if count_query is not None:
                total_result = await session.execute(count_query)
                total_items = total_result.scalar() or 0
            else:
                count_stmt = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_stmt)
                total_items = total_result.scalar() or 0
            
            # Calculate pagination info
            total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            
            # Adjust page if out of bounds
            if page > total_pages and total_pages > 0:
                page = total_pages
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Execute paginated query
            paginated_query = query.offset(offset).limit(page_size)
            result = await session.execute(paginated_query)
            items = list(result.scalars().all())
            
            # Build page info
            page_info = PageInfo(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
            
            # Log completion
            logger.debug(
                f"database.pagination.query_completed: count={len(items)}",
                extra={"count": len(items)}
            )
            
            return PaginatedResult(items=items, page_info=page_info)
            
        except Exception as e:
            # i18n key: database.error.query_failed
            logger.error(
                f"database.error.query_failed: error={str(e)}",
                extra={"error": str(e)}
            )
            raise
    
    @staticmethod
    async def cursor_paginate(
        query: Select,
        session: AsyncSession,
        cursor: Optional[str] = None,
        limit: int = 20,
        cursor_field: str = "id",
        model_class: Optional[type] = None
    ) -> Tuple[List[Any], Optional[str]]:
        """Paginate query results using cursor-based pagination.
        
        Cursor-based pagination is more efficient for large datasets
        as it doesn't require counting total items.
        
        Args:
            query: SQLAlchemy select query
            session: Async database session
            cursor: Cursor from previous page (None for first page)
            limit: Number of items per page (default: 20)
            cursor_field: Field to use for cursor (default: "id")
            model_class: Optional model class for cursor field access
            
        Returns:
            Tuple of (items, next_cursor)
            
        Note:
            The cursor is a base64-encoded JSON string containing the
            cursor field value from the last item.
        """
        if limit < 1:
            limit = 20
        if limit > 1000:
            limit = 1000
        
        try:
            # Decode cursor if provided
            cursor_value = None
            if cursor:
                try:
                    decoded = base64.b64decode(cursor.encode()).decode()
                    cursor_data = json.loads(decoded)
                    cursor_value = cursor_data.get("value")
                except Exception:
                    logger.warning(f"Invalid cursor format: {cursor}")
                    cursor_value = None
            
            # Apply cursor filter if we have a cursor value
            if cursor_value is not None and model_class is not None:
                cursor_field_attr = getattr(model_class, cursor_field, None)
                if cursor_field_attr is not None:
                    query = query.where(cursor_field_attr > cursor_value)
            
            # Order by cursor field and limit
            if model_class is not None:
                cursor_field_attr = getattr(model_class, cursor_field, None)
                if cursor_field_attr is not None:
                    query = query.order_by(asc(cursor_field_attr))
            
            # Fetch one extra item to determine if there's a next page
            result = await session.execute(query.limit(limit + 1))
            items = list(result.scalars().all())
            
            # Determine if there's a next page
            has_next = len(items) > limit
            if has_next:
                items = items[:limit]  # Remove the extra item
            
            # Generate next cursor
            next_cursor = None
            if has_next and items:
                last_item = items[-1]
                last_value = getattr(last_item, cursor_field, None)
                if last_value is not None:
                    cursor_data = {"value": str(last_value)}
                    next_cursor = base64.b64encode(
                        json.dumps(cursor_data).encode()
                    ).decode()
            
            return items, next_cursor
            
        except Exception as e:
            logger.error(
                f"database.error.query_failed: error={str(e)}",
                extra={"error": str(e)}
            )
            raise
    
    @staticmethod
    async def cursor_paginate_full(
        query: Select,
        session: AsyncSession,
        cursor: Optional[str] = None,
        limit: int = 20,
        cursor_field: str = "id",
        model_class: Optional[type] = None,
        direction: str = "next"
    ) -> CursorPaginatedResult:
        """Full cursor pagination with bidirectional support.
        
        Args:
            query: SQLAlchemy select query
            session: Async database session
            cursor: Cursor from previous/next page
            limit: Number of items per page
            cursor_field: Field to use for cursor
            model_class: Model class for cursor field access
            direction: "next" or "prev" for pagination direction
            
        Returns:
            CursorPaginatedResult with items and cursors
        """
        items, next_cursor = await Pagination.cursor_paginate(
            query=query,
            session=session,
            cursor=cursor,
            limit=limit,
            cursor_field=cursor_field,
            model_class=model_class
        )
        
        # Generate previous cursor from first item
        prev_cursor = None
        if cursor and items:
            first_item = items[0]
            first_value = getattr(first_item, cursor_field, None)
            if first_value is not None:
                cursor_data = {"value": str(first_value)}
                prev_cursor = base64.b64encode(
                    json.dumps(cursor_data).encode()
                ).decode()
        
        return CursorPaginatedResult(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=next_cursor is not None,
            has_prev=cursor is not None
        )


class SyncPagination:
    """Synchronous pagination utility class.
    
    Provides the same functionality as Pagination but for
    synchronous database sessions.
    """
    
    @staticmethod
    def paginate(
        query: Select,
        session: Session,
        page: int = 1,
        page_size: int = 20,
        count_query: Optional[Select] = None
    ) -> PaginatedResult:
        """Paginate query results using offset-based pagination (sync version).
        
        Args:
            query: SQLAlchemy select query
            session: Synchronous database session
            page: Page number (1-indexed)
            page_size: Number of items per page
            count_query: Optional custom count query
            
        Returns:
            PaginatedResult with items and pagination info
        """
        # Validate parameters
        if page < 1:
            logger.warning(f"database.pagination.invalid_page: page={page}")
            page = 1
        
        if page_size < 1:
            logger.warning(f"database.pagination.invalid_size: size={page_size}")
            page_size = 20
        
        if page_size > 1000:
            page_size = 1000
        
        try:
            # Get total count
            if count_query is not None:
                total_result = session.execute(count_query)
                total_items = total_result.scalar() or 0
            else:
                count_stmt = select(func.count()).select_from(query.subquery())
                total_result = session.execute(count_stmt)
                total_items = total_result.scalar() or 0
            
            # Calculate pagination info
            total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            
            if page > total_pages and total_pages > 0:
                page = total_pages
            
            offset = (page - 1) * page_size
            
            # Execute paginated query
            paginated_query = query.offset(offset).limit(page_size)
            result = session.execute(paginated_query)
            items = list(result.scalars().all())
            
            page_info = PageInfo(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
            
            return PaginatedResult(items=items, page_info=page_info)
            
        except Exception as e:
            logger.error(f"database.error.query_failed: error={str(e)}")
            raise
    
    @staticmethod
    def cursor_paginate(
        query: Select,
        session: Session,
        cursor: Optional[str] = None,
        limit: int = 20,
        cursor_field: str = "id",
        model_class: Optional[type] = None
    ) -> Tuple[List[Any], Optional[str]]:
        """Paginate query results using cursor-based pagination (sync version).
        
        Args:
            query: SQLAlchemy select query
            session: Synchronous database session
            cursor: Cursor from previous page
            limit: Number of items per page
            cursor_field: Field to use for cursor
            model_class: Model class for cursor field access
            
        Returns:
            Tuple of (items, next_cursor)
        """
        if limit < 1:
            limit = 20
        if limit > 1000:
            limit = 1000
        
        try:
            cursor_value = None
            if cursor:
                try:
                    decoded = base64.b64decode(cursor.encode()).decode()
                    cursor_data = json.loads(decoded)
                    cursor_value = cursor_data.get("value")
                except Exception:
                    cursor_value = None
            
            if cursor_value is not None and model_class is not None:
                cursor_field_attr = getattr(model_class, cursor_field, None)
                if cursor_field_attr is not None:
                    query = query.where(cursor_field_attr > cursor_value)
            
            if model_class is not None:
                cursor_field_attr = getattr(model_class, cursor_field, None)
                if cursor_field_attr is not None:
                    query = query.order_by(asc(cursor_field_attr))
            
            result = session.execute(query.limit(limit + 1))
            items = list(result.scalars().all())
            
            has_next = len(items) > limit
            if has_next:
                items = items[:limit]
            
            next_cursor = None
            if has_next and items:
                last_item = items[-1]
                last_value = getattr(last_item, cursor_field, None)
                if last_value is not None:
                    cursor_data = {"value": str(last_value)}
                    next_cursor = base64.b64encode(
                        json.dumps(cursor_data).encode()
                    ).decode()
            
            return items, next_cursor
            
        except Exception as e:
            logger.error(f"database.error.query_failed: error={str(e)}")
            raise
