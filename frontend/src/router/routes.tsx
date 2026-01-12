// Route configuration with optimized lazy loading for < 3s page load
import { lazy, Suspense, ComponentType } from 'react';
import type { RouteObject } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import { MainLayout } from '@/components/Layout/MainLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { Loading } from '@/components/Common/Loading';
import { SkeletonLoader } from '@/components/Common/SkeletonLoader';
import { ROUTES } from '@/constants';

/**
 * Enhanced lazy loading with preload support
 * Allows prefetching of route chunks for faster navigation
 */
type LazyComponent = ComponentType<unknown> & { preload?: () => Promise<{ default: ComponentType<unknown> }> };

function lazyWithPreload<T extends ComponentType<unknown>>(
  factory: () => Promise<{ default: T }>
): LazyComponent {
  const Component = lazy(factory) as LazyComponent;
  Component.preload = factory;
  return Component;
}

// Lazy load pages with preload support
// Critical path pages (login, dashboard) are prioritized
const LoginPage = lazyWithPreload(() => import('@/pages/Login'));
const RegisterPage = lazyWithPreload(() => import('@/pages/Register'));
const ForgotPasswordPage = lazyWithPreload(() => import('@/pages/ForgotPassword'));
const ResetPasswordPage = lazyWithPreload(() => import('@/pages/ResetPassword'));
const DashboardPage = lazyWithPreload(() => import('@/pages/Dashboard'));
const TasksPage = lazyWithPreload(() => import('@/pages/Tasks'));
const TaskDetailPage = lazyWithPreload(() => import('@/pages/Tasks/TaskDetail'));
const TaskAnnotatePage = lazyWithPreload(() => import('@/pages/Tasks/TaskAnnotate'));
const BillingPage = lazyWithPreload(() => import('@/pages/Billing'));
const SettingsPage = lazyWithPreload(() => import('@/pages/Settings'));
const AdminPage = lazyWithPreload(() => import('@/pages/Admin'));
const AugmentationPage = lazyWithPreload(() => import('@/pages/Augmentation'));
const QualityPage = lazyWithPreload(() => import('@/pages/Quality'));
const SecurityPage = lazyWithPreload(() => import('@/pages/Security'));
const DataSyncPage = lazyWithPreload(() => import('@/pages/DataSync'));
const NotFoundPage = lazyWithPreload(() => import('@/pages/Error/404'));
const ForbiddenPage = lazyWithPreload(() => import('@/pages/Error/403'));
const ServerErrorPage = lazyWithPreload(() => import('@/pages/Error/500'));

/**
 * Preload critical routes after initial page load
 * This improves subsequent navigation performance
 */
export function preloadCriticalRoutes(): void {
  // Use requestIdleCallback for non-blocking preload
  const preload = () => {
    // Preload dashboard first (most common destination after login)
    DashboardPage.preload?.();
    
    // Then preload other frequently accessed pages
    setTimeout(() => {
      TasksPage.preload?.();
      BillingPage.preload?.();
    }, 1000);
  };

  if ('requestIdleCallback' in window) {
    requestIdleCallback(preload, { timeout: 3000 });
  } else {
    setTimeout(preload, 2000);
  }
}

// Skeleton type mapping for different routes
type SkeletonType = 'page' | 'dashboard' | 'table' | 'form' | 'list';

const routeSkeletonMap: Record<string, SkeletonType> = {
  dashboard: 'dashboard',
  tasks: 'table',
  billing: 'table',
  settings: 'form',
  admin: 'table',
  quality: 'dashboard',
  security: 'table',
  'data-sync': 'table',
};

/**
 * Enhanced Suspense wrapper with route-specific skeleton
 */
const withSuspense = (Component: ComponentType, skeletonType: SkeletonType = 'page') => (
  <Suspense fallback={<SkeletonLoader type={skeletonType} />}>
    <Component />
  </Suspense>
);

/**
 * Minimal loading for auth pages (faster perceived load)
 */
const withMinimalSuspense = (Component: ComponentType) => (
  <Suspense fallback={<Loading />}>
    <Component />
  </Suspense>
);

export const routes: RouteObject[] = [
  {
    path: ROUTES.LOGIN,
    element: withMinimalSuspense(LoginPage),
  },
  {
    path: ROUTES.REGISTER,
    element: withMinimalSuspense(RegisterPage),
  },
  {
    path: ROUTES.FORGOT_PASSWORD,
    element: withMinimalSuspense(ForgotPasswordPage),
  },
  {
    path: ROUTES.RESET_PASSWORD,
    element: withMinimalSuspense(ResetPasswordPage),
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to={ROUTES.DASHBOARD} replace />,
      },
      {
        path: 'dashboard',
        element: withSuspense(DashboardPage, 'dashboard'),
      },
      {
        path: 'tasks',
        element: withSuspense(TasksPage, 'table'),
      },
      {
        path: 'tasks/:id',
        element: withSuspense(TaskDetailPage, 'page'),
      },
      {
        path: 'tasks/:id/annotate',
        element: withSuspense(TaskAnnotatePage, 'page'),
      },
      {
        path: 'billing',
        element: withSuspense(BillingPage, 'table'),
      },
      {
        path: 'settings',
        element: withSuspense(SettingsPage, 'form'),
      },
      {
        path: 'admin',
        element: withSuspense(AdminPage, 'table'),
      },
      {
        path: 'augmentation',
        element: withSuspense(AugmentationPage, 'page'),
      },
      {
        path: 'quality',
        element: withSuspense(QualityPage, 'dashboard'),
      },
      {
        path: 'security',
        element: withSuspense(SecurityPage, 'table'),
      },
      {
        path: 'data-sync',
        element: withSuspense(DataSyncPage, 'table'),
      },
    ],
  },
  {
    path: ROUTES.FORBIDDEN,
    element: withMinimalSuspense(ForbiddenPage),
  },
  {
    path: ROUTES.SERVER_ERROR,
    element: withMinimalSuspense(ServerErrorPage),
  },
  {
    path: '*',
    element: withMinimalSuspense(NotFoundPage),
  },
];
