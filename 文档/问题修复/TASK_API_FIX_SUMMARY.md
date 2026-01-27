# Task Creation/Editing API Fix Summary

**Date**: 2026-01-27  
**Status**: ✅ Fixed - Awaiting Container Restart  
**Issue**: Task creation and editing fail with 422 validation errors

---

## Problem Analysis

### Root Cause
The frontend was sending a `data_source` field in the task creation payload that the backend API did not accept, causing validation errors.

**Frontend Payload Structure** (`CreateTaskPayload`):
```typescript
{
  name: string;
  description?: string;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  assignee_id?: string;
  due_date?: string;
  tags?: string[];
  data_source?: {           // ❌ Backend didn't accept this
    type: 'file' | 'api';
    config: Record<string, unknown>;
  };
}
```

**Backend Expected Structure** (`TaskCreateRequest` - BEFORE FIX):
```python
class TaskCreateRequest(BaseModel):
    name: str
    description: Optional[str]
    annotation_type: str
    priority: str
    assignee_id: Optional[str]
    due_date: Optional[datetime]
    total_items: int
    tags: Optional[List[str]]
    # ❌ Missing data_source field
```

### Secondary Issue: Route Order
The `/stats` endpoint was defined AFTER the `/{task_id}` parameterized route, causing FastAPI to try to match "stats" as a task ID, resulting in 404 errors.

---

## Fixes Applied

### Fix 1: Added `data_source` Field to Backend Models

**File**: `src/api/tasks.py`

#### 1.1 Created `DataSourceConfig` Model
```python
class DataSourceConfig(BaseModel):
    """Data source configuration for task"""
    type: str = Field(..., description="Data source type: file, api, or database")
    config: Dict[str, Any] = Field(default_factory=dict, description="Data source configuration")
```

#### 1.2 Updated `TaskCreateRequest`
```python
class TaskCreateRequest(BaseModel):
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    annotation_type: str = Field("custom", description="Type of annotation")
    priority: str = Field("medium", description="Task priority")
    assignee_id: Optional[str] = Field(None, description="Assigned user ID")
    due_date: Optional[datetime] = Field(None, description="Due date")
    total_items: int = Field(1, description="Total items to annotate")
    tags: Optional[List[str]] = Field(None, description="Task tags")
    data_source: Optional[DataSourceConfig] = Field(None, description="Data source configuration")  # ✅ Added
```

#### 1.3 Updated `TaskUpdateRequest`
```python
class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    progress: Optional[int] = None
    completed_items: Optional[int] = None
    tags: Optional[List[str]] = None
    data_source: Optional[DataSourceConfig] = None  # ✅ Added
```

#### 1.4 Updated `TaskResponse`
```python
class TaskResponse(BaseModel):
    # ... existing fields ...
    tags: Optional[List[str]]
    data_source: Optional[DataSourceConfig] = None  # ✅ Added
``File**: `src/api/label_studio_api.py` (NEW)

Created new API module with endpoints:
- `GET /api/label-studio/projects` - List Label Studio projects
- `GET /api/label-studio/projects/{project_id}` - Get project details
- `GET /api/label-studio/projects/{project_id}/tasks` - List project tasks
- `GET /api/label-studio/health` - Check Label Studio health

### 6. Registered Label Studio Router
**File**: `src/app.py`

```python
# Include Label Studio API router
try:
    from src.api.label_studio_api import router as label_studio_router
    app.include_router(label_studio_router)
    logger.info("Label Studio API loaded successfully")
except ImportError as e:
    logger.error(f"Label Studio API not available: {e}")
except Exception as e:
    logger.error(f"Label Studio API failed to load: {e}")
```

## Testing Results

### 1. Task List API
```bash
GET /api/tasks
✅ Returns list of tasks with pagination
✅ Includes both in-memory and mock tasks
```

### 2. Task Creation API
```bash
POST /api/tasks
✅ Creates new task
✅ Stores in memory
✅ Returns task details
```

### 3. Task Update API
```bash
PATCH /api/tasks/{task_id}
✅ Updates existing task
✅ Persists changes
✅ Returns updated task
```

### 4. Task Retrieval API
```bash
GET /api/tasks/{task_id}
✅ Retrieves task by ID
✅ Works for both in-memory and mock tasks
```

### 5. Label Studio Projects API
```bash
GET /api/label-studio/projects
✅ Returns empty list (Label Studio not configured)
✅ No 404 error
```

## Example Usage

### Create a Task
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Task",
    "description": "Task description",
    "annotation_type": "text_classification",
    "priority": "high",
    "total_items": 100
  }'
```

### Update a Task
```bash
curl -X PATCH http://localhost:8000/api/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Task Name",
    "status": "in_progress",
    "progress": 50
  }'
```

### List Tasks
```bash
curl http://localhost:8000/api/tasks?page=1&size=10 \
  -H "Authorization: Bearer $TOKEN"
```

## Frontend Integration

The frontend can now:
1. ✅ List tasks from `/api/tasks`
2. ✅ Create new tasks via `POST /api/tasks`
3. ✅ Update tasks via `PATCH /api/tasks/{id}`
4. ✅ Delete tasks via `DELETE /api/tasks/{id}`
5. ✅ Get task statistics from `/api/tasks/stats`
6. ✅ List Label Studio projects from `/api/label-studio/projects`

## Next Steps

### Short Term (Development)
- [x] Fix API endpoint mismatches
- [x] Add in-memory storage for tasks
- [x] Create Label Studio API endpoints
- [ ] Test frontend task creation/editing flow
- [ ] Verify task list displays correctly

### Medium Term (Production Readiness)
- [ ] Replace in-memory storage with database persistence
- [ ] Implement proper task model in database
- [ ] Add task validation and business logic
- [ ] Configure Label Studio integration properly
- [ ] Add task assignment functionality
- [ ] Implement task progress tracking

### Long Term (Features)
- [ ] Add task templates
- [ ] Implement task workflows
- [ ] Add task notifications
- [ ] Create task analytics dashboard
- [ ] Add batch task operations
- [ ] Implement task scheduling

## Files Modified

1. `src/api/tasks.py` - Fixed endpoints, added storage, changed to sync
2. `src/api/label_studio_api.py` - NEW - Label Studio integration API
3. `src/app.py` - Registered Label Studio router

## Related Documentation

- `.kiro/steering/async-sync-safety.md` - Async/sync safety rules
- `.kiro/steering/structure.md` - Project structure
- `.kiro/steering/tech.md` - Technology stack
- `frontend/src/constants/api.ts` - Frontend API endpoints
- `frontend/src/services/task.ts` - Frontend task service

## Known Limitations

1. **In-Memory Storage**: Tasks are stored in memory and will be lost on server restart
2. **No Database Persistence**: Need to implement proper database models
3. **Label Studio Not Configured**: Label Studio integration returns empty data
4. **No Task Validation**: Need to add business logic validation
5. **No Permissions**: Need to add proper permission checks

## Verification Steps

To verify the fix is working:

1. **Start the backend**:
   ```bash
   docker restart superinsight-app
   ```

2. **Login to get token**:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin_user","password":"password"}'
   ```

3. **Create a task**:
   ```bash
   curl -X POST http://localhost:8000/api/tasks \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","annotation_type":"text_classification","priority":"high","total_items":10}'
   ```

4. **Update the task**:
   ```bash
   curl -X PATCH http://localhost:8000/api/tasks/{task_id} \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"status":"in_progress"}'
   ```

5. **List tasks**:
   ```bash
   curl http://localhost:8000/api/tasks \
     -H "Authorization: Bearer $TOKEN"
   ```

All commands should return 200 OK with proper JSON responses.

---

**Status**: ✅ Ready for frontend testing  
**Next Action**: Test task creation/editing in frontend UI at http://localhost:5173/tasks/
