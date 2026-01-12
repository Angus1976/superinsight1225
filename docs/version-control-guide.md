# Data Version Control and Lineage Tracking Guide

## Overview

SuperInsight 2.3 introduces comprehensive data version control and lineage tracking capabilities, enabling enterprise-grade data governance with full audit trails and impact analysis.

## Features

### Version Control
- **Full Snapshots**: Complete data state at any point in time
- **Delta Storage**: Efficient incremental storage with automatic delta calculation
- **Branching**: Support for parallel version development
- **Tagging**: Mark important versions for easy reference
- **Rollback**: Safe version restoration with conflict detection

### Lineage Tracking
- **Automatic Tracking**: Capture data transformations automatically
- **Column-Level Lineage**: Track field-level data flow
- **Impact Analysis**: Assess change risks before deployment
- **Visualization**: Graph-based lineage visualization

## API Reference

### Version Control Endpoints

#### Create Version
```http
POST /api/v1/versions/create
Content-Type: application/json

{
  "entity_type": "task",
  "entity_id": "uuid-string",
  "data": {"field": "value"},
  "comment": "Initial version",
  "use_delta": true
}
```

#### Get Version History
```http
GET /api/v1/versions/entity/{entity_type}/{entity_id}/history?limit=50
```

#### Compare Versions
```http
GET /api/v1/versions/compare/{version1_id}/{version2_id}
```

#### Get Version at Time
```http
GET /api/v1/versions/at-time/{entity_type}/{entity_id}?timestamp=2026-01-12T10:00:00Z
```

#### Create Tag
```http
POST /api/v1/versions/tags
Content-Type: application/json

{
  "version_id": "uuid-string",
  "tag_name": "v1.0-release",
  "description": "Production release"
}
```

#### Create Branch
```http
POST /api/v1/versions/branches
Content-Type: application/json

{
  "entity_type": "task",
  "entity_id": "uuid-string",
  "branch_name": "feature-branch",
  "base_version_id": "uuid-string"
}
```

### Lineage Tracking Endpoints

#### Track Lineage
```http
POST /api/v1/lineage/track
Content-Type: application/json

{
  "source_entity_type": "document",
  "source_entity_id": "uuid-string",
  "target_entity_type": "task",
  "target_entity_id": "uuid-string",
  "relationship_type": "derived_from",
  "transformation_info": {"operation": "extract"}
}
```

#### Get Entity Lineage
```http
GET /api/v1/lineage/entity/{entity_type}/{entity_id}?direction=both
```

#### Get Full Lineage Path
```http
GET /api/v1/lineage/entity/{entity_type}/{entity_id}/full-path?max_depth=10
```

#### Analyze Impact
```http
GET /api/v1/lineage/impact/{entity_type}/{entity_id}?max_depth=5
```

#### Get Lineage Graph
```http
GET /api/v1/lineage/graph?entity_types=task,document
```

## Relationship Types

| Type | Description |
|------|-------------|
| `derived_from` | Target was derived from source |
| `transformed_to` | Source was transformed to target |
| `copied_from` | Target is a copy of source |
| `aggregated_from` | Target aggregates data from source |
| `filtered_from` | Target is filtered subset of source |
| `joined_from` | Target joins data from source |
| `enriched_by` | Target was enriched by source |

## Risk Levels

Impact analysis returns risk levels:

| Level | Criteria |
|-------|----------|
| `low` | Few downstream dependencies, no critical systems |
| `medium` | Some dependencies or critical systems affected |
| `high` | Many dependencies or multiple critical systems |
| `critical` | 50+ downstream entities or 5+ critical dependencies |

## Best Practices

### Version Control
1. **Use meaningful comments** for each version
2. **Tag important milestones** (releases, checkpoints)
3. **Use branches** for experimental changes
4. **Enable delta storage** for large datasets

### Lineage Tracking
1. **Track all transformations** for complete audit trail
2. **Include column-level lineage** for detailed tracing
3. **Run impact analysis** before major changes
4. **Review critical dependencies** regularly

## Multi-Tenant Support

All version and lineage operations support multi-tenant isolation via `tenant_id` parameter:

```http
GET /api/v1/versions/entity/task/{id}/history?tenant_id=tenant123
```

## Performance Considerations

- Delta storage reduces storage by ~30% for incremental changes
- Lineage queries are optimized with database indexes
- Cache integration for frequently accessed versions
- Batch operations for bulk version creation

## Integration with Existing Systems

### Audit System
All version and lineage operations are automatically logged to the audit system.

### Security
- Role-based access control for version operations
- Tenant isolation for multi-tenant deployments
- Encrypted storage for sensitive version data

### Monitoring
- Prometheus metrics for version/lineage operations
- Health checks for version control service
- Performance tracking for query latency
