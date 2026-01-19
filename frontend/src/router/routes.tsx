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
type LazyComponent = ComponentType<any> & { preload?: () => Promise<{ default: ComponentType<any> }> };

function lazyWithPreload(
  factory: () => Promise<{ default: ComponentType<any> }>
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
const TaskEditPage = lazyWithPreload(() => import('@/pages/Tasks/TaskEdit'));
const TaskAnnotatePage = lazyWithPreload(() => import('@/pages/Tasks/TaskAnnotate'));
const BillingPage = lazyWithPreload(() => import('@/pages/Billing'));
const SettingsPage = lazyWithPreload(() => import('@/pages/Settings'));
const AdminPage = lazyWithPreload(() => import('@/pages/Admin'));

// Augmentation pages
const AugmentationPage = lazyWithPreload(() => import('@/pages/Augmentation'));
const AugmentationSamplesPage = lazyWithPreload(() => import('@/pages/Augmentation/Samples'));
const AugmentationConfigPage = lazyWithPreload(() => import('@/pages/Augmentation/Config'));

// Quality pages
const QualityPage = lazyWithPreload(() => import('@/pages/Quality'));
const QualityRulesPage = lazyWithPreload(() => import('@/pages/Quality/Rules'));
const QualityReportsPage = lazyWithPreload(() => import('@/pages/Quality/Reports'));
const QualityImprovementTaskListPage = lazyWithPreload(() => import('@/pages/Quality/ImprovementTaskList'));
const QualityImprovementTaskDetailPage = lazyWithPreload(() => import('@/pages/Quality/ImprovementTaskDetail'));

// License pages
const LicensePage = lazyWithPreload(() => import('@/pages/License'));
const LicenseActivatePage = lazyWithPreload(() => import('@/pages/License/ActivationWizard'));
const LicenseUsagePage = lazyWithPreload(() => import('@/pages/License/UsageMonitor'));
const LicenseReportPage = lazyWithPreload(() => import('@/pages/License/LicenseReport'));
const LicenseAlertsPage = lazyWithPreload(() => import('@/pages/License/AlertConfig'));

// Security pages
const SecurityPage = lazyWithPreload(() => import('@/pages/Security'));
const SecurityAuditPage = lazyWithPreload(() => import('@/pages/Security/Audit'));
const SecurityPermissionsPage = lazyWithPreload(() => import('@/pages/Security/Permissions'));

// Data Sync pages
const DataSyncPage = lazyWithPreload(() => import('@/pages/DataSync'));
const DataSyncSourcesPage = lazyWithPreload(() => import('@/pages/DataSync/Sources'));
const DataSyncSecurityPage = lazyWithPreload(() => import('@/pages/DataSync/Security'));

// Admin pages
const AdminConsolePage = lazyWithPreload(() => import('@/pages/Admin/Console'));
const AdminTenantsPage = lazyWithPreload(() => import('@/pages/Admin/Tenants'));
const AdminUsersPage = lazyWithPreload(() => import('@/pages/Admin/Users'));
const AdminSystemPage = lazyWithPreload(() => import('@/pages/Admin/System'));
const AdminLLMConfigPage = lazyWithPreload(() => import('@/pages/Admin/LLMConfig'));
const AdminTextToSQLConfigPage = lazyWithPreload(() => import('@/pages/Admin/TextToSQLConfig'));
const AdminPermissionConfigPage = lazyWithPreload(() => import('@/pages/Admin/PermissionConfig'));
const AdminQuotaManagementPage = lazyWithPreload(() => import('@/pages/Admin/QuotaManagement'));
const AdminBillingManagementPage = lazyWithPreload(() => import('@/pages/Admin/BillingManagement'));

// Admin Configuration pages (new admin-configuration module)
const AdminConfigDashboardPage = lazyWithPreload(() => import('@/pages/Admin/ConfigDashboard'));
const AdminConfigLLMPage = lazyWithPreload(() => import('@/pages/Admin/ConfigLLM'));
const AdminConfigDBPage = lazyWithPreload(() => import('@/pages/Admin/ConfigDB'));
const AdminConfigSyncPage = lazyWithPreload(() => import('@/pages/Admin/ConfigSync'));
const AdminSQLBuilderPage = lazyWithPreload(() => import('@/pages/Admin/SQLBuilder'));
const AdminConfigHistoryPage = lazyWithPreload(() => import('@/pages/Admin/ConfigHistory'));
const AdminThirdPartyConfigPage = lazyWithPreload(() => import('@/pages/Admin/ThirdPartyConfig'));

// Workspace pages
const WorkspaceManagementPage = lazyWithPreload(() => import('@/pages/Workspace/WorkspaceManagement'));
const MemberManagementPage = lazyWithPreload(() => import('@/pages/Workspace/MemberManagement'));

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
        path: 'tasks/:id/edit',
        element: withSuspense(TaskEditPage, 'form'),
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
        children: [
          {
            path: 'console',
            element: withSuspense(AdminConsolePage, 'dashboard'),
          },
          {
            path: 'tenants',
            element: withSuspense(AdminTenantsPage, 'table'),
          },
          {
            path: 'workspaces',
            element: withSuspense(WorkspaceManagementPage, 'table'),
          },
          {
            path: 'members',
            element: withSuspense(MemberManagementPage, 'table'),
          },
          {
            path: 'permissions',
            element: withSuspense(AdminPermissionConfigPage, 'table'),
          },
          {
            path: 'quotas',
            element: withSuspense(AdminQuotaManagementPage, 'table'),
          },
          {
            path: 'billing',
            element: withSuspense(AdminBillingManagementPage, 'table'),
          },
          {
            path: 'users',
            element: withSuspense(AdminUsersPage, 'table'),
          },
          {
            path: 'system',
            element: withSuspense(AdminSystemPage, 'form'),
          },
          {
            path: 'llm-config',
            element: withSuspense(AdminLLMConfigPage, 'form'),
          },
          {
            path: 'text-to-sql',
            element: withSuspense(AdminTextToSQLConfigPage, 'form'),
          },
          // Admin Configuration Module Routes
          {
            path: 'config',
            element: withSuspense(AdminConfigDashboardPage, 'dashboard'),
          },
          {
            path: 'config/llm',
            element: withSuspense(AdminConfigLLMPage, 'table'),
          },
          {
            path: 'config/databases',
            element: withSuspense(AdminConfigDBPage, 'table'),
          },
          {
            path: 'config/sync',
            element: withSuspense(AdminConfigSyncPage, 'table'),
          },
          {
            path: 'config/sql-builder',
            element: withSuspense(AdminSQLBuilderPage, 'form'),
          },
          {
            path: 'config/history',
            element: withSuspense(AdminConfigHistoryPage, 'table'),
          },
          {
            path: 'config/third-party',
            element: withSuspense(AdminThirdPartyConfigPage, 'table'),
          },
        ],
      },
      {
        path: 'augmentation',
        element: withSuspense(AugmentationPage, 'page'),
        children: [
          {
            path: 'samples',
            element: withSuspense(AugmentationSamplesPage, 'table'),
          },
          {
            path: 'config',
            element: withSuspense(AugmentationConfigPage, 'form'),
          },
        ],
      },
      {
        path: 'quality',
        element: withSuspense(QualityPage, 'dashboard'),
        children: [
          {
            path: 'rules',
            element: withSuspense(QualityRulesPage, 'table'),
          },
          {
            path: 'reports',
            element: withSuspense(QualityReportsPage, 'dashboard'),
          },
          {
            path: 'workflow/tasks',
            element: withSuspense(QualityImprovementTaskListPage, 'table'),
          },
          {
            path: 'workflow/tasks/:taskId',
            element: withSuspense(QualityImprovementTaskDetailPage, 'page'),
          },
        ],
      },
      {
        path: 'license',
        element: withSuspense(LicensePage, 'dashboard'),
      },
      {
        path: 'license/activate',
        element: withSuspense(LicenseActivatePage, 'form'),
      },
      {
        path: 'license/usage',
        element: withSuspense(LicenseUsagePage, 'dashboard'),
      },
      {
        path: 'license/report',
        element: withSuspense(LicenseReportPage, 'table'),
      },
      {
        path: 'license/alerts',
        element: withSuspense(LicenseAlertsPage, 'form'),
      },
      {
        path: 'security',
        element: withSuspense(SecurityPage, 'table'),
        children: [
          {
            path: 'audit',
            element: withSuspense(SecurityAuditPage, 'table'),
          },
          {
            path: 'permissions',
            element: withSuspense(SecurityPermissionsPage, 'table'),
          },
        ],
      },
      {
        path: 'data-sync',
        element: withSuspense(DataSyncPage, 'table'),
        children: [
          {
            path: 'sources',
            element: withSuspense(DataSyncSourcesPage, 'table'),
          },
          {
            path: 'security',
            element: withSuspense(DataSyncSecurityPage, 'form'),
          },
        ],
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
