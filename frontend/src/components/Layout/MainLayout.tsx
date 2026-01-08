// Main layout component
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { ProLayout, PageContainer } from '@ant-design/pro-components';
import { Breadcrumb } from 'antd';
import {
  DashboardOutlined,
  OrderedListOutlined,
  DollarOutlined,
  SettingOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  AuditOutlined,
  HomeOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useUIStore } from '@/stores/uiStore';
import { HeaderContent } from './HeaderContent';
import { ROUTES } from '@/constants';
import { useBreadcrumb } from '@/hooks/useBreadcrumb';

const menuItems = [
  {
    path: ROUTES.DASHBOARD,
    name: 'dashboard',
    icon: <DashboardOutlined />,
  },
  {
    path: ROUTES.TASKS,
    name: 'tasks',
    icon: <OrderedListOutlined />,
    children: [
      {
        path: `${ROUTES.TASKS}/list`,
        name: 'taskList',
      },
      {
        path: `${ROUTES.TASKS}/create`,
        name: 'taskCreate',
      },
    ],
  },
  {
    path: ROUTES.AUGMENTATION,
    name: 'augmentation',
    icon: <ThunderboltOutlined />,
    children: [
      {
        path: `${ROUTES.AUGMENTATION}/samples`,
        name: 'samples',
      },
      {
        path: `${ROUTES.AUGMENTATION}/config`,
        name: 'config',
      },
    ],
  },
  {
    path: ROUTES.QUALITY,
    name: 'quality',
    icon: <SafetyCertificateOutlined />,
    children: [
      {
        path: `${ROUTES.QUALITY}/rules`,
        name: 'rules',
      },
      {
        path: `${ROUTES.QUALITY}/reports`,
        name: 'reports',
      },
    ],
  },
  {
    path: ROUTES.BILLING,
    name: 'billing',
    icon: <DollarOutlined />,
    children: [
      {
        path: `${ROUTES.BILLING}/overview`,
        name: 'overview',
      },
      {
        path: `${ROUTES.BILLING}/reports`,
        name: 'reports',
      },
    ],
  },
  {
    path: ROUTES.SECURITY,
    name: 'security',
    icon: <AuditOutlined />,
    access: 'admin',
    children: [
      {
        path: `${ROUTES.SECURITY}/audit`,
        name: 'audit',
      },
      {
        path: `${ROUTES.SECURITY}/permissions`,
        name: 'permissions',
      },
    ],
  },
  {
    path: ROUTES.DATA_SYNC,
    name: 'dataSync',
    icon: <SyncOutlined />,
    children: [
      {
        path: `${ROUTES.DATA_SYNC}/sources`,
        name: 'dataSources',
      },
      {
        path: `${ROUTES.DATA_SYNC}/tasks`,
        name: 'syncTasks',
      },
      {
        path: `${ROUTES.DATA_SYNC}/security`,
        name: 'dataSecurity',
      },
    ],
  },
  {
    path: ROUTES.SETTINGS,
    name: 'settings',
    icon: <SettingOutlined />,
  },
  {
    path: ROUTES.ADMIN,
    name: 'admin',
    icon: <SafetyOutlined />,
    access: 'admin',
    children: [
      {
        path: `${ROUTES.ADMIN}/tenants`,
        name: 'tenants',
      },
      {
        path: `${ROUTES.ADMIN}/users`,
        name: 'users',
      },
      {
        path: `${ROUTES.ADMIN}/system`,
        name: 'system',
      },
    ],
  },
];

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation('common');
  const { user } = useAuthStore();
  const { theme, sidebarCollapsed, toggleSidebar } = useUIStore();
  const { breadcrumbItems, pageTitle } = useBreadcrumb();

  const filteredMenuItems = menuItems.filter((item) => {
    if (item.access === 'admin') {
      return user?.role === 'admin';
    }
    return true;
  });

  // Transform menu items for ProLayout
  const transformMenuItems = (items: typeof menuItems) => {
    return items.map((item) => ({
      ...item,
      name: t(`menu.${item.name}`),
      children: item.children?.map((child) => ({
        ...child,
        name: t(`menu.${child.name}`),
      })),
    }));
  };

  return (
    <ProLayout
      title="SuperInsight"
      logo="/logo.svg"
      navTheme={theme === 'dark' ? 'realDark' : 'light'}
      layout="mix"
      splitMenus={false}
      fixedHeader
      fixSiderbar
      collapsed={sidebarCollapsed}
      onCollapse={toggleSidebar}
      location={{ pathname: location.pathname }}
      route={{
        path: '/',
        routes: transformMenuItems(filteredMenuItems),
      }}
      menuItemRender={(item, dom) => (
        <div onClick={() => item.path && navigate(item.path)}>{dom}</div>
      )}
      headerContentRender={() => <HeaderContent />}
      breadcrumbRender={(routers = []) => [
        {
          path: '/',
          breadcrumbName: t('menu.dashboard'),
          icon: <HomeOutlined />,
        },
        ...breadcrumbItems,
      ]}
      pageTitleRender={() => pageTitle}
      contentStyle={{
        padding: 0,
        minHeight: 'calc(100vh - 56px)',
      }}
    >
      <PageContainer
        header={{
          title: pageTitle,
          breadcrumb: {
            items: [
              {
                path: '/',
                title: (
                  <span>
                    <HomeOutlined />
                    <span style={{ marginLeft: 8 }}>{t('menu.dashboard')}</span>
                  </span>
                ),
              },
              ...breadcrumbItems,
            ],
          },
        }}
        content={
          <div style={{ marginBottom: 16 }}>
            {/* Page description can be added here */}
          </div>
        }
      >
        <Outlet />
      </PageContainer>
    </ProLayout>
  );
};
