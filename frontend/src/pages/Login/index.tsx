// Login page — redesigned with animated background and social login placeholders
import { Card, Typography, Spin, Tooltip } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { Navigate, useLocation } from 'react-router-dom';
import { LoginForm } from '@/components/Auth/LoginForm';
import { LogoFull } from '@/components/Brand/LogoFull';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants';
import { isTokenExpired } from '@/utils/token';
import styles from './style.module.scss';

const { Text } = Typography;

const LoginPage: React.FC = () => {
  const { t } = useTranslation('auth');
  const { isAuthenticated, token, _hasHydrated } = useAuthStore();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || ROUTES.DASHBOARD;

  if (!_hasHydrated) {
    return (
      <div className={styles.container}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  if (isAuthenticated && token && !isTokenExpired(token)) {
    return <Navigate to={from} replace />;
  }

  return (
    <div className={styles.container}>
      {/* Animated gradient blobs — pure CSS */}
      <div className={styles.blobs}>
        <div className={`${styles.blob} ${styles.blob1}`} />
        <div className={`${styles.blob} ${styles.blob2}`} />
        <div className={`${styles.blob} ${styles.blob3}`} />
        <div className={`${styles.blob} ${styles.blob4}`} />
      </div>

      <Card className={styles.card}>
        <div className={styles.header}>
          <LogoFull height={40} className={styles.logoFull} />
          <Text type="secondary">{t('login.subtitle')}</Text>
        </div>

        <LoginForm />

        {/* Social login placeholders */}
        <div className={styles.divider}>{t('login.socialDivider', 'Or continue with')}</div>
        <div className={styles.socialButtons}>
          <Tooltip title={t('login.comingSoon', 'Coming Soon')}>
            <button type="button" className={styles.socialBtn} disabled>
              <SafetyCertificateOutlined />
              {t('login.enterpriseSSO', 'Enterprise SSO')}
            </button>
          </Tooltip>
        </div>

        <div className={styles.footer}>
          <a href={ROUTES.REGISTER}>{t('login.registerLink')}</a>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
