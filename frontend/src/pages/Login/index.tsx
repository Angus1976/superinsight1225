// Login page
import { Card, Typography, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import { Navigate, useLocation } from 'react-router-dom';
import { LoginForm } from '@/components/Auth/LoginForm';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants';
import { isTokenExpired } from '@/utils/token';
import styles from './style.module.scss';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const { t } = useTranslation('auth');
  const { isAuthenticated, token, _hasHydrated } = useAuthStore();
  const location = useLocation();

  // Get the intended destination from location state
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || ROUTES.DASHBOARD;

  // Show loading spinner while store is hydrating
  if (!_hasHydrated) {
    return (
      <div className={styles.container}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  // Redirect if already authenticated with valid token
  if (isAuthenticated && token && !isTokenExpired(token)) {
    return <Navigate to={from} replace />;
  }

  return (
    <div className={styles.container}>
      <Card className={styles.card}>
        <div className={styles.header}>
          <img src="/logo-wenshijian.svg" alt={t('login.logoAlt')} className={styles.logo} />
          <Title level={2} className={styles.title}>
            {t('login.appName')}
          </Title>
          <Text type="secondary">{t('login.subtitle')}</Text>
        </div>
        <LoginForm />
        <div className={styles.footer}>
          <a href={ROUTES.REGISTER}>{t('login.registerLink')}</a>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
