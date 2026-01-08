// Forgot password page
import { Card, Typography } from 'antd';
import { Navigate, useNavigate } from 'react-router-dom';
import { ForgotPasswordForm } from '@/components/Auth/ForgotPasswordForm';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants';
import styles from '../Login/style.module.scss';

const { Title } = Typography;

const ForgotPasswordPage: React.FC = () => {
  const { isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  const handleBack = () => {
    navigate(ROUTES.LOGIN);
  };

  return (
    <div className={styles.container}>
      <Card className={styles.card}>
        <div className={styles.header}>
          <img src="/logo.svg" alt="SuperInsight" className={styles.logo} />
          <Title level={2} className={styles.title}>
            SuperInsight
          </Title>
        </div>
        <ForgotPasswordForm onBack={handleBack} />
      </Card>
    </div>
  );
};

export default ForgotPasswordPage;