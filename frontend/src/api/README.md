# Data Lifecycle API

Frontend API integration for data lifecycle transfer operations.

## Overview

This module provides TypeScript functions for interacting with the data lifecycle transfer backend API. It includes:

- Data transfer operations (single and batch)
- Permission checking
- Approval management
- Error handling with retry logic
- Internationalization support

## Installation

```typescript
import {
  transferDataAPI,
  batchTransferDataAPI,
  checkPermissionAPI,
  listApprovalsAPI,
  approveTransferAPI,
} from '@/api/dataLifecycleAPI';
```

## API Functions

### transferDataAPI

Transfer data to the data lifecycle system.

```typescript
const result = await transferDataAPI({
  source_type: 'structuring',
  source_id: 'task-123',
  target_state: 'temp_stored',
  data_attributes: {
    category: 'product_info',
    tags: ['ecommerce', 'products'],
    quality_score: 0.95,
    description: 'Product catalog data',
  },
  records: [
    {
      id: 'record-1',
      content: { name: 'Product A', price: 99.99 },
      metadata: { source: 'api' },
    },
  ],
});

if (result.approval_required) {
  console.log('Approval needed:', result.approval_id);
} else {
  console.log('Transferred:', result.transferred_count, 'records');
}
```

### batchTransferDataAPI

Batch transfer multiple data sources.

```typescript
const results = await batchTransferDataAPI([
  {
    source_type: 'structuring',
    source_id: 'task-1',
    target_state: 'temp_stored',
    data_attributes: { category: 'test', tags: [] },
    records: [...],
  },
  {
    source_type: 'augmentation',
    source_id: 'job-2',
    target_state: 'in_sample_library',
    data_attributes: { category: 'enhanced', tags: [] },
    records: [...],
  },
]);

console.log(`${results.successful_transfers}/${results.total_transfers} succeeded`);
```

### checkPermissionAPI

Check user permissions for operations.

```typescript
const permission = await checkPermissionAPI({
  source_type: 'structuring',
  target_state: 'in_sample_library',
});

if (permission.allowed) {
  if (permission.requires_approval) {
    console.log('Operation requires approval');
  } else {
    console.log('Operation allowed without approval');
  }
} else {
  console.log('Permission denied:', permission.reason);
}
```

### listApprovalsAPI

List approval requests.

```typescript
const approvals = await listApprovalsAPI({
  status: 'pending',
  limit: 20,
  offset: 0,
});

console.log(`Found ${approvals.total} pending approvals`);
approvals.approvals.forEach(approval => {
  console.log(`- ${approval.id}: ${approval.status}`);
});
```

### approveTransferAPI

Approve or reject a transfer request.

```typescript
// Approve
const result = await approveTransferAPI(
  'approval-123',
  true,
  'Data quality looks good'
);

// Reject
const result = await approveTransferAPI(
  'approval-456',
  false,
  'Data quality issues found'
);
```

## Types

### DataTransferRequest

```typescript
interface DataTransferRequest {
  source_type: 'structuring' | 'augmentation' | 'sync' | 'annotation' | 'ai_assistant' | 'manual';
  source_id: string;
  target_state: 'temp_stored' | 'in_sample_library' | 'annotation_pending';
  data_attributes: DataAttributes;
  records: TransferRecord[];
  request_approval?: boolean;
}
```

### DataAttributes

```typescript
interface DataAttributes {
  category: string;
  tags: string[];
  quality_score?: number;
  description?: string;
}
```

### TransferRecord

```typescript
interface TransferRecord {
  id: string;
  content: Record<string, any>;
  metadata?: Record<string, any>;
}
```

### TransferResponse

```typescript
interface TransferResponse {
  success: boolean;
  transferred_count?: number;
  lifecycle_ids?: string[];
  target_state?: string;
  message: string;
  navigation_url?: string;
  approval_required?: boolean;
  approval_id?: string;
  estimated_approval_time?: string;
}
```

## Error Handling

All API functions throw `DataTransferError` on failure:

```typescript
try {
  await transferDataAPI(request);
} catch (error) {
  if (error instanceof DataTransferError) {
    console.error('Transfer failed:', error.message);
    console.error('Error code:', error.code);
    console.error('Status:', error.status);
    console.error('Details:', error.details);
  }
}
```

### Error Codes

- `PERMISSION_DENIED`: User lacks required permissions
- `INVALID_SOURCE`: Source data not found or invalid
- `NETWORK_ERROR`: Network connectivity issue
- `UNKNOWN_ERROR`: Unexpected error

## Retry Logic

Network errors are automatically retried with exponential backoff:

- Max retries: 3
- Backoff delays: 100ms, 200ms, 400ms
- Client errors (4xx) are not retried (except 408 timeout)
- Server errors (5xx) are retried once

## Internationalization

All API calls include the `Accept-Language` header based on the current locale:

- `zh-CN` for Chinese
- `en-US` for English

The locale is read from `localStorage.getItem('locale')`.

## Timeouts

- Single transfer: 30 seconds
- Batch transfer: 60 seconds
- Other operations: Default (10 seconds)

## Testing

Run tests with:

```bash
npm test -- src/api/__tests__/dataLifecycleAPI.test.ts
```

## Backend API Endpoints

- `POST /api/data-lifecycle/transfer` - Transfer data
- `POST /api/data-lifecycle/batch-transfer` - Batch transfer
- `GET /api/data-lifecycle/permissions/check` - Check permissions
- `GET /api/data-lifecycle/approvals` - List approvals
- `POST /api/data-lifecycle/approvals/{id}/approve` - Approve/reject

## Related Files

- Implementation: `frontend/src/api/dataLifecycleAPI.ts`
- Tests: `frontend/src/api/__tests__/dataLifecycleAPI.test.ts`
- API Client: `frontend/src/services/api/client.ts`
- Backend API: `src/api/data_lifecycle_api.py`
