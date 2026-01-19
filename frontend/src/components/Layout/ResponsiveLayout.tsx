// Responsive layout wrapper
import { useState, useMemo, ReactNode } from 'react';
import { Drawer, Button } from 'antd';
import { MenuOutlined, CloseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useResponsive } from '@/hooks/useResponsive';
import styles from './ResponsiveLayout.module.scss';

interface ResponsiveLayoutProps {
  children: ReactNode;
  siderContent: ReactNode;
  headerContent: ReactNode;
  logo?: ReactNode;
  title?: string;
}

export const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({
  children,
  siderContent,
  headerContent,
  logo,
  title,
}) => {
  const { t } = useTranslation('common');
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);
  const { isMobile, isTablet, isDesktop } = useResponsive();

  const displayTitle = title || t('appName');

  // Handler for closing mobile menu
  const handleCloseMobileMenu = () => {
    setMobileMenuVisible(false);
  };

  // Handler for opening mobile menu
  const handleOpenMobileMenu = () => {
    setMobileMenuVisible(true);
  };

  // Automatically close menu when on desktop (computed value)
  const shouldShowMenu = useMemo(() => {
    // Don't show menu on desktop regardless of state
    if (isDesktop) return false;
    return mobileMenuVisible;
  }, [isDesktop, mobileMenuVisible]);

  // Mobile layout
  if (isMobile) {
    return (
      <div className={styles.mobileLayout}>
        {/* Mobile Header */}
        <header className={styles.mobileHeader}>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={handleOpenMobileMenu}
            className={styles.menuButton}
            aria-label={t('layout.openMenu')}
          />
          <div className={styles.mobileTitle}>
            {logo && <span className={styles.mobileLogo}>{logo}</span>}
            <strong>{displayTitle}</strong>
          </div>
          <div className={styles.mobileHeaderContent}>{headerContent}</div>
        </header>

        {/* Mobile Content */}
        <main className={styles.mobileContent}>
          {children}
        </main>

        {/* Mobile Menu Drawer */}
        <Drawer
          title={
            <div className={styles.drawerTitle}>
              {logo && <span className={styles.drawerLogo}>{logo}</span>}
              <span>{displayTitle}</span>
            </div>
          }
          placement="left"
          onClose={handleCloseMobileMenu}
          open={shouldShowMenu}
          width={280}
          className={styles.mobileDrawer}
          closeIcon={<CloseOutlined />}
          styles={{
            body: { padding: 0 },
            header: { borderBottom: '1px solid #f0f0f0' },
          }}
        >
          {siderContent}
        </Drawer>
      </div>
    );
  }

  // Tablet layout
  if (isTablet) {
    return (
      <div className={styles.tabletLayout}>
        {/* Tablet Header */}
        <header className={styles.tabletHeader}>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={handleOpenMobileMenu}
            className={styles.menuButton}
            aria-label={t('layout.openMenu')}
          />
          <div className={styles.tabletTitle}>
            {logo && <span className={styles.tabletLogo}>{logo}</span>}
            <strong>{displayTitle}</strong>
          </div>
          <div className={styles.tabletHeaderContent}>{headerContent}</div>
        </header>

        {/* Tablet Content */}
        <main className={styles.tabletContent}>
          {children}
        </main>

        {/* Tablet Menu Drawer */}
        <Drawer
          title={
            <div className={styles.drawerTitle}>
              {logo && <span className={styles.drawerLogo}>{logo}</span>}
              <span>{displayTitle}</span>
            </div>
          }
          placement="left"
          onClose={handleCloseMobileMenu}
          open={shouldShowMenu}
          width={300}
          className={styles.tabletDrawer}
          closeIcon={<CloseOutlined />}
          styles={{
            body: { padding: 0 },
            header: { borderBottom: '1px solid #f0f0f0' },
          }}
        >
          {siderContent}
        </Drawer>
      </div>
    );
  }

  // Desktop layout - return children as-is (handled by ProLayout)
  return <>{children}</>;
};