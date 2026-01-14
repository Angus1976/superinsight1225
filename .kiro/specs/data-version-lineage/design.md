# Design Document: Data Version & Lineage (数据版本与血缘)

## Overview

本设计文档描述 Data Version & Lineage 模块的架构设计，该模块实现完整的数据版本控制和血缘追踪功能，支持数据变更历史、版本回滚、血缘图谱和影响分析。

设计原则：
- **完整追溯**：记录数据的完整生命周期
- **高效存储**：增量存储减少空间占用
- **图谱可视化**：直观展示血缘关系
- **影响可控**：变更前评估影响范围

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        VersionUI[Version UI]
        LineageUI[Lineage UI]
        ImpactUI[Impact UI]
        SnapshotUI[Snapshot UI]
    end

    subgraph API["API 层"]
        VersionRouter[/api/v1/versions]
        LineageRouter[/api/v1/lineage]
        SnapshotRouter[/api/v1/snapshots]
    end
    
    subgraph Core["核心层"]
        VersionManager[Version Manager]
        ChangeTracker[Change Tracker]
        LineageEngine[Lineage Engine]
        ImpactAnalyzer[Impact Analyzer]
        SnapshotManager[Snapshot Manager]
        DiffEngine[Diff Engine]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Neo4j[(Neo4j Graph)]
        ObjectStore[(Object Storage)]
    end
    
    VersionUI --> VersionRouter
    LineageUI --> LineageRouter
    ImpactUI --> LineageRouter
    SnapshotUI --> SnapshotRouter
    
    VersionRouter --> VersionManager
    VersionRouter --> ChangeTracker
    VersionRouter --> DiffEngine
    LineageRouter --> LineageEngine
    LineageRouter --> ImpactAnalyzer
    SnapshotRouter --> SnapshotManager
    
    VersionManager --> DB
    ChangeTracker --> DB
    LineageEngine --> Neo4j
    ImpactAnalyzer --> Neo4j
    SnapshotManager --> ObjectStore
    DiffEngine --> DB
```

## Components and Interfaces

### 1. Version Manager (版本管理器)

**文件**: `src/versioning/version_manager.py`

**职责**: 管理数据的版本控制

```python
class VersionManager:
    """版本管理器"""
    
    def __init__(self, db: AsyncSession, change_tracker: ChangeTracker):
        self.db = db
        self.change_tracker = change_tracker
    
    async def create_version(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict,
        message: str,
        user_id: str,
        version_type: VersionType = VersionType.PATCH
    ) -> DataVersion:
        """创建新版本"""
        # 获取当前版本
        current = await self.get_current_version(entity_type, entity_id)
        
        # 计算新版本号
        new_version = self._calculate_next_version(
            current.version if current else "0.0.0",
            version_type
        )
        
        # 创建版本记录
        version = DataVersion(
            entity_type=entity_type,
            entity_id=entity_id,
            version=new_version,
            data=data,
            message=message,
            created_by=user_id,
            parent_version_id=current.id if current else None
        )
        
        await self.db.add(version)
        
        # 记录变更
        await self.change_tracker.track_change(
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=ChangeType.UPDATE if current else ChangeType.CREATE,
            old_data=current.data if current else None,
            new_data=data,
            user_id=user_id
        )
        
        return version
    
    def _calculate_next_version(self, current: str, version_type: VersionType) -> str:
        """计算下一个版本号"""
        major, minor, patch = map(int, current.split('.'))
        
        if version_type == VersionType.MAJOR:
            return f"{major + 1}.0.0"
        elif version_type == VersionType.MINOR:
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"
    
    async def get_version(self, entity_type: str, entity_id: str, version: str) -> DataVersion:
        """获取指定版本"""
        pass
    
    async def get_current_version(self, entity_type: str, entity_id: str) -> Optional[DataVersion]:
        """获取当前版本"""
        pass
    
    async def get_version_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[DataVersion]:
        """获取版本历史"""
        pass
    
    async def add_tag(self, version_id: str, tag: str) -> DataVersion:
        """添加版本标签"""
        pass
    
    async def rollback(
        self,
        entity_type: str,
        entity_id: str,
        target_version: str,
        user_id: str
    ) -> DataVersion:
        """回滚到指定版本"""
        target = await self.get_version(entity_type, entity_id, target_version)
        
        # 创建新版本（内容为目标版本的数据）
        return await self.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data=target.data,
            message=f"Rollback to version {target_version}",
            user_id=user_id,
            version_type=VersionType.PATCH
        )

class VersionType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"

class DataVersion(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    version: str
    data: Dict
    message: str
    tags: List[str] = []
    created_by: str
    created_at: datetime
    parent_version_id: Optional[str] = None
```

### 2. Change Tracker (变更追踪器)

**文件**: `src/versioning/change_tracker.py`

**职责**: 追踪数据的所有变更

```python
class ChangeTracker:
    """变更追踪器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_change(
        self,
        entity_type: str,
        entity_id: str,
        change_type: ChangeType,
        old_data: Optional[Dict],
        new_data: Optional[Dict],
        user_id: str,
        metadata: Dict = None
    ) -> ChangeRecord:
        """记录变更"""
        # 计算差异
        diff = self._compute_diff(old_data, new_data) if old_data and new_data else None
        
        record = ChangeRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            old_snapshot=old_data,
            new_snapshot=new_data,
            diff=diff,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        await self.db.add(record)
        return record
    
    def _compute_diff(self, old_data: Dict, new_data: Dict) -> Dict:
        """计算差异"""
        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            if key not in old_data:
                diff["added"][key] = new_data[key]
            elif key not in new_data:
                diff["removed"][key] = old_data[key]
            elif old_data[key] != new_data[key]:
                diff["modified"][key] = {
                    "old": old_data[key],
                    "new": new_data[key]
                }
        
        return diff
    
    async def get_changes(
        self,
        entity_type: str = None,
        entity_id: str = None,
        user_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[ChangeRecord]:
        """查询变更历史"""
        pass
    
    async def get_entity_timeline(self, entity_type: str, entity_id: str) -> List[ChangeRecord]:
        """获取实体变更时间线"""
        pass

class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class ChangeRecord(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    change_type: ChangeType
    old_snapshot: Optional[Dict]
    new_snapshot: Optional[Dict]
    diff: Optional[Dict]
    user_id: str
    metadata: Dict
    created_at: datetime
```

### 3. Lineage Engine (血缘引擎)

**文件**: `src/versioning/lineage_engine.py`

**职责**: 构建和查询数据血缘关系

```python
class LineageEngine:
    """血缘引擎"""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        self.driver = neo4j_driver
    
    async def add_lineage(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship: str,
        transformation: Dict = None
    ) -> LineageEdge:
        """添加血缘关系"""
        query = """
        MERGE (s:DataNode {type: $source_type, id: $source_id})
        MERGE (t:DataNode {type: $target_type, id: $target_id})
        CREATE (s)-[r:LINEAGE {
            relationship: $relationship,
            transformation: $transformation,
            created_at: datetime()
        }]->(t)
        RETURN r
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                relationship=relationship,
                transformation=transformation or {}
            )
            return LineageEdge.from_neo4j(await result.single())
    
    async def get_upstream(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 3
    ) -> LineageGraph:
        """获取上游血缘"""
        query = """
        MATCH path = (target:DataNode {type: $type, id: $id})<-[:LINEAGE*1..$depth]-(upstream)
        RETURN path
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                type=entity_type,
                id=entity_id,
                depth=depth
            )
            return self._build_graph(await result.data())
    
    async def get_downstream(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 3
    ) -> LineageGraph:
        """获取下游血缘"""
        query = """
        MATCH path = (source:DataNode {type: $type, id: $id})-[:LINEAGE*1..$depth]->(downstream)
        RETURN path
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                type=entity_type,
                id=entity_id,
                depth=depth
            )
            return self._build_graph(await result.data())
    
    async def get_full_lineage(
        self,
        entity_type: str,
        entity_id: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3
    ) -> LineageGraph:
        """获取完整血缘图谱"""
        upstream = await self.get_upstream(entity_type, entity_id, upstream_depth)
        downstream = await self.get_downstream(entity_type, entity_id, downstream_depth)
        
        return self._merge_graphs(upstream, downstream)
    
    async def find_path(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str
    ) -> List[LineagePath]:
        """查找血缘路径"""
        pass
    
    def _build_graph(self, paths: List[Dict]) -> LineageGraph:
        """构建血缘图"""
        pass
    
    def _merge_graphs(self, *graphs: LineageGraph) -> LineageGraph:
        """合并血缘图"""
        pass

class LineageEdge(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str
    transformation: Dict
    created_at: datetime

class LineageGraph(BaseModel):
    nodes: List[LineageNode]
    edges: List[LineageEdge]
    
class LineageNode(BaseModel):
    type: str
    id: str
    name: str
    metadata: Dict
```

### 4. Impact Analyzer (影响分析器)

**文件**: `src/versioning/impact_analyzer.py`

**职责**: 分析数据变更的影响范围

```python
class ImpactAnalyzer:
    """影响分析器"""
    
    def __init__(self, lineage_engine: LineageEngine, notification_service: NotificationService):
        self.lineage_engine = lineage_engine
        self.notification_service = notification_service
    
    async def analyze_impact(
        self,
        entity_type: str,
        entity_id: str,
        change_type: str = "update"
    ) -> ImpactReport:
        """分析变更影响"""
        # 获取下游血缘
        downstream = await self.lineage_engine.get_downstream(entity_type, entity_id, depth=5)
        
        # 分析影响
        affected_entities = []
        critical_paths = []
        
        for node in downstream.nodes:
            impact = await self._assess_node_impact(node, change_type)
            affected_entities.append(impact)
            
            if impact.severity == "critical":
                path = await self.lineage_engine.find_path(
                    entity_type, entity_id, node.type, node.id
                )
                critical_paths.extend(path)
        
        # 估算影响数据量
        estimated_records = await self._estimate_affected_records(affected_entities)
        
        report = ImpactReport(
            source_type=entity_type,
            source_id=entity_id,
            change_type=change_type,
            affected_entities=affected_entities,
            critical_paths=critical_paths,
            estimated_records=estimated_records,
            risk_level=self._calculate_risk_level(affected_entities)
        )
        
        return report
    
    async def _assess_node_impact(self, node: LineageNode, change_type: str) -> EntityImpact:
        """评估节点影响"""
        pass
    
    async def _estimate_affected_records(self, entities: List[EntityImpact]) -> int:
        """估算影响记录数"""
        pass
    
    def _calculate_risk_level(self, entities: List[EntityImpact]) -> str:
        """计算风险等级"""
        critical_count = sum(1 for e in entities if e.severity == "critical")
        high_count = sum(1 for e in entities if e.severity == "high")
        
        if critical_count > 0:
            return "critical"
        elif high_count > 3:
            return "high"
        elif high_count > 0:
            return "medium"
        else:
            return "low"
    
    async def send_impact_alert(self, report: ImpactReport) -> None:
        """发送影响预警"""
        if report.risk_level in ["critical", "high"]:
            await self.notification_service.send_alert(
                title=f"数据变更影响预警 - {report.risk_level.upper()}",
                message=f"实体 {report.source_type}/{report.source_id} 的变更将影响 {len(report.affected_entities)} 个下游实体",
                severity=report.risk_level
            )
    
    async def visualize_impact(self, report: ImpactReport) -> Dict:
        """生成影响可视化数据"""
        pass

class ImpactReport(BaseModel):
    source_type: str
    source_id: str
    change_type: str
    affected_entities: List[EntityImpact]
    critical_paths: List[LineagePath]
    estimated_records: int
    risk_level: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EntityImpact(BaseModel):
    entity_type: str
    entity_id: str
    entity_name: str
    severity: str  # critical/high/medium/low
    impact_type: str  # data_loss/data_corruption/delay/none
    distance: int  # 距离源节点的跳数
```

### 5. Snapshot Manager (快照管理器)

**文件**: `src/versioning/snapshot_manager.py`

**职责**: 管理数据快照

```python
class SnapshotManager:
    """快照管理器"""
    
    def __init__(self, db: AsyncSession, object_store: ObjectStore):
        self.db = db
        self.object_store = object_store
    
    async def create_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        snapshot_type: SnapshotType = SnapshotType.FULL,
        user_id: str = None
    ) -> Snapshot:
        """创建快照"""
        # 获取当前数据
        data = await self._get_entity_data(entity_type, entity_id)
        
        if snapshot_type == SnapshotType.INCREMENTAL:
            # 获取上一个快照
            last_snapshot = await self.get_latest_snapshot(entity_type, entity_id)
            if last_snapshot:
                # 计算增量
                data = self._compute_incremental(last_snapshot.data, data)
        
        # 存储快照数据
        storage_key = f"snapshots/{entity_type}/{entity_id}/{uuid4()}"
        await self.object_store.put(storage_key, data)
        
        snapshot = Snapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            snapshot_type=snapshot_type,
            storage_key=storage_key,
            size_bytes=len(json.dumps(data)),
            created_by=user_id
        )
        
        await self.db.add(snapshot)
        return snapshot
    
    async def create_scheduled_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        schedule: str  # cron 表达式
    ) -> SnapshotSchedule:
        """创建定时快照"""
        pass
    
    async def restore_from_snapshot(
        self,
        snapshot_id: str,
        user_id: str
    ) -> RestoreResult:
        """从快照恢复"""
        snapshot = await self.get_snapshot(snapshot_id)
        
        # 获取快照数据
        data = await self.object_store.get(snapshot.storage_key)
        
        # 如果是增量快照，需要重建完整数据
        if snapshot.snapshot_type == SnapshotType.INCREMENTAL:
            data = await self._rebuild_full_data(snapshot)
        
        # 恢复数据
        await self._restore_entity_data(snapshot.entity_type, snapshot.entity_id, data)
        
        return RestoreResult(
            snapshot_id=snapshot_id,
            entity_type=snapshot.entity_type,
            entity_id=snapshot.entity_id,
            restored_at=datetime.utcnow(),
            restored_by=user_id
        )
    
    async def get_latest_snapshot(self, entity_type: str, entity_id: str) -> Optional[Snapshot]:
        """获取最新快照"""
        pass
    
    async def list_snapshots(
        self,
        entity_type: str = None,
        entity_id: str = None,
        limit: int = 50
    ) -> List[Snapshot]:
        """列出快照"""
        pass
    
    async def delete_snapshot(self, snapshot_id: str) -> None:
        """删除快照"""
        pass
    
    async def apply_retention_policy(self, policy: RetentionPolicy) -> int:
        """应用保留策略"""
        # 删除过期快照
        expired = await self._get_expired_snapshots(policy)
        for snapshot in expired:
            await self.delete_snapshot(snapshot.id)
        return len(expired)

class SnapshotType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"

class Snapshot(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    snapshot_type: SnapshotType
    storage_key: str
    size_bytes: int
    created_by: Optional[str]
    created_at: datetime

class RetentionPolicy(BaseModel):
    max_age_days: int = 90
    max_count: int = 100
    keep_tagged: bool = True
```

### 6. Diff Engine (差异引擎)

**文件**: `src/versioning/diff_engine.py`

**职责**: 计算版本间的差异

```python
class DiffEngine:
    """差异引擎"""
    
    def __init__(self):
        pass
    
    def compute_diff(
        self,
        old_data: Dict,
        new_data: Dict,
        diff_level: DiffLevel = DiffLevel.FIELD
    ) -> DiffResult:
        """计算差异"""
        if diff_level == DiffLevel.LINE:
            return self._line_diff(old_data, new_data)
        else:
            return self._field_diff(old_data, new_data)
    
    def _field_diff(self, old_data: Dict, new_data: Dict) -> DiffResult:
        """字段级差异"""
        changes = []
        
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            if key not in old_data:
                changes.append(FieldChange(
                    field=key,
                    change_type="added",
                    old_value=None,
                    new_value=new_data[key]
                ))
            elif key not in new_data:
                changes.append(FieldChange(
                    field=key,
                    change_type="removed",
                    old_value=old_data[key],
                    new_value=None
                ))
            elif old_data[key] != new_data[key]:
                changes.append(FieldChange(
                    field=key,
                    change_type="modified",
                    old_value=old_data[key],
                    new_value=new_data[key]
                ))
        
        return DiffResult(
            diff_level=DiffLevel.FIELD,
            changes=changes,
            summary=self._generate_summary(changes)
        )
    
    def _line_diff(self, old_data: Dict, new_data: Dict) -> DiffResult:
        """行级差异"""
        import difflib
        
        old_lines = json.dumps(old_data, indent=2).splitlines()
        new_lines = json.dumps(new_data, indent=2).splitlines()
        
        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        
        return DiffResult(
            diff_level=DiffLevel.LINE,
            unified_diff=list(differ),
            summary=self._generate_line_summary(old_lines, new_lines)
        )
    
    def three_way_merge(
        self,
        base: Dict,
        ours: Dict,
        theirs: Dict
    ) -> MergeResult:
        """三方合并"""
        merged = {}
        conflicts = []
        
        all_keys = set(base.keys()) | set(ours.keys()) | set(theirs.keys())
        
        for key in all_keys:
            base_val = base.get(key)
            ours_val = ours.get(key)
            theirs_val = theirs.get(key)
            
            if ours_val == theirs_val:
                # 双方相同，使用任一
                merged[key] = ours_val
            elif ours_val == base_val:
                # 只有 theirs 修改
                merged[key] = theirs_val
            elif theirs_val == base_val:
                # 只有 ours 修改
                merged[key] = ours_val
            else:
                # 冲突
                conflicts.append(MergeConflict(
                    field=key,
                    base_value=base_val,
                    ours_value=ours_val,
                    theirs_value=theirs_val
                ))
        
        return MergeResult(
            merged=merged,
            conflicts=conflicts,
            has_conflicts=len(conflicts) > 0
        )
    
    def resolve_conflict(
        self,
        merge_result: MergeResult,
        field: str,
        resolution: str  # "ours" | "theirs" | "custom"
        custom_value: Any = None
    ) -> MergeResult:
        """解决冲突"""
        pass
    
    def _generate_summary(self, changes: List[FieldChange]) -> DiffSummary:
        """生成差异摘要"""
        return DiffSummary(
            added=sum(1 for c in changes if c.change_type == "added"),
            removed=sum(1 for c in changes if c.change_type == "removed"),
            modified=sum(1 for c in changes if c.change_type == "modified")
        )

class DiffLevel(str, Enum):
    LINE = "line"
    FIELD = "field"

class FieldChange(BaseModel):
    field: str
    change_type: str  # added/removed/modified
    old_value: Any
    new_value: Any

class DiffResult(BaseModel):
    diff_level: DiffLevel
    changes: List[FieldChange] = []
    unified_diff: List[str] = []
    summary: DiffSummary

class MergeConflict(BaseModel):
    field: str
    base_value: Any
    ours_value: Any
    theirs_value: Any

class MergeResult(BaseModel):
    merged: Dict
    conflicts: List[MergeConflict]
    has_conflicts: bool
```


### 7. API Router (API 路由)

**文件**: `src/api/versioning.py`

```python
router = APIRouter(prefix="/api/v1", tags=["Versioning"])

# 版本管理
@router.post("/versions/{entity_type}/{entity_id}")
async def create_version(
    entity_type: str,
    entity_id: str,
    request: CreateVersionRequest
) -> DataVersion:
    """创建新版本"""
    pass

@router.get("/versions/{entity_type}/{entity_id}")
async def get_version_history(
    entity_type: str,
    entity_id: str,
    limit: int = 50
) -> List[DataVersion]:
    """获取版本历史"""
    pass

@router.get("/versions/{entity_type}/{entity_id}/{version}")
async def get_version(
    entity_type: str,
    entity_id: str,
    version: str
) -> DataVersion:
    """获取指定版本"""
    pass

@router.post("/versions/{entity_type}/{entity_id}/rollback")
async def rollback_version(
    entity_type: str,
    entity_id: str,
    request: RollbackRequest
) -> DataVersion:
    """回滚版本"""
    pass

@router.post("/versions/{version_id}/tags")
async def add_version_tag(version_id: str, request: AddTagRequest) -> DataVersion:
    """添加版本标签"""
    pass

# 变更追踪
@router.get("/changes")
async def get_changes(
    entity_type: str = None,
    entity_id: str = None,
    user_id: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = 100
) -> List[ChangeRecord]:
    """查询变更历史"""
    pass

@router.get("/changes/{entity_type}/{entity_id}/timeline")
async def get_entity_timeline(entity_type: str, entity_id: str) -> List[ChangeRecord]:
    """获取实体变更时间线"""
    pass

# 血缘追踪
@router.post("/lineage")
async def add_lineage(request: AddLineageRequest) -> LineageEdge:
    """添加血缘关系"""
    pass

@router.get("/lineage/{entity_type}/{entity_id}/upstream")
async def get_upstream_lineage(
    entity_type: str,
    entity_id: str,
    depth: int = 3
) -> LineageGraph:
    """获取上游血缘"""
    pass

@router.get("/lineage/{entity_type}/{entity_id}/downstream")
async def get_downstream_lineage(
    entity_type: str,
    entity_id: str,
    depth: int = 3
) -> LineageGraph:
    """获取下游血缘"""
    pass

@router.get("/lineage/{entity_type}/{entity_id}/full")
async def get_full_lineage(
    entity_type: str,
    entity_id: str,
    upstream_depth: int = 3,
    downstream_depth: int = 3
) -> LineageGraph:
    """获取完整血缘图谱"""
    pass

# 影响分析
@router.post("/impact/{entity_type}/{entity_id}/analyze")
async def analyze_impact(
    entity_type: str,
    entity_id: str,
    request: AnalyzeImpactRequest
) -> ImpactReport:
    """分析变更影响"""
    pass

# 快照管理
@router.post("/snapshots/{entity_type}/{entity_id}")
async def create_snapshot(
    entity_type: str,
    entity_id: str,
    request: CreateSnapshotRequest
) -> Snapshot:
    """创建快照"""
    pass

@router.get("/snapshots")
async def list_snapshots(
    entity_type: str = None,
    entity_id: str = None,
    limit: int = 50
) -> List[Snapshot]:
    """列出快照"""
    pass

@router.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str) -> RestoreResult:
    """从快照恢复"""
    pass

@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str) -> None:
    """删除快照"""
    pass

@router.post("/snapshots/schedules")
async def create_snapshot_schedule(request: CreateScheduleRequest) -> SnapshotSchedule:
    """创建定时快照"""
    pass

# 差异比较
@router.post("/diff")
async def compute_diff(request: ComputeDiffRequest) -> DiffResult:
    """计算差异"""
    pass

@router.post("/merge")
async def three_way_merge(request: MergeRequest) -> MergeResult:
    """三方合并"""
    pass

@router.post("/merge/resolve")
async def resolve_conflict(request: ResolveConflictRequest) -> MergeResult:
    """解决冲突"""
    pass
```

## Data Models

### 数据库模型

```python
class DataVersionModel(Base):
    """数据版本表"""
    __tablename__ = "data_versions"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    data = Column(JSONB, nullable=False)
    message = Column(Text, nullable=True)
    tags = Column(ARRAY(String), default=[])
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    parent_version_id = Column(UUID, ForeignKey("data_versions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'version', name='uq_entity_version'),
        Index('ix_entity_version', 'entity_type', 'entity_id', 'created_at'),
    )

class ChangeRecordModel(Base):
    """变更记录表"""
    __tablename__ = "change_records"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    change_type = Column(String(20), nullable=False)
    old_snapshot = Column(JSONB, nullable=True)
    new_snapshot = Column(JSONB, nullable=True)
    diff = Column(JSONB, nullable=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class SnapshotModel(Base):
    """快照表"""
    __tablename__ = "snapshots"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    snapshot_type = Column(String(20), nullable=False)
    storage_key = Column(String(500), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)

class SnapshotScheduleModel(Base):
    """快照调度表"""
    __tablename__ = "snapshot_schedules"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    schedule = Column(String(100), nullable=False)  # cron 表达式
    snapshot_type = Column(String(20), default="full")
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties (Property-Based Testing)

使用 Hypothesis 库进行属性测试，每个属性至少运行 100 次迭代。

### Property 1: 版本号单调递增

```python
@given(
    versions=st.lists(st.sampled_from(["major", "minor", "patch"]), min_size=1, max_size=20)
)
@settings(max_examples=100)
def test_version_monotonically_increasing(versions):
    """版本号必须单调递增"""
    current = "0.0.0"
    for version_type in versions:
        next_version = calculate_next_version(current, version_type)
        assert compare_versions(next_version, current) > 0
        current = next_version
```

### Property 2: 变更追踪完整性

```python
@given(
    changes=st.lists(
        st.fixed_dictionaries({
            "field": st.text(min_size=1, max_size=50),
            "value": st.one_of(st.integers(), st.text(), st.booleans())
        }),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
def test_change_tracking_completeness(changes):
    """所有变更必须被完整记录"""
    old_data = {}
    new_data = {}
    
    for change in changes:
        new_data[change["field"]] = change["value"]
    
    diff = compute_diff(old_data, new_data)
    
    # 所有新增字段都应该在 diff 中
    for field in new_data:
        assert field in [c.field for c in diff.changes if c.change_type == "added"]
```

### Property 3: 血缘图谱一致性

```python
@given(
    edges=st.lists(
        st.tuples(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=20)),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_lineage_graph_consistency(edges):
    """血缘图谱必须保持一致性"""
    graph = LineageGraph()
    
    for source, target in edges:
        graph.add_edge(source, target)
    
    # 上游的下游包含自己
    for source, target in edges:
        downstream = graph.get_downstream(source)
        assert target in [n.id for n in downstream.nodes]
        
        upstream = graph.get_upstream(target)
        assert source in [n.id for n in upstream.nodes]
```

### Property 4: 快照恢复幂等性

```python
@given(
    data=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.integers(), st.text(max_size=100), st.booleans()),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
def test_snapshot_restore_idempotent(data):
    """从快照恢复必须是幂等的"""
    snapshot = create_snapshot(data)
    
    restored1 = restore_from_snapshot(snapshot.id)
    restored2 = restore_from_snapshot(snapshot.id)
    
    assert restored1 == restored2
    assert restored1 == data
```

### Property 5: 差异计算可逆性

```python
@given(
    old_data=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.integers(),
        min_size=0,
        max_size=10
    ),
    new_data=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.integers(),
        min_size=0,
        max_size=10
    )
)
@settings(max_examples=100)
def test_diff_reversibility(old_data, new_data):
    """差异计算必须可逆"""
    diff = compute_diff(old_data, new_data)
    reconstructed = apply_diff(old_data, diff)
    
    assert reconstructed == new_data
```

### Property 6: 三方合并确定性

```python
@given(
    base=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
    ours_changes=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=3),
    theirs_changes=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=3)
)
@settings(max_examples=100)
def test_three_way_merge_deterministic(base, ours_changes, theirs_changes):
    """三方合并必须是确定性的"""
    ours = {**base, **ours_changes}
    theirs = {**base, **theirs_changes}
    
    result1 = three_way_merge(base, ours, theirs)
    result2 = three_way_merge(base, ours, theirs)
    
    assert result1.merged == result2.merged
    assert result1.conflicts == result2.conflicts
```

### Property 7: 影响分析传递性

```python
@given(
    graph=st.lists(
        st.tuples(st.integers(0, 10), st.integers(0, 10)),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_impact_analysis_transitivity(graph):
    """影响分析必须满足传递性"""
    lineage = build_lineage_graph(graph)
    
    for source, target in graph:
        # 如果 A 影响 B，B 影响 C，则 A 影响 C
        downstream_of_source = lineage.get_downstream(source)
        
        for intermediate in downstream_of_source.nodes:
            downstream_of_intermediate = lineage.get_downstream(intermediate.id)
            
            # 所有 intermediate 的下游也应该是 source 的下游
            for node in downstream_of_intermediate.nodes:
                assert node.id in [n.id for n in downstream_of_source.nodes]
```

### Property 8: 版本回滚正确性

```python
@given(
    versions=st.lists(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.integers(),
            min_size=1,
            max_size=5
        ),
        min_size=2,
        max_size=10
    )
)
@settings(max_examples=100)
def test_rollback_correctness(versions):
    """版本回滚必须恢复到正确的状态"""
    entity_id = "test_entity"
    
    # 创建多个版本
    version_ids = []
    for data in versions:
        version = create_version(entity_id, data)
        version_ids.append(version.id)
    
    # 回滚到任意历史版本
    target_idx = random.randint(0, len(versions) - 1)
    rollback(entity_id, version_ids[target_idx])
    
    # 验证当前数据等于目标版本的数据
    current = get_current_version(entity_id)
    assert current.data == versions[target_idx]
```

## Frontend Components

### 1. 版本历史时间线

**文件**: `frontend/src/pages/versioning/VersionTimeline.tsx`

```typescript
interface VersionTimelineProps {
  entityType: string;
  entityId: string;
}

const VersionTimeline: React.FC<VersionTimelineProps> = ({ entityType, entityId }) => {
  const { data: versions, isLoading } = useQuery(
    ['versions', entityType, entityId],
    () => versioningApi.getVersionHistory(entityType, entityId)
  );

  return (
    <Timeline mode="left">
      {versions?.map((version) => (
        <Timeline.Item
          key={version.id}
          label={formatDate(version.created_at)}
          color={version.tags.includes('release') ? 'green' : 'blue'}
        >
          <Card size="small">
            <Space direction="vertical">
              <Text strong>v{version.version}</Text>
              <Text type="secondary">{version.message}</Text>
              <Space>
                {version.tags.map((tag) => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
              </Space>
              <Space>
                <Button size="small" onClick={() => handleViewDiff(version)}>
                  查看差异
                </Button>
                <Button size="small" onClick={() => handleRollback(version)}>
                  回滚
                </Button>
              </Space>
            </Space>
          </Card>
        </Timeline.Item>
      ))}
    </Timeline>
  );
};
```

### 2. 血缘图谱可视化

**文件**: `frontend/src/pages/versioning/LineageGraph.tsx`

```typescript
interface LineageGraphProps {
  entityType: string;
  entityId: string;
}

const LineageGraph: React.FC<LineageGraphProps> = ({ entityType, entityId }) => {
  const { data: lineage, isLoading } = useQuery(
    ['lineage', entityType, entityId],
    () => versioningApi.getFullLineage(entityType, entityId)
  );

  const graphData = useMemo(() => {
    if (!lineage) return { nodes: [], edges: [] };
    
    return {
      nodes: lineage.nodes.map((node) => ({
        id: node.id,
        label: node.name,
        type: node.type,
        style: {
          fill: node.id === entityId ? '#1890ff' : '#f0f0f0',
        },
      })),
      edges: lineage.edges.map((edge) => ({
        source: edge.source_id,
        target: edge.target_id,
        label: edge.relationship,
      })),
    };
  }, [lineage, entityId]);

  return (
    <Card title="数据血缘图谱">
      <G6Graph
        data={graphData}
        layout={{ type: 'dagre', rankdir: 'LR' }}
        height={500}
        onNodeClick={handleNodeClick}
      />
      <Space style={{ marginTop: 16 }}>
        <Button onClick={() => setDepth(depth + 1)}>展开更多</Button>
        <Button onClick={handleExport}>导出图谱</Button>
      </Space>
    </Card>
  );
};
```

### 3. 影响分析面板

**文件**: `frontend/src/pages/versioning/ImpactAnalysis.tsx`

```typescript
interface ImpactAnalysisProps {
  entityType: string;
  entityId: string;
}

const ImpactAnalysis: React.FC<ImpactAnalysisProps> = ({ entityType, entityId }) => {
  const [report, setReport] = useState<ImpactReport | null>(null);
  
  const analyzeMutation = useMutation(
    () => versioningApi.analyzeImpact(entityType, entityId),
    { onSuccess: setReport }
  );

  return (
    <Card title="影响分析">
      <Button 
        type="primary" 
        onClick={() => analyzeMutation.mutate()}
        loading={analyzeMutation.isLoading}
      >
        分析影响
      </Button>
      
      {report && (
        <>
          <Alert
            type={report.risk_level === 'critical' ? 'error' : 
                  report.risk_level === 'high' ? 'warning' : 'info'}
            message={`风险等级: ${report.risk_level.toUpperCase()}`}
            description={`预计影响 ${report.affected_entities.length} 个下游实体，约 ${report.estimated_records} 条记录`}
          />
          
          <Table
            dataSource={report.affected_entities}
            columns={[
              { title: '实体', dataIndex: 'entity_name' },
              { title: '类型', dataIndex: 'entity_type' },
              { title: '严重程度', dataIndex: 'severity', render: renderSeverity },
              { title: '距离', dataIndex: 'distance' },
            ]}
          />
        </>
      )}
    </Card>
  );
};
```

### 4. 差异对比视图

**文件**: `frontend/src/pages/versioning/DiffViewer.tsx`

```typescript
interface DiffViewerProps {
  oldVersion: DataVersion;
  newVersion: DataVersion;
}

const DiffViewer: React.FC<DiffViewerProps> = ({ oldVersion, newVersion }) => {
  const { data: diff } = useQuery(
    ['diff', oldVersion.id, newVersion.id],
    () => versioningApi.computeDiff({
      old_data: oldVersion.data,
      new_data: newVersion.data,
      diff_level: 'field'
    })
  );

  return (
    <Card title={`版本对比: v${oldVersion.version} → v${newVersion.version}`}>
      <Row gutter={16}>
        <Col span={12}>
          <Card title="旧版本" size="small">
            <pre>{JSON.stringify(oldVersion.data, null, 2)}</pre>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="新版本" size="small">
            <pre>{JSON.stringify(newVersion.data, null, 2)}</pre>
          </Card>
        </Col>
      </Row>
      
      <Divider>变更摘要</Divider>
      
      <Space>
        <Tag color="green">新增: {diff?.summary.added}</Tag>
        <Tag color="red">删除: {diff?.summary.removed}</Tag>
        <Tag color="blue">修改: {diff?.summary.modified}</Tag>
      </Space>
      
      <Table
        dataSource={diff?.changes}
        columns={[
          { title: '字段', dataIndex: 'field' },
          { title: '变更类型', dataIndex: 'change_type', render: renderChangeType },
          { title: '旧值', dataIndex: 'old_value', render: renderValue },
          { title: '新值', dataIndex: 'new_value', render: renderValue },
        ]}
      />
    </Card>
  );
};
```

## Error Handling

```python
class VersioningError(Exception):
    """版本控制基础异常"""
    pass

class VersionNotFoundError(VersioningError):
    """版本不存在"""
    pass

class VersionConflictError(VersioningError):
    """版本冲突"""
    pass

class LineageNotFoundError(VersioningError):
    """血缘关系不存在"""
    pass

class SnapshotNotFoundError(VersioningError):
    """快照不存在"""
    pass

class SnapshotRestoreError(VersioningError):
    """快照恢复失败"""
    pass

class MergeConflictError(VersioningError):
    """合并冲突"""
    def __init__(self, conflicts: List[MergeConflict]):
        self.conflicts = conflicts
        super().__init__(f"Merge has {len(conflicts)} conflicts")
```

## Performance Considerations

1. **增量存储**: 使用增量快照减少存储空间
2. **图数据库**: 使用 Neo4j 高效存储和查询血缘关系
3. **缓存策略**: 缓存热点版本和血缘查询结果
4. **异步处理**: 影响分析和快照创建使用异步任务
5. **分页查询**: 版本历史和变更记录支持分页
6. **索引优化**: 为常用查询字段创建索引
