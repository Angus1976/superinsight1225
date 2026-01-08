// Breadcrumb hook for navigation
import { useMemo } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ROUTES } from '@/constants';

interface BreadcrumbItem {
  path?: string;
  title: string;
}

export const useBreadcrumb = () => {
  const location = useLocation();
  const params = useParams();
  const { t } = useTranslation('common');

  const { breadcrumbItems, pageTitle } = useMemo(() => {
    const pathname = location.pathname;
    const segments = pathname.split('/').filter(Boolean);
    
    let items: BreadcrumbItem[] = [];
    let title = t('menu.dashboard');

    // Dashboard
    if (pathname === ROUTES.DASHBOARD || pathname === '/') {
      title = t('menu.dashboard');
      items = [];
    }
    // Tasks
    else if (pathname.startsWith('/tasks')) {
      items.push({ title: t('menu.tasks'), path: ROUTES.TASKS });
      
      if (segments.length === 1) {
        title = t('menu.tasks');
      } else if (segments[1] === 'create') {
        title = t('tasks.create');
        items.push({ title: t('tasks.create') });
      } else if (params.id) {
        if (pathname.includes('/annotate')) {
          title = t('tasks.annotate');
          items.push({ title: t('tasks.detail'), path: `/tasks/${params.id}` });
          items.push({ title: t('tasks.annotate') });
        } else {
          title = t('tasks.detail');
          items.push({ title: t('tasks.detail') });
        }
      }
    }
    // Billing
    else if (pathname.startsWith('/billing')) {
      items.push({ title: t('menu.billing'), path: ROUTES.BILLING });
      title = t('menu.billing');
      
      if (segments[1] === 'reports') {
        title = t('billing.reports');
        items.push({ title: t('billing.reports') });
      }
    }
    // Augmentation
    else if (pathname.startsWith('/augmentation')) {
      items.push({ title: t('menu.augmentation'), path: ROUTES.AUGMENTATION });
      title = t('menu.augmentation');
      
      if (segments[1] === 'samples') {
        title = t('augmentation.samples');
        items.push({ title: t('augmentation.samples') });
      } else if (segments[1] === 'config') {
        title = t('augmentation.config');
        items.push({ title: t('augmentation.config') });
      }
    }
    // Quality
    else if (pathname.startsWith('/quality')) {
      items.push({ title: t('menu.quality'), path: ROUTES.QUALITY });
      title = t('menu.quality');
      
      if (segments[1] === 'rules') {
        title = t('quality.rules');
        items.push({ title: t('quality.rules') });
      } else if (segments[1] === 'reports') {
        title = t('quality.reports');
        items.push({ title: t('quality.reports') });
      }
    }
    // Security
    else if (pathname.startsWith('/security')) {
      items.push({ title: t('menu.security'), path: ROUTES.SECURITY });
      title = t('menu.security');
      
      if (segments[1] === 'audit') {
        title = t('security.audit');
        items.push({ title: t('security.audit') });
      } else if (segments[1] === 'permissions') {
        title = t('security.permissions');
        items.push({ title: t('security.permissions') });
      }
    }
    // Settings
    else if (pathname.startsWith('/settings')) {
      items.push({ title: t('menu.settings'), path: ROUTES.SETTINGS });
      title = t('menu.settings');
    }
    // Admin
    else if (pathname.startsWith('/admin')) {
      items.push({ title: t('menu.admin'), path: ROUTES.ADMIN });
      title = t('menu.admin');
      
      if (segments[1] === 'tenants') {
        title = t('admin.tenants');
        items.push({ title: t('admin.tenants') });
      } else if (segments[1] === 'users') {
        title = t('admin.users');
        items.push({ title: t('admin.users') });
      } else if (segments[1] === 'system') {
        title = t('admin.system');
        items.push({ title: t('admin.system') });
      }
    }

    return { breadcrumbItems: items, pageTitle: title };
  }, [location.pathname, params, t]);

  return { breadcrumbItems, pageTitle };
};