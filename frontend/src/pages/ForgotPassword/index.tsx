// Forgot password page
import { Card, Typography } from 'antd';
import { Navigate, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ForgotPasswordForm } from '@/components/Auth/ForgotPasswordForm';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants';
import styles from '../Login/style.module.scss';

const { Title } = Typography;

const ForgotPasswordPage: React.FC = () => {
  const { t } = useTranslation('auth');
  const { isAuthenticated, token } = useAuthStore();
  const navigate = useNavigate();
  const [isChecking, setIsChecking] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsChecking(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // Show loading while checking authentication
  if (isChecking) {
    return null;
  }

  // Redirect if already authenticated
  if (isAuthenticated && token) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  const handleBack = () => {
    navigate(ROUTES.LOGIN);
  };

  return (
    <div className={styles.container}>
      <Card className={styles.card}>
        <div className={styles.header}>
          <img src="/logo.svg" alt={t('login.logoAlt')} className={styles.logo} />
          <Title level={2} className={styles.title}>
            {t('login.appName')}
          </Title>
        </div>
        <ForgotPasswordForm onBack={handleBack} />
      </Card>
    </div>
  );
};

export default ForgotPasswordPage;
