# Label Studio Annotation Workflow API

## Overview

This document describes the API endpoints for the Label Studio annotation workflow integration in SuperInsight. These endpoints enable seamless annotation workflows with automatic project management, language synchronization, and error handling.

## Base URL

```
/api/label-studio
```

## Authentication

All endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

## Endpoints

### 1. Ensure Project Exists

Creates a Label Studio project if it doesn't exist, or returns the existing project.

**Endpoint:** `POST /api/label-studio/projects/ensure`

**Request Body:**
```json
{
  "task_id": "string",
  "task_name": "string",
  "annotation_type": "string"
}
```

**Response:**
```json
{
  "project_id": "string",
  "created": true,
  "status": "ready",
  "task_count": 0,
  "message": "Project created successfully"
}
```

**Status Codes:**
- `200 OK` - Project exists or was created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication failed
- `503 Service Unavailable` - Label Studio service unavailable

**Example:**
```bash
curl -X POST "http://localhost:8000/api/label-studio/projects/ensure" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-123",
    "task_name": "Customer Review Classification",
    "annotation_type": "sentiment"
  }'
```

---

### 2. Validate Project

Validates if a Label Studio project exists and is accessible.

**Endpoint:** `GET /api/label-studio/projects/{project_id}/validate`

**Path Parameters:**
- `project_id` (string, required) - Label Studio project ID

**Response:**
```json
{
  "exists": true,
  "accessible": true,
  "task_count": 100,
  "annotation_count": 50,
  "status": "ready",
  "error_message": null
}
```

**Status Values:**
- `ready` - Project is ready for annotation
- `creating` - Project is being created
- `error` - Project has an error
- `not_found` - Project does not exist

**Status Codes:**
- `200 OK` - Validation completed
- `401 Unauthorized` - Authentication failed
- `404 Not Found` - Project not found

**Example:**
```bash
curl -X GET "http://localhost:8000/api/label-studio/projects/123/validate" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Import Tasks

Imports tasks from SuperInsight to a Label Studio project.

**Endpoint:** `POST /api/label-studio/projects/{project_id}/import-tasks`

**Path Parameters:**
- `project_id` (string, required) - Label Studio project ID

**Request Body:**
```json
{
  "task_id": "string"
}
```

**Response:**
```json
{
  "imported_count": 100,
  "failed_count": 0,
  "status": "success",
  "errors": []
}
```

**Status Values:**
- `success` - All tasks imported successfully
- `partial` - Some tasks failed to import
- `failed` - Import failed completely

**Status Codes:**
- `200 OK` - Import completed
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Authentication failed
- `404 Not Found` - Project not found

**Example:**
```bash
curl -X POST "http://localhost:8000/api/label-studio/projects/123/import-tasks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task-123"}'
```

---

### 4. Get Authenticated URL

Generates an authenticated URL for accessing Label Studio with language preference.

**Endpoint:** `GET /api/label-studio/projects/{project_id}/auth-url`

**Path Parameters:**
- `project_id` (string, required) - Label Studio project ID

**Query Parameters:**
- `language` (string, optional) - Language preference (`zh` or `en`). Default: `zh`

**Response:**
```json
{
  "url": "https://labelstudio.example.com/projects/123?token=abc123&lang=zh",
  "expires_at": "2025-01-20T15:00:00Z",
  "project_id": "123"
}
```

**Status Codes:**
- `200 OK` - URL generated successfully
- `401 Unauthorized` - Authentication failed
- `404 Not Found` - Project not found

**Example:**
```bash
# Chinese language (default)
curl -X GET "http://localhost:8000/api/label-studio/projects/123/auth-url" \
  -H "Authorization: Bearer <token>"

# English language
curl -X GET "http://localhost:8000/api/label-studio/projects/123/auth-url?language=en" \
  -H "Authorization: Bearer <token>"
```

---

## Error Handling

All endpoints return errors in the following format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-01-20T12:00:00Z"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `LABEL_STUDIO_UNAVAILABLE` | Label Studio service is not available |
| `PROJECT_NOT_FOUND` | The specified project does not exist |
| `AUTHENTICATION_FAILED` | Authentication with Label Studio failed |
| `INVALID_REQUEST` | Request parameters are invalid |
| `IMPORT_FAILED` | Task import failed |

### Retry Logic

The API implements automatic retry with exponential backoff for transient errors:

- **Max Attempts:** 3
- **Base Delay:** 1 second
- **Max Delay:** 30 seconds
- **Backoff Multiplier:** 2.0

Retryable errors:
- Network timeouts
- Connection errors
- 503 Service Unavailable

Non-retryable errors:
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found

---

## Language Support

### Supported Languages

| Code | Language |
|------|----------|
| `zh` | Chinese (Simplified) |
| `en` | English |

### Language Synchronization

The system synchronizes language settings between SuperInsight and Label Studio:

1. **URL Parameter:** Language is passed via `?lang=zh` or `?lang=en` in the URL
2. **PostMessage:** Language changes are communicated to Label Studio iframe via postMessage
3. **Iframe Reload:** When language changes, the iframe is reloaded to apply the new language

### Default Language

The default language is Chinese (`zh`). This can be configured in:
- Docker Compose: `LANGUAGE_CODE=zh-hans`
- Frontend: `DEFAULT_LANGUAGE` constant

---

## Integration Examples

### Starting Annotation Workflow

```typescript
// 1. Validate project exists
const validation = await labelStudioService.validateProject(projectId);

if (!validation.exists) {
  // 2. Create project if needed
  const result = await labelStudioService.ensureProject({
    task_id: taskId,
    task_name: taskName,
    annotation_type: 'sentiment',
  });
  projectId = result.project_id;
}

// 3. Navigate to annotation page
navigate(`/tasks/${taskId}/annotate`);
```

### Opening in New Window

```typescript
// 1. Get authenticated URL with language
const authUrl = await labelStudioService.getAuthUrl(projectId, language);

// 2. Open in new window
window.open(authUrl.url, '_blank', 'noopener,noreferrer');
```

### Embedding Label Studio

```tsx
<LabelStudioEmbed
  projectId={projectId}
  taskId={taskId}
  baseUrl="/label-studio"
  onAnnotationCreate={handleAnnotationCreate}
  onTaskComplete={handleTaskComplete}
/>
```

---

## Performance Considerations

### Response Times

| Operation | Target | Max |
|-----------|--------|-----|
| Validate Project | < 500ms | 2s |
| Ensure Project | < 3s | 10s |
| Import Tasks (100) | < 5s | 30s |
| Get Auth URL | < 200ms | 1s |

### Caching

- Project validation results are cached for 30 seconds
- Auth URLs are valid for 1 hour

---

## Changelog

### v1.0.0 (2026-01-26)

- Initial release
- Added `POST /projects/ensure` endpoint
- Added `GET /projects/{id}/validate` endpoint
- Added `POST /projects/{id}/import-tasks` endpoint
- Added `GET /projects/{id}/auth-url` endpoint with language support
- Implemented retry logic with exponential backoff
- Added language synchronization support
