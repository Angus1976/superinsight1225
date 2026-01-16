// Reset password page
import { Card, Typography } from 'antd';
import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ResetPasswordForm } from '@/components/Auth/ResetPasswordForm';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants';
import styles from '../Login/style.module.scss';

const { Title } = Typography;

const ResetPasswordPage: React.FC = () => {
  const { t } = useTranslation('auth');
  const { isAuthenticated } = useAuthStore();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return (
    <div className={styles.container}>
      <Card className={styles.card}>
        <div className={styles.header}>
          <img src="/logo.svg" alt={t('login.logoAlt')} className={styles.logo} />
          <Title level={2} className={styles.title}>
            {t('login.appName')}
          </Title>
        </div>
        <ResetPasswordForm />
      </Card>
    </div>
  );
};

export default ResetPasswordPage;
