# Frontend Coding Standards

This document outlines the coding standards and best practices for the SuperInsight frontend codebase.

## Table of Contents

1. [TypeScript Guidelines](#typescript-guidelines)
2. [React Component Patterns](#react-component-patterns)
3. [State Management](#state-management)
4. [Error Handling](#error-handling)
5. [Testing Standards](#testing-standards)
6. [Performance Guidelines](#performance-guidelines)
7. [Accessibility Standards](#accessibility-standards)
8. [File Organization](#file-organization)

---

## TypeScript Guidelines

### Type Safety

- **Always use explicit types** for function parameters and return values
- **Avoid `any` type** - use `unknown` when type is truly unknown
- **Use type guards** for runtime type checking
- **Prefer interfaces** for object shapes, types for unions/intersections

```typescript
// ✅ Good
interface User {
  id: string;
  name: string;
  email: string;
}

function getUser(id: string): Promise<User> {
  return api.get(`/users/${id}`);
}

// ❌ Bad
function getUser(id: any): any {
  return api.get(`/users/${id}`);
}
```

### Type Imports

Use type-only imports for types to improve build performance:

```typescript
// ✅ Good
import type { User, UserRole } from '@/types/user';
import { useState, useEffect } from 'react';

// ❌ Bad
import { User, UserRole } from '@/types/user';
```

### Utility Types

Use built-in utility types and custom utilities from `@/utils/codeQuality`:

```typescript
import { isDefined, assertDefined, RequireKeys } from '@/utils/codeQuality';

// Type guards
if (isDefined(user)) {
  console.log(user.name); // user is typed correctly
}

// Assertions
assertDefined(config, 'Configuration is required');

// Utility types
type CreateUserInput = RequireKeys<User, 'name' | 'email'>;
```

---

## React Component Patterns

### Component Structure

Follow this structure for components:

```typescript
/**
 * ComponentName
 * 
 * Brief description of what the component does.
 * 
 * @example
 * <ComponentName prop1="value" onAction={handleAction} />
 */

import React, { type FC, useState, useCallback, useMemo } from 'react';
import type { ComponentNameProps } from './types';
import styles from './ComponentName.module.scss';

export const ComponentName: FC<ComponentNameProps> = ({
  prop1,
  prop2,
  onAction,
}) => {
  // 1. State declarations
  const [state, setState] = useState<StateType>(initialState);

  // 2. Derived state (useMemo)
  const derivedValue = useMemo(() => {
    return computeValue(prop1, state);
  }, [prop1, state]);

  // 3. Callbacks (useCallback)
  const handleClick = useCallback(() => {
    onAction?.(state);
  }, [onAction, state]);

  // 4. Effects (useEffect)
  // ...

  // 5. Render
  return (
    <div className={styles.container}>
      {/* Component content */}
    </div>
  );
};

ComponentName.displayName = 'ComponentName';

export default ComponentName;
```

### Props Interface

Define props interfaces with JSDoc comments:

```typescript
/**
 * Props for the UserCard component
 */
export interface UserCardProps {
  /** The user to display */
  user: User;
  /** Whether the card is in compact mode */
  compact?: boolean;
  /** Callback when the card is clicked */
  onClick?: (user: User) => void;
  /** Additional CSS class name */
  className?: string;
}
```

### Higher-Order Components

Use HOCs from `@/utils/componentPatterns`:

```typescript
import { withDataState, withLoading } from '@/utils/componentPatterns';

// Wrap component with data state handling
const UserListWithState = withDataState(UserList);

// Usage
<UserListWithState
  isLoading={isLoading}
  error={error}
  isEmpty={users.length === 0}
  users={users}
/>
```

### Custom Hooks

Extract reusable logic into custom hooks:

```typescript
/**
 * useUserData Hook
 * 
 * Fetches and manages user data with loading and error states.
 * 
 * @param userId - The user ID to fetch
 * @returns User data state and actions
 */
export function useUserData(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchUser(userId);
      setUser(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { user, isLoading, error, refetch };
}
```

---

## State Management

### Zustand Store Pattern

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UserStore {
  // State
  user: User | null;
  isAuthenticated: boolean;
  
  // Actions
  setUser: (user: User) => void;
  logout: () => void;
}

export const useUserStore = create<UserStore>()(
  devtools(
    persist(
      (set) => ({
        // Initial state
        user: null,
        isAuthenticated: false,
        
        // Actions
        setUser: (user) => set({ user, isAuthenticated: true }),
        logout: () => set({ user: null, isAuthenticated: false }),
      }),
      {
        name: 'user-storage',
        partialize: (state) => ({ user: state.user }),
      }
    ),
    { name: 'UserStore' }
  )
);
```

### Selector Pattern

Use selectors to prevent unnecessary re-renders:

```typescript
import { useShallow } from 'zustand/react/shallow';

// ✅ Good - Only re-renders when selected values change
const { user, isAuthenticated } = useUserStore(
  useShallow((state) => ({
    user: state.user,
    isAuthenticated: state.isAuthenticated,
  }))
);

// ❌ Bad - Re-renders on any store change
const store = useUserStore();
```

---

## Error Handling

### Use Error Handler Hook

```typescript
import { useErrorHandler } from '@/hooks/useErrorHandler';

const MyComponent = () => {
  const { handleError, withErrorHandling } = useErrorHandler();

  const fetchData = async () => {
    const result = await withErrorHandling(
      () => api.getData(),
      {
        showNotification: true,
        autoRetry: true,
        onError: (error) => {
          // Custom error handling
        },
      }
    );
    
    if (result) {
      // Handle success
    }
  };
};
```

### Error Boundaries

Wrap components with error boundaries:

```typescript
import { EnhancedErrorBoundary } from '@/components/Common/ErrorHandling';

<EnhancedErrorBoundary
  level="component"
  onError={(error, errorInfo) => {
    // Log to monitoring service
  }}
>
  <MyComponent />
</EnhancedErrorBoundary>
```

---

## Testing Standards

### Test File Structure

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  // Setup
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Group related tests
  describe('rendering', () => {
    it('renders with default props', () => {
      render(<MyComponent />);
      expect(screen.getByRole('button')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onClick when clicked', () => {
      const onClick = vi.fn();
      render(<MyComponent onClick={onClick} />);
      
      fireEvent.click(screen.getByRole('button'));
      
      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });
});
```

### Test Naming

Use descriptive test names:

```typescript
// ✅ Good
it('displays error message when form validation fails', () => {});
it('disables submit button while loading', () => {});

// ❌ Bad
it('works', () => {});
it('test 1', () => {});
```

---

## Performance Guidelines

### Memoization

Use memoization appropriately:

```typescript
// Memoize expensive computations
const sortedItems = useMemo(() => {
  return items.sort((a, b) => a.name.localeCompare(b.name));
}, [items]);

// Memoize callbacks passed to children
const handleClick = useCallback(() => {
  onItemClick(item.id);
}, [onItemClick, item.id]);

// Memoize components that receive stable props
const MemoizedChild = memo(ChildComponent);
```

### Code Splitting

Use lazy loading for routes and large components:

```typescript
import { lazyWithFallback } from '@/utils/componentPatterns';

const Dashboard = lazyWithFallback(
  () => import('@/pages/Dashboard'),
  <LoadingSpinner text="Loading dashboard..." />
);
```

### Virtual Lists

Use virtual scrolling for large lists:

```typescript
import { VirtualList } from '@/components/Common';

<VirtualList
  items={largeDataset}
  itemHeight={50}
  renderItem={(item) => <ListItem item={item} />}
/>
```

---

## Accessibility Standards

### ARIA Attributes

```typescript
// ✅ Good
<button
  aria-label="Close dialog"
  aria-pressed={isPressed}
  onClick={handleClose}
>
  <CloseIcon />
</button>

// ❌ Bad
<div onClick={handleClose}>
  <CloseIcon />
</div>
```

### Keyboard Navigation

```typescript
const handleKeyDown = (event: React.KeyboardEvent) => {
  switch (event.key) {
    case 'Enter':
    case ' ':
      handleSelect();
      break;
    case 'Escape':
      handleClose();
      break;
  }
};
```

### Focus Management

```typescript
import { FocusTrap } from '@/components/Common/Accessibility';

<FocusTrap active={isModalOpen}>
  <Modal>
    {/* Modal content */}
  </Modal>
</FocusTrap>
```

---

## File Organization

### Directory Structure

```
src/
├── components/
│   ├── Common/           # Shared components
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.module.scss
│   │   │   ├── Button.test.tsx
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   └── index.ts
│   └── Feature/          # Feature-specific components
├── hooks/                # Custom hooks
├── pages/                # Page components
├── services/             # API services
├── stores/               # Zustand stores
├── types/                # TypeScript types
└── utils/                # Utility functions
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `UserCard.tsx` |
| Hooks | camelCase with `use` prefix | `useUserData.ts` |
| Utilities | camelCase | `formatDate.ts` |
| Types | PascalCase | `UserTypes.ts` |
| Constants | UPPER_SNAKE_CASE | `API_ENDPOINTS.ts` |
| CSS Modules | PascalCase | `UserCard.module.scss` |

### Import Order

```typescript
// 1. React and external libraries
import React, { useState, useEffect } from 'react';
import { Button, Card } from 'antd';

// 2. Internal absolute imports
import { useAuth } from '@/hooks/useAuth';
import type { User } from '@/types/user';

// 3. Relative imports
import { UserAvatar } from './UserAvatar';
import styles from './UserCard.module.scss';
```

---

## Code Review Checklist

Before submitting code for review, ensure:

- [ ] TypeScript types are properly defined
- [ ] Components have displayName set
- [ ] Props interfaces have JSDoc comments
- [ ] Error handling is implemented
- [ ] Loading states are handled
- [ ] Accessibility attributes are added
- [ ] Tests are written and passing
- [ ] No console.log statements (except in development)
- [ ] No unused imports or variables
- [ ] Code follows naming conventions
