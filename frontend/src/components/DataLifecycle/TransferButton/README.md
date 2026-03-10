# TransferButton Component

A reusable button component for triggering data transfer operations in the data lifecycle system.

## Features

- ✅ Automatic permission checking on mount
- ✅ Disabled state handling with tooltips
- ✅ Loading state during permission checks
- ✅ Internationalization support (i18n)
- ✅ Integration with TransferModal (task 2.2)

## Usage

```tsx
import { TransferButton } from '@/components/DataLifecycle/TransferButton';

function MyComponent() {
  const records = [
    {
      id: 'record-1',
      content: { field1: 'value1' },
      metadata: { source: 'test' },
    },
  ];

  const handleTransferComplete = (result) => {
    console.log('Transfer completed:', result);
    // Refresh data or navigate
  };

  return (
    <TransferButton
      sourceType="structuring"
      sourceId="task-123"
      records={records}
      onTransferComplete={handleTransferComplete}
    />
  );
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `sourceType` | `'structuring' \| 'augmentation' \| 'sync' \| 'annotation' \| 'ai_assistant' \| 'manual'` | Yes | Source type of the data |
| `sourceId` | `string` | Yes | Unique identifier of the source |
| `records` | `TransferRecord[]` | Yes | Array of records to transfer |
| `disabled` | `boolean` | No | Optional disabled state |
| `onTransferComplete` | `(result: any) => void` | No | Callback after successful transfer |

## Disabled States

The button will be automatically disabled when:

1. **No records selected**: `records.length === 0`
2. **User lacks permissions**: Permission check returns `allowed: false`
3. **External disabled prop**: `disabled={true}`

## Permission Checking

The component automatically checks permissions on mount using the `checkPermissionAPI`:

```typescript
const permissionResult = await checkPermissionAPI({
  source_type: sourceType,
  operation: 'transfer',
});
```

## Internationalization

All user-visible text uses the `dataLifecycle` namespace:

- `transfer.button`: Button text
- `transfer.validation.minRecords`: No records error
- `transfer.messages.permissionDenied`: Permission denied message
- `common.messages.networkError`: Network error message

## Testing

Run tests with:

```bash
npm test -- TransferButton.test.tsx
```

## Implementation Status

- [x] Task 2.1.1: Create TransferButton component
- [x] Task 2.1.2: Implement button click to open modal logic (placeholder)
- [x] Task 2.1.3: Integrate i18n (useTranslation hook)
- [x] Task 2.1.4: Implement disabled state handling

## Next Steps

Task 2.2 will implement the TransferModal component that this button opens.
