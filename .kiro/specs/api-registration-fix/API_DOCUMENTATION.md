# SuperInsight API Documentation

## Overview

This document provides comprehensive documentation for the 12 high-priority API endpoints that were registered as part of the API Registration Fix. These APIs cover License Management, Quality Management, Data Augmentation, Security, and Versioning modules.

**Base URL**: `http://localhost:8000`

**Authentication**: Most endpoints require JWT authentication. Include the token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Table of Contents

1. [License Module](#1-license-module)
   - [License Management API](#11-license-management-api)
   - [Usage Monitoring API](#12-usage-monitoring-api)
   - [Activation API](#13-activation-api)
2. [Quality Module](#2-quality-module)
   - [Quality Rules API](#21-quality-rules-api)
   - [Quality Reports API](#22-quality-reports-api)
   - [Quality Workflow API](#23-quality-workflow-api)
3. [Augmentation Module](#3-augmentation-module)
4. [Security Module](#4-security-module)
   - [Sessions API](#41-sessions-api)
   - [SSO API](#42-sso-api)
   - [RBAC API](#43-rbac-api)
   - [Data Permissions API](#44-data-permissions-api)
5. [Versioning Module](#5-versioning-module)

---

## 1. License Module

### 1.1 License Management API

**Base Path**: `/api/v1/license`

#### Get License Status

```bash
curl -X GET "http://localhost:8000/api/v1/license/status" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "license_id": "uuid",
  "license_key": "XXXX-XXXX-XXXX",
  "license_type": "enterprise",
  "status": "active",
  "validity_status": "active",
  "days_remaining": 365,
  "features": ["feature1", "feature2"],
  "limits": {
    "max_concurrent_users": 100,
    "max_cpu_cores": 16,
    "max_storage_gb": 1000,
    "max_projects": 50,
    "max_datasets": 200
  },
  "warnings": []
}
```

#### Create License

```bash
curl -X POST "http://localhost:8000/api/v1/license" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "license_type": "enterprise",
    "features": ["ai_annotation", "quality_management"],
    "max_concurrent_users": 50
  }'
```

#### List Licenses

```bash
curl -X GET "http://localhost:8000/api/v1/license?status=active&limit=10" \
  -H "Authorization: Bearer <token>"
```

#### Renew License

```bash
curl -X POST "http://localhost:8000/api/v1/license/{license_id}/renew" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"new_end_date": "2027-01-01T00:00:00Z"}'
```

#### Validate License

```bash
curl -X GET "http://localhost:8000/api/v1/license/validate?hardware_id=abc123" \
  -H "Authorization: Bearer <token>"
```

---

### 1.2 Usage Monitoring API

**Base Path**: `/api/v1/usage`

#### Get Concurrent Usage

```bash
curl -X GET "http://localhost:8000/api/v1/usage/concurrent" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "current_users": 25,
  "max_users": 100,
  "utilization_percent": 25.0,
  "active_sessions": [...]
}
```

#### Register Session

```bash
curl -X POST "http://localhost:8000/api/v1/usage/sessions/register" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "session_id": "sess456"
  }'
```

#### Get Resource Usage

```bash
curl -X GET "http://localhost:8000/api/v1/usage/resources" \
  -H "Authorization: Bearer <token>"
```

#### Generate Usage Report

```bash
curl -X POST "http://localhost:8000/api/v1/usage/report" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z"
  }'
```

---

### 1.3 Activation API

**Base Path**: `/api/v1/activation`

#### Activate License Online

```bash
curl -X POST "http://localhost:8000/api/v1/activation/activate" \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "hardware_fingerprint": "optional_fingerprint"
  }'
```

**Response**:
```json
{
  "success": true,
  "license": {...},
  "message": "License activated successfully"
}
```

#### Get Hardware Fingerprint

```bash
curl -X GET "http://localhost:8000/api/v1/activation/fingerprint"
```

**Response**:
```json
{
  "fingerprint": "abc123def456...",
  "message": "Use this fingerprint for license activation"
}
```

#### Offline Activation Request

```bash
curl -X POST "http://localhost:8000/api/v1/activation/offline/request?license_key=XXXX-XXXX"
```

#### Verify Activation

```bash
curl -X GET "http://localhost:8000/api/v1/activation/verify/{license_id}" \
  -H "Authorization: Bearer <token>"
```

---

## 2. Quality Module

### 2.1 Quality Rules API

**Base Path**: `/api/v1/quality-rules`

#### Create Quality Rule

```bash
curl -X POST "http://localhost:8000/api/v1/quality-rules" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Text Length Check",
    "rule_type": "builtin",
    "config": {"min_length": 10, "max_length": 1000},
    "severity": "medium",
    "priority": 1,
    "project_id": "project123"
  }'
```

#### List Rules

```bash
curl -X GET "http://localhost:8000/api/v1/quality-rules?project_id=project123&enabled_only=true" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "rules": [
    {
      "id": "rule1",
      "name": "Text Length Check",
      "rule_type": "builtin",
      "severity": "medium",
      "enabled": true,
      "version": 1
    }
  ],
  "total": 1
}
```

#### Update Rule

```bash
curl -X PUT "http://localhost:8000/api/v1/quality-rules/{rule_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

#### Create from Template

```bash
curl -X POST "http://localhost:8000/api/v1/quality-rules/from-template" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "nlp_basic",
    "project_id": "project123"
  }'
```

#### List Templates

```bash
curl -X GET "http://localhost:8000/api/v1/quality-rules/templates/list?category=nlp" \
  -H "Authorization: Bearer <token>"
```

---

### 2.2 Quality Reports API

**Base Path**: `/api/v1/quality-reports`

#### Generate Project Report

```bash
curl -X POST "http://localhost:8000/api/v1/quality-reports/project" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project123",
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z"
  }'
```

**Response**:
```json
{
  "id": "report123",
  "project_id": "project123",
  "total_annotations": 1500,
  "average_scores": {"accuracy": 0.95, "completeness": 0.88},
  "passed_count": 1400,
  "failed_count": 100,
  "generated_at": "2025-01-20T10:00:00Z"
}
```

#### Generate Annotator Ranking

```bash
curl -X POST "http://localhost:8000/api/v1/quality-reports/annotator-ranking" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project123",
    "period": "month"
  }'
```

#### Generate Trend Report

```bash
curl -X POST "http://localhost:8000/api/v1/quality-reports/trend" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project123",
    "granularity": "day"
  }'
```

#### Export Report

```bash
curl -X POST "http://localhost:8000/api/v1/quality-reports/export" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "project",
    "project_id": "project123",
    "format": "pdf",
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z"
  }' \
  --output report.pdf
```

#### Schedule Report

```bash
curl -X POST "http://localhost:8000/api/v1/quality-reports/schedule" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project123",
    "report_type": "project",
    "name": "Weekly Quality Report",
    "schedule": "0 9 * * 1",
    "recipients": ["admin@example.com"],
    "export_format": "pdf"
  }'
```

---

### 2.3 Quality Workflow API

**Base Path**: `/api/v1/quality-workflow`

#### Configure Workflow

```bash
curl -X POST "http://localhost:8000/api/v1/quality-workflow/configure" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project123",
    "stages": ["identify", "assign", "improve", "review", "verify"],
    "auto_create_task": true
  }'
```

#### Create Improvement Task

```bash
curl -X POST "http://localhost:8000/api/v1/quality-workflow/tasks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "annotation_id": "ann123",
    "issues": [
      {
        "rule_id": "rule1",
        "rule_name": "Text Length",
        "severity": "high",
        "message": "Text too short"
      }
    ],
    "assignee_id": "user456"
  }'
```

#### List Tasks

```bash
curl -X GET "http://localhost:8000/api/v1/quality-workflow/tasks?project_id=project123&status=pending" \
  -H "Authorization: Bearer <token>"
```

#### Submit Improvement

```bash
curl -X POST "http://localhost:8000/api/v1/quality-workflow/tasks/{task_id}/submit" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "improved_data": {"text": "Improved annotation text..."}
  }'
```

#### Review Improvement

```bash
curl -X POST "http://localhost:8000/api/v1/quality-workflow/tasks/{task_id}/review" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "reviewer123",
    "approved": true,
    "comments": "Good improvement"
  }'
```

---

## 3. Augmentation Module

**Base Path**: `/api/v1/augmentation`

#### Get Samples

```bash
curl -X GET "http://localhost:8000/api/v1/augmentation/samples?skip=0&limit=100" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
[
  {
    "id": "sample1",
    "name": "Customer Reviews Dataset",
    "type": "text",
    "status": "completed",
    "original_count": 1000,
    "augmented_count": 3500,
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T12:30:00Z"
  }
]
```

#### Create Sample

```bash
curl -X POST "http://localhost:8000/api/v1/augmentation/samples" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Dataset",
    "type": "text",
    "description": "Sample dataset for augmentation"
  }'
```

#### Upload Sample Data

```bash
curl -X POST "http://localhost:8000/api/v1/augmentation/samples/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@data.csv"
```

#### Get Configuration

```bash
curl -X GET "http://localhost:8000/api/v1/augmentation/config" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "text_augmentation": {
    "enabled": true,
    "synonym_replacement": true,
    "random_insertion": true,
    "augmentation_ratio": 1.5
  },
  "image_augmentation": {
    "enabled": true,
    "rotation": true,
    "flip": true,
    "augmentation_ratio": 2.0
  },
  "general": {
    "max_augmentations_per_sample": 5,
    "preserve_original": true,
    "quality_threshold": 0.8
  }
}
```

#### Update Configuration

```bash
curl -X PUT "http://localhost:8000/api/v1/augmentation/config" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text_augmentation": {"augmentation_ratio": 2.0},
    "general": {"max_augmentations_per_sample": 10}
  }'
```

---

## 4. Security Module

### 4.1 Sessions API

**Base Path**: `/api/v1/sessions`

#### Create Session

```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "timeout": 3600
  }'
```

#### List Sessions

```bash
curl -X GET "http://localhost:8000/api/v1/sessions?user_id=user123" \
  -H "Authorization: Bearer <token>"
```

#### Validate Session

```bash
curl -X POST "http://localhost:8000/api/v1/sessions/{session_id}/validate" \
  -H "Authorization: Bearer <token>"
```

#### Force Logout User

```bash
curl -X POST "http://localhost:8000/api/v1/sessions/force-logout/user123?admin_user_id=admin1" \
  -H "Authorization: Bearer <token>"
```

#### Get Session Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/sessions/stats/overview" \
  -H "Authorization: Bearer <token>"
```

---

### 4.2 SSO API

**Base Path**: `/api/v1/sso`

#### Create SSO Provider

```bash
curl -X POST "http://localhost:8000/api/v1/sso/providers" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "corporate-okta",
    "protocol": "oidc",
    "config": {
      "client_id": "your_client_id",
      "client_secret": "your_client_secret",
      "authorization_url": "https://your-domain.okta.com/oauth2/v1/authorize",
      "token_url": "https://your-domain.okta.com/oauth2/v1/token",
      "userinfo_url": "https://your-domain.okta.com/oauth2/v1/userinfo",
      "scopes": ["openid", "profile", "email"]
    },
    "enabled": true
  }'
```

#### List SSO Providers

```bash
curl -X GET "http://localhost:8000/api/v1/sso/providers?enabled_only=true" \
  -H "Authorization: Bearer <token>"
```

#### Initiate SSO Login

```bash
curl -X GET "http://localhost:8000/api/v1/sso/login/corporate-okta?redirect_uri=https://app.example.com/callback"
```

**Response**:
```json
{
  "redirect_url": "https://your-domain.okta.com/oauth2/v1/authorize?...",
  "state": "random_state_string",
  "provider_name": "corporate-okta"
}
```

#### Test SSO Provider

```bash
curl -X POST "http://localhost:8000/api/v1/sso/providers/corporate-okta/test" \
  -H "Authorization: Bearer <token>"
```

---

### 4.3 RBAC API

**Base Path**: `/api/v1/rbac`

#### Create Role

```bash
curl -X POST "http://localhost:8000/api/v1/rbac/roles" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "project_manager",
    "description": "Can manage projects and view reports",
    "permissions": [
      {"resource": "projects/*", "action": "*"},
      {"resource": "reports/*", "action": "read"}
    ]
  }'
```

#### List Roles

```bash
curl -X GET "http://localhost:8000/api/v1/rbac/roles?limit=50" \
  -H "Authorization: Bearer <token>"
```

#### Assign Role to User

```bash
curl -X POST "http://localhost:8000/api/v1/rbac/users/user123/roles" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": "role456",
    "expires_at": "2026-01-01T00:00:00Z"
  }'
```

#### Check Permission

```bash
curl -X POST "http://localhost:8000/api/v1/rbac/check" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "resource": "projects/proj456",
    "action": "write"
  }'
```

**Response**:
```json
{
  "allowed": true,
  "reason": "Permission granted via role: project_manager",
  "checked_at": "2025-01-20T10:00:00Z"
}
```

#### Get User Permissions

```bash
curl -X GET "http://localhost:8000/api/v1/rbac/users/user123/permissions" \
  -H "Authorization: Bearer <token>"
```

---

### 4.4 Data Permissions API

**Base Path**: `/api/v1/data-permissions`

#### Check Permission

```bash
curl -X POST "http://localhost:8000/api/v1/data-permissions/check" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "resource_id": "dataset456",
    "action": "read"
  }'
```

#### Grant Permission

```bash
curl -X POST "http://localhost:8000/api/v1/data-permissions/grant" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "resource_type": "dataset",
    "resource_id": "dataset456",
    "action": "read"
  }'
```

#### Grant Temporary Permission

```bash
curl -X POST "http://localhost:8000/api/v1/data-permissions/grant/temporary?user_id=user123&resource=dataset456&action=read&expires_at=2025-02-01T00:00:00Z" \
  -H "Authorization: Bearer <token>"
```

#### Revoke Permission

```bash
curl -X POST "http://localhost:8000/api/v1/data-permissions/revoke" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "resource_type": "dataset",
    "resource_id": "dataset456",
    "action": "read"
  }'
```

#### Get User Permissions

```bash
curl -X GET "http://localhost:8000/api/v1/data-permissions/user/user123?include_role_permissions=true" \
  -H "Authorization: Bearer <token>"
```

---

## 5. Versioning Module

**Base Path**: `/api/v1/versioning`

#### Create Version

```bash
curl -X POST "http://localhost:8000/api/v1/versioning/annotation/ann123?user_id=user456" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"text": "Updated annotation text", "labels": ["label1"]},
    "message": "Fixed typo in annotation",
    "version_type": "patch"
  }'
```

**Response**:
```json
{
  "success": true,
  "version": {
    "id": "ver123",
    "version": "1.0.1",
    "entity_type": "annotation",
    "entity_id": "ann123",
    "created_at": "2025-01-20T10:00:00Z"
  },
  "message": "Created version 1.0.1"
}
```

#### Get Version History

```bash
curl -X GET "http://localhost:8000/api/v1/versioning/annotation/ann123?limit=50" \
  -H "Authorization: Bearer <token>"
```

#### Get Specific Version

```bash
curl -X GET "http://localhost:8000/api/v1/versioning/annotation/ann123/1.0.0" \
  -H "Authorization: Bearer <token>"
```

#### Rollback Version

```bash
curl -X POST "http://localhost:8000/api/v1/versioning/annotation/ann123/rollback?user_id=user456" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"target_version": "1.0.0"}'
```

#### Get Changes

```bash
curl -X GET "http://localhost:8000/api/v1/versioning/changes?entity_type=annotation&limit=100" \
  -H "Authorization: Bearer <token>"
```

#### Compute Diff

```bash
curl -X POST "http://localhost:8000/api/v1/versioning/diff" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "old_data": {"text": "Original text"},
    "new_data": {"text": "Updated text"},
    "diff_level": "field"
  }'
```

#### Three-Way Merge

```bash
curl -X POST "http://localhost:8000/api/v1/versioning/merge" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "base": {"text": "Base text", "status": "draft"},
    "ours": {"text": "Our changes", "status": "draft"},
    "theirs": {"text": "Base text", "status": "review"}
  }'
```

---

## Error Handling

All APIs return standard HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

**Error Response Format**:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

API requests are rate-limited to prevent abuse:
- **Standard endpoints**: 100 requests/minute
- **Report generation**: 10 requests/minute
- **Bulk operations**: 20 requests/minute

---

## Pagination

List endpoints support pagination via query parameters:
- `skip` or `offset`: Number of items to skip (default: 0)
- `limit`: Maximum items to return (default: 100, max: 1000)

---

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

**Document Version**: 1.0  
**Created**: 2026-01-22  
**Validates**: Requirements 3.3 - 可维护性要求
