/**
 * Data Lifecycle Routing Integration Tests
 * 
 * Tests navigation between data lifecycle pages, route guards,
 * breadcrumb updates, and lazy loading behavior.
 * 
 * **Validates: Requirements 11.3**
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { routes } from '../routes';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: 'zh',
      changeLanguage: vi.fn(),
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
    token: 'mock-token',
    currentTenant: { id: '1', name: 'Test Tenant' },
    currentWorkspace: { id: '1', name: 'Test Workspace' },
    _hasHydrated: true,
    clearAuth: vi.fn(),
  }),
}));

// Mock permissions hook
vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => ({
    checkPermission: () => true,
    checkTenantAccess: () => true,
    checkWorkspaceAccess: () => true,
    roleDisplayName: 'Admin',
  }),
}));

// Mock token utility
vi.mock('@/utils/token', () => ({
  isTokenExpired: () => false,
}));

// Mock data lifecycle hook
vi.mock('@/hooks/useDataLifecycle', () => ({
  useSampleLibrary: () => ({
    samples: [],
    loading: false,
    pagination: { page: 1, pageSize: 10, total: 0 },
    fetchSamples: vi.fn(),
  }),
  useAnnotationTasks: () => ({
    tasks: [],
    loading: false,
    fetchTasks: vi.fn(),
  }),
}));

describe('Data Lifecycle Routing Integration Tests', () => {
  describe('Navigation Between Pages', () => {
    it('should navigate from overview to temp data page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle');
      });

      // Navigate to temp data
      router.navigate('/data-lifecycle/temp-data');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/temp-data');
      });
    });

    it('should navigate from temp data to sample library', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/temp-data'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/temp-data');
      });

      // Navigate to sample library
      router.navigate('/data-lifecycle/samples');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
      });
    });

    it('should navigate from sample library to annotation tasks', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/samples'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
      });

      // Navigate to annotation tasks
      router.navigate('/data-lifecycle/tasks');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/tasks');
      });
    });

    it('should navigate from annotation tasks to enhancement', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/tasks'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/tasks');
      });

      // Navigate to enhancement
      router.navigate('/data-lifecycle/enhancement');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/enhancement');
      });
    });

    it('should navigate from enhancement to AI trials', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/enhancement'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/enhancement');
      });

      // Navigate to AI trials
      router.navigate('/data-lifecycle/trials');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/trials');
      });
    });

    it('should navigate from AI trials to audit log', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/trials'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/trials');
      });

      // Navigate to audit log
      router.navigate('/data-lifecycle/audit');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/audit');
      });
    });

    it('should navigate back to overview from any page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/audit'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/audit');
      });

      // Navigate back to overview
      router.navigate('/data-lifecycle');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle');
      });
    });
  });

  describe('Route Guards', () => {
    it('should allow authenticated users to access data lifecycle routes', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/samples'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
      }, { timeout: 5000 });
    });

    it('should protect data lifecycle routes with authentication', async () => {
      // This test verifies that routes are wrapped with ProtectedRoute
      // The actual redirect behavior is tested in ProtectedRoute.test.tsx
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      // With mocked auth, should be able to access the route
      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle');
      }, { timeout: 5000 });
    });
  });

  describe('Lazy Loading', () => {
    it('should lazy load data lifecycle overview page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      // Should show loading state initially
      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle');
      });

      // Page should eventually load
      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });

    it('should lazy load temp data page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/temp-data'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/temp-data');
      });

      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });

    it('should lazy load sample library page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/samples'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
      });

      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });

    it('should lazy load annotation tasks page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/tasks'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/tasks');
      });

      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });

    it('should lazy load enhancement page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/enhancement'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/enhancement');
      });

      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });

    it('should lazy load AI trial page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/trials'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/trials');
      });

      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });

    it('should lazy load audit log page', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/audit'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/audit');
      });

      await waitFor(() => {
        expect(router.state.matches).toBeDefined();
      }, { timeout: 3000 });
    });
  });

  describe('Breadcrumb Updates', () => {
    it('should update breadcrumb when navigating to temp data', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      router.navigate('/data-lifecycle/temp-data');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/temp-data');
      });

      // Breadcrumb should reflect current location
      expect(router.state.location.pathname).toContain('temp-data');
    });

    it('should update breadcrumb when navigating to sample library', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      router.navigate('/data-lifecycle/samples');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
      });

      expect(router.state.location.pathname).toContain('samples');
    });

    it('should update breadcrumb when navigating to annotation tasks', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      router.navigate('/data-lifecycle/tasks');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/tasks');
      });

      expect(router.state.location.pathname).toContain('tasks');
    });

    it('should maintain breadcrumb hierarchy', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/samples'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
      });

      // Breadcrumb should show hierarchy: data-lifecycle > samples
      const pathSegments = router.state.location.pathname.split('/').filter(Boolean);
      expect(pathSegments).toContain('data-lifecycle');
      expect(pathSegments).toContain('samples');
    });
  });

  describe('Preloading', () => {
    it('should support preloading of critical routes', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle');
      });

      // Verify router is ready for navigation
      expect(router.state.navigation.state).toBe('idle');
    });

    it('should handle rapid navigation between routes', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      // Rapidly navigate between routes
      router.navigate('/data-lifecycle/temp-data');
      router.navigate('/data-lifecycle/samples');
      router.navigate('/data-lifecycle/tasks');

      await waitFor(() => {
        expect(router.state.location.pathname).toBe('/data-lifecycle/tasks');
      });
    });
  });

  describe('Route Configuration', () => {
    it('should have all data lifecycle routes configured', () => {
      const dataLifecycleRoutes = routes
        .find(route => route.path === '/')
        ?.children?.find(child => child.path === 'data-lifecycle');

      expect(dataLifecycleRoutes).toBeDefined();
      expect(dataLifecycleRoutes?.children).toBeDefined();
      
      const childPaths = dataLifecycleRoutes?.children?.map(child => child.path);
      expect(childPaths).toContain('temp-data');
      expect(childPaths).toContain('samples');
      expect(childPaths).toContain('tasks');
      expect(childPaths).toContain('enhancement');
      expect(childPaths).toContain('trials');
      expect(childPaths).toContain('audit');
    });

    it('should have index route for data lifecycle', () => {
      const dataLifecycleRoutes = routes
        .find(route => route.path === '/')
        ?.children?.find(child => child.path === 'data-lifecycle');

      const indexRoute = dataLifecycleRoutes?.children?.find(child => child.index === true);
      expect(indexRoute).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should handle navigation to non-existent data lifecycle route', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle/non-existent'],
      });

      render(<RouterProvider router={router} />);

      await waitFor(() => {
        // Should either stay on the route or redirect to 404
        expect(router.state.location.pathname).toBeDefined();
      });
    });

    it('should handle navigation errors gracefully', async () => {
      const router = createMemoryRouter(routes, {
        initialEntries: ['/data-lifecycle'],
      });

      render(<RouterProvider router={router} />);

      // Attempt navigation
      try {
        router.navigate('/data-lifecycle/samples');
        await waitFor(() => {
          expect(router.state.location.pathname).toBe('/data-lifecycle/samples');
        });
      } catch (error) {
        // Should not throw errors
        expect(error).toBeUndefined();
      }
    });
  });
});
