// Responsive layout wrapper
import { useState, useEffect } from 'react';
import { Drawer, Button } from 'antd';
import { MenuOutlined } from '@ant-design/icons';
import { useUIStore } from '@/stores/uiStore';

interface ResponsiveLayoutProps {
  children: React.ReactNode;
  siderContent: React.ReactNode;
  headerContent: React.ReactNode;
}

export const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({
  children,
  siderContent,
  headerContent,
}) => {
  const [isMobile, setIsMobile] = useState(false);
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);
  const { sidebarCollapsed } = useUIStore();

  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkIsMobile();
    window.addEventListener('resize', checkIsMobile);
    return () => window.removeEventListener('resize', checkIsMobile);
  }, []);

  if (isMobile) {
    return (
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Mobile Header */}
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 16px',
            borderBottom: '1px solid #f0f0f0',
            background: '#fff',
          }}
        >
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setMobileMenuVisible(true)}
          />
          <div style={{ flex: 1, textAlign: 'center' }}>
            <strong>SuperInsight</strong>
          </div>
          <div>{headerContent}</div>
        </div>

        {/* Mobile Content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>

        {/* Mobile Menu Drawer */}
        <Drawer
          title="导航菜单"
          placement="left"
          onClose={() => setMobileMenuVisible(false)}
          open={mobileMenuVisible}
          width={280}
          bodyStyle={{ padding: 0 }}
        >
          {siderContent}
        </Drawer>
      </div>
    );
  }

  // Desktop layout - return children as-is
  return <>{children}</>;
};