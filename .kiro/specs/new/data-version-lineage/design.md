# Design Document

## Overview

数据版本控制与血缘追踪系统为SuperInsight 2.3提供完整的数据生命周期管理能力。系统基于现有数据库架构扩展，利用PostgreSQL JSONB特性实现高效的版本存储，结合现有监控系统提供全面的数据血缘追踪和影响分析。

## Architecture Design

### System Architecture

```
Data Version Lineage System
├── Version Control Engine
│   ├── Version Manager
│   ├── Snapshot Creator
│   ├── Delta Calculator
│   └── Merge Controller
├── Lineage Tracking Engine
│   ├── Lineage Recorder
│   ├── Relationship Mapper
│   ├── Impact Analyzer
│   └── Dependency Tracker
├── Change Management
│   ├── Change Detector
│   ├── Change Classifier
│   ├── Change Validator
│   └── Change Notifier
├── Query & Analysis
│   ├── Version Query Engine
│   ├── Lineage Query Engine
│   ├── Impact Analysis
│   └── Trend Analyzer
└── Storage & Optimization
    ├── Version Storage
    ├── Lineage Storage
    ├── Index Manager
    └── Cleanup Service
```

## Implementation Strategy

### Phase 1: 基于现有数据库扩展版本控制

#### 扩展现有数据库模型
```python
# 扩展 src/database/models.py
from src.database.models import BaseModel

class DataVersion(BaseModel):
    """数据版本模型 - 基于现有模型扩展"""
    
    __tablename__ = 'data_versions'
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(100), nullable=False)  # task, annotation, dataset
    entity_id = Column(UUID, nullable=False)
    version_number = Column(Integer, nullable=False)
    parent_version_id = Column(UUID, ForeignKey('data_versions.id'))
    
    # 使用PostgreSQL JSONB存储版本数据
    version_data = Column(JSONB, nullable=False)
    delta_data = Column(JSONB)  # 增量数据
    metadata = Column(JSONB, default={})
    
    # 基于现有用户和租户模型
    created_by = Column(UUID, ForeignKey('users.id'))
    tenant_id = Column(UUID, ForeignKey('tenants.id'))
    workspace_id = Column(UUID, ForeignKey('workspaces.id'))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引优化
    __table_args__ = (
        Index('idx_data_versions_entity', 'entity_type', 'entity_id'),
        Index('idx_data_versions_tenant', 'tenant_id', 'workspace_id'),
        Index('idx_data_versions_created', 'created_at'),
    )

class DataLineage(BaseModel):
    """数据血缘模型"""
    
    __tablename__ = 'data_lineage'
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    source_entity_type = Column(String(100), nullable=False)
    source_entity_id = Column(UUID, nullable=False)
    target_entity_type = Column(String(100), nullable=False)
    target_entity_id = Column(UUID, nullable=False)
    
    relationship_type = Column(String(50), nullable=False)  # derived_from, transformed_to, etc.
    transformation_info = Column(JSONB, default={})
    
    # 版本关联
    source_version_id = Column(UUID, ForeignKey('data_versions.id'))
    target_version_id = Column(UUID, ForeignKey('data_versions.id'))
    
    tenant_id = Column(UUID, ForeignKey('tenants.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 扩展现有数据库管理
```python
# 扩展现有数据库管理器
from src.database.manager import DatabaseManager

class VersionControlManager(DatabaseManager):
    """版本控制管理器 - 基于现有数据库管理"""
    
    def __init__(self):
        super().__init__()  # 保持现有数据库连接逻辑
        self.version_calculator = VersionCalculator()
        self.delta_processor = DeltaProcessor()
    
    async def create_version(
        self, 
        entity_type: str, 
        entity_id: str, 
        data: dict,
        user_id: str,
        comment: str = None
    ) -> DataVersion:
        """创建数据版本"""
        # 基于现有数据库操作
        async with self.get_session() as session:
            # 获取当前最新版本
            latest_version = await self.get_latest_version(entity_type, entity_id)
            
            # 计算版本号和增量
            version_number = (latest_version.version_number + 1) if latest_version else 1
            delta_data = await self.delta_processor.calculate_delta(
                latest_version.version_data if latest_version else {},
                data
            )
            
            # 创建新版本
            new_version = DataVersion(
                entity_type=entity_type,
                entity_id=entity_id,
                version_number=version_number,
                parent_version_id=latest_version.id if latest_version else None,
                version_data=data,
                delta_data=delta_data,
                created_by=user_id,
                metadata={'comment': comment}
            )
            
            session.add(new_version)
            await session.commit()
            
            return new_version
    
    async def get_version_history(
        self, 
        entity_type: str, 
        entity_id: str,
        limit: int = 50
    ) -> List[DataVersion]:
        """获取版本历史"""
        # 基于现有查询模式
        async with self.get_session() as session:
            query = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id
            ).order_by(DataVersion.version_number.desc()).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
```

### Phase 2: 血缘追踪系统

#### 扩展现有监控系统
```python
# 扩展 src/sync/monitoring/ 现有监控
from src.sync.monitoring.sync_monitor import SyncMonitor

class LineageTracker(SyncMonitor):
    """血缘追踪器 - 基于现有监控系统"""
    
    def __init__(self):
        super().__init__()  # 保持现有监控逻辑
        self.relationship_mapper = RelationshipMapper()
        self.impact_analyzer = ImpactAnalyzer()
    
    async def track_data_transformation(
        self,
        source_entity: dict,
        target_entity: dict,
        transformation_type: str,
        transformation_details: dict = None
    ):
        """追踪数据转换血缘"""
        # 基于现有监控记录模式
        lineage_record = DataLineage(
            source_entity_type=source_entity['type'],
            source_entity_id=source_entity['id'],
            target_entity_type=target_entity['type'],
            target_entity_id=target_entity['id'],
            relationship_type=transformation_type,
            transformation_info=transformation_details or {}
        )
        
        # 记录到数据库
        await self.store_lineage_record(lineage_record)
        
        # 更新血缘图
        await self.update_lineage_graph(lineage_record)
    
    async def analyze_impact(self, entity_type: str, entity_id: str) -> ImpactAnalysis:
        """分析数据变更影响"""
        # 基于现有分析逻辑
        downstream_entities = await self.get_downstream_entities(entity_type, entity_id)
        upstream_entities = await self.get_upstream_entities(entity_type, entity_id)
        
        impact_analysis = ImpactAnalysis(
            affected_downstream=len(downstream_entities),
            affected_upstream=len(upstream_entities),
            critical_dependencies=await self.identify_critical_dependencies(entity_type, entity_id),
            risk_level=await self.assess_change_risk(entity_type, entity_id)
        )
        
        return impact_analysis
```

### Phase 3: 查询和分析引擎

#### 版本查询引擎
```python
# src/version/query_engine.py
class VersionQueryEngine:
    """版本查询引擎"""
    
    def __init__(self, db_manager: VersionControlManager):
        self.db_manager = db_manager
        self.cache_manager = CacheManager()
    
    async def query_version_at_time(
        self, 
        entity_type: str, 
        entity_id: str, 
        timestamp: datetime
    ) -> Optional[DataVersion]:
        """查询指定时间点的版本"""
        # 使用缓存优化查询性能
        cache_key = f"version:{entity_type}:{entity_id}:{timestamp.isoformat()}"
        cached_version = await self.cache_manager.get(cache_key)
        
        if cached_version:
            return cached_version
        
        # 数据库查询
        async with self.db_manager.get_session() as session:
            query = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.created_at <= timestamp
            ).order_by(DataVersion.created_at.desc()).limit(1)
            
            result = await session.execute(query)
            version = result.scalar_one_or_none()
            
            # 缓存结果
            if version:
                await self.cache_manager.set(cache_key, version, ttl=3600)
            
            return version
    
    async def compare_versions(
        self, 
        version1_id: str, 
        version2_id: str
    ) -> VersionComparison:
        """比较两个版本"""
        version1 = await self.get_version_by_id(version1_id)
        version2 = await self.get_version_by_id(version2_id)
        
        if not version1 or not version2:
            raise ValueError("Version not found")
        
        # 计算差异
        differences = await self.calculate_differences(
            version1.version_data, 
            version2.version_data
        )
        
        return VersionComparison(
            version1=version1,
            version2=version2,
            differences=differences,
            similarity_score=await self.calculate_similarity(differences)
        )
```

This comprehensive design provides enterprise-grade data version control and lineage tracking capabilities for SuperInsight 2.3, building upon the existing database infrastructure and monitoring systems.