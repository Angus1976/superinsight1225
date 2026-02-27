// Main layout component
import { useMemo } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { ProLayout, PageContainer } from '@ant-design/pro-components';
import { HomeOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useUIStore } from '@/stores/uiStore';
import { HeaderContent } from './HeaderContent';
import { ClientBranding } from './ClientBranding';
import { SidebarMenuItem } from './SidebarGroupHeader';
import { LayoutFooter } from './LayoutFooter';
import { LogoIcon } from '@/components/Brand/LogoIcon';
import { NAV_GROUPS, buildMenuRoutes } from '@/config/navGroups';
import { ROUTES } from '@/constants';
import { useBreadcrumb } from '@/hooks/useBreadcrumb';

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation('common');
  const { user } = useAuthStore();
  const { theme, sidebarCollapsed, toggleSidebar } = useUIStore();
  const { breadcrumbItems, pageTitle } = useBreadcrumb();

  const routes = useMemo(
    () => buildMenuRoutes(NAV_GROUPS, user?.role ?? 'user', t),
    [user?.role, t],
  );

  return (
    <ProLayout
      title="问视间"
      logo={<LogoIcon size={28} />}
      navTheme={theme === 'dark' ? 'realDark' : 'light'}
      layout="mix"
      splitMenus={false}
      fixedHeader
      fixSiderbar
      collapsed={sidebarCollapsed}
      onCollapse={toggleSidebar}
      location={{ pathname: location.pathname }}
      route={{ path: '/', routes }}
      token={{
        sider: {
          colorMenuBackground: 'transparent',
          colorMenuItemDivider: 'transparent',
          colorTextMenuSelected: '#1890ff',
          colorBgMenuItemSelected: 'transparent',
          colorBgMenuItemHover: 'transparent',
          colorTextMenuItemHover: '#1890ff',
          colorBgMenuItemActive: 'transparent',
        },
      }}
      menuHeaderRender={() => <ClientBranding collapsed={sidebarCollapsed} />}
      menuItemRender={(item, dom) => (
        <SidebarMenuItem
          item={item}
          dom={dom}
          collapsed={sidebarCollapsed}
          isActive={
            location.pathname === item.path ||
            location.pathname.startsWith(item.path + '/')
          }
          onNavigate={navigate}
        />
      )}
      headerContentRender={() => <HeaderContent />}
      footerRender={() => <LayoutFooter collapsed={sidebarCollapsed} />}
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
