// Login page
import { Card, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { LoginForm } from '@/components/Auth/LoginForm';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants';
import styles from './style.module.scss';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const { t } = useTranslation('auth');
  const { isAuthenticated, token } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    // Give a small delay to ensure store is properly hydrated
    const timer = setTimeout(() => {
      setIsChecking(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // Show loading while checking authentication
  if (isChecking) {
    return null; // or a loading spinner
  }

  // Redirect if already authenticated
  if (isAuthenticated && token) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return (
    <div className={styles.container}>
      <Card className={styles.card}>
        <div className={styles.header}>
          <img src="/logo-wenshijian.svg" alt="问视间" className={styles.logo} />
          <Title level={2} className={styles.title}>
            问视间
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
